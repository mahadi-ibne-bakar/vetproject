from django.shortcuts import render
from core.models import SiteSettings
from accounts.models import User, VetProfile
from consultations.models import Appointment


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