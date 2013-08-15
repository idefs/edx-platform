import copy
from xblock.core import Scope
from collections import namedtuple
from xblock.runtime import InvalidScopeError
from .definition_lazy_loader import DefinitionLazyLoader
from xmodule.modulestore.inheritance import InheritanceKeyValueStore

# id is a BlockUsageLocator, def_id is the definition's guid
SplitMongoKVSid = namedtuple('SplitMongoKVSid', 'id, def_id')


class SplitMongoKVS(InheritanceKeyValueStore):
    """
    A KeyValueStore that maps keyed data access to one of the 3 data areas
    known to the MongoModuleStore (data, children, and metadata)
    """

    def __init__(self, definition, fields, inherited_settings, location, category):
        """

        :param definition: either a lazyloader or definition id for the definition
        :param fields: a dictionary of the locally set fields
        :param inherited_settings: the value of each inheritable field from above this.
            Note, local fields may override and disagree w/ this b/c this says what the value
            should be if the field is undefined.
        """
        super(SplitMongoKVS, self).__init__(copy.copy(fields), inherited_settings)
        self._definition = definition  # either a DefinitionLazyLoader or the db id of the definition.
        # if the db id, then the definition is presumed to be loaded into _fields

        self._location = location
        self._category = category

    def get(self, key):
        # simplest case, field is directly set
        if key.field_name in self._fields:
            return self._fields[key.field_name]

        # parent undefined in editing runtime (I think)
        if key.scope == Scope.parent:
            # see STUD-624. Right now copies MongoKeyValueStore.get's behavior of returning None
            return None
        if key.scope == Scope.children:
            # didn't find children in _fields; so, see if there's a default
            raise KeyError()
        elif key.scope == Scope.settings:
            # didn't find in _fields; so, get from inheritance since not locally set
            if key.field_name in self.inherited_settings:
                return self.inherited_settings[key.field_name]
            else:
                # or get default
                raise KeyError()
        elif key.scope == Scope.content:
            if key.field_name == 'location':
                return self._location
            elif key.field_name == 'category':
                return self._category
            elif isinstance(self._definition, DefinitionLazyLoader):
                self._load_definition()
                if key.field_name in self._fields:
                    return self._fields[key.field_name]

            raise KeyError()
        else:
            raise InvalidScopeError(key.scope)

    def set(self, key, value):
        # handle any special cases
        if key.scope not in [Scope.children, Scope.settings, Scope.content]:
            raise InvalidScopeError(key.scope)
        if key.scope == Scope.content:
            if key.field_name == 'location':
                self._location = value  # is changing this legal?
                return
            elif key.field_name == 'category':
                # TODO should this raise an exception? category is not changeable.
                return
            else:
                self._load_definition()

        # set the field
        self._fields[key.field_name] = value

        # handle any side effects -- story STUD-624
        # if key.scope == Scope.children:
            # STUD-624 remove inheritance from any exchildren
            # STUD-624 add inheritance to any new children
        # if key.scope == Scope.settings:
            # STUD-624 if inheritable, push down to children

    def delete(self, key):
        # handle any special cases
        if key.scope not in [Scope.children, Scope.settings, Scope.content]:
            raise InvalidScopeError(key.scope)
        if key.scope == Scope.content:
            if key.field_name == 'location':
                return  # noop
            elif key.field_name == 'category':
                # TODO should this raise an exception? category is not deleteable.
                return  # noop
            else:
                self._load_definition()

        # delete the field value
        if key.field_name in self._fields:
            del self._fields[key.field_name]

        # handle any side effects
        # if key.scope == Scope.children:
            # STUD-624 remove inheritance from any exchildren
        # if key.scope == Scope.settings:
            # STUD-624 if inheritable, push down _inherited_settings value to children

    def has(self, key):
        """
        Is the given field explicitly set in this kvs (not inherited nor default)
        """
        # handle any special cases
        if key.scope == Scope.content:
            if key.field_name == 'location':
                return True
            elif key.field_name == 'category':
                return self._category is not None
            else:
                self._load_definition()
        elif key.scope == Scope.parent:
            return True

        # it's not clear whether inherited values should return True. Right now they don't
        # if someone changes it so that they do, then change any tests of field.name in xx._model_data
        return key.field_name in self._fields

    def field_value_provenance(self, key):
        """
        Where the field value comes from: one of ['local', 'default', 'inherited'].
        """
        # I had the return values in constants but kept getting circular import dependencies. Do we have
        # a std safe place for such constants?
        # handle any special cases
        if key.scope == Scope.content:
            if key.name == 'location':
                return 'local'
            elif key.name == 'category':
                return 'local'
            else:
                self._load_definition()
                if key.name in self._fields:
                    return 'local'
                else:
                    return 'default'
        elif key.scope == Scope.parent:
            return 'default'
        # catch the locally set state
        elif key.name in self._fields:
            return 'local'
        elif key.scope == Scope.settings and key.name in self.inherited_settings:
            return 'inherited'
        else:
            return 'default'

    def _load_definition(self):
        """
        Update fields w/ the lazily loaded definitions
        """
        if isinstance(self._definition, DefinitionLazyLoader):
            persisted_definition = self._definition.fetch()
            if persisted_definition is not None:
                self._fields.update(persisted_definition.get('fields'))
                # do we want to cache any of the edit_info?
            self._definition = None  # already loaded
