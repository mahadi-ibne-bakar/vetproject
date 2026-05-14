from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model — extends Django's built-in user.
    We start minimal here and add fields on Day 2.
    Using a custom model from day one means we can freely
    add fields later without painful migrations.
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