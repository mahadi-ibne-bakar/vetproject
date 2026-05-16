from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Avg, Count

from accounts.decorators import login_required_user, login_required_vet
from .models import Pet, VetAvailability, BlockedDate, Appointment, Payment, Prescription
from .forms import (
    VetProfileForm, PetForm, PrescriptionForm,
    RecurringAvailabilityForm, SpecificDateAvailabilityForm, BlockedDateForm,
)

import json
from django.http import JsonResponse
from consultations.slots import get_available_slots as compute_slots
from consultations.slots import get_available_dates

# ── Vet Dashboard ──────────────────────────────────────────────────────────────

@login_required_vet
def vet_dashboard(request):
    vet_profile = request.user.vet_profile
    today = timezone.localdate()
    now = timezone.localtime()

    # Today's appointments
    todays_appointments = Appointment.objects.filter(
        vet=vet_profile,
        date=today,
        status__in=['confirmed', 'in_progress'],
    ).select_related('user', 'pet').order_by('start_time')

    # Upcoming appointments (next 7 days, not today)
    upcoming_appointments = Appointment.objects.filter(
        vet=vet_profile,
        date__gt=today,
        date__lte=today + timedelta(days=7),
        status='confirmed',
    ).select_related('user', 'pet').order_by('date', 'start_time')

    # Stats
    total_consultations = Appointment.objects.filter(
        vet=vet_profile,
        status='completed',
    ).count()

    avg_rating = vet_profile.reviews.filter(
        is_visible=True
    ).aggregate(avg=Avg('rating'))['avg']

    pending_prescriptions = Appointment.objects.filter(
        vet=vet_profile,
        status='awaiting_second_payment',
    ).exclude(
        prescription__isnull=False
    ).count()

    upcoming_count = Appointment.objects.filter(
        vet=vet_profile,
        date__gte=today,
        status='confirmed',
    ).count()

    # Recent completed consultations
    recent_completed = Appointment.objects.filter(
        vet=vet_profile,
        status='completed',
    ).select_related('user', 'pet').order_by('-date', '-start_time')[:5]

    ctx = {
        'vet_profile': vet_profile,
        'today': today,
        'todays_appointments': todays_appointments,
        'upcoming_appointments': upcoming_appointments,
        'total_consultations': total_consultations,
        'avg_rating': round(avg_rating, 1) if avg_rating else None,
        'pending_prescriptions': pending_prescriptions,
        'upcoming_count': upcoming_count,
        'recent_completed': recent_completed,
    }
    return render(request, 'vet/dashboard.html', ctx)


# ── Remaining placeholders ─────────────────────────────────────────────────────

@login_required_vet
def vet_edit_profile(request):
    vet_profile = request.user.vet_profile

    if request.method == 'POST':
        form = VetProfileForm(
            request.POST,
            request.FILES,
            instance=vet_profile,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('consultations:vet_edit_profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = VetProfileForm(
            instance=vet_profile,
            user=request.user,
        )

    return render(request, 'vet/edit_profile.html', {
        'form': form,
        'vet_profile': vet_profile,
    })

@login_required_vet
def vet_availability(request):
    vet_profile = request.user.vet_profile
    today = timezone.localdate()

    recurring_windows = VetAvailability.objects.filter(
        vet=vet_profile,
        is_recurring=True,
        is_active=True,
    ).order_by('day_of_week', 'start_time')

    specific_windows = VetAvailability.objects.filter(
        vet=vet_profile,
        is_recurring=False,
        is_active=True,
        specific_date__gte=today,
    ).order_by('specific_date', 'start_time')

    blocked_dates = BlockedDate.objects.filter(
        vet=vet_profile,
        date__gte=today,
    ).order_by('date')

    # Group recurring windows by day for display
    days = {i: [] for i in range(7)}
    day_names = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    for window in recurring_windows:
        if window.day_of_week is not None:
            days[window.day_of_week].append(window)

    recurring_form = RecurringAvailabilityForm()
    specific_form  = SpecificDateAvailabilityForm()
    blocked_form   = BlockedDateForm()

    ctx = {
        'vet_profile': vet_profile,
        'recurring_windows': recurring_windows,
        'specific_windows': specific_windows,
        'blocked_dates': blocked_dates,
        'days': days,
        'day_names': day_names,
        'days_with_names': [(i, day_names[i], days[i]) for i in range(7)],
        'recurring_form': recurring_form,
        'specific_form': specific_form,
        'blocked_form': blocked_form,
    }
    return render(request, 'vet/availability.html', ctx)


@login_required_vet
def add_availability(request):
    vet_profile = request.user.vet_profile

    if request.method != 'POST':
        return redirect('consultations:vet_availability')

    availability_type = request.POST.get('availability_type')

    if availability_type == 'recurring':
        form = RecurringAvailabilityForm(request.POST)
        if form.is_valid():
            days     = form.cleaned_data['days']
            end_date = form.cleaned_data.get('end_date')

            # Collect the time windows from the form
            windows = []
            for i in range(1, 4):
                start = form.cleaned_data.get(f'window{i}_start')
                end   = form.cleaned_data.get(f'window{i}_end')
                if start and end:
                    windows.append((start, end))

            if not windows:
                messages.error(request, "Please add at least one time window.")
                return redirect('consultations:vet_availability')

            # Create one VetAvailability row per day per window
            created_count = 0
            for day in days:
                for start_time, end_time in windows:
                    # Check for duplicate — same vet, day, start, end
                    exists = VetAvailability.objects.filter(
                        vet=vet_profile,
                        is_recurring=True,
                        day_of_week=int(day),
                        start_time=start_time,
                        end_time=end_time,
                        is_active=True,
                    ).exists()
                    if not exists:
                        VetAvailability.objects.create(
                            vet=vet_profile,
                            is_recurring=True,
                            day_of_week=int(day),
                            start_time=start_time,
                            end_time=end_time,
                            end_date=end_date,
                            is_active=True,
                        )
                        created_count += 1

            if created_count > 0:
                messages.success(
                    request,
                    f"Created {created_count} availability window"
                    f"{'s' if created_count != 1 else ''}."
                )
            else:
                messages.warning(
                    request,
                    "No new windows were added — they may already exist."
                )

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")

    elif availability_type == 'specific':
        form = SpecificDateAvailabilityForm(request.POST)
        if form.is_valid():
            specific_date = form.cleaned_data['specific_date']
            today = timezone.localdate()

            if specific_date < today:
                messages.error(request, "Cannot add availability for a past date.")
                return redirect('consultations:vet_availability')

            # Check if this date is blocked
            if BlockedDate.objects.filter(
                vet=vet_profile, date=specific_date
            ).exists():
                messages.error(
                    request,
                    f"{specific_date} is currently blocked. "
                    f"Remove the block first to add availability."
                )
                return redirect('consultations:vet_availability')

            windows = []
            for i in range(1, 4):
                start = form.cleaned_data.get(f'window{i}_start')
                end   = form.cleaned_data.get(f'window{i}_end')
                if start and end:
                    windows.append((start, end))

            if not windows:
                messages.error(request, "Please add at least one time window.")
                return redirect('consultations:vet_availability')

            created_count = 0
            for start_time, end_time in windows:
                exists = VetAvailability.objects.filter(
                    vet=vet_profile,
                    is_recurring=False,
                    specific_date=specific_date,
                    start_time=start_time,
                    end_time=end_time,
                    is_active=True,
                ).exists()
                if not exists:
                    VetAvailability.objects.create(
                        vet=vet_profile,
                        is_recurring=False,
                        specific_date=specific_date,
                        start_time=start_time,
                        end_time=end_time,
                        is_active=True,
                    )
                    created_count += 1

            messages.success(
                request,
                f"Added {created_count} window"
                f"{'s' if created_count != 1 else ''} for {specific_date}."
            )

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")

    elif availability_type == 'blocked':
        form = BlockedDateForm(request.POST)
        if form.is_valid():
            date = form.cleaned_data['date']
            today = timezone.localdate()

            if date < today:
                messages.error(request, "Cannot block a past date.")
                return redirect('consultations:vet_availability')

            # Check if there are confirmed appointments on this date
            booked = Appointment.objects.filter(
                vet=vet_profile,
                date=date,
                status__in=['confirmed', 'in_progress'],
            ).exists()

            if booked:
                messages.error(
                    request,
                    f"Cannot block {date} — there are confirmed appointments on this day. "
                    f"Cancel or reschedule them first."
                )
                return redirect('consultations:vet_availability')

            blocked, created = BlockedDate.objects.get_or_create(
                vet=vet_profile,
                date=date,
                defaults={'reason': form.cleaned_data.get('reason', '')}
            )
            if created:
                messages.success(request, f"{date} has been blocked.")
            else:
                messages.warning(request, f"{date} is already blocked.")

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")

    return redirect('consultations:vet_availability')


@login_required_vet
def delete_availability(request, window_id):
    if request.method == 'POST':
        action = request.POST.get('action', 'window')

        if action == 'blocked':
            # Deleting a blocked date
            blocked = get_object_or_404(
                BlockedDate, id=window_id, vet=request.user.vet_profile
            )
            date = blocked.date
            blocked.delete()
            messages.success(request, f"Block removed for {date}.")

        else:
            # Deleting an availability window
            window = get_object_or_404(
                VetAvailability, id=window_id, vet=request.user.vet_profile
            )
            # Check for confirmed appointments in this window
            if window.is_recurring:
                booked = Appointment.objects.filter(
                    vet=request.user.vet_profile,
                    date__week_day=window.day_of_week + 2,
                    start_time=window.start_time,
                    status__in=['confirmed', 'in_progress'],
                ).exists()
            else:
                booked = Appointment.objects.filter(
                    vet=request.user.vet_profile,
                    date=window.specific_date,
                    start_time=window.start_time,
                    status__in=['confirmed', 'in_progress'],
                ).exists()

            if booked:
                messages.error(
                    request,
                    "Cannot remove this window — there are confirmed appointments in it."
                )
            else:
                window.delete()
                messages.success(request, "Availability window removed.")

    return redirect('consultations:vet_availability')

@login_required_vet
def vet_appointments(request):
    return HttpResponse("Coming soon")

@login_required_vet
def vet_appointment_detail(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_vet
def start_consultation(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_vet
def end_consultation(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_vet
def submit_prescription(request, appointment_id):
    return HttpResponse("Coming soon")


# ── User-facing placeholders ───────────────────────────────────────────────────

def vet_list(request):
    return HttpResponse("Coming soon")

def vet_detail(request, vet_id):
    return HttpResponse("Coming soon")

def book_appointment(request, vet_id):
    return HttpResponse("Coming soon")

def get_available_slots(request, vet_id):
    """
    AJAX endpoint. Returns available slots for a vet on a given date.
    Called by the booking form when the user picks a date.

    GET /consultations/book/<vet_id>/slots/?date=2026-05-20
    Returns: { "slots": [ { "start_str": "18:00", "end_str": "18:15",
                             "label": "6:00 PM – 6:15 PM" }, ... ] }
    """
    from accounts.models import VetProfile
    from datetime import date as date_cls

    vet_profile = get_object_or_404(
        VetProfile,
        id=vet_id,
        application_status='approved',
        is_active=True,
    )

    date_str = request.GET.get('date', '')
    if not date_str:
        return JsonResponse({'error': 'No date provided'}, status=400)

    try:
        target_date = date_cls.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    today = timezone.localdate()
    if target_date < today:
        return JsonResponse({'slots': [], 'message': 'Date is in the past'})

    slots = compute_slots(vet_profile, target_date)

    return JsonResponse({
        'slots': [
            {
                'start_str': s['start_str'],
                'end_str':   s['end_str'],
                'label':     s['label'],
            }
            for s in slots
        ]
    })

def submit_payment(request, appointment_id):
    return HttpResponse("Coming soon")

def payment_done(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def my_appointments(request):
    return HttpResponse("Coming soon")

@login_required_user
def appointment_detail(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def reschedule_appointment(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def cancel_appointment(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def submit_feedback(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def submit_second_payment(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def my_pets(request):
    return HttpResponse("Coming soon")

@login_required_user
def add_pet(request):
    return HttpResponse("Coming soon")

@login_required_user
def edit_pet(request, pet_id):
    return HttpResponse("Coming soon")

@login_required_user
def delete_pet(request, pet_id):
    return HttpResponse("Coming soon")

@login_required_user
def view_prescription(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def download_prescription(request, appointment_id):
    return HttpResponse("Coming soon")