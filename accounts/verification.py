"""
Email verification utilities using Django's signing framework.
No separate model needed — the token is a signed, time-limited string
containing the user's PK.
"""

from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import logging

logger   = logging.getLogger(__name__)
signer   = TimestampSigner(salt='email-verification')
MAX_AGE  = 60 * 60 * 24 * 3  # 3 days


def generate_verification_token(user):
    """Returns a signed token string for the given user."""
    return signer.sign(str(user.pk))


def verify_token(token):
    """
    Validates a token and returns the user PK if valid.
    Returns None if the token is invalid or expired.
    """
    try:
        user_pk = signer.unsign(token, max_age=MAX_AGE)
        return int(user_pk)
    except (BadSignature, SignatureExpired):
        return None


def send_verification_email(user, request):
    """
    Sends a verification email to the user.
    Safe to call multiple times — always generates a fresh token.
    """
    token = generate_verification_token(user)
    domain = get_current_site(request).domain
    path   = reverse('accounts:verify_email', args=[token])
    link   = f"https://{domain}{path}"

    try:
        send_mail(
            subject="Verify your VetProject account",
            message=(
                f"Hi {user.first_name},\n\n"
                f"Please verify your email address by clicking the link below:\n\n"
                f"{link}\n\n"
                f"This link expires in 3 days.\n\n"
                f"If you did not create a VetProject account, "
                f"you can safely ignore this email.\n\n"
                f"— The VetProject Team"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        logger.info(f"Verification email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {e}")
        return False