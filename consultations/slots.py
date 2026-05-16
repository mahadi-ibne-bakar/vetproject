"""
Slot Generation Engine
======================
Given a vet and a date, returns a list of available time slots.

Rules applied in order:
1. If the date is blocked → return empty (no slots)
2. Collect all availability windows for that date:
   a. Specific-date windows (exact match)
   b. Recurring windows (matching day of week, not expired)
3. If no windows found → return empty
4. Generate slots of slot_duration_minutes within each window
5. Remove slots that are already booked (confirmed or in_progress)
6. If the date is today, remove slots that have already passed
7. Return the remaining slots sorted by time
"""

from datetime import datetime, date, time, timedelta
from django.utils import timezone

from .models import VetAvailability, BlockedDate, Appointment
from core.models import SiteSettings


def get_available_slots(vet_profile, target_date: date) -> list[dict]:
    """
    Returns a list of available slot dicts for a vet on a given date.

    Each slot dict:
    {
        'start': time object,
        'end':   time object,
        'start_str': '18:00',
        'end_str':   '18:15',
        'label':     '6:00 PM – 6:15 PM',
    }

    Returns [] if no slots are available.
    """
    today = timezone.localdate()

    # ── Rule 1: Blocked date overrides everything ─────────────────────────────
    if BlockedDate.objects.filter(vet=vet_profile, date=target_date).exists():
        return []

    # ── Rule 2: Collect windows ───────────────────────────────────────────────
    windows = []  # list of (start_time, end_time)

    # 2a: Specific-date windows
    specific = VetAvailability.objects.filter(
        vet=vet_profile,
        is_recurring=False,
        specific_date=target_date,
        is_active=True,
    )
    for w in specific:
        windows.append((w.start_time, w.end_time))

    # 2b: Recurring windows (if no specific windows override this date)
    # Specific-date windows take priority — if any exist, skip recurring
    if not windows:
        day_of_week = target_date.weekday()  # 0=Monday, 6=Sunday
        recurring = VetAvailability.objects.filter(
            vet=vet_profile,
            is_recurring=True,
            day_of_week=day_of_week,
            is_active=True,
        ).filter(
            # end_date is null (no end) OR end_date >= target_date (still active)
            end_date__isnull=True
        ) | VetAvailability.objects.filter(
            vet=vet_profile,
            is_recurring=True,
            day_of_week=day_of_week,
            is_active=True,
            end_date__gte=target_date,
        )
        for w in recurring:
            windows.append((w.start_time, w.end_time))

    # ── Rule 3: No windows → no slots ─────────────────────────────────────────
    if not windows:
        return []

    # ── Rule 4: Generate slots ────────────────────────────────────────────────
    settings       = SiteSettings.get()
    slot_minutes   = settings.slot_duration_minutes
    slot_delta     = timedelta(minutes=slot_minutes)
    all_slots      = []  # list of (start_time, end_time)

    for (window_start, window_end) in windows:
        # Convert time → datetime for arithmetic
        base = datetime(
            target_date.year,
            target_date.month,
            target_date.day,
        )
        current = datetime.combine(target_date, window_start)
        window_end_dt = datetime.combine(target_date, window_end)

        while current + slot_delta <= window_end_dt:
            slot_start = current.time()
            slot_end   = (current + slot_delta).time()
            all_slots.append((slot_start, slot_end))
            current += slot_delta

    # ── Rule 5: Remove already-booked slots ───────────────────────────────────
    booked_starts = set(
        Appointment.objects.filter(
            vet=vet_profile,
            date=target_date,
            status__in=['confirmed', 'in_progress', 'pending_payment'],
        ).values_list('start_time', flat=True)
    )

    available = [
        (s, e) for (s, e) in all_slots
        if s not in booked_starts
    ]

    # ── Rule 6: Remove past slots if today ────────────────────────────────────
    if target_date == today:
        now = timezone.localtime().time()
        # Add a 10-minute buffer so users can't book a slot starting very soon
        buffer = (
            datetime.combine(target_date, now) + timedelta(minutes=10)
        ).time()
        available = [(s, e) for (s, e) in available if s >= buffer]

    # ── Rule 7: Build output dicts ────────────────────────────────────────────
    def fmt_time(t: time) -> str:
        """Format time as '6:00 PM'."""
        return datetime.combine(date.today(), t).strftime('%-I:%M %p')

    result = []
    for (s, e) in sorted(available):
        result.append({
            'start':     s,
            'end':       e,
            'start_str': s.strftime('%H:%M'),
            'end_str':   e.strftime('%H:%M'),
            'label':     f"{fmt_time(s)} – {fmt_time(e)}",
        })

    return result


def get_available_dates(vet_profile, days_ahead: int = 30) -> list[date]:
    """
    Returns a list of dates in the next `days_ahead` days
    that have at least one available slot for this vet.
    Used to highlight available dates in the booking calendar.
    """
    today      = timezone.localdate()
    available  = []

    for i in range(days_ahead):
        target = today + timedelta(days=i)
        slots  = get_available_slots(vet_profile, target)
        if slots:
            available.append(target)

    return available