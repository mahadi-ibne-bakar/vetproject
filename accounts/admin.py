from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, VetProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_banned', 'created_at']
    list_filter = ['role', 'is_banned']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Amarvet Fields', {
            'fields': ('role', 'phone_number', 'address', 'profile_photo', 'is_banned')
        }),
    )

@admin.register(VetProfile)
class VetProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'application_status', 'is_active', 'years_of_experience', 'created_at']
    list_filter = ['application_status', 'is_active']