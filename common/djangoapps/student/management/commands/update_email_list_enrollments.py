##
## One-off script to sync all user information to the user email list & groups according to enrollment


from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from student.views import courses_list_subscribe, update_courses_list_subscriptions


class Command(BaseCommand):
    help = \
'''
Sync all user ids, usernames, and emails to the discussion
service'''

    def handle(self, *args, **options):
        for user in User.objects.all().iterator():
            courses_list_subscribe(user)
            update_courses_list_subscriptions(user)
