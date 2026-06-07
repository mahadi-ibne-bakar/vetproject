from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('shop/', views.shop, name='shop'),
    path('cron/send-reminders/', views.send_reminders_endpoint, name='send_reminders'),
    path('health/', views.health_check, name='health_check'),
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain',
    ), name='robots_txt'),
    path('.well-known/security.txt', views.security_txt, name='security_txt'),
    path('offline/', views.offline_page, name='offline'),
    path('sw.js',    views.service_worker, name='service_worker'),
]