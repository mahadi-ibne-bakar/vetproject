from django.urls import path
from . import views

app_name = 'consultations'

urlpatterns = [
    # User-facing booking flow
    path('vets/', views.vet_list, name='vet_list'),
    path('vets/<int:vet_id>/', views.vet_detail, name='vet_detail'),
    path('book/<int:vet_id>/', views.book_appointment, name='book_appointment'),
    path('book/<int:vet_id>/slots/', views.get_available_slots, name='get_available_slots'),
    path('payment/<int:appointment_id>/', views.submit_payment, name='submit_payment'),
    path('payment/<int:appointment_id>/done/', views.payment_done, name='payment_done'),

    # User dashboard
    path('my/appointments/', views.my_appointments, name='my_appointments'),
    path('my/appointments/<int:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('my/appointments/<int:appointment_id>/reschedule/', views.reschedule_appointment, name='reschedule_appointment'),
    path('my/appointments/<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('my/appointments/<int:appointment_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('my/appointments/<int:appointment_id>/second-payment/', views.submit_second_payment, name='submit_second_payment'),
    path('my/pets/', views.my_pets, name='my_pets'),
    path('my/pets/add/', views.add_pet, name='add_pet'),
    path('my/pets/<int:pet_id>/edit/', views.edit_pet, name='edit_pet'),
    path('my/pets/<int:pet_id>/delete/', views.delete_pet, name='delete_pet'),

    # Prescription
    path('prescription/<int:appointment_id>/', views.view_prescription, name='view_prescription'),
    path('prescription/<int:appointment_id>/download/', views.download_prescription, name='download_prescription'),

    # Vet dashboard
    path('vet/dashboard/', views.vet_dashboard, name='vet_dashboard'),
    path('vet/profile/edit/', views.vet_edit_profile, name='vet_edit_profile'),
    path('vet/availability/', views.vet_availability, name='vet_availability'),
    path('vet/availability/add/', views.add_availability, name='add_availability'),
    path('vet/availability/<int:window_id>/delete/', views.delete_availability, name='delete_availability'),
    path('vet/appointments/', views.vet_appointments, name='vet_appointments'),
    path('vet/appointments/<int:appointment_id>/', views.vet_appointment_detail, name='vet_appointment_detail'),
    path('vet/appointments/<int:appointment_id>/start/', views.start_consultation, name='start_consultation'),
    path('vet/appointments/<int:appointment_id>/end/', views.end_consultation, name='end_consultation'),
    path('vet/appointments/<int:appointment_id>/prescription/', views.submit_prescription, name='submit_prescription'),
]