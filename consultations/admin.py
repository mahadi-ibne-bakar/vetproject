from django.contrib import admin
from .models import Pet, VetAvailability, Appointment, Payment, Prescription

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ['name', 'species', 'breed', 'owner', 'created_at']

@admin.register(VetAvailability)
class VetAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['vet', 'is_recurring', 'day_of_week', 'start_time', 'end_time', 'is_active']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['pet', 'vet', 'user', 'date', 'start_time', 'status', 'created_at']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'payment_type', 'amount', 'bkash_number', 'transaction_id', 'status']

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'created_at', 'updated_at']