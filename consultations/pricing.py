"""
Pricing utilities for VetProject consultations.

Handles:
- Sitewide discount calculation
- Coupon code validation and discount calculation
- Final price computation with correct precedence
  (coupon overrides sitewide — best deal wins, no stacking)
"""

from core.models import SiteSettings
from consultations.models import CouponCode


def get_effective_price(consultation_fee, user=None, coupon_code=None):
    """
    Returns a pricing dict for a consultation.

    Args:
        consultation_fee: The vet's standard fee
        user:             The requesting user (for coupon eligibility checks)
        coupon_code:      Optional coupon code string to apply

    Returns dict:
        {
            'original_fee':      int,
            'sitewide_discount': int,
            'coupon_discount':   int,
            'final_discount':    int,   # whichever is larger
            'final_fee':         int,
            'discount_source':   str,   # 'none', 'sitewide', 'coupon'
            'coupon':            CouponCode or None,
            'sitewide_label':    str,
        }
    """
    fee = int(consultation_fee)
    settings = SiteSettings.get()

    sitewide_discount = settings.calculate_sitewide_discount(fee)
    coupon_discount   = 0
    coupon_obj        = None
    coupon_error      = None

    if coupon_code and user:
        result = validate_coupon(coupon_code.strip().upper(), user, fee)
        if result['valid']:
            coupon_obj      = result['coupon']
            coupon_discount = result['discount_amount']
        else:
            coupon_error = result['error']

    # No stacking — use the better discount
    if coupon_discount >= sitewide_discount and coupon_discount > 0:
        final_discount = coupon_discount
        discount_source = 'coupon'
    elif sitewide_discount > 0:
        final_discount = sitewide_discount
        discount_source = 'sitewide'
        coupon_obj = None  # coupon not applied if sitewide is better
    else:
        final_discount = 0
        discount_source = 'none'

    return {
        'original_fee':      fee,
        'sitewide_discount': sitewide_discount,
        'coupon_discount':   coupon_discount,
        'final_discount':    final_discount,
        'final_fee':         max(0, fee - final_discount),
        'discount_source':   discount_source,
        'coupon':            coupon_obj,
        'coupon_error':      coupon_error,
        'sitewide_label':    settings.sitewide_discount_label,
    }


def validate_coupon(code, user, consultation_fee):
    """
    Validates a coupon code for a specific user and fee.

    Returns dict:
        {
            'valid':           bool,
            'coupon':          CouponCode or None,
            'discount_amount': int,
            'error':           str or None,
        }
    """
    try:
        coupon = CouponCode.objects.get(code=code.upper())
    except CouponCode.DoesNotExist:
        return {
            'valid':           False,
            'coupon':          None,
            'discount_amount': 0,
            'error':           "Invalid coupon code.",
        }

    if not coupon.is_active:
        return {
            'valid': False, 'coupon': None, 'discount_amount': 0,
            'error': "This coupon is no longer active.",
        }

    from django.utils import timezone
    if coupon.expiry_date and coupon.expiry_date < timezone.localdate():
        return {
            'valid': False, 'coupon': None, 'discount_amount': 0,
            'error': "This coupon has expired.",
        }

    if coupon.max_uses is not None:
        if coupon.usages.count() >= coupon.max_uses:
            return {
                'valid': False, 'coupon': None, 'discount_amount': 0,
                'error': "This coupon has reached its usage limit.",
            }

    if coupon.get_user_uses(user) >= coupon.max_uses_per_user:
        return {
            'valid': False, 'coupon': None, 'discount_amount': 0,
            'error': "You have already used this coupon.",
        }

    if not coupon.check_customer_type(user):
        if coupon.customer_type == 'new':
            msg = "This coupon is for new customers only."
        else:
            msg = "This coupon is for returning customers only."
        return {
            'valid': False, 'coupon': None, 'discount_amount': 0,
            'error': msg,
        }

    discount_amount = coupon.calculate_discount(consultation_fee)
    return {
        'valid':           True,
        'coupon':          coupon,
        'discount_amount': discount_amount,
        'error':           None,
    }