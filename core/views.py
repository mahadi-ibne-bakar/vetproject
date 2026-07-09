from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings
from accounts.models import User
from core.models import SiteSettings
from blog.models import BlogPost, Review
from django.db.models import Avg, Count, Q


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
        review_count=Count(
            'reviews',
            filter=Q(reviews__is_visible=True)
        ),
        consultation_count=Count(
            'appointments',
            filter=Q(appointments__status='completed')
        ),
    ).order_by('-consultation_count')[:3]

    # Featured reviews — 4 stars and above, visible, with comments
    featured_reviews = Review.objects.filter(
        is_visible=True,
        rating__gte=4,
        comment__isnull=False,
    ).exclude(
        comment=''
    ).select_related(
        'reviewer', 'vet__user', 'appointment__pet'
    ).order_by('-rating', '-created_at')[:6]

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
        'featured_reviews': featured_reviews,
    }
    return render(request, 'home.html', ctx)


def about(request):
    team = [
        {
            'name': 'The Amarvet Team',
            'role': 'Founded in Bangladesh',
            'description': (
                'Amarvet was built by a team passionate about improving '
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
                    subject=f"Amarvet Contact: {subject or 'No subject'}",
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
    feedback_submitted = False

    if request.method == 'POST':
        email   = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        if email and message:
            import logging
            from django.core.mail import send_mail
            from django.conf import settings as django_settings

            logger = logging.getLogger(__name__)
            logger.info(f"Shop feedback from {email}: {message}")

            try:
                # Acknowledgement to user
                send_mail(
                    subject="Thanks for your feedback — Amarvet Shop",
                    message=(
                        f"Hi,\n\n"
                        f"Thank you for sharing what you'd like to see in the "
                        f"Amarvet Shop. We read every message and your input "
                        f"directly shapes what we stock.\n\n"
                        f"We'll let you know as soon as the shop is live!\n\n"
                        f"— The Amarvet Team"
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )
                # Notify admin
                send_mail(
                    subject=f"Shop feedback from {email}",
                    message=f"Email: {email}\n\nMessage:\n{message}",
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[django_settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass
            feedback_submitted = True

    coming_soon_items = [
        {'emoji': '🐱', 'name': 'Cat Food',          'description': 'Premium nutrition for cats'},
        {'emoji': '🐶', 'name': 'Dog Food',           'description': 'Vet-approved dog nutrition'},
        {'emoji': '💊', 'name': 'Medicines',          'description': 'Vet-prescribed medications'},
        {'emoji': '🧸', 'name': 'Toys & Accessories', 'description': 'Keep your pet happy'},
        {'emoji': '🛁', 'name': 'Grooming',           'description': 'Shampoos and grooming tools'},
        {'emoji': '🏠', 'name': 'Pet Furniture',      'description': 'Beds, crates, and carriers'},
    ]

    return render(request, 'public/shop.html', {
        'coming_soon_items':  coming_soon_items,
        'feedback_submitted': feedback_submitted,
    })


@csrf_exempt
def send_reminders_endpoint(request):
    secret = (
        request.GET.get('secret') or
        request.headers.get('X-Reminder-Secret', '')
    )
    if secret != django_settings.REMINDER_SECRET:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    from django.utils import timezone
    from datetime import timedelta
    from consultations.models import Appointment
    from consultations.emails import (
        send_appointment_reminder,
        send_cancellation_confirm,
    )

    now   = timezone.localtime()
    today = now.date()

    # ── Send 30-minute reminders ───────────────────────────────────────────────
    window_start = (now + timedelta(minutes=25)).time()
    window_end   = (now + timedelta(minutes=35)).time()

    reminders = Appointment.objects.filter(
        date=today,
        status='confirmed',
        reminder_sent=False,
        start_time__gte=window_start,
        start_time__lte=window_end,
    ).select_related('user', 'vet__user', 'pet', 'meet_link')

    reminder_ids = []
    for appt in reminders:
        send_appointment_reminder(appt)
        appt.reminder_sent = True
        appt.save(update_fields=['reminder_sent'])
        reminder_ids.append(appt.id)

    # ── Auto-cancel unpaid appointments older than 1 hour ─────────────────────
    cutoff = now - timedelta(hours=1)

    stale = Appointment.objects.filter(
        status='pending_payment',
        created_at__lt=cutoff,
    ).select_related('user', 'vet__user', 'pet')

    cancelled_ids = []
    for appt in stale:
        appt.status = Appointment.Status.CANCELLED
        appt.cancellation_reason = (
            'Automatically cancelled — booking payment not received within 1 hour.'
        )
        appt.save()

        # Free meet link if somehow assigned
        if appt.meet_link:
            appt.meet_link.is_in_use = False
            appt.meet_link.save()

        # Notify user
        send_cancellation_confirm(appt, refund_amount=None)
        cancelled_ids.append(appt.id)

    # ── Auto-assign meet links to confirmed appointments that don't have one ───────
    from core.models import MeetLink

    confirmed_without_link = Appointment.objects.filter(
        status__in=['confirmed', 'rescheduled'],
        date__gte=today.date() if hasattr(today, 'date') else today,
        meet_link__isnull=True,
    ).select_related('vet')

    assigned_ids = []
    for appt in confirmed_without_link:
        # Find a free link not used by another appointment on the same date
        used_on_date = Appointment.objects.filter(
            date=appt.date,
            status__in=['confirmed', 'in_progress', 'completed', 'rescheduled'],
            meet_link__isnull=False,
        ).exclude(
            id=appt.id
        ).values_list('meet_link_id', flat=True)

        free_link = MeetLink.objects.filter(
            is_in_use=False,
        ).exclude(
            id__in=used_on_date,
        ).first()

        if free_link:
            appt.meet_link      = free_link
            free_link.is_in_use = True
            free_link.save()
            appt.save(update_fields=['meet_link'])
            assigned_ids.append(appt.id)

            # Notify user that their meet link is now available
            from consultations.emails import send_booking_confirmed
            # Only resend if appointment is more than 2 hours away
            from datetime import datetime, time as time_cls
            appt_datetime = datetime.combine(appt.date, appt.start_time)
            appt_datetime = timezone.make_aware(appt_datetime)
            if appt_datetime > now + timedelta(hours=2):
                send_booking_confirmed(appt)

    return JsonResponse({
        'status':          'ok',
        'reminders_sent':  len(reminder_ids),
        'auto_cancelled':  len(cancelled_ids),
        'meet_assigned':   len(assigned_ids),
        'appointment_ids': reminder_ids,
        'cancelled_ids':   cancelled_ids,
        'checked_at':      now.isoformat(),
    })

def health_check(request):
    """
    Simple health check endpoint.
    Render uses this to verify the service is running.
    Also checks database connectivity.
    """
    from django.db import connection
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    status = 200 if db_ok else 503
    return JsonResponse({
        'status':   'ok' if db_ok else 'degraded',
        'database': 'ok' if db_ok else 'error',
    }, status=status)


def security_txt(request):
    from django.http import HttpResponse
    from django.utils import timezone
    # Update the Expires date annually
    content = """Contact: mailto:admin@amarvet.live
Expires: 2027-01-01T00:00:00.000Z
Preferred-Languages: en, bn
Canonical: https://amarvet.live/.well-known/security.txt
Policy: https://amarvet.live/about/
"""
    return HttpResponse(content, content_type='text/plain')


def error_404(request, exception=None):
    return render(request, '404.html', status=404)

def error_500(request):
    return render(request, '500.html', status=500)


def offline_page(request):
    return render(request, 'offline.html')


def service_worker(request):
    from django.http import HttpResponse
    js = """
const CACHE_NAME = 'vetproject-v1';
const OFFLINE_URL = '/offline/';

// Pre-cache the offline page on install
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.add(OFFLINE_URL);
        })
    );
    self.skipWaiting();
});

// Clean up old caches on activate
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            );
        })
    );
    self.clients.claim();
});

// Network-first strategy — fall back to offline page if navigation fails
self.addEventListener('fetch', event => {
    if (event.request.mode !== 'navigate') return;

    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(OFFLINE_URL);
        })
    );
});
"""
    response = HttpResponse(js, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


from django.views.decorators.csrf import csrf_exempt
from core.middleware import logger

@csrf_exempt
def csp_report(request):
    """Receives CSP violation reports from browsers."""
    import json
    from django.http import HttpResponse

    if request.method == 'POST':
        try:
            report = json.loads(request.body)
            violation = report.get('csp-report', {})
            blocked = violation.get('blocked-uri', 'unknown')
            directive = violation.get('violated-directive', 'unknown')
            document = violation.get('document-uri', 'unknown')
            logger.warning(
                f"CSP violation: blocked={blocked} "
                f"directive={directive} document={document}"
            )
        except Exception:
            pass
    return HttpResponse(status=204)