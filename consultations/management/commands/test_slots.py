"""
Management command to test the slot generation engine.
Usage: python manage.py test_slots <vet_email> <date>
Example: python manage.py test_slots vet@example.com 2026-05-24
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date

from accounts.models import User
from consultations.slots import get_available_slots, get_available_dates


class Command(BaseCommand):
    help = 'Test slot generation for a vet on a given date'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Vet email address')
        parser.add_argument('date',  type=str, help='Date in YYYY-MM-DD format')

    def handle(self, *args, **options):
        email = options['email']
        date_str = options['date']

        try:
            user = User.objects.get(email=email, role='vet')
            vet_profile = user.vet_profile
        except User.DoesNotExist:
            self.stderr.write(f"No vet found with email: {email}")
            return
        except Exception as e:
            self.stderr.write(f"Error: {e}")
            return

        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            self.stderr.write("Invalid date format. Use YYYY-MM-DD")
            return

        self.stdout.write(f"\nVet: {vet_profile}")
        self.stdout.write(f"Date: {target_date} ({target_date.strftime('%A')})")
        self.stdout.write("─" * 40)

        slots = get_available_slots(vet_profile, target_date)

        if not slots:
            self.stdout.write(self.style.WARNING("No slots available."))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{len(slots)} slot(s) available:")
            )
            for slot in slots:
                self.stdout.write(f"  {slot['label']}")

        self.stdout.write("\nAvailable dates in next 30 days:")
        available_dates = get_available_dates(vet_profile, days_ahead=30)
        if available_dates:
            for d in available_dates[:10]:
                self.stdout.write(f"  {d} ({d.strftime('%A')})")
            if len(available_dates) > 10:
                self.stdout.write(f"  ... and {len(available_dates) - 10} more")
        else:
            self.stdout.write(self.style.WARNING("  No available dates found."))