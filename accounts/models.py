from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model extending Django's built-in user.
    A single User can be a pet owner, vet, or admin — determined by role.
    We define this from day one so we can freely add fields without
    painful migrations later.
    """

    class Role(models.TextChoices):
        USER = 'user', 'Pet Owner'
        VET = 'vet', 'Veterinarian'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    profile_photo = models.ImageField(
        upload_to='profile_photos/',
        blank=True,
        null=True,
    )
    email_verified = models.BooleanField(
        default=True,
        help_text="False only when email verification is enabled and user hasn't verified yet.",
    )
    is_banned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_vet(self):
        return self.role == self.Role.VET

    @property
    def is_pet_owner(self):
        return self.role == self.Role.USER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN


class VetProfile(models.Model):
    """
    Extended profile for veterinarians.
    Created when a vet submits an application.
    Only visible/active after admin approval.
    """

    class ApplicationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='vet_profile',
    )
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(
        upload_to='vet_photos/',
        blank=True,
        null=True,
    )

    # Credentials
    bvc_registration_number = models.CharField(max_length=100, blank=True)
    education = models.TextField(
        blank=True,
        help_text="Degrees and institutions, one per line",
    )
    years_of_experience = models.PositiveIntegerField(default=0)
    specializations = models.TextField(
        blank=True,
        help_text="e.g. Cats, Dogs, Dermatology, Nutrition",
    )

    # Admin controls
    application_status = models.CharField(
        max_length=10,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
    )
    rejection_reason = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=False,
        help_text="Admin can deactivate a vet without deleting them",
    )

    # Fees — admin sets the consultation fee per vet or globally
    consultation_fee = models.PositiveIntegerField(
        default=250,
        help_text="Fee in BDT charged after consultation (booking fee is separate)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"

    @property
    def average_rating(self):
        reviews = self.reviews.filter(is_visible=True)
        if not reviews.exists():
            return None
        return round(reviews.aggregate(
            avg=models.Avg('rating')
        )['avg'], 1)

    @property
    def total_consultations(self):
        return self.appointments.filter(
            status='completed'
        ).count()