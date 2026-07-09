"""
Email Notifications
===================
All transactional emails sent by the platform.

Functions:
- send_booking_confirmed     — sent when admin verifies booking payment
- send_appointment_reminder  — sent 30 minutes before appointment
- send_prescription_ready    — sent when second payment verified
- send_cancellation_confirm  — sent when appointment is cancelled
"""

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def _send(subject: str, message: str, recipient_email: str) -> bool:
    try:
        from django.core.mail import EmailMessage
        from django.conf import settings as django_settings

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        email.send(fail_silently=True)
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Email send failed to {recipient_email}: {e}")
        return False


def send_booking_confirmed(appointment):
    """
    Sent to both user and vet when booking payment is verified
    and the appointment is confirmed.
    """
    user     = appointment.user
    vet      = appointment.vet
    pet      = appointment.pet
    date_str = appointment.date.strftime('%A, %B %d, %Y')
    time_str = appointment.start_time.strftime('%I:%M %p')
    meet_url = appointment.meet_link.url if appointment.meet_link else 'To be assigned'

    # Email to user
    user_message = f"""Hi {user.first_name},

Your appointment has been confirmed!

━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPOINTMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vet:        Dr. {vet.user.get_full_name()}
Pet:        {pet.name} ({pet.get_species_display()})
Date:       {date_str}
Time:       {time_str}
Google Meet: {meet_url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please join the Google Meet link at the scheduled time.
You will also receive a reminder 30 minutes before your appointment.

If you need to cancel or reschedule, please do so at least 2 hours in advance
to receive a full refund (minus the ৳10 cancellation fee).

Thank you for choosing Amarvet.

— The Amarvet Team
"""

    _send(
        subject=f"Appointment Confirmed — Dr. {vet.user.last_name} on {date_str}",
        message=user_message,
        recipient_email=user.email,
    )

    # Email to vet
    vet_message = f"""Hi Dr. {vet.user.last_name},

You have a new confirmed appointment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPOINTMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pet Owner:  {user.get_full_name()}
Phone:      {user.phone_number or 'Not provided'}
Pet:        {pet.name} ({pet.get_species_display()})
Complaint:  {appointment.get_primary_complaint_display()}
Date:       {date_str}
Time:       {time_str}
Google Meet: {meet_url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Description:
{appointment.complaint_description}

Please log in to your Amarvet dashboard to view full details.

— The Amarvet Team
"""

    _send(
        subject=f"New Appointment — {pet.name} on {date_str}",
        message=vet_message,
        recipient_email=vet.user.email,
    )


def send_appointment_reminder(appointment):
    """
    Sent to both user and vet 30 minutes before the appointment.
    Called by the management command send_reminders.
    """
    user     = appointment.user
    vet      = appointment.vet
    pet      = appointment.pet
    time_str = appointment.start_time.strftime('%I:%M %p')
    meet_url = appointment.meet_link.url if appointment.meet_link else 'Check your dashboard'

    # Reminder to user
    user_message = f"""Hi {user.first_name},

Your appointment starts in 30 minutes!

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vet:        Dr. {vet.user.get_full_name()}
Pet:        {pet.name}
Time:       {time_str}
Google Meet: {meet_url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Click the Google Meet link above to join at the scheduled time.

— The Amarvet Team
"""

    _send(
        subject=f"Reminder: Appointment in 30 minutes — {time_str}",
        message=user_message,
        recipient_email=user.email,
    )

    # Reminder to vet
    vet_message = f"""Hi Dr. {vet.user.last_name},

Reminder: You have an appointment in 30 minutes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pet Owner:  {user.get_full_name()}
Pet:        {pet.name} ({pet.get_species_display()})
Complaint:  {appointment.get_primary_complaint_display()}
Time:       {time_str}
Google Meet: {meet_url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

— The Amarvet Team
"""

    _send(
        subject=f"Reminder: Appointment in 30 minutes — {pet.name}",
        message=vet_message,
        recipient_email=vet.user.email,
    )


def send_prescription_ready(appointment):
    """
    Sent to user when second payment is verified
    and prescription is unlocked.
    """
    user     = appointment.user
    vet      = appointment.vet
    pet      = appointment.pet
    date_str = appointment.date.strftime('%B %d, %Y')

    message = f"""Hi {user.first_name},

Your prescription from your consultation with Dr. {vet.user.get_full_name()} is now ready.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pet:   {pet.name}
Date:  {date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━

You can view and download your prescription by logging in to Amarvet
and visiting your appointments page.

Thank you for choosing Amarvet. We hope {pet.name} feels better soon!

— The Amarvet Team
"""

    _send(
        subject=f"Your Prescription is Ready — {pet.name}",
        message=message,
        recipient_email=user.email,
    )


def send_cancellation_confirm(appointment, refund_amount=None):
    """
    Sent to user when they cancel an appointment.
    Includes refund details if applicable.
    """
    user     = appointment.user
    vet      = appointment.vet
    pet      = appointment.pet
    date_str = appointment.date.strftime('%A, %B %d, %Y')
    time_str = appointment.start_time.strftime('%I:%M %p')

    if refund_amount is not None and refund_amount > 0:
        refund_text = (
            f"\nYour booking fee refund of ৳{refund_amount} will be sent to "
            f"your bKash number within 24 hours.\n"
        )
    else:
        refund_text = "\nNo refund is applicable for this cancellation.\n"

    message = f"""Hi {user.first_name},

Your appointment has been cancelled.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vet:   Dr. {vet.user.get_full_name()}
Pet:   {pet.name}
Date:  {date_str}
Time:  {time_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
{refund_text}
If you'd like to book a new appointment, visit Amarvet anytime.

— The Amarvet Team
"""

    _send(
        subject=f"Appointment Cancelled — {date_str}",
        message=message,
        recipient_email=user.email,
    )