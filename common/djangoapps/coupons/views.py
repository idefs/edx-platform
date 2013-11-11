
# Imports #####################################################################

import json

from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic.base import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from mitxmako.shortcuts import render_to_response

from coupons.models import Coupon, get_base_price_for_course_id
from coupons.payment import pay_with_token
from student.models import CourseEnrollment
from student.views import course_from_id


# Views #######################################################################

class CouponCheckoutView(View):

    @method_decorator(login_required)
    def get(self, request, course_id, error=None):
        if CourseEnrollment.enrollment_mode_for_user(request.user, course_id) == 'pay_with_coupon':
            return redirect(reverse('dashboard'))
        price = get_base_price_for_course_id(course_id)

        context = {
            "course_id": course_id,
            "price": price,
            "course_name": course_from_id(course_id).display_name,
            "error": error,
        }
        return render_to_response("coupons/pay_with_coupon.html", context)

    @method_decorator(login_required)
    def post(self, request, course_id):
        payment_token = request.POST.get('payment_token')
        coupon_name = request.POST.get('coupon', '')
        user = request.user

        error_msg = pay_with_token(user, course_id, payment_token, coupon_name=coupon_name)

        if error_msg:
            return self.get(request, course_id, error=error_msg)
        else:
            return redirect(reverse('dashboard'))


def price_with_coupon(request):
    coupon_name = request.GET['coupon']
    course_id = request.GET['course_id']
    price = Coupon.objects.get_price_with_coupon(course_id, coupon_name)
    return HttpResponse(json.dumps({'price': price}))

