"""
WE'RE USING MIGRATIONS!

If you make changes to this model, be sure to create an appropriate migration
file and check it in at the same time as your model changes. To do that,

1. Go to the edx-platform dir
2. ./manage.py schemamigration bulk_email --auto description_of_your_change
3. Add the migration file created in edx-platform/lms/djangoapps/bulk_email/migrations/


"""
import logging
from django.db import models
from django.contrib.auth.models import User

log = logging.getLogger(__name__)


class Email(models.Model):
    """
    Abstract base class for common information for an email.
    """
    sender = models.ForeignKey(User, default=1, blank=True, null=True)
    hash = models.CharField(max_length=128, db_index=True)
    subject = models.CharField(max_length=128, blank=True)
    html_message = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CourseEmail(Email, models.Model):
    """
    Stores information for an email to a course.
    """
    TO_OPTIONS = (('myself', 'Myself'),
                  ('staff', 'Staff and instructors'),
                  ('all', 'All')
                  )
    course_id = models.CharField(max_length=255, db_index=True)
    to = models.CharField(max_length=64, choices=TO_OPTIONS, default='myself')

    def __unicode__(self):
        return self.subject


class Optout(models.Model):
    """
    Stores emails that have opted out of receiving emails from a course.
    """
    email = models.CharField(max_length=255, db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        unique_together = ('email', 'course_id')

# Defines the tag that must appear in a template, to indicate
# the location where the email message body is to be inserted.
COURSE_EMAIL_MESSAGE_BODY_TAG = '{{message_body}}'


class CourseEmailTemplate(models.Model):
    """
    Stores templates for all emails to a course to use.

    This is expected to be a singleton, to be shared across all courses.
    Initialization takes place in a migration that in turn loads a fixture.
    The admin console interface disables add and delete operations.
    Validation is handled in the CourseEmailTemplateForm class.
    """
    html_template = models.TextField(null=True, blank=True)
    plain_template = models.TextField(null=True, blank=True)

    @staticmethod
    def get_template():
        """
        Fetch the current template

        If one isn't stored, an exception is thrown.
        """
        return CourseEmailTemplate.objects.get()

    @staticmethod
    def _render(format_string, message_body, context):
        """
        TODO
        """
        # DON'T insert user's text into template, until such time we can support
        # proper error handling due to errors in the message body (e.g. due to
        # the use of curly braces).  If we wanted to, we'd call:
        # format_string = format_string.replace(COURSE_EMAIL_MESSAGE_BODY_TAG, message_body)
        result = format_string.format(**context)
        # Instead, for now, we insert the message body *after* the substitutions
        # have been performed, so that anything in the message body that might
        # interfere will be innocently returned.  Note that the body tag in
        # the template will now have been "formatted", so we need to do the
        # same to the tag being searched for.
        message_body_tag = COURSE_EMAIL_MESSAGE_BODY_TAG.format()
        result = result.replace(message_body_tag, message_body, 1)
        return result.encode('utf-8')

    def render_plaintext(self, plaintext, context):
        """
        TODO
        """
        return CourseEmailTemplate._render(self.plain_template, plaintext, context)

    def render_htmltext(self, htmltext, context):
        """
        TODO
        """
        return CourseEmailTemplate._render(self.html_template, htmltext, context)
