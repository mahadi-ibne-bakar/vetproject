from django.db import models
from django.utils.text import slugify


class BlogPost(models.Model):
    """
    Written by vets or admins.
    Vets submit drafts which admin reviews before publishing.
    Admins can publish directly.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending Review'
        PUBLISHED = 'published', 'Published'
        REJECTED = 'rejected', 'Rejected'

    author = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='blog_posts',
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        help_text="Auto-generated from title. Used in the URL.",
    )
    content = models.TextField()
    featured_image = models.ImageField(
        upload_to='blog_images/',
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    rejection_note = models.TextField(
        blank=True,
        help_text="Admin's note to vet explaining why the post was rejected",
    )
    published_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not set
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-published_at', '-created_at']


class Review(models.Model):
    """
    Left by pet owner after a completed consultation.
    Only one review per appointment allowed.
    Admin can hide reviews without deleting them.
    """

    appointment = models.OneToOneField(
        'consultations.Appointment',
        on_delete=models.CASCADE,
        related_name='review',
    )
    reviewer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reviews_given',
    )
    vet = models.ForeignKey(
        'accounts.VetProfile',
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    rating = models.PositiveIntegerField(
        help_text="1 to 5 stars",
    )
    comment = models.TextField(blank=True)
    is_visible = models.BooleanField(
        default=True,
        help_text="Admin can hide a review without deleting it",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reviewer.username} → {self.vet} ({self.rating}★)"

    class Meta:
        ordering = ['-created_at']