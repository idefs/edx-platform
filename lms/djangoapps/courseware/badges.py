"""
Contains the function make_badge_data, responsible for getting badge data from the badge service.
"""

import json
import os
import urllib2
import hashlib

from django.conf import settings

def make_badge_data(request, course=None):
    """
    Returns a dictionary:
        earned_badges -- a list of dictionaries; each dictionary has information about a badge
        unlockable_badgeclasses -- a list of dictionaries; each dictionary has information about an unearned badgeclass
        badge_urls -- a list of urls, each url has badge JSON, the urls are sent to Open Badging to export badges
    """

    # Use a recipient id that is a unique encryption of the student's email, not the email itself.
    # This is important for preventing scraping of email addresses from badge service.
    email = request.user.email
    recipient_id = hashlib.sha256(email).hexdigest()

    def read(url):
        """
        Reads the JSON object located at a URL. Returns the Python representation of the JSON object.

        If the fetched JSON object is paginated -- with the next url at 'next' and the content at 'results' --
        this reads through all of the pages, and compiles the results together into one list.

        Prints an error message if unsuccessful.
        """
        try:
            f = urllib2.urlopen(url)
            obj = json.loads(f.read())

            results = obj.get('results', None)

            if results is not None:
                next_url = obj.get('next', None)

                while next_url is not None:
                    next_f = urllib2.urlopen(next_url)
                    next_obj = json.loads(next_f)
                    results.extend(next_obj.get('results', []))
                    next_url = obj.get('next', None)

                return results

            else:
                return obj

        except:
            print "Badge service failing? URL not found -- %s" % str(url)
            return []

    badges_url = os.path.join(settings.BADGE_SERVICE_URL, 'badges/.json?recipient_id=' + recipient_id)

    if course is not None:
        suffix = "&course=" + course.id
        unlockable_badgeclasses_url = os.path.join(settings.BADGE_SERVICE_URL, 'badgeclasses/?format=json' + suffix)

        unlockable_badgeclasses = read(unlockable_badgeclasses_url)

        # Use unlockable_badgeclasses to get earned badges by recipient & badgeclass.
        earned_badges_lists = [
            read(badges_url + '&badgeclass=' + str(badgeclass.get('id', None)))
            for badgeclass in unlockable_badgeclasses
        ]

        # Flatten the list and filter out any revoked badges.
        earned_badges = [
            badge
            for badge_list in earned_badges_lists
            for badge in badge_list
            if not badge.get('revoked', False)
        ]

        # Filter out any already-earned badges from the list of unlockable badgeclasses.
        earned_badgeclass_urls = [
            earned_badge.get('badgeclass', '')
            for earned_badge in earned_badges
        ]
        unlockable_badgeclasses = [
            badgeclass
            for badgeclass in unlockable_badgeclasses
            if not badgeclass.get('id', '') in earned_badgeclass_urls
        ]

        # Filter out any not-enabled badgeclasses from the list of unlockable badgeclasses.
        unlockable_badgeclasses = [
            badgeclass
            for badgeclass in unlockable_badgeclasses
            if badgeclass.get('is_enabled', True)
        ]

    else:
        unlockable_badgeclasses = []

        # Flatten the list and filter out any revoked badges.
        earned_badges = read(badges_url)
        earned_badges = [
            badge
            for badge in earned_badges
            if not badge.get('revoked', False)
        ]

    # Get the list of URLs to access to export badges to Mozilla.
    badge_urls = [
        earned_badge['url']
        for earned_badge in earned_badges
        if 'url' in earned_badge
    ]

    # Replace the field 'badge' in earned_badges, which is a URL, with the content of that URL.
    # ... and also the field 'issuer' in _that_ content, which is a URL, with the content of that URL.
    for badge in earned_badges:
        badge.update({
            'badge': read(badge.get('badge'))
        })
        badge['badge'].update({
            'issuer': read(badge['badge'].get('issuer'))
        })

    output = {
        'earned_badges': earned_badges,
        'unlockable_badgeclasses': unlockable_badgeclasses,
        'badge_urls': json.dumps(badge_urls),
    }

    return output
