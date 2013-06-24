"""
Django models used to store and manipulate content tests
"""

from django.db import models
from xmodule.modulestore.django import modulestore
from xmodule.modulestore import Location
from contentstore.views.preview import get_preview_module
from mitxmako.shortcuts import render_to_string  # pylint: disable=F0401
from lxml import etree
from copy import deepcopy
from difflib import SequenceMatcher
import pickle
# pylint: disable=E1101


def hash_xml(tree):
    """
    create a hash of the etree xml element solely based on 'meaningful' parts of the xml string
    """
    tree = deepcopy(tree)
    remove_ids(tree, (lambda k: k[-2:] == 'id' or k == 'size'))
    return etree.tostring(tree).__hash__()


def remove_ids(tree, should_be_removed):
    """
    remove all keys for which `should_be_removed(attrib)` returns true
    """
    for attrib in tree.attrib:
        if should_be_removed(attrib):
            tree.attrib.pop(attrib)

    # do the same to all the children
    for child in tree:
        remove_ids(child, should_be_removed)


def hash_xml_structure(tree):
    """
    create hash of xml that ignores all attributes except ones involving `id`
    """
    tree = deepcopy(tree)
    remove_ids(tree, (lambda k: True))
    return etree.tostring(tree).__hash__()


def condense_attributes(tree):
    """
    take an XML tree and collect all `meaningful` attributes into single dict
    """

    tree = deepcopy(tree)
    remove_ids(tree, (lambda k: k[-2:] == 'id' or k == 'size'))
    attrib = tree.attrib

    # add in childrens attributes
    for child in tree:
        attrib.update(condense_attributes(child))

    return attrib


def remove_xml_wrapper(tree, name):
    """
    Remove all elements by the name of `name` in `tree` but keep
    any children by inserting them into the location of `name`.

    Return a new tree.

    Accepts either lxml.etree.Element objects or strings.
    """

    # we want to return the same type we were given
    tree = deepcopy(tree)
    return_string = False
    if isinstance(tree, basestring):
        tree = etree.XML(tree)
        return_string = True

    for item in tree.iterfind('.//'+name):
        # reverse children for inserting
        children = [elts for elts in item]
        children.reverse()

        # index for insertion
        index = item.getparent().index(item)

        # insert the form contents
        for child in children:
            item.getparent().insert(index, child)

        # remove item
        item.getparent().remove(item)

    # return a string if that is what we were given
    if return_string:
        tree = etree.tostring(tree)

    return tree


def condense_dict(dictionary):
    """
    returns a string ondensation of the dictionary for %% comparison purposes.

    {'tree': 3, 'apple': 'hello'} -> 'tree3applehello'
    """

    return ''.join([attribute for sublist in [(lambda x: [str(k) for k in x])(item) for item in dictionary.items()] for attribute in sublist])


def closeness(model, responder):
    """
    Return a value between 0 and ~1 representing how good a match these two are.
    0 = Terribad.  1 = identical. 1.01 = identical in original location.
    """

    # no match if the structure is different
    if model.structure_hash != hash_xml_structure(responder.xml):
        return 0

    # almost all the xml will be the same since they have the same structure anyway.
    # Thus, we look at just the attributes that are meaningful
    model_xml = etree.XML(model.xml_string)
    resp_xml = responder.xml

    model_string = condense_dict(condense_attributes(model_xml))
    responder_string = condense_dict(condense_attributes(resp_xml))

    # use difflib to calculate string closeness
    seq = SequenceMatcher(None, model_string, responder_string)
    ratio = seq.ratio()

    # favor matches that are in the same location (this might need tweaking!!)
    if model.string_id == responder.id:
        ratio = 1.01 * (1 - (1 - ratio) ** (1.2))
    return ratio


class ContentTest(models.Model):
    """
    Model for a user-created test for a capa-problem
    """

    # the problem to test (location)
    # future-proof against long locations?
    problem_location = models.CharField(max_length=100, db_index=True)

    # what the problem should evaluate as (correct or incorrect)
    should_be = models.CharField(max_length=20, db_index=True)

    # the current state of the test
    verdict = models.TextField()

    # pickle of dictionary that is the stored input
    response_dict = models.TextField()

    # messeges for verdict
    ERROR = "ERROR"
    PASS = "Pass"
    FAIL = "Fail"
    NONE = "Not Run"

    def __init__(self, *arg, **kwargs):
        """
        Overwrite default __init__ behavior to pickle the dictionary and
            save in a new field so we know if the response_dict gets overwritten
        """

        if 'response_dict' not in kwargs:
            kwargs['response_dict'] = {}

        kwargs['response_dict'] = pickle.dumps(kwargs['response_dict'])
        super(ContentTest, self).__init__(*arg, **kwargs)

        # store the old dict for later comparison (only update if it is changed)
        self._old_response_dict = self.response_dict

        # set the default to be checking for updates to the capa problem
        self.check_for_updates = True

    @property
    def capa_problem(self):
        """
        create the capa_problem.  In teh process override the render_html methods of the
        response objects for the purpose of inserting html into the problem.  This is for
        the possible future feature of specifying verdict-per-response.
        """

        # create a preview capa problem
        lcp = self.capa_module().lcp

        # override html methods
        # for key in lcp.responders:

        #     # define wrapper
        #     def wrapper(func):
        #         def html_wrapper(*args, **kwargs):

        #             # make surrounding div for each response
        #             div = etree.Element('div')
        #             div.set('class', "verdict-response-wrapper")

        #             # should_be choice for this response
        #             buttons = etree.fromstring(self._should_be_buttons(self.should_be))

        #             div.append(func(*args, **kwargs))
        #             div.append(buttons)
        #             return div

        #         return html_wrapper

        #     # execute the override
        #     lcp.responders[key].render_html = wrapper(lcp.responders[key].render_html)
        return lcp

    def capa_module(self):
        """
        resturns a preview instance of the capa module pointed to by
        self.problem_location
        """
        # if we are checking for updates, refetch from mongo, else return saved version
        if self.check_for_updates:
            return self.construct_preview_module()
        else:
            if not hasattr(self, 'module'):
                self.module = self.construct_preview_module()

        return self.module

    def construct_preview_module(self):
        """
        construct a new preview capa module
        """
        # create a preview of the capa_module
        problem_descriptor = modulestore().get_item(Location(self.problem_location))
        preview_module = get_preview_module(0, problem_descriptor)

        # edit the module to have the correct test-student-responses
        # and (in the future support randomization)
        new_lcp_state = preview_module.get_state_for_lcp()  # pylint: disable=E1103
        new_lcp_state['student_answers'] = self._get_response_dictionary()
        preview_module.lcp = preview_module.new_lcp(new_lcp_state)  # pylint: disable=E1103

        return preview_module

    def save(self, *arg, **kwargs):
        """
        Overwrite default save behavior with the following features:
            > If the children haven't been created, create them
            > If the response dictionary is being changed, update the children
        """

        # if we are changing something, reset verdict by default
        if not('dont_reset' in kwargs):
            self.verdict = self.NONE
        else:
            kwargs.pop('dont_reset')

        # if we have a dictionary
        if hasattr(self, 'response_dict'):
            #if it isn't pickled, pickle it.
            if not(isinstance(self.response_dict, basestring)):
                self.response_dict = pickle.dumps(self.response_dict)

                # if it is new, update children
                if self.response_dict != self._old_response_dict:
                    self._update_dictionary(pickle.loads(self.response_dict))

        # save it as normal
        super(ContentTest, self).save(*arg, **kwargs)

        # look for children
        children = Response.objects.filter(content_test=self.pk)

        # if there are none, try to create them
        if children.count() == 0:
            self._create_children()

    def run(self):
        """
        run the test, and see if it passes
        """

        # process dictionary that is the response from grading
        grade_dict = self._evaluate(self._get_response_dictionary())

        # compare the result with what is should be
        self.verdict = self._make_verdict(grade_dict)

        # write the change to the database and return the result
        self.save(dont_reset=True)
        return self.verdict

    def get_html_summary(self):
        """
        return an html summary of this test
        """
        # check for changes to the capa_problem
        self.rematch_if_necessary()

        # retrieve all inputs sorted first by response, and then by order in that response
        sorted_inputs = self.input_set.order_by('response_index', 'input_index').values('answer')  # pylint: disable=E1101
        answers = [input_model['answer'] or '-- Not Set --' for input_model in sorted_inputs]

        # construct a context for rendering this
        context = {'answers': answers, 'verdict': self.verdict, 'should_be': self.should_be}
        return render_to_string('content_testing/unit_summary.html', context)

    def get_html_form(self):
        """
        return html to put into form for editing and creating
        """
        # check for changes to the capa_problem
        self.rematch_if_necessary()

        # html with the inputs blank
        html_form = self.capa_problem.get_html()

        # remove form tags
        html_form = remove_xml_wrapper(html_form, 'form')

        # add the radio buttons
        html_form = html_form + self._should_be_buttons(self.should_be)
        return html_form

    def rematch_if_necessary(self):
        """
        Rematches itself to its problem if it no longer matches.
        Reassigns hashes to response models if they no longer
        match but the structure still does (so future matching
        can happen).
        """

        # if this contentTest has not been saved, no need to check
        if self.pk is None:
            return

        for model in self.response_set.all():
            model.content_test = self

        # tell it not to check for for updates to the capa problem
        self.check_for_updates = False

        try:
            if not self._still_matches():
                self._rematch()
            else:
                self._reassign_hashes_if_necessary()
        except:
            raise

        finally:
            # Now that we are done, turn checking back on
            self.check_for_updates = True
            del self.module

#======= Private Methods =======#

    def _still_matches(self):
        """
        Returns true if the test still corresponds to the structure of the
        problem
        """

        # if there are no longer the same number, not a match.
        if not(self.response_set.count() == len(self.capa_problem.responders)):  # pylint: disable=E1101
            return False

        # loop through response models, and check that they match
        all_match = True
        for resp_model in self.response_set.all():  # pylint: disable=E1101
            if not resp_model.still_matches():
                all_match = False
                break

        return all_match

    def _reassign_hashes_if_necessary(self):
        """
        Iterate through the response models, and rematch their
        xml_string and xml_hashes if they have changed in the capa problem
        """

        for model in self.response_set.all():
            model.rematch(model.capa_response)

    def _rematch(self):
        """
        corrects structure to reflect the state of the capa problem
        """

        resp_models = list(self.response_set.all())  # pylint: disable=E1101

        self._fuzzy_rematch(resp_models, self.capa_problem.responders.values())

        # remake the dictionary
        self._remake_dict_from_children()

    def _fuzzy_rematch(self, unmatched_models, unmatched_responders):
        """
        Out of the list of unmatched objects, make only the matches that
        are above a certain closeness threshold.

        unmatched_models is a list of the response models involved in the
        potential matches
        [obj1, obj2, ...]

        unmatched_responders is a list of the responders involved in the
        potential matches
        [obj1, obj2, ...]
        """

        # how desperate are we to make matches?
        cutoff = 0.92

        # make a list of triples of all possible matches and their closeness value
        potential_matches = [(closeness(model, responder), model, responder) for model in unmatched_models for responder in unmatched_responders]

        # sort matches, then start applying them
        potential_matches.sort()
        while potential_matches:
            match = potential_matches.pop()

            # interpret the tuple
            percent_match = match[0]
            model = match[1]
            responder = match[2]

            # if it is not good enought of a match, just stop
            if percent_match < cutoff:
                break

            # only make the match if neither object has been matched
            elif (model in unmatched_models) and (responder in unmatched_responders):

                # make the match and mark as used
                model.rematch(responder)
                unmatched_models.remove(model)
                unmatched_responders.remove(responder)

        # delete unused models
        for model in unmatched_models:
            model.delete()

        # create new models for unmatched responders
        for responder in unmatched_responders:
            self._create_child(responder)

    def _reassign_hashes(self):
        """
        tell all children to reassign their hashes
        """

        for resp_model in self.response_set.all():  # pylint: disable=E1101
            resp_model.reassign_hashes()

    def _should_be_buttons(self, resp_should_be):
        """
        given an individual should_be, generate the appropriate radio buttons
        """

        # default to filling in the correct bubble
        context = {
            "check_correct": "checked=\"True\"",
            "check_incorrect": "",
            "check_error": ""
        }

        if resp_should_be.lower() == "incorrect":
            context = {
                "check_correct": "",
                "check_incorrect": "checked=\"True\"",
                "check_error": ""
            }
        elif resp_should_be.lower() == "error":
            context = {
                "check_correct": "",
                "check_incorrect": "",
                "check_error": "checked=\"True\""
            }

        return render_to_string('content_testing/form_bottom.html', context)

    def _evaluate(self, response_dict):
        """
        Give the capa_problem the response dictionary and return the result
        """

        # instantiate the capa problem so it can grade itself
        capa = self.capa_problem

        try:
            correct_map = capa.grade_answers(response_dict)
            return correct_map.get_dict()

        # if there is any error, we just return None
        except Exception:  # pylint: disable=W0703
            return None

    def _make_verdict(self, grade_dict):
        """
        compare what the result of the grading should be with the actual grading
        and return the verdict
        """

        # if there was an error
        if grade_dict is None:
            # if we want error, return pass
            if self.should_be == self.ERROR:
                return self.PASS
            return self.ERROR

        # see that they all are the expected value (if not blank)
        passing = True
        for string_id, grade in grade_dict.iteritems():
            # check it is not blank
            input_model = self.input_set.get(string_id=string_id)
            if input_model.answer != '':
                # make sure it is what it should be
                if grade['correctness'] != self.should_be.lower():
                    passing = False

        if passing:
            return self.PASS
        else:
            return self.FAIL

    def _get_response_dictionary(self):
        """
        create dictionary to be submitted to the grading function
        """

        # assume integrity has been maintained!!
        resp_dict = self.response_dict

        # unpickle if necessary
        if isinstance(resp_dict, basestring):
            resp_dict = pickle.loads(resp_dict)

        return resp_dict

    def _remake_dict_from_children(self):
        """
        build the response dictionary by getting the values from the children
        """

        # refetch the answers from all the children
        resp_dict = {}
        for input_model in self.input_set.all():  # pylint: disable=E1101
            resp_dict[input_model.string_id] = input_model.answer

        # update the dictionary
        self.response_dict = resp_dict
        self.save()

    def _create_children(self):
        """
        create child responses and input entries
        """
        # create a preview capa problem
        problem_capa = self.capa_problem

        # go through responder objects
        for responder in problem_capa.responders.itervalues():
            self._create_child(responder, self._get_response_dictionary())

    def _create_child(self, responder, response_dict=dict()):
        """
        from a responder object, create the associated child response model
        """

        # put the response object in the database
        response_model = Response.objects.create(
            content_test=self,
            xml_hash=hash_xml(responder.xml),
            string_id=responder.id,
            structure_hash=hash_xml_structure(responder.xml),
            xml_string=etree.tostring(responder.xml))

        # tell it to put its children in the database
        response_model.create_children(responder, response_dict)

    def _update_dictionary(self, new_dict):
        """
        update the input models with the new responses
        """

        # for resp_model in self.response_set.all():
        for input_model in self.input_set.all():  # pylint: disable=E1101
            input_model.answer = new_dict[input_model.string_id]
            input_model.save()


class Response(models.Model):
    """
    Object that corresponds to the <_____response> fields
    """
    # the tests in which this response resides
    content_test = models.ForeignKey(ContentTest, db_index=True)

    # the string identifier
    string_id = models.CharField(max_length=100)

    # hash of the xml for mathcing purposes
    xml_hash = models.BigIntegerField()

    # hash without any attribute
    structure_hash = models.BigIntegerField()

    # xml description of the response
    xml_string = models.TextField()

    def rematch(self, responder):
        """
        reassociates the ids with this new responder object.
        If the hashes match, then all that needs
        changing are the ids. If not, we recalculate hashes.
        (It is assumed that structure_hash's match).
        """

        # if the ids and hashes match, we are done
        if self.string_id == responder.id:
            if self.xml_hash == hash_xml(responder.xml):
                return

            # if just the hashes don't match,
            # only update the response model
            # (not the children)
            else:
                self.xml_string = etree.tostring(responder.xml)
                self.xml_hash = hash_xml(responder.xml)
                self.save()
                return

        # The id's don't match, so we re-associate them
        self.string_id = responder.id

        # rematch xml if necessary
        if self.xml_hash != hash_xml(responder.xml):
            self.xml_string = etree.tostring(responder.xml)
            self.xml_hash = hash_xml(responder.xml)

        # rematch all the childrens ids
        input_models = self.input_set.order_by('input_index')  # pylint: disable=E1101
        for input_field, input_model in zip(responder.inputfields, input_models):

            # reassign the other ids
            input_model.response_index = input_field.attrib['response_id']
            input_model.string_id = input_field.attrib['id']

            # save the result
            input_model.save()
        self.save()

    def create_children(self, resp_obj=None, response_dict={}):
        """
        generate the database entries for the inputs to this response
        """

        # see if we need to construct the object from database
        if resp_obj is None:
            resp_obj = self.capa_response

        # go through inputs in this response object
        for entry in resp_obj.inputfields:
            # create the input models
            Input.objects.create(
                response=self,
                content_test=self.content_test,
                string_id=entry.attrib['id'],
                response_index=entry.attrib['response_id'],
                input_index=entry.attrib['answer_id'],
                answer=response_dict.get(entry.attrib['id'], ''))

    @property
    def capa_response(self):
        """
        get the capa-response object to which this response model corresponds
        """

        parent_capa = self.content_test.capa_problem  # pylint: disable=E1101
        self_capa = parent_capa.responders_by_id[self.string_id]

        return self_capa

    def still_matches(self):
        """
        check that the model has the same structure as corresponding responder object
        """

        try:
            return self.structure_hash == hash_xml_structure(self.capa_response.xml)
        except KeyError:
            return False


class Input(models.Model):
    """
    the input to a Response
    """

    # The response in which this input lives
    response = models.ForeignKey(Response, db_index=True)

    # The test in which this input resides (grandchild)
    content_test = models.ForeignKey(ContentTest, db_index=True)

    # sequence (first response field, second, etc)
    string_id = models.CharField(max_length=100, editable=False)

    # number for the response that this input is in
    response_index = models.PositiveSmallIntegerField()

    # number for the place this input is in the response
    input_index = models.PositiveSmallIntegerField()

    # the input, supposed a string
    answer = models.CharField(max_length=50, blank=True)
