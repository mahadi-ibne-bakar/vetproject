from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Pet(models.Model):
    """
    A pet owned by a user. One user can have multiple pets.
    When booking, the user selects which pet the consultation is for.
    Vets can view and add to the pet's medical history.
    """

    class Species(models.TextChoices):
        CAT       = 'cat',       'Cat'
        DOG       = 'dog',       'Dog'
        BIRD      = 'bird',      'Bird'
        RABBIT    = 'rabbit',    'Rabbit'
        LIVESTOCK = 'livestock', 'Livestock'
        OTHER     = 'other',     'Other'

    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='pets',
    )
    name = models.CharField(max_length=100)
    species = models.CharField(
        max_length=10,
        choices=Species.choices,
    )
    breed = models.CharField(max_length=100, blank=True)
    age_years = models.PositiveIntegerField(default=0)
    age_months = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(11)],
    )
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )
    photo = models.ImageField(
        upload_to='pet_photos/',
        blank=True,
        null=True,
    )
    medical_history_notes = models.TextField(
        blank=True,
        help_text="Ongoing notes about this pet's health history. Vets can add to this.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_species_display()}) — owned by {self.owner.username}"


class VetAvailability(models.Model):
    """
    Defines when a vet is available for consultations.
    Can be recurring (same time every week on chosen days, with optional end date)
    or a one-off specific date.
    Multiple windows per day are supported — each window is a separate row.
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY    = 0, 'Monday'
        TUESDAY   = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY  = 3, 'Thursday'
        FRIDAY    = 4, 'Friday'
        SATURDAY  = 5, 'Saturday'
        SUNDAY    = 6, 'Sunday'

    vet = models.ForeignKey(
        'accounts.VetProfile',
        on_delete=models.CASCADE,
        related_name='availability_windows',
    )

    # Recurring availability
    is_recurring = models.BooleanField(
        default=True,
        help_text="If true, repeats every week on the selected day",
    )
    day_of_week = models.IntegerField(
        choices=DayOfWeek.choices,
        blank=True,
        null=True,
        help_text="Used when is_recurring is True",
    )
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text="Recurring availability stops after this date. Leave blank for indefinite.",
    )

    # One-off availability
    specific_date = models.DateField(
        blank=True,
        null=True,
        help_text="Used when is_recurring is False",
    )

    start_time = models.TimeField()
    end_time   = models.TimeField()
    is_active  = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.is_recurring:
            day = self.get_day_of_week_display()
            end = f" until {self.end_date}" if self.end_date else " (no end date)"
            return f"{self.vet} — Every {day} {self.start_time}–{self.end_time}{end}"
        return f"{self.vet} — {self.specific_date} {self.start_time}–{self.end_time}"

    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name_plural = "Vet Availabilities"

class BlockedDate(models.Model):
    """
    A specific date on which a vet is completely unavailable.
    Overrides any recurring or specific-date availability windows for that day.
    Used when a vet needs a day off without deleting their recurring schedule.
    """
    vet = models.ForeignKey(
        'accounts.VetProfile',
        on_delete=models.CASCADE,
        related_name='blocked_dates',
    )
    date = models.DateField()
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional note e.g. 'National holiday', 'Personal leave'",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']
        unique_together = ['vet', 'date']
        verbose_name = "Blocked Date"

    def __str__(self):
        return f"{self.vet} — Blocked {self.date}"

class Appointment(models.Model):
    """
    Core model — represents a booked consultation.
    Tracks the full lifecycle from booking to completion.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', 'Pending Booking Payment'
        CONFIRMED = 'confirmed', 'Confirmed'
        RESCHEDULED = 'rescheduled', 'Rescheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        AWAITING_SECOND_PAYMENT = 'awaiting_second_payment', 'Awaiting Consultation Payment'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    class PrimaryComplaint(models.TextChoices):
        DIGESTIVE = 'digestive', 'Digestive Issue'
        SKIN = 'skin', 'Skin / Fur Problem'
        BEHAVIOURAL = 'behavioural', 'Behavioural Issue'
        INJURY = 'injury', 'Injury'
        BREATHING = 'breathing', 'Breathing Problem'
        EATING = 'eating', 'Not Eating / Loss of Appetite'
        VACCINATION = 'vaccination', 'Vaccination Advice'
        GENERAL = 'general', 'General Checkup'
        OTHER = 'other', 'Other'

    # Core relations
    pet = models.ForeignKey(
        Pet,
        on_delete=models.PROTECT,
        related_name='appointments',
    )
    vet = models.ForeignKey(
        'accounts.VetProfile',
        on_delete=models.PROTECT,
        related_name='appointments',
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='appointments',
    )

    # Scheduling
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Status
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )

    # Meet link assigned from pool
    meet_link = models.ForeignKey(
        'core.MeetLink',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments',
    )

    # Pre-consultation form (filled by user when booking)
    primary_complaint = models.CharField(
        max_length=20,
        choices=PrimaryComplaint.choices,
    )
    complaint_description = models.TextField(
        help_text="User describes the issue in their own words",
    )
    symptom_photo = models.ImageField(
        upload_to='symptom_photos/',
        blank=True,
        null=True,
    )

    # Consultation session tracking
    consultation_start_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Set when vet clicks Start Meeting",
    )
    consultation_end_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Set when vet clicks End Meeting",
    )

    # Vet notes (entered during or after consultation)
    consultation_notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)

    # Rescheduling
    reschedule_count = models.PositiveIntegerField(default=0)
    rescheduled_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rescheduled_to',
    )
    reminder_sent = models.BooleanField(
        default=False,
        help_text="True once the 30-minute reminder email has been sent",
    )

    # ── Discount fields ────────────────────────────────────────────────────────────
    coupon = models.ForeignKey(
        'CouponCode',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments',
    )
    discount_amount = models.PositiveIntegerField(
        default=0,
        help_text="Taka amount discounted from consultation fee",
    )
    original_consultation_fee = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Consultation fee at time of booking before any discount",
    )

    # Cancellation
    cancellation_reason = models.TextField(blank=True)

    # Post-consultation feedback (filled by user)
    feedback_rating = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    feedback_comment = models.TextField(blank=True)
    feedback_submitted_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.pet.name} with {self.vet} on {self.date} at {self.start_time}"

    class Meta:
        ordering = ['-date', '-start_time']

class AppointmentPhoto(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='symptom_photos',
    )
    photo       = models.ImageField(upload_to='symptom_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Photo for appointment {self.appointment.id}"

class Payment(models.Model):
    """
    Tracks bKash payments. Two payments per appointment:
    1. Booking fee (upfront, before confirmation)
    2. Consultation fee (after consultation ends)

    Admin manually verifies by entering details from bKash SMS.
    """

    class PaymentType(models.TextChoices):
        BOOKING = 'booking', 'Booking Fee'
        CONSULTATION = 'consultation', 'Consultation Fee'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Verification'
        VERIFIED = 'verified', 'Verified'
        WRONG_TRANSACTION = 'wrong_transaction', 'Wrong Transaction ID'
        FAILED = 'failed', 'Failed / Discarded'
        REFUNDED = 'refunded', 'Refunded'

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    payment_type = models.CharField(
        max_length=15,
        choices=PaymentType.choices,
    )
    amount = models.PositiveIntegerField(help_text="Amount in BDT")

    # Entered by user when submitting payment
    bkash_number = models.CharField(
        max_length=20,
        help_text="User's bKash number used to send payment",
    )
    transaction_id = models.CharField(max_length=100)

    # Verification
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
    )
    verified_at = models.DateTimeField(blank=True, null=True)

    # Refund tracking
    refund_amount = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Amount to refund after deduction",
    )
    refund_sent_at = models.DateTimeField(blank=True, null=True)
    refund_bkash_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="bKash number to send refund to",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_payment_type_display()} — {self.amount} BDT — {self.get_status_display()}"


class Prescription(models.Model):
    """
    Created by vet during or after consultation.
    Once submitted, generates a PDF for the user to download.
    Locked behind second payment verification.
    """

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='prescription',
    )
    medications = models.TextField(
        help_text="List medications, one per line",
    )
    dosage_instructions = models.TextField(
        help_text="Dosage and administration instructions",
    )
    follow_up_advice = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)
    pdf_file = models.FileField(
        upload_to='prescriptions/',
        blank=True,
        null=True,
        help_text="Auto-generated PDF — do not upload manually",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prescription for {self.appointment}"


class CouponCode(models.Model):

    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED      = 'fixed',      'Fixed Amount'

    class CustomerType(models.TextChoices):
        ALL        = 'all',        'All Customers'
        NEW        = 'new',        'New Customers Only'
        RETURNING  = 'returning',  'Returning Customers Only'

    code                = models.CharField(max_length=50, unique=True)
    description         = models.CharField(
        max_length=200, blank=True, default='',
        help_text="Internal admin note about this coupon"
    )
    discount_type       = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    discount_value      = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="Percentage (e.g. 20 for 20%) or fixed amount in Taka",
    )
    max_discount_amount = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Optional cap — e.g. '20% off but maximum ৳100'",
    )
    customer_type       = models.CharField(
        max_length=10,
        choices=CustomerType.choices,
        default=CustomerType.ALL,
    )
    expiry_date         = models.DateField(
        null=True, blank=True,
        help_text="Leave blank for no expiry",
    )
    max_uses            = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Global usage cap — leave blank for unlimited",
    )
    max_uses_per_user   = models.PositiveIntegerField(
        default=1,
        help_text="How many times one user can use this code",
    )
    is_active           = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    created_by          = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_coupons',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def is_valid(self):
        """Returns True if the coupon is currently usable."""
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.expiry_date and self.expiry_date < timezone.localdate():
            return False
        if self.max_uses is not None:
            if self.usages.count() >= self.max_uses:
                return False
        return True

    def calculate_discount(self, consultation_fee):
        """
        Returns the discount amount in Taka for a given consultation fee.
        Never exceeds the fee itself.
        """
        fee = float(consultation_fee)
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = fee * float(self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, float(self.max_discount_amount))
        else:
            discount = float(self.discount_value)
        return min(round(discount), int(fee))

    def get_user_uses(self, user):
        """Returns how many times a specific user has used this coupon."""
        return self.usages.filter(user=user).count()

    def check_customer_type(self, user):
        """
        Returns True if user matches the coupon's customer type restriction.
        'new' = never completed a paid consultation.
        'returning' = has at least one completed paid consultation.
        """
        if self.customer_type == self.CustomerType.ALL:
            return True

        has_completed = Appointment.objects.filter(
            user=user,
            status='completed',
        ).exists()

        if self.customer_type == self.CustomerType.NEW:
            return not has_completed
        if self.customer_type == self.CustomerType.RETURNING:
            return has_completed
        return True


class CouponUsage(models.Model):
    coupon          = models.ForeignKey(
        CouponCode,
        on_delete=models.CASCADE,
        related_name='usages',
    )
    user            = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='coupon_usages',
    )
    appointment     = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='coupon_usage',
        null=True, blank=True,
    )
    discount_amount = models.PositiveIntegerField(
        help_text="Actual Taka amount discounted",
    )
    used_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.coupon.code} — {self.user.email} — ৳{self.discount_amount}"