from django.contrib import admin
from .models import SiteSettings, MeetLink

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['booking_enabled', 'slot_duration_minutes', 'booking_fee', 'updated_at']

@admin.register(MeetLink)
class MeetLinkAdmin(admin.ModelAdmin):
    list_display = ['url', 'is_in_use', 'notes', 'added_at']