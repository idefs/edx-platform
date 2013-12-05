"""
Allow to use discount codes for payment, using Stripe
"""

# Imports #####################################################################

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from collections import namedtuple

from course_modes.models import CourseMode


# Constants ###################################################################

Mode = namedtuple('Mode', ['slug', 'name', 'min_price', 'suggested_prices', 'currency'])


# Functions ###################################################################

def get_base_price_for_course_id(course_id):
    modes = CourseMode.modes_for_course_dict(course_id)
    if 'pay_with_coupon' in modes:
        mode = modes['pay_with_coupon']
        return {
            'value': mode.min_price,
            'currency': mode.currency
        }
    else:
        return {
            'value': 0,
            'currency': None
        }


# Models ######################################################################

class CouponManager(models.Manager):
    def get_price_with_coupon(self, course_id, coupon_name):
        coupon_name = coupon_name.strip()
        try:
            coupon = Coupon.objects.get(coupon_name__iexact=coupon_name)
        except Coupon.DoesNotExist:
            return get_base_price_for_course_id(course_id)
        else:
            return coupon.get_price_with_coupon(course_id)


class Coupon(models.Model):
    """
    Discount coupon which can be redeemed by users when paying for a course which
    has the mode 'pay_with_coupon'
    """
    objects = CouponManager()

    # the coupon name the user will have to enter to get the reduction
    coupon_name = models.CharField(max_length=100, unique=True)

    # price reduction that the coupon grants, in currency
    price_reduction = models.IntegerField(default=0)

    # the currency these prices are in, using lower case ISO currency codes
    currency = models.CharField(default="usd", max_length=8)

    # Number of times the coupon can be used (default = 0/infinite)
    valid_nb_times = models.IntegerField(default=0)

    # Date until which the coupon can be used (default = None/always)
    valid_until = models.DateTimeField(null=True)

    # Course on which the coupon can be applied (default = ''/all)
    valid_course_id = models.CharField(max_length=100, blank=True)

    def get_price_with_coupon(self, course_id):
        """
        Returns the price with the coupon applied

        Only applies if it uses the same currency, as we don't support currency conversion yet
        """
        price = get_base_price_for_course_id(course_id)
        nb_uses = self.courseenrollment_set.count()
        if price['currency'].lower() == self.currency.lower() and \
                (not self.valid_nb_times or nb_uses < self.valid_nb_times) and \
                (not self.valid_until or timezone.now() <= self.valid_until) and \
                (not self.valid_course_id or self.valid_course_id == course_id):
            price['value'] -= self.price_reduction

        # Coupon can make the course free
        if price['value'] <= 0:
            price['value'] = 0

        return price

    def __unicode__(self):
        return u"{} : reduction={}, currency={}".format(
            self.coupon_name, self.price_reduction, self.currency
        )


class UserBillingProfile(models.Model):
    """
    Student account details related to billing
    """
    user = models.ForeignKey(User, db_index=True, related_name='billing_profile', unique=True)
    stripe_customer_id = models.CharField(blank=True, max_length=30)
    last_changed_at = models.DateTimeField(auto_now=True)




