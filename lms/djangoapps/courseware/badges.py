import json
import os
import urllib2
import hashlib

def make_badge_data(request, course=None):
    """
    Returns a dictionary:
        earned_badges -- a list of dictionaries; each dictionary has information about a badge
        unlockable_badgeclasses -- a list of dictionaries; each dictionary has information about an unearned badgeclass
        badge_urls -- a list of urls, each url has badge JSON, the urls are sent to Open Badging to export badges
    """

    # TODO: Update this with the URL of the badge service once deployed.
    badge_service_url = 'http://18.189.90.17:8002'

    # Should use a recipient id that is a unique encryption of the student's email, not the email itself.
    # This is important for preventing scraping of email addresses from badge service.
    email = request.user.email
    recipient_id = hashlib.sha256(email).hexdigest()

    def read(url):
        """
        Reads the JSON object located at a URL. Returns the Python representation of the JSON object.
        Prints an error message if unsuccessful.
        """
        try:
            f = urllib2.urlopen(url)
            return json.loads(f.read())
        except:
            return []

    badges_url = os.path.join(badge_service_url, 'badges/.json?recipient_id=' + recipient_id)

    if course is not None:
        suffix = "&course=" + course.id
        unlockable_badgeclasses_url = os.path.join(badge_service_url, 'badgeclasses/?format=json' + suffix)

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
