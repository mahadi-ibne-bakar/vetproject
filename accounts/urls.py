from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # User auth
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # User profile
    path('profile/', views.profile, name='profile'),

    # Password reset
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),

    # Vet auth (separate URLs)
    path('vet/apply/', views.vet_apply, name='vet_apply'),
    path('vet/login/', views.vet_login, name='vet_login'),
    path('vet/application-pending/', views.vet_application_pending, name='vet_application_pending'),
]