"""
Management command to send appointment reminders.
Should be run every 5 minutes via a cron job or scheduled task.

Usage: python manage.py send_reminders

How it works:
- Finds all confirmed appointments starting in 25-35 minutes from now
- Sends reminder emails to both user and vet
- Marks appointment with reminder_sent flag to avoid duplicate sends

We use a 25-35 minute window (not exactly 30) to account for the
fact that the command runs every 5 minutes — this ensures every
appointment gets exactly one reminder.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime

from consultations.models import Appointment
from consultations.emails import send_appointment_reminder


class Command(BaseCommand):
    help = 'Send appointment reminders for appointments starting in ~30 minutes'

    def handle(self, *args, **options):
        now          = timezone.localtime()
        today        = now.date()
        window_start = (now + timedelta(minutes=25)).time()
        window_end   = (now + timedelta(minutes=35)).time()

        # Find confirmed appointments in the 30-minute window
        # that haven't had a reminder sent yet
        appointments = Appointment.objects.filter(
            date=today,
            status='confirmed',
            reminder_sent=False,
            start_time__gte=window_start,
            start_time__lte=window_end,
        ).select_related('user', 'vet__user', 'pet', 'meet_link')

        if not appointments.exists():
            self.stdout.write("No reminders to send.")
            return

        sent_count = 0
        for appt in appointments:
            send_appointment_reminder(appt)
            appt.reminder_sent = True
            appt.save(update_fields=['reminder_sent'])
            sent_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Reminder sent for appointment {appt.id} — "
                    f"{appt.pet.name} with Dr. {appt.vet.user.last_name} "
                    f"at {appt.start_time.strftime('%H:%M')}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f"Done. {sent_count} reminder(s) sent.")
        )