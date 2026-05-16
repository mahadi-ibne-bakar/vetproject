from django.shortcuts import render
from core.models import SiteSettings


def home(request):
    settings = SiteSettings.get()
    return render(request, 'home.html', {
        'site_settings': settings,
    })


def about(request):
    return render(request, 'about.html', {})


def contact(request):
    return render(request, 'contact.html', {})