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