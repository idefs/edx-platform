
# Imports #####################################################################

import logging
import stripe

from django.conf import settings
from django.utils.translation import ugettext as _

from coupons.models import Coupon, UserBillingProfile
from courseware.access import has_access
from student.models import CourseEnrollment
from student.views import course_from_id


# Globals #####################################################################

log = logging.getLogger("coupons")
stripe.api_key = settings.STRIPE_KEY_SECRET


# Functions ###################################################################

def pay_with_token(user, course_id, payment_token, coupon_name=''):
    course = course_from_id(course_id)
    price = Coupon.objects.get_price_with_coupon(course_id, coupon_name)
    error_msg = ''
    coupon = None
    try:
        coupon = Coupon.objects.get(coupon_name__iexact=coupon_name)
    except Coupon.DoesNotExist:
        pass

    if not has_access(user, course, 'enroll'):
        error_msg = _("Enrollment is closed")
    if price['value']:
        if not payment_token:
            error_msg = _("Payment required")
        if not create_or_update_customer(user, payment_token):
            error_msg = _("Error during registration with payment provider")
        if not apply_payment_to_customer(user, course_id, coupon_name=coupon_name):
            error_msg = _("Payment denied")

    if not error_msg:
        enrollment = CourseEnrollment.enroll(user, course_id)
        if coupon is not None:
            enrollment.coupon = coupon
            enrollment.save()

    return error_msg

def get_billing_profile(user):
    billing_profile, created = UserBillingProfile.objects.get_or_create(user=user)
    return billing_profile

def get_customer_id(user):
    billing_profile = get_billing_profile(user)
    return billing_profile.stripe_customer_id

def create_or_update_customer(user, payment_token):
    if get_customer_id(user):
        return update_customer(user, payment_token)
    else:
        return create_customer(user, payment_token)

def create_customer(user, payment_token):
    billing_profile = get_billing_profile(user)
    try:
        customer = stripe.Customer.create(description=user.profile.name,
                                          email=user.email,
                                          card=payment_token)
    except stripe.StripeError as e:
        log.exception(e)
        return False
    else:
        billing_profile.stripe_customer_id = customer.id
        billing_profile.save()
        return True

def update_customer(user, payment_token):
    customer_id = get_customer_id(user)
    try:
        customer = stripe.Customer.retrieve(customer_id)
        customer.description = user.profile.name
        customer.email = user.email
        customer.card = payment_token
        customer.save()
    except stripe.StripeError as e:
        log.exception(e)
        return False
    else:
        return True

def apply_payment_to_customer(user, course_id, coupon_name=''):
    price = Coupon.objects.get_price_with_coupon(course_id, coupon_name)
    description = '{},{}'.format(user.email, course_id)
    if coupon_name:
        description += ',coupon={}'.format(coupon_name)
    try:
        stripe.Charge.create(
            amount=price['value']*100,
            currency=price['currency'].lower(),
            customer=get_customer_id(user),
            description=description
        )
        return True
    except stripe.CardError:
        return False


