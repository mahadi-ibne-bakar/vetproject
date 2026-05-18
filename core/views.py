from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings
from accounts.models import User
from core.models import SiteSettings


def home(request):
    from accounts.models import VetProfile
    from consultations.models import Appointment
    from blog.models import BlogPost
    from django.db.models import Avg, Count, Q

    site_settings = SiteSettings.get()

    # Featured vets — approved, active, ordered by consultation count
    featured_vets = VetProfile.objects.filter(
        application_status='approved',
        is_active=True,
    ).select_related('user').annotate(
        avg_rating=Avg(
            'reviews__rating',
            filter=Q(reviews__is_visible=True)
        ),
        consultation_count=Count(
            'appointments',
            filter=Q(appointments__status='completed')
        ),
    ).order_by('-consultation_count')[:3]

    # Recent blog posts
    recent_posts = BlogPost.objects.filter(
        status='published'
    ).select_related('author').order_by('-published_at')[:3]

    how_it_works = [
        {
            'icon': 'calendar_month',
            'title': 'Pick a date and time',
            'description': 'Choose when you want the consultation '
                           'and see available vets.',
        },
        {
            'icon': 'stethoscope',
            'title': 'Choose your vet',
            'description': 'Browse certified vets and pick one '
                           'that fits your needs.',
        },
        {
            'icon': 'payments',
            'title': 'Pay the booking fee',
            'description': 'Pay ৳50 via bKash to confirm your appointment.',
        },
        {
            'icon': 'videocam',
            'title': 'Meet on Google Meet',
            'description': 'Join the video call at the scheduled '
                           'time from anywhere.',
        },
    ]

    ctx = {
        'site_settings': site_settings,
        'total_consultations': Appointment.objects.filter(
            status='completed'
        ).count(),
        'total_users': User.objects.filter(role='user').count(),
        'total_vets': VetProfile.objects.filter(
            application_status='approved',
            is_active=True,
        ).count(),
        'how_it_works': how_it_works,
        'featured_vets': featured_vets,
        'recent_posts': recent_posts,
    }
    return render(request, 'home.html', ctx)


def about(request):
    team = [
        {
            'name': 'The VetProject Team',
            'role': 'Founded in Bangladesh',
            'description': (
                'VetProject was built by a team passionate about improving '
                'access to veterinary care for pet owners across Bangladesh. '
                'We believe every cat and dog deserves quality healthcare, '
                'regardless of where their owner lives.'
            ),
        },
    ]

    values = [
        {
            'icon': 'verified',
            'title': 'Quality First',
            'description': (
                'Every vet on our platform is verified with a valid BVC '
                'registration number. We never compromise on credentials.'
            ),
        },
        {
            'icon': 'accessibility',
            'title': 'Accessible Care',
            'description': (
                'Whether you\'re in Dhaka, Chittagong, or a small town, '
                'you deserve access to a qualified vet. We make that possible.'
            ),
        },
        {
            'icon': 'favorite',
            'title': 'Pet Wellbeing',
            'description': (
                'We put the health and happiness of your pets at the centre '
                'of everything we build and every decision we make.'
            ),
        },
        {
            'icon': 'lock',
            'title': 'Privacy & Trust',
            'description': (
                'Your consultation details, pet records, and payment '
                'information are kept strictly private and secure.'
            ),
        },
    ]

    ctx = {
        'values': values,
        'team': team,
    }
    return render(request, 'public/about.html', ctx)


def contact(request):
    submitted = False

    faqs = [
        {
            'q': 'How does the online consultation work?',
            'a': 'You book a slot, pay ৳50 via bKash to confirm, '
                 'then join a Google Meet video call with your vet at the scheduled time.',
        },
        {
            'q': 'What if my pet needs physical treatment?',
            'a': 'Our vets will advise you if an in-person visit is necessary. '
                 'Online consultations are best for advice, diagnosis, and follow-ups.',
        },
        {
            'q': 'How do I get my prescription?',
            'a': 'After the consultation, pay the consultation fee via bKash. '
                 'Once verified, your prescription PDF is instantly available to download.',
        },
        {
            'q': 'Can I cancel my appointment?',
            'a': 'Yes. Cancel at least 2 hours before your appointment for a refund '
                 'of your booking fee minus a ৳10 cancellation fee.',
        },
    ]

    if request.method == 'POST':
        # ... existing POST handling code ...
        name    = request.POST.get('name', '').strip()
        email   = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if name and email and message:
            from django.core.mail import send_mail
            from django.conf import settings as django_settings

            full_message = (
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Subject: {subject}\n\n"
                f"Message:\n{message}"
            )
            try:
                send_mail(
                    subject=f"VetProject Contact: {subject or 'No subject'}",
                    message=full_message,
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[django_settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass
            submitted = True

    return render(request, 'public/contact.html', {
        'submitted': submitted,
        'faqs': faqs,
    })

def shop(request):
    notify_submitted = False

    if request.method == 'POST':
        notify_email = request.POST.get('notify_email', '').strip()
        if notify_email:
            # Store in a simple log for now
            # In future this connects to a mailing list
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Shop notify request: {notify_email}")

            # Send a simple acknowledgement email
            from django.core.mail import send_mail
            from django.conf import settings as django_settings
            try:
                send_mail(
                    subject="VetProject Shop — You're on the list!",
                    message=(
                        f"Hi,\n\n"
                        f"You've been added to our shop launch notification list.\n"
                        f"We'll email you as soon as the VetProject Shop goes live "
                        f"with an exclusive launch discount.\n\n"
                        f"Thank you for your interest!\n\n"
                        f"— The VetProject Team"
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[notify_email],
                    fail_silently=True,
                )
                # Also notify admin
                send_mail(
                    subject=f"Shop notify signup: {notify_email}",
                    message=f"New shop notify signup: {notify_email}",
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[django_settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass
            notify_submitted = True

    coming_soon_items = [
        {
            'emoji': '🐱',
            'name': 'Cat Food',
            'description': 'Premium nutrition for cats',
        },
        {
            'emoji': '🐶',
            'name': 'Dog Food',
            'description': 'Vet-approved dog nutrition',
        },
        {
            'emoji': '💊',
            'name': 'Medicines',
            'description': 'Vet-prescribed medications',
        },
        {
            'emoji': '🧸',
            'name': 'Toys & Accessories',
            'description': 'Keep your pet happy',
        },
        {
            'emoji': '🛁',
            'name': 'Grooming',
            'description': 'Shampoos and grooming tools',
        },
        {
            'emoji': '🏠',
            'name': 'Pet Furniture',
            'description': 'Beds, crates, and carriers',
        },
    ]

    return render(request, 'public/shop.html', {
        'coming_soon_items': coming_soon_items,
        'notify_submitted': notify_submitted,
    })


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