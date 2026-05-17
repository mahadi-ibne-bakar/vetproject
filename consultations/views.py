from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Avg, Count

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
from core.models import SiteSettings, MeetLink

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
    from accounts.models import VetProfile
    from consultations.slots import get_available_dates

    specialty_filter = request.GET.get('specialty', '').strip()
    search = request.GET.get('search', '').strip()

    vets = VetProfile.objects.filter(
        application_status='approved',
        is_active=True,
    ).select_related('user').prefetch_related('reviews')

    if specialty_filter:
        vets = vets.filter(
            specializations__icontains=specialty_filter
        )

    if search:
        vets = vets.filter(
            user__first_name__icontains=search
        ) | vets.filter(
            user__last_name__icontains=search
        ) | vets.filter(
            specializations__icontains=search
        )

    # Annotate each vet with available dates count and average rating
    from django.db.models import Avg, Count
    vets = vets.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_visible=True)),
        review_count=Count('reviews', filter=Q(reviews__is_visible=True)),
        consultation_count=Count('appointments', filter=Q(appointments__status='completed')),
    )

    # Common specializations for filter chips
    all_specializations = []
    for vet in VetProfile.objects.filter(
        application_status='approved', is_active=True
    ):
        for s in vet.specializations.split(','):
            s = s.strip()
            if s and s not in all_specializations:
                all_specializations.append(s)

    ctx = {
        'vets': vets,
        'specialty_filter': specialty_filter,
        'search': search,
        'all_specializations': all_specializations[:10],
        'total_count': vets.count(),
    }
    return render(request, 'public/vet_list.html', ctx)

def vet_detail(request, vet_id):
    from accounts.models import VetProfile
    from blog.models import Review

    vet = get_object_or_404(
        VetProfile,
        id=vet_id,
        application_status='approved',
        is_active=True,
    )

    reviews = Review.objects.filter(
        vet=vet,
        is_visible=True,
    ).select_related('reviewer').order_by('-created_at')[:10]

    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']

    # Get available dates for the next 30 days
    available_dates = get_available_dates(vet, days_ahead=30)
    available_dates_str = [str(d) for d in available_dates]

    ctx = {
        'vet': vet,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1) if avg_rating else None,
        'available_dates_json': json.dumps(available_dates_str),
        'available_dates': available_dates,
    }
    return render(request, 'public/vet_detail.html', ctx)

@login_required_user
def book_appointment(request, vet_id):
    from accounts.models import VetProfile
    from core.models import SiteSettings
    from datetime import date as date_cls

    # Check service is enabled
    settings = SiteSettings.get()
    if not settings.booking_enabled:
        messages.error(request, "Booking is currently disabled. Please check back soon.")
        return redirect('core:home')

    vet = get_object_or_404(
        VetProfile,
        id=vet_id,
        application_status='approved',
        is_active=True,
    )

    # Get date and slot from URL params
    date_str    = request.GET.get('date', '')
    start_str   = request.GET.get('start', '')
    end_str     = request.GET.get('end', '')
    next_url    = request.GET.get('next', '')

    # Validate date and slot
    selected_date = None
    if date_str:
        try:
            selected_date = date_cls.fromisoformat(date_str)
        except ValueError:
            pass

    if not selected_date or not start_str or not end_str:
        messages.error(request, "Please select a date and time slot first.")
        return redirect('consultations:vet_detail', vet_id=vet_id)

    # Confirm the slot is still available
    from consultations.slots import get_available_slots as compute_slots
    available = compute_slots(vet, selected_date)
    available_starts = [s['start_str'] for s in available]

    if start_str not in available_starts:
        messages.error(
            request,
            "That slot is no longer available. Please choose another."
        )
        return redirect(
            f"{{% url 'consultations:vet_detail' vet_id %}}?"
            f"date={date_str}"
        )

    # Smart pet redirect
    user_pets = Pet.objects.filter(owner=request.user)
    if not user_pets.exists():
        from django.urls import reverse
        from urllib.parse import urlencode, quote
        booking_next = (
            f"{request.path}"
            f"?date={date_str}&start={start_str}&end={end_str}"
        )
        messages.info(
            request,
            "First, tell us about your pet so we can get started."
        )
        return redirect(
            reverse('consultations:add_pet')
            + '?'
            + urlencode({'next': booking_next, 'context': 'booking'})
        )

    if request.method == 'POST':
        pet_id = request.POST.get('pet_id')
        primary_complaint = request.POST.get('primary_complaint')
        description = request.POST.get('complaint_description', '').strip()

        # Validate
        errors = []
        if not pet_id:
            errors.append("Please select a pet.")
        if not primary_complaint:
            errors.append("Please select the primary complaint.")
        if not description:
            errors.append("Please describe what is wrong with your pet.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            try:
                pet = Pet.objects.get(id=pet_id, owner=request.user)
            except Pet.DoesNotExist:
                messages.error(request, "Invalid pet selection.")
                pet = None

            if pet:
                # Double-check slot still available
                if start_str not in available_starts:
                    messages.error(
                        request,
                        "That slot is no longer available. Please choose another."
                    )
                    from django.urls import reverse
                    return redirect(
                        reverse('consultations:vet_detail', args=[vet_id])
                        + f"?date={date_str}"
                    )

                # Create appointment in pending_payment status
                appointment = Appointment.objects.create(
                    pet=pet,
                    vet=vet,
                    user=request.user,
                    date=selected_date,
                    start_time=start_str,
                    end_time=end_str,
                    status=Appointment.Status.PENDING_PAYMENT,
                    primary_complaint=primary_complaint,
                    complaint_description=description,
                )

                # Handle symptom photo if uploaded
                if 'symptom_photo' in request.FILES:
                    appointment.symptom_photo = request.FILES['symptom_photo']
                    appointment.save()

                messages.success(
                    request,
                    "Appointment created. Please complete payment to confirm."
                )
                return redirect(
                    'consultations:submit_payment',
                    appointment_id=appointment.id
                )

    # Complaint choices for the form
    complaint_choices = Appointment.PrimaryComplaint.choices

    ctx = {
        'vet': vet,
        'user_pets': user_pets,
        'selected_date': selected_date,
        'date_str': date_str,
        'start_str': start_str,
        'end_str': end_str,
        'complaint_choices': complaint_choices,
    }
    return render(request, 'public/book_appointment.html', ctx)

def book_by_time(request):
    """
    Time-first booking flow.
    Step 1: User picks a date.
    Step 2: User picks a time slot.
    Step 3: Available vets for that slot are shown.
    Step 4: User picks a vet and proceeds to the booking form.

    The slot and date are passed as GET params so the page is shareable.
    """
    from accounts.models import VetProfile
    from consultations.slots import get_available_slots as compute_slots
    from datetime import date as date_cls

    today = timezone.localdate()
    selected_date_str = request.GET.get('date', today.isoformat())
    selected_start    = request.GET.get('start', '')
    selected_end      = request.GET.get('end', '')

    selected_date = None
    available_slots = []
    available_vets  = []
    
    try:
        selected_date = date_cls.fromisoformat(selected_date_str)
    except ValueError:
        selected_date = today
        selected_date_str = today.isoformat()

    if selected_date and selected_date >= today:
        # Get all active approved vets
        all_vets = VetProfile.objects.filter(
            application_status='approved',
            is_active=True,
        ).select_related('user')

        # Collect all slots across all vets for this date
        slot_map = {}  # start_str -> list of (slot_dict, vet)
        for vet in all_vets:
            vet_slots = compute_slots(vet, selected_date)
            for slot in vet_slots:
                key = slot['start_str']
                if key not in slot_map:
                    slot_map[key] = {'slot': slot, 'vets': []}
                slot_map[key]['vets'].append(vet)

        # Build sorted list of unique slots
        available_slots = [
            {
                'start_str': key,
                'end_str':   slot_map[key]['slot']['end_str'],
                'label':     slot_map[key]['slot']['label'],
                'vet_count': len(slot_map[key]['vets']),
            }
            for key in sorted(slot_map.keys())
        ]

        # If a slot is selected, get the vets for it
        if selected_start and selected_start in slot_map:
            available_vets = slot_map[selected_start]['vets']

    ctx = {
        'today': today.isoformat(),
        'selected_date': selected_date,
        'selected_date_str': selected_date_str,
        'selected_start': selected_start,
        'selected_end': selected_end,
        'available_slots': available_slots,
        'available_vets': available_vets,
    }
    return render(request, 'public/book_by_time.html', ctx)

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

@login_required_user
def submit_payment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        status=Appointment.Status.PENDING_PAYMENT,
    )
    settings = SiteSettings.get()

    if request.method == 'POST':
        bkash_number   = request.POST.get('bkash_number', '').strip()
        transaction_id = request.POST.get('transaction_id', '').strip().upper()

        errors = []

        # Validate bKash number — must be 11 digits starting with 01
        import re
        if not re.match(r'^01[0-9]{9}$', bkash_number):
            errors.append(
                "Invalid bKash number. Must be 11 digits starting with 01."
            )

        # Validate transaction ID — bKash TrxIDs are alphanumeric, 8-12 chars
        if not re.match(r'^[A-Z0-9]{8,12}$', transaction_id):
            errors.append(
                "Invalid transaction ID. "
                "bKash transaction IDs are 8–12 characters (letters and numbers)."
            )

        # Check transaction ID not already used
        if Payment.objects.filter(transaction_id=transaction_id).exists():
            errors.append(
                "This transaction ID has already been submitted. "
                "If this is a mistake, please contact support."
            )

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            # Create the pending payment record
            Payment.objects.create(
                appointment=appointment,
                payment_type=Payment.PaymentType.BOOKING,
                amount=settings.booking_fee,
                bkash_number=bkash_number,
                transaction_id=transaction_id,
                status=Payment.Status.PENDING,
            )
            messages.success(
                request,
                "Payment submitted. We'll verify it shortly and confirm your booking."
            )
            return redirect('consultations:payment_done', appointment_id=appointment.id)

    # Get the bKash number to display from site settings
    # We'll store it as a simple setting — for now hardcode and we'll
    # add it to SiteSettings in a moment
    ctx = {
        'appointment': appointment,
        'vet': appointment.vet,
        'booking_fee': settings.booking_fee,
        'bkash_merchant_number': getattr(settings, 'bkash_merchant_number', ''),
    }
    return render(request, 'user/submit_payment.html', ctx)


@login_required_user
def payment_done(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
    )
    return render(request, 'user/payment_done.html', {
        'appointment': appointment,
    })


@login_required_user
def submit_second_payment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        status=Appointment.Status.AWAITING_SECOND_PAYMENT,
    )

    if request.method == 'POST':
        bkash_number   = request.POST.get('bkash_number', '').strip()
        transaction_id = request.POST.get('transaction_id', '').strip().upper()

        import re
        errors = []

        if not re.match(r'^01[0-9]{9}$', bkash_number):
            errors.append("Invalid bKash number.")

        if not re.match(r'^[A-Z0-9]{8,12}$', transaction_id):
            errors.append("Invalid transaction ID.")

        if Payment.objects.filter(transaction_id=transaction_id).exists():
            errors.append("This transaction ID has already been submitted.")

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            Payment.objects.create(
                appointment=appointment,
                payment_type=Payment.PaymentType.CONSULTATION,
                amount=appointment.vet.consultation_fee,
                bkash_number=bkash_number,
                transaction_id=transaction_id,
                status=Payment.Status.PENDING,
            )
            messages.success(
                request,
                "Payment submitted. "
                "Your prescription will be available once payment is verified."
            )
            return redirect(
                'consultations:appointment_detail',
                appointment_id=appointment.id
            )

    settings = SiteSettings.get()
    ctx = {
        'appointment': appointment,
        'consultation_fee': appointment.vet.consultation_fee,
        'bkash_merchant_number': getattr(settings, 'bkash_merchant_number', ''),
    }
    return render(request, 'user/submit_second_payment.html', ctx)

@login_required_user
def my_appointments(request):
    tab = request.GET.get('tab', 'upcoming')

    upcoming = Appointment.objects.filter(
        user=request.user,
        status__in=[
            'pending_payment', 'confirmed',
            'rescheduled', 'in_progress',
        ],
    ).select_related('vet__user', 'pet').order_by('date', 'start_time')

    awaiting_payment = Appointment.objects.filter(
        user=request.user,
        status='awaiting_second_payment',
    ).select_related('vet__user', 'pet').order_by('date')

    past = Appointment.objects.filter(
        user=request.user,
        status__in=['completed', 'cancelled'],
    ).select_related('vet__user', 'pet').order_by('-date', '-start_time')

    ctx = {
        'tab': tab,
        'upcoming': upcoming,
        'awaiting_payment': awaiting_payment,
        'past': past,
        'upcoming_count': upcoming.count(),
        'awaiting_count': awaiting_payment.count(),
        'past_count': past.count(),
    }
    return render(request, 'user/my_appointments.html', ctx)


@login_required_user
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
    )

    # Get payment records
    booking_payment = appointment.payments.filter(
        payment_type='booking'
    ).first()

    consultation_payment = appointment.payments.filter(
        payment_type='consultation'
    ).first()

    # Check if prescription is available
    try:
        prescription = appointment.prescription
    except Exception:
        prescription = None

    # Check if feedback already submitted
    feedback_submitted = bool(appointment.feedback_rating)

    ctx = {
        'appointment': appointment,
        'booking_payment': booking_payment,
        'consultation_payment': consultation_payment,
        'prescription': prescription,
        'feedback_submitted': feedback_submitted,
    }
    return render(request, 'user/appointment_detail.html', ctx)

@login_required_user
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
    )

    if request.method == 'POST':
        # Only allow cancelling pending or confirmed appointments
        if appointment.status not in ['pending_payment', 'confirmed', 'rescheduled']:
            messages.error(request, "This appointment cannot be cancelled.")
            return redirect('consultations:appointment_detail',
                          appointment_id=appointment_id)

        reason = request.POST.get('reason', '').strip()
        appointment.status = Appointment.Status.CANCELLED
        appointment.cancellation_reason = reason
        appointment.save()

        # Free up the meet link if one was assigned
        if appointment.meet_link:
            appointment.meet_link.is_in_use = False
            appointment.meet_link.save()
            appointment.meet_link = None
            appointment.save()

        # Flag booking payment for refund if it was verified
        booking_payment = appointment.payments.filter(
            payment_type='booking',
            status='verified',
        ).first()

        if booking_payment:
            settings = SiteSettings.get()
            booking_payment.refund_amount = max(
                0, booking_payment.amount - settings.cancellation_deduction
            )
            booking_payment.refund_bkash_number = booking_payment.bkash_number
            booking_payment.save()
            messages.success(
                request,
                f"Appointment cancelled. A refund of "
                f"৳{booking_payment.refund_amount} will be sent to "
                f"{booking_payment.bkash_number} shortly."
            )
        else:
            messages.success(request, "Appointment cancelled.")

    return redirect('consultations:my_appointments')


@login_required_user
def reschedule_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        status__in=['confirmed', 'rescheduled'],
    )

    if appointment.reschedule_count >= 1:
        messages.error(
            request,
            "You can only reschedule an appointment once. "
            "Please cancel and book a new appointment if needed."
        )
        return redirect('consultations:appointment_detail',
                      appointment_id=appointment_id)

    from datetime import date as date_cls
    new_date_str  = request.POST.get('new_date', '')
    new_start_str = request.POST.get('new_start', '')
    new_end_str   = request.POST.get('new_end', '')

    if request.method == 'POST' and new_date_str and new_start_str:
        try:
            new_date = date_cls.fromisoformat(new_date_str)
        except ValueError:
            messages.error(request, "Invalid date.")
            return redirect('consultations:appointment_detail',
                          appointment_id=appointment_id)

        # Verify new slot is available
        from consultations.slots import get_available_slots as compute_slots
        available = compute_slots(appointment.vet, new_date)
        available_starts = [s['start_str'] for s in available]

        if new_start_str not in available_starts:
            messages.error(
                request,
                "That slot is no longer available. Please choose another."
            )
            return redirect('consultations:appointment_detail',
                          appointment_id=appointment_id)

        # Update appointment
        appointment.date          = new_date
        appointment.start_time    = new_start_str
        appointment.end_time      = new_end_str
        appointment.status        = Appointment.Status.RESCHEDULED
        appointment.reschedule_count += 1
        appointment.save()

        messages.success(
            request,
            f"Appointment rescheduled to "
            f"{new_date.strftime('%B %d, %Y')} at {new_start_str}."
        )
        return redirect('consultations:appointment_detail',
                      appointment_id=appointment_id)

    # GET — show reschedule form
    ctx = {
        'appointment': appointment,
        'today': timezone.localdate().isoformat(),
    }
    return render(request, 'user/reschedule_appointment.html', ctx)


@login_required_user
def submit_feedback(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        status='completed',
    )

    if appointment.feedback_rating:
        messages.info(request, "You've already submitted feedback for this appointment.")
        return redirect('consultations:appointment_detail',
                      appointment_id=appointment_id)

    if request.method == 'POST':
        from blog.models import Review
        rating  = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
            messages.error(request, "Please select a rating between 1 and 5.")
            return redirect('consultations:appointment_detail',
                          appointment_id=appointment_id)

        appointment.feedback_rating      = int(rating)
        appointment.feedback_comment     = comment
        appointment.feedback_submitted_at = timezone.now()
        appointment.save()

        # Create a Review record
        Review.objects.create(
            appointment=appointment,
            reviewer=request.user,
            vet=appointment.vet,
            rating=int(rating),
            comment=comment,
        )

        messages.success(request, "Thank you for your feedback!")
        return redirect('consultations:appointment_detail',
                      appointment_id=appointment_id)

    return redirect('consultations:appointment_detail',
                  appointment_id=appointment_id)

@login_required_user
def cancel_appointment(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def submit_second_payment(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def my_pets(request):
    pets = Pet.objects.filter(owner=request.user).order_by('name')
    return render(request, 'user/my_pets.html', {'pets': pets})


@login_required_user
def add_pet(request):
    # Detect if we're in booking context
    from urllib.parse import unquote
    next_url = unquote(request.GET.get('next', '') or request.POST.get('next', ''))
    context  = request.GET.get('context', '') or request.POST.get('context', '')
    in_booking = context == 'booking'

    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES)
        if form.is_valid():
            pet = form.save(commit=False)
            pet.owner = request.user
            pet.save()
            messages.success(
                request,
                f"{pet.name} has been added."
            )
            if next_url:
                return redirect(next_url)
            return redirect('consultations:my_pets')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = PetForm()

    return render(request, 'user/add_pet.html', {
        'form': form,
        'next_url': next_url,
        'in_booking': in_booking,
    })


@login_required_user
def edit_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)

    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            form.save()
            messages.success(request, f"{pet.name}'s profile has been updated.")
            return redirect('consultations:my_pets')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = PetForm(instance=pet)

    return render(request, 'user/edit_pet.html', {
        'form': form,
        'pet': pet,
    })


@login_required_user
def delete_pet(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, owner=request.user)
    if request.method == 'POST':
        name = pet.name
        # Check if pet has upcoming appointments
        upcoming = Appointment.objects.filter(
            pet=pet,
            status__in=['pending_payment', 'confirmed', 'in_progress'],
        ).exists()
        if upcoming:
            messages.error(
                request,
                f"Cannot delete {name} — they have upcoming appointments. "
                f"Cancel the appointments first."
            )
            return redirect('consultations:my_pets')
        pet.delete()
        messages.success(request, f"{name} has been removed.")
    return redirect('consultations:my_pets')

@login_required_user
def view_prescription(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_user
def download_prescription(request, appointment_id):
    return HttpResponse("Coming soon")