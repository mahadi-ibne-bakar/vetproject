from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('shop/', views.shop, name='shop'),
    path('cron/send-reminders/', views.send_reminders_endpoint, name='send_reminders'),
    path('health/', views.health_check, name='health_check'),
]