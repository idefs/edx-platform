
# Imports #####################################################################

import datetime
import json
from mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils.timezone import utc

from coupons.models import Coupon, get_base_price_for_course_id
from coupons.views import CouponCheckoutView, price_with_coupon
from course_modes.models import CourseMode
from student.tests.factories import CourseEnrollmentFactory


# Classes #####################################################################

class CouponTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.course_id = 'Test/Course/Test'
        self.mode, created = self.create_mode('pay_with_coupon', 'Pay with coupon', min_price=100, currency='usd')
        self.coupon_name = 'test-coupon'
        self.coupon, created = self.create_coupon(self.coupon_name, 25)

        self.user = User.objects.create_user('test', 'test@example.com', 'test')
        self.client.login(username='test', password='test')

    def create_mode(self, mode_slug, mode_name, min_price=0, suggested_prices='', currency='usd',
                          course_id=None):
        if course_id is None:
            course_id = self.course_id

        return CourseMode.objects.get_or_create(
            course_id=course_id,
            mode_display_name=mode_name,
            mode_slug=mode_slug,
            min_price=min_price,
            suggested_prices=suggested_prices,
            currency=currency
        )

    def create_coupon(self, coupon_name, price_reduction, **kwargs):
        return Coupon.objects.get_or_create(
            coupon_name=coupon_name,
            price_reduction=price_reduction,
            **kwargs
        )

    def test_get_base_price_for_course_id(self):
        self.assertEqual(get_base_price_for_course_id(self.course_id), {
            'value': 100,
            'currency': 'usd'
        })

    def test_get_price_with_coupon(self):
        self.assertEqual(self.coupon.get_price_with_coupon(self.course_id), {
            'value': 75,
            'currency': 'usd'
        })
        self.assertEqual(Coupon.objects.get_price_with_coupon(self.course_id, self.coupon_name), {
            'value': 75,
            'currency': 'usd'
        })

    def test_get_price_with_coupon_different_currencies(self):
        """
        Should not return a reduced price when the currencies are different
        """
        coupon, created = self.create_coupon('test-coupon2', 25, currency='eur')
        self.assertEqual(coupon.get_price_with_coupon(self.course_id), {
            'value': 100,
            'currency': 'usd'
        })

    def test_get_price_with_coupon_valid_nb_times(self):
        """
        Should not return a reduced price when a maximum nb of uses is exceeded
        """
        coupon, created = self.create_coupon('test-coupon2', 30, valid_nb_times=2)
        self.assertEqual(coupon.get_price_with_coupon(self.course_id), {
            'value': 70,
            'currency': 'usd'
        })
        CourseEnrollmentFactory.create(course_id=self.course_id, coupon=coupon)
        self.assertEqual(coupon.get_price_with_coupon(self.course_id), {
            'value': 70,
            'currency': 'usd'
        })
        CourseEnrollmentFactory.create(course_id=self.course_id, coupon=coupon)
        self.assertEqual(coupon.get_price_with_coupon(self.course_id), {
            'value': 100,
            'currency': 'usd'
        })

    @patch('coupons.models.timezone.now')
    def test_get_price_with_coupon_valid_until(self, mock_now):
        """
        Should not return a reduced price when the maximum date is exceeded
        """
        valid_until = datetime.datetime(2013, 1, 2, 0, 0, tzinfo=utc)
        coupon, created = self.create_coupon('test-coupon2', 30, valid_until=valid_until)

        mock_now.return_value = datetime.datetime(2013, 1, 1, 0, 0, tzinfo=utc)
        self.assertEqual(coupon.get_price_with_coupon(self.course_id), {
            'value': 70,
            'currency': 'usd'
        })

        mock_now.return_value = datetime.datetime(2013, 1, 3, 0, 0, tzinfo=utc)
        self.assertEqual(coupon.get_price_with_coupon(self.course_id), {
            'value': 100,
            'currency': 'usd'
        })

    def test_get_price_with_coupon_valid_course_id(self):
        """
        Should not return a reduced price when a coupon is valid with a specific
        course_id, and the price difference is asked on a different course_id
        """
        coupon, created = self.create_coupon('test-coupon2', 30, valid_course_id=self.course_id)

        self.assertEqual(coupon.get_price_with_coupon(self.course_id), {
            'value': 70,
            'currency': 'usd'
        })

        self.create_mode('pay_with_coupon', 'Pay with coupon', min_price=40, course_id='other/course/id')
        self.assertEqual(coupon.get_price_with_coupon('other/course/id'), {
            'value': 40,
            'currency': 'usd'
        })

    def test_price_with_coupon_view(self):
        request = self.factory.get('/coupons/price', {
            'coupon': self.coupon_name,
            'course_id': self.course_id
        })
        response = price_with_coupon(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {
            'price': {
                'value': 75,
                'currency': 'usd'
            }
        })

    @patch('coupons.views.course_from_id')
    @patch('coupons.views.render_to_response')
    def test_coupon_checkout_view_get(self, mock_render_to_response, mock_course_from_id):
        """
        Test payment page display (GET)
        """
        mock_course_from_id.return_value.display_name = 'Test Course Name'

        coupon_checkout_view = CouponCheckoutView.as_view()
        request = self.factory.get('/coupons/checkout/{}'.format(self.course_id))
        request.user = self.user
        coupon_checkout_view(request, self.course_id)

        mock_course_from_id.assert_called_once_with(self.course_id)
        mock_render_to_response.assert_called_once_with("coupons/pay_with_coupon.html", {
            "course_id": self.course_id,
            "price": {'currency': u'usd', 'value': 100},
            "course_name": 'Test Course Name',
            "error": None,
        })

    @patch('coupons.views.course_from_id')
    @patch('coupons.views.has_access')
    @patch('coupons.views.stripe')
    def test_coupon_checkout_view_post(self, mock_stripe, mock_has_access, mock_course_from_id):
        """
        Test successful payment processing, without coupon
        """
        mock_has_access.return_value = True

        coupon_checkout_view = CouponCheckoutView.as_view()
        request = self.factory.post('/coupons/checkout/{}'.format(self.course_id), {
            'payment_token': 'test-token',
        })
        request.user = self.user
        response = coupon_checkout_view(request, self.course_id)

        mock_course_from_id.assert_called_once_with(self.course_id)
        mock_stripe.Charge.create.assert_called_once_with(
            amount=100*100,
            currency='usd',
            card='test-token',
            description='test@example.com,Test/Course/Test'
        )
        self.assertEqual(response.get('location'), '/dashboard')

    @patch('coupons.views.course_from_id')
    @patch('coupons.views.has_access')
    @patch('coupons.views.stripe')
    def test_coupon_checkout_view_post_coupon(self, mock_stripe, mock_has_access, mock_course_from_id):
        """
        Test successful payment processing, with coupon
        """
        mock_has_access.return_value = True

        coupon_checkout_view = CouponCheckoutView.as_view()
        request = self.factory.post('/coupons/checkout/{}'.format(self.course_id), {
            'payment_token': 'test-token',
            'coupon': self.coupon_name
        })
        request.user = self.user
        response = coupon_checkout_view(request, self.course_id)

        mock_course_from_id.assert_called_once_with(self.course_id)
        mock_stripe.Charge.create.assert_called_once_with(
            amount=75*100,
            currency='usd',
            card='test-token',
            description='test@example.com,Test/Course/Test,coupon=test-coupon'
        )
        self.assertEqual(response.get('location'), '/dashboard')

    @patch('coupons.views.render_to_response')
    @patch('coupons.views.course_from_id')
    @patch('coupons.views.has_access')
    @patch('coupons.views.stripe')
    def test_coupon_checkout_view_post_denied(self, mock_stripe, mock_has_access, mock_course_from_id, mock_render_to_response):
        """
        Test denied payment processing
        """
        class CardError(Exception):
            pass
        mock_stripe.CardError = CardError
        def card_error(*args, **kwargs):
            raise CardError
        mock_stripe.Charge.create.side_effect = card_error

        mock_has_access.return_value = True
        mock_course_from_id.return_value.display_name = 'Test Course Name'

        coupon_checkout_view = CouponCheckoutView.as_view()
        request = self.factory.post('/coupons/checkout/{}'.format(self.course_id), {
            'payment_token': 'test-token'
        })
        request.user = self.user
        coupon_checkout_view(request, self.course_id)

        mock_stripe.Charge.create.assert_called_once_with(
            amount=100*100,
            currency='usd',
            card='test-token',
            description='test@example.com,Test/Course/Test'
        )
        mock_render_to_response.assert_called_once_with("coupons/pay_with_coupon.html", {
            "course_id": self.course_id,
            "price": {'currency': u'usd', 'value': 100},
            "course_name": 'Test Course Name',
            "error": 'Payment denied',
        })

