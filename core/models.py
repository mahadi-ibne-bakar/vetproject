from django.db import models


class SiteSettings(models.Model):
    """
    Singleton model — only one row should ever exist.
    Controls global site behaviour like booking on/off toggle.
    Admin edits this from the dashboard.
    """

    # Booking toggle
    booking_enabled = models.BooleanField(
        default=True,
        help_text="Uncheck to disable all new bookings",
    )
    service_off_message = models.TextField(
        blank=True,
        default="Our service is temporarily unavailable. Please check back soon.",
        help_text="Shown on homepage when booking is disabled",
    )
    service_off_from = models.DateField(
        blank=True,
        null=True,
        help_text="Optional: start date of downtime shown to users",
    )
    service_off_until = models.DateField(
        blank=True,
        null=True,
        help_text="Optional: end date of downtime shown to users",
    )

    # Slot configuration
    slot_duration_minutes = models.PositiveIntegerField(
        default=15,
        help_text="Duration of each consultation slot in minutes",
    )

    # Fees
    booking_fee = models.PositiveIntegerField(
        default=50,
        help_text="Upfront booking fee in BDT",
    )
    cancellation_deduction = models.PositiveIntegerField(
        default=10,
        help_text="Amount deducted from refund on cancellation in BDT",
    )
    bkash_merchant_number = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text="Your bKash merchant/personal number shown to users for payment",
    )
    # ── Sitewide discount ──────────────────────────────────────────────────────────
    sitewide_discount_enabled = models.BooleanField(
        default=False,
        help_text="Enable a sitewide discount on all consultation fees",
    )
    sitewide_discount_type = models.CharField(
        max_length=10,
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        default='percentage',
    )
    sitewide_discount_value = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Percentage (e.g. 20 for 20%) or fixed amount in Taka",
    )
    sitewide_discount_label = models.CharField(
        max_length=100, blank=True, default='',
        help_text="Shown to users e.g. 'Eid Special — 15% off all consultations'",
    )
    sitewide_discount_expiry = models.DateField(
        null=True, blank=True,
        help_text="Optional — discount automatically deactivates after this date",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return "Site Settings"

    def save(self, *args, **kwargs):
        # Enforce singleton — only one settings row allowed
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Always use SiteSettings.get() to retrieve settings."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def calculate_sitewide_discount(self, consultation_fee):
        from django.utils import timezone
        if not self.sitewide_discount_enabled or not self.sitewide_discount_value:
            return 0
        if self.sitewide_discount_expiry and self.sitewide_discount_expiry < timezone.localdate():
            return 0
        fee = float(consultation_fee)
        if self.sitewide_discount_type == 'percentage':
            discount = fee * float(self.sitewide_discount_value) / 100
        else:
            discount = float(self.sitewide_discount_value)
        return min(int(round(discount)), int(fee))

class AuditLog(models.Model):
    """
    Records significant admin actions for accountability.
    """
    class Action(models.TextChoices):
        PAYMENT_VERIFIED   = 'payment_verified',   'Payment Verified'
        PAYMENT_FAILED     = 'payment_failed',     'Payment Marked Failed'
        PAYMENT_REFUNDED   = 'payment_refunded',   'Payment Refunded'
        USER_BANNED        = 'user_banned',        'User Banned'
        USER_UNBANNED      = 'user_unbanned',      'User Unbanned'
        VET_APPROVED       = 'vet_approved',       'Vet Application Approved'
        VET_REJECTED       = 'vet_rejected',       'Vet Application Rejected'
        SETTINGS_CHANGED   = 'settings_changed',   'Site Settings Changed'
        COUPON_CREATED     = 'coupon_created',     'Coupon Created'
        COUPON_TOGGLED     = 'coupon_toggled',     'Coupon Toggled'
        COUPON_DELETED     = 'coupon_deleted',     'Coupon Deleted'
        APPOINTMENT_CANCELLED = 'appt_cancelled',  'Appointment Cancelled by Admin'

    actor       = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action      = models.CharField(max_length=50, choices=Action.choices)
    description = models.TextField()
    target_id   = models.PositiveIntegerField(null=True, blank=True)
    target_type = models.CharField(max_length=50, blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor} — {self.action} — {self.created_at:%Y-%m-%d %H:%M}"

class MeetLink(models.Model):
    """
    Pool of Google Meet links managed by admin.
    Each link is assigned to one active consultation at a time.
    When consultation ends the link is freed for reuse.
    """

    url = models.URLField(unique=True)
    is_in_use = models.BooleanField(default=False)
    notes = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional label e.g. 'Link 1', 'Backup link'",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "IN USE" if self.is_in_use else "available"
        return f"{self.url} [{status}]"

    class Meta:
        ordering = ['is_in_use', 'added_at']