from django.shortcuts import render
from core.models import SiteSettings
from accounts.models import User, VetProfile
from consultations.models import Appointment
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings


def home(request):
    settings = SiteSettings.get()

    how_it_works = [
        {
            'icon': 'calendar_month',
            'title': 'Pick a date and time',
            'description': 'Choose when you want the consultation and see available vets.',
        },
        {
            'icon': 'stethoscope',
            'title': 'Choose your vet',
            'description': 'Browse certified vets and pick one that fits your needs.',
        },
        {
            'icon': 'payments',
            'title': 'Pay the booking fee',
            'description': 'Pay ৳50 via bKash to confirm your appointment.',
        },
        {
            'icon': 'videocam',
            'title': 'Meet on Google Meet',
            'description': 'Join the video call at the scheduled time from anywhere.',
        },
    ]

    ctx = {
        'site_settings': settings,
        'total_consultations': Appointment.objects.filter(status='completed').count(),
        'total_users': User.objects.filter(role='user').count(),
        'total_vets': VetProfile.objects.filter(
            application_status='approved', is_active=True
        ).count(),
        'how_it_works': how_it_works,
    }
    return render(request, 'home.html', ctx)


def about(request):
    return render(request, 'about.html', {})


def contact(request):
    return render(request, 'contact.html', {})

def shop(request):
    return render(request, 'public/shop.html', {})


@csrf_exempt
def send_reminders_endpoint(request):
    """
    Protected endpoint called by cron-job.org every 5 minutes.
    Sends 30-minute appointment reminders.
    Protected by a secret key in the Authorization header or query param.
    """
    # Verify secret
    secret = (
        request.GET.get('secret') or
        request.headers.get('X-Reminder-Secret', '')
    )
    if secret != django_settings.REMINDER_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    from django.utils import timezone
    from datetime import timedelta
    from consultations.models import Appointment
    from consultations.emails import send_appointment_reminder

    now          = timezone.localtime()
    today        = now.date()
    window_start = (now + timedelta(minutes=25)).time()
    window_end   = (now + timedelta(minutes=35)).time()

    appointments = Appointment.objects.filter(
        date=today,
        status='confirmed',
        reminder_sent=False,
        start_time__gte=window_start,
        start_time__lte=window_end,
    ).select_related('user', 'vet__user', 'pet', 'meet_link')

    sent = []
    for appt in appointments:
        send_appointment_reminder(appt)
        appt.reminder_sent = True
        appt.save(update_fields=['reminder_sent'])
        sent.append(appt.id)

    return JsonResponse({
        'status': 'ok',
        'reminders_sent': len(sent),
        'appointment_ids': sent,
        'checked_at': now.isoformat(),
    })