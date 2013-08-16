"""
Contains the function make_badge_data, responsible for getting badge data from the badge service.
"""

import json
import requests

from django.conf import settings


def make_badge_data(request, course=None):
    """
    Returns a dictionary:
        'earned_badges': a list of dictionaries; each dictionary has information about a badge
        'unlockable_badgeclasses': a list of dictionaries; each dictionary has information about an unearned badgeclass
        'badge_urls': a list of urls, each url has badge JSON, the urls are sent to Open Badging to export badges
    """

    email = request.user.email

    def read(url):
        """
        Reads the JSON object located at a relative URL. Returns the Python representation of the JSON object.

        If the fetched JSON object is paginated -- with the next url at 'next' and the content at 'results' --
        this reads through all of the pages, and compiles the results together into one list.

        Prints an error message if unsuccessful.
        """
        if not settings.BADGE_SERVICE_URL in url:
            url = settings.BADGE_SERVICE_URL + url

        try:
            obj = requests.get(url).json

            results = obj.get('results', None)

            if results is not None:
                next_url = obj.get('next', None)

                while next_url is not None:
                    next_obj = request.get(next_url).json
                    results.extend(next_obj.get('results', []))
                    next_url = obj.get('next', None)

                return results

            else:
                return obj

        except Exception as e:
            print e
            print "Badge service failing? URL not found -- %s" % str(url)
            return []


    if course is not None:

        earned_badges = read('badges/.json?badgeclass__issuer__course=%(course)s&email=%(email)s' %
            {'course': course.id, 'email': email})

        unlockable_badgeclasses = read('badgeclasses/.json?issuer__course=%(course)s' % {'course': course.id})

        # Filter out any already-earned badges from the list of unlockable badgeclasses.
        earned_badgeclass_urls = [
            earned_badge.get('badge', '')
            for earned_badge in earned_badges
        ]

        unlockable_badgeclasses = [
            badgeclass
            for badgeclass in unlockable_badgeclasses
            if not badgeclass.get('href', '') in earned_badgeclass_urls
        ]

    else:
        badges_url = 'badges/.json?email=%s' % email
        unlockable_badgeclasses = []
        earned_badges = read(badges_url)


    # Get the list of URLs to access to export badges to Mozilla.
    badge_urls = [
        earned_badge['href']
        for earned_badge in earned_badges
        if 'href' in earned_badge
    ]

    # Remove duplicate badges from earned_badges. It looks really silly to have two of the same exact badge.
    new_earned_badges = []
    new_earned_badgeclasses = []
    for badge in earned_badges:
        if not badge['badgeclass'] in new_earned_badgeclasses:
            new_earned_badges.append(badge)
            new_earned_badgeclasses.append(badge['badgeclass'])
            print "Added: "+str(badge)

    earned_badges = new_earned_badges

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
