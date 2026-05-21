from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate
from datetime import timedelta
import json

from accounts.models import User, VetProfile
from consultations.models import Appointment, Payment, Pet
from blog.models import BlogPost, Review
from core.models import SiteSettings, MeetLink
from accounts.decorators import login_required_admin
from django.http import HttpResponse

# ── Context helper ─────────────────────────────────────────────────────────────
# Adds sidebar badge counts to every admin view automatically

def admin_context(request):
    """Returns context shared across all admin pages — sidebar badges etc."""
    return {
        'pending_vet_count': VetProfile.objects.filter(
            application_status='pending'
        ).count(),
        'pending_payment_count': Payment.objects.filter(
            status='pending'
        ).count(),
    }


# ── Dashboard Home ─────────────────────────────────────────────────────────────

@login_required_admin
def dashboard_home(request):
    today = timezone.localdate()
    week_ago = today - timedelta(days=7)

    # Core stats
    total_users = User.objects.filter(role='user').count()
    total_vets = VetProfile.objects.filter(
        application_status='approved', is_active=True
    ).count()
    total_consultations = Appointment.objects.filter(
        status='completed'
    ).count()

    # Revenue — sum of all verified payments
    revenue_data = Payment.objects.filter(
        status='verified'
    ).aggregate(total=Sum('amount'))
    total_revenue = revenue_data['total'] or 0

    # Pending items needing attention
    pending_payments = Payment.objects.filter(status='pending').count()
    pending_vets = VetProfile.objects.filter(
        application_status='pending'
    ).count()
    pending_refunds = Payment.objects.filter(status='refunded').count()

    # Available meet links
    available_meet_links = MeetLink.objects.filter(is_in_use=False).count()
    total_meet_links = MeetLink.objects.count()

    # Recent consultations (last 5)
    recent_consultations = Appointment.objects.select_related(
        'user', 'vet__user', 'pet'
    ).order_by('-created_at')[:5]

    # Consultations this week vs last week
    this_week = Appointment.objects.filter(
        created_at__date__gte=week_ago
    ).count()

    # Recent vet applications
    recent_vet_applications = VetProfile.objects.filter(
        application_status='pending'
    ).select_related('user').order_by('-created_at')[:5]

    ctx = {
        **admin_context(request),
        'total_users': total_users,
        'total_vets': total_vets,
        'total_consultations': total_consultations,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'pending_vets': pending_vets,
        'pending_refunds': pending_refunds,
        'available_meet_links': available_meet_links,
        'total_meet_links': total_meet_links,
        'recent_consultations': recent_consultations,
        'this_week': this_week,
        'recent_vet_applications': recent_vet_applications,
    }
    return render(request, 'dashboard/home.html', ctx)


# ── Analytics ──────────────────────────────────────────────────────────────────

@login_required_admin
def analytics(request):
    today = timezone.localdate()

    # Consultations per day for the last 30 days
    thirty_days_ago = today - timedelta(days=30)
    daily_consultations = (
        Appointment.objects
        .filter(created_at__date__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    # Build full 30-day list (fill zeros for days with no data)
    daily_data = {}
    for row in daily_consultations:
        daily_data[str(row['day'])] = row['count']

    chart_labels = []
    chart_values = []
    for i in range(30):
        day = thirty_days_ago + timedelta(days=i)
        chart_labels.append(day.strftime('%b %d'))
        chart_values.append(daily_data.get(str(day), 0))

    # Revenue per day for the last 30 days
    daily_revenue = (
        Payment.objects
        .filter(status='verified', created_at__date__gte=thirty_days_ago)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )
    revenue_data = {}
    for row in daily_revenue:
        revenue_data[str(row['day'])] = row['total']

    revenue_values = []
    for i in range(30):
        day = thirty_days_ago + timedelta(days=i)
        revenue_values.append(revenue_data.get(str(day), 0))

    # Status breakdown
    status_counts = (
        Appointment.objects
        .values('status')
        .annotate(count=Count('id'))
    )
    status_labels = []
    status_values = []
    status_display = dict(Appointment.Status.choices)
    for row in status_counts:
        status_labels.append(status_display.get(row['status'], row['status']))
        status_values.append(row['count'])

    # Top vets by consultation count
    top_vets = (
        VetProfile.objects
        .filter(application_status='approved')
        .annotate(consultation_count=Count(
            'appointments',
            filter=Q(appointments__status='completed')
        ))
        .select_related('user')
        .order_by('-consultation_count')[:5]
    )

    # Top complaint types
    complaint_counts = (
        Appointment.objects
        .values('primary_complaint')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    complaint_display = dict(Appointment.PrimaryComplaint.choices)
    top_complaints = [
        {
            'label': complaint_display.get(row['primary_complaint'], row['primary_complaint']),
            'count': row['count']
        }
        for row in complaint_counts
    ]

    # Species breakdown
    species_counts = (
        Pet.objects
        .values('species')
        .annotate(count=Count('id'))
    )

    # Overall totals
    total_revenue = Payment.objects.filter(
        status='verified'
    ).aggregate(total=Sum('amount'))['total'] or 0

    avg_rating = Review.objects.filter(
        is_visible=True
    ).aggregate(avg=Avg('rating'))['avg']

    ctx = {
        **admin_context(request),
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'revenue_values': json.dumps(revenue_values),
        'status_labels': json.dumps(status_labels),
        'status_values': json.dumps(status_values),
        'top_vets': top_vets,
        'top_complaints': top_complaints,
        'species_counts': species_counts,
        'total_revenue': total_revenue,
        'avg_rating': round(avg_rating, 1) if avg_rating else None,
        'total_consultations': Appointment.objects.filter(status='completed').count(),
        'total_users': User.objects.filter(role='user').count(),
        'total_pets': Pet.objects.count(),
    }
    return render(request, 'dashboard/analytics.html', ctx)


# ── Remaining placeholders (filled in later chunks) ───────────────────────────

@login_required_admin
def vet_list(request):
    tab = request.GET.get('tab', 'pending')

    pending = VetProfile.objects.filter(
        application_status='pending'
    ).select_related('user').order_by('-created_at')

    approved = VetProfile.objects.filter(
        application_status='approved'
    ).select_related('user').order_by('-created_at')

    rejected = VetProfile.objects.filter(
        application_status='rejected'
    ).select_related('user').order_by('-created_at')

    ctx = {
        **admin_context(request),
        'tab': tab,
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'pending_count': pending.count(),
        'approved_count': approved.count(),
        'rejected_count': rejected.count(),
    }
    return render(request, 'dashboard/vet_list.html', ctx)


@login_required_admin
def vet_detail(request, vet_id):
    from consultations.models import BlockedDate
    vet = get_object_or_404(VetProfile, id=vet_id)
    today = timezone.localdate()

    consultations = Appointment.objects.filter(
        vet=vet
    ).select_related('user', 'pet').order_by('-created_at')[:10]

    reviews = Review.objects.filter(
        vet=vet, is_visible=True
    ).select_related('reviewer').order_by('-created_at')[:5]

    recurring_windows = vet.availability_windows.filter(
        is_recurring=True, is_active=True
    ).order_by('day_of_week', 'start_time')

    specific_windows = vet.availability_windows.filter(
        is_recurring=False, is_active=True,
        specific_date__gte=today,
    ).order_by('specific_date')

    blocked_dates = BlockedDate.objects.filter(
        vet=vet, date__gte=today
    ).order_by('date')

    ctx = {
        **admin_context(request),
        'vet': vet,
        'consultations': consultations,
        'reviews': reviews,
        'recurring_windows': recurring_windows,
        'specific_windows': specific_windows,
        'blocked_dates': blocked_dates,
        'day_names': [
            'Monday','Tuesday','Wednesday',
            'Thursday','Friday','Saturday','Sunday'
        ],
    }
    return render(request, 'dashboard/vet_detail.html', ctx)


@login_required_admin
def approve_vet(request, vet_id):
    if request.method == 'POST':
        vet = get_object_or_404(VetProfile, id=vet_id)
        vet.application_status = VetProfile.ApplicationStatus.APPROVED
        vet.is_active = True
        vet.rejection_reason = ''
        vet.save()
        # Update the user role to ensure it's set correctly
        vet.user.role = User.Role.VET
        vet.user.save()
        messages.success(
            request,
            f"Dr. {vet.user.get_full_name()} has been approved and can now log in."
        )
    return redirect('dashboard:vet_list')


@login_required_admin
def reject_vet(request, vet_id):
    if request.method == 'POST':
        vet = get_object_or_404(VetProfile, id=vet_id)
        reason = request.POST.get('reason', '')
        vet.application_status = VetProfile.ApplicationStatus.REJECTED
        vet.is_active = False
        vet.rejection_reason = reason
        vet.save()
        messages.success(
            request,
            f"Application from {vet.user.get_full_name()} has been rejected."
        )
    return redirect('dashboard:vet_list')


@login_required_admin
def toggle_vet(request, vet_id):
    if request.method == 'POST':
        vet = get_object_or_404(VetProfile, id=vet_id)
        vet.is_active = not vet.is_active
        vet.save()
        status = "activated" if vet.is_active else "deactivated"
        messages.success(request, f"Dr. {vet.user.get_full_name()} has been {status}.")
    return redirect('dashboard:vet_list')

@login_required_admin
def user_list(request):
    search = request.GET.get('search', '').strip()
    users = User.objects.filter(
        role='user'
    ).order_by('-created_at')

    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search)
        )

    ctx = {
        **admin_context(request),
        'users': users,
        'search': search,
        'total_count': User.objects.filter(role='user').count(),
        'banned_count': User.objects.filter(role='user', is_banned=True).count(),
    }
    return render(request, 'dashboard/user_list.html', ctx)


@login_required_admin
def ban_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        reason = request.POST.get('reason', '')
        user.is_banned = True
        user.save()
        messages.success(
            request,
            f"{user.get_full_name() or user.email} has been banned."
        )
    return redirect('dashboard:user_list')


@login_required_admin
def unban_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_banned = False
        user.save()
        messages.success(
            request,
            f"{user.get_full_name() or user.email} has been unbanned."
        )
    return redirect('dashboard:user_list')

@login_required_admin
def consultation_list(request):
    return render(request, 'dashboard/consultation_list.html', admin_context(request))

@login_required_admin
def consultation_detail(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_admin
def cancel_consultation(request, appointment_id):
    return HttpResponse("Coming soon")

@login_required_admin
def payment_list(request):
    status_filter = request.GET.get('status', 'pending')

    payments = Payment.objects.filter(
        status=status_filter
    ).select_related(
        'appointment__user',
        'appointment__pet',
        'appointment__vet__user',
    ).order_by('-created_at')

    ctx = {
        **admin_context(request),
        'payments': payments,
        'status_filter': status_filter,
        'pending_count': Payment.objects.filter(status='pending').count(),
        'verified_count': Payment.objects.filter(status='verified').count(),
        'failed_count': Payment.objects.filter(
            status__in=['wrong_transaction', 'failed']
        ).count(),
        'status_choices': [
            ('pending', 'Pending'),
            ('verified', 'Verified'),
            ('wrong_transaction', 'Wrong TrxID'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
    }
    return render(request, 'dashboard/payment_list.html', ctx)


@login_required_admin
def verify_payment(request):
    """
    Admin pastes the full bKash SMS into a textarea.
    We parse it with regex to extract:
      - amount  e.g. 300.00
      - sender phone  e.g. 01700933125
      - transaction ID  e.g. DE96117110
      - date/time  e.g. 09/05/2026 09:13
    Then match against pending payments.
    """
    import re

    if request.method == 'POST':
        sms_text = request.POST.get('sms_text', '').strip()

        if not sms_text:
            messages.error(request, "Please paste the bKash SMS message.")
            return redirect('dashboard:payment_list')

        # Parse the bKash SMS
        # Format: You have received Tk 300.00 from 01700933125.
        #         Fee Tk 0.00. Balance Tk 398.81.
        #         TrxID DE96117110 at 09/05/2026 09:13.
        amount_match = re.search(
            r'received\s+Tk\s+([\d,]+\.?\d*)', sms_text, re.IGNORECASE
        )
        phone_match = re.search(
            r'from\s+(01[\d]{9})', sms_text
        )
        trxid_match = re.search(
            r'TrxID\s+([A-Z0-9]+)', sms_text, re.IGNORECASE
        )
        time_match = re.search(
            r'at\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})', sms_text
        )

        # Validate we got all fields
        if not all([amount_match, phone_match, trxid_match]):
            messages.error(
                request,
                "Could not parse the SMS. Make sure you pasted the full bKash message."
            )
            return redirect('dashboard:payment_list')

        # Clean extracted values
        amount_str = amount_match.group(1).replace(',', '')
        try:
            amount = int(float(amount_str))
        except ValueError:
            messages.error(request, "Could not read the payment amount from SMS.")
            return redirect('dashboard:payment_list')

        phone = phone_match.group(1).strip()
        trxid = trxid_match.group(1).strip().upper()
        trx_time = time_match.group(1) if time_match else None

        # Try to find a matching pending payment
        # Match on: bkash_number + transaction_id + amount
        full_match = Payment.objects.filter(
            status='pending',
            bkash_number=phone,
            transaction_id__iexact=trxid,
            amount=amount,
        ).first()

        if full_match:
            full_match.status = Payment.Status.VERIFIED
            full_match.verified_by = request.user
            full_match.verified_at = timezone.now()
            full_match.save()

            # If this was the booking payment, confirm the appointment
            if full_match.payment_type == 'booking':
                appt = full_match.appointment
                if appt.status == 'pending_payment':
                    appt.status = 'confirmed'
                    # Assign a free meet link from the pool
                    free_link = MeetLink.objects.filter(
                        is_in_use=False
                    ).first()
                    if free_link:
                        appt.meet_link = free_link
                        free_link.is_in_use = True
                        free_link.save()
                    appt.save()
                    # Send confirmation emails to user and vet
                    from consultations.emails import send_booking_confirmed
                    send_booking_confirmed(appt)

            # If this was the consultation payment, mark as completed
            elif full_match.payment_type == 'consultation':
                appt = full_match.appointment
                if appt.status == 'awaiting_second_payment':
                    appt.status = 'completed'
                    appt.save()
                    # Send prescription ready email
                    from consultations.emails import send_prescription_ready
                    send_prescription_ready(appt)

            messages.success(
                request,
                f"Payment verified. "
                f"৳{amount} from {phone} (TrxID: {trxid}). "
                f"Appointment status updated."
            )
            return redirect('dashboard:payment_list')

        # Phone matches but transaction ID doesn't
        phone_match_only = Payment.objects.filter(
            status='pending',
            bkash_number=phone,
            amount=amount,
        ).first()

        if phone_match_only:
            phone_match_only.status = Payment.Status.WRONG_TRANSACTION
            phone_match_only.save()
            messages.warning(
                request,
                f"Phone number {phone} and amount ৳{amount} matched, "
                f"but transaction ID '{trxid}' did not match. "
                f"Payment marked as wrong transaction ID."
            )
            return redirect('dashboard:payment_list')

        # Nothing matched
        messages.error(
            request,
            f"No pending payment found matching "
            f"phone {phone}, amount ৳{amount}, TrxID {trxid}. "
            f"Message discarded."
        )
        return redirect('dashboard:payment_list')

    return redirect('dashboard:payment_list')

@login_required_admin
def quick_verify_payment(request, payment_id):
    """
    One-tap payment verification from the payment list.
    Admin manually confirms a pending payment without pasting SMS.
    Used when admin already knows the payment is legitimate.
    """
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)

        if payment.status != Payment.Status.PENDING:
            messages.error(
                request,
                f"Payment is already {payment.get_status_display()} "
                f"and cannot be verified again."
            )
            return redirect('dashboard:payment_list')

        payment.status      = Payment.Status.VERIFIED
        payment.verified_by = request.user
        payment.verified_at = timezone.now()
        payment.save()

        # Update appointment status
        appt = payment.appointment

        if payment.payment_type == 'booking':
            if appt.status == 'pending_payment':
                appt.status = 'confirmed'
                # Assign a free meet link
                free_link = MeetLink.objects.filter(is_in_use=False).first()
                if free_link:
                    appt.meet_link       = free_link
                    free_link.is_in_use  = True
                    free_link.save()
                appt.save()
                # Send confirmation email
                from consultations.emails import send_booking_confirmed
                send_booking_confirmed(appt)

        elif payment.payment_type == 'consultation':
            if appt.status == 'awaiting_second_payment':
                appt.status = 'completed'
                appt.save()
                # Send prescription ready email
                from consultations.emails import send_prescription_ready
                send_prescription_ready(appt)

        messages.success(
            request,
            f"Payment of ৳{payment.amount} from {payment.bkash_number} "
            f"(TrxID: {payment.transaction_id}) manually verified. "
            f"Appointment status updated to {appt.get_status_display()}."
        )

    return redirect('dashboard:payment_list')

@login_required_admin
def refund_list(request):
    settings = SiteSettings.get()
    deduction = settings.cancellation_deduction

    pending_refunds_qs = Payment.objects.filter(
        payment_type='booking',
        status='verified',
        refund_sent_at__isnull=True,
        appointment__status='cancelled',
    ).select_related(
        'appointment__user',
        'appointment__pet',
        'appointment__vet__user',
    ).order_by('-created_at')

    # Pre-calculate refund amount for each payment
    pending_refunds = []
    for payment in pending_refunds_qs:
        payment.refund_amount_calculated = max(
            0, payment.amount - deduction
        )
        pending_refunds.append(payment)

    completed_refunds = Payment.objects.filter(
        payment_type='booking',
        refund_sent_at__isnull=False,
    ).select_related(
        'appointment__user',
    ).order_by('-refund_sent_at')[:20]

    ctx = {
        **admin_context(request),
        'pending_refunds': pending_refunds,
        'completed_refunds': completed_refunds,
        'deduction': deduction,
    }
    return render(request, 'dashboard/refund_list.html', ctx)


@login_required_admin
def mark_refunded(request, payment_id):
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)
        settings = SiteSettings.get()
        refund_amount = payment.amount - settings.cancellation_deduction
        payment.refund_sent_at = timezone.now()
        payment.refund_amount = refund_amount
        payment.refund_bkash_number = payment.bkash_number
        payment.status = Payment.Status.REFUNDED
        payment.save()
        messages.success(
            request,
            f"Refund of ৳{refund_amount} marked as sent to {payment.bkash_number}."
        )
    return redirect('dashboard:refund_list')

@login_required_admin
def meet_links(request):
    links = MeetLink.objects.all().order_by('is_in_use', 'added_at')
    ctx = {
        **admin_context(request),
        'links': links,
        'total_count': links.count(),
        'available_count': links.filter(is_in_use=False).count(),
        'in_use_count': links.filter(is_in_use=True).count(),
    }
    return render(request, 'dashboard/meet_links.html', ctx)


@login_required_admin
def add_meet_link(request):
    if request.method == 'POST':
        url = request.POST.get('url', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not url:
            messages.error(request, "Please enter a Google Meet URL.")
            return redirect('dashboard:meet_links')

        # Basic validation — must look like a Meet link
        if 'meet.google.com' not in url:
            messages.error(
                request,
                "That doesn't look like a Google Meet link. "
                "It should contain 'meet.google.com'."
            )
            return redirect('dashboard:meet_links')

        # Check for duplicates
        if MeetLink.objects.filter(url=url).exists():
            messages.error(request, "This Meet link has already been added.")
            return redirect('dashboard:meet_links')

        MeetLink.objects.create(url=url, notes=notes)
        messages.success(request, "Meet link added successfully.")
    return redirect('dashboard:meet_links')


@login_required_admin
def delete_meet_link(request, link_id):
    if request.method == 'POST':
        link = get_object_or_404(MeetLink, id=link_id)
        if link.is_in_use:
            messages.error(
                request,
                "Cannot delete a Meet link that is currently in use. "
                "Wait for the consultation to end first."
            )
            return redirect('dashboard:meet_links')
        link.delete()
        messages.success(request, "Meet link removed.")
    return redirect('dashboard:meet_links')

@login_required_admin
def blog_list(request):
    tab = request.GET.get('tab', 'pending')

    pending = BlogPost.objects.filter(
        status='pending'
    ).select_related('author').order_by('-created_at')

    published = BlogPost.objects.filter(
        status='published'
    ).select_related('author').order_by('-published_at')

    drafts = BlogPost.objects.filter(
        status__in=['draft', 'rejected']
    ).select_related('author').order_by('-updated_at')

    ctx = {
        **admin_context(request),
        'tab': tab,
        'pending': pending,
        'published': published,
        'drafts': drafts,
        'pending_count': pending.count(),
        'published_count': published.count(),
        'drafts_count': drafts.count(),
    }
    return render(request, 'dashboard/blog_list.html', ctx)


@login_required_admin
def blog_detail(request, post_id):
    post = get_object_or_404(BlogPost, id=post_id)
    ctx = {
        **admin_context(request),
        'post': post,
    }
    return render(request, 'dashboard/blog_detail.html', ctx)


@login_required_admin
def approve_blog(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(BlogPost, id=post_id)
        post.status = BlogPost.Status.PUBLISHED
        post.published_at = timezone.now()
        post.rejection_note = ''
        post.save()
        messages.success(
            request,
            f"'{post.title}' has been published."
        )
    return redirect('dashboard:blog_list')


@login_required_admin
def reject_blog(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(BlogPost, id=post_id)
        note = request.POST.get('rejection_note', '')
        post.status = BlogPost.Status.REJECTED
        post.rejection_note = note
        post.save()
        messages.success(
            request,
            f"'{post.title}' has been rejected."
        )
    return redirect('dashboard:blog_list')


@login_required_admin
def create_blog(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        if not title or not content:
            messages.error(request, "Title and content are required.")
            return redirect('dashboard:blog_list')

        from django.utils.text import slugify
        slug = slugify(title)
        # Ensure slug is unique
        base_slug = slug
        counter = 1
        while BlogPost.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        BlogPost.objects.create(
            title=title,
            slug=slug,
            content=content,
            author=request.user,
            status=BlogPost.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        messages.success(request, f"Blog post '{title}' published successfully.")
        return redirect('dashboard:blog_list')

    return render(request, 'dashboard/create_blog.html', admin_context(request))


@login_required_admin
def delete_blog(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(BlogPost, id=post_id)
        title = post.title
        post.delete()
        messages.success(request, f"'{title}' has been deleted.")
    return redirect('dashboard:blog_list')


@login_required_admin
def review_list(request):
    tab = request.GET.get('tab', 'visible')

    visible = Review.objects.filter(
        is_visible=True
    ).select_related('reviewer', 'vet__user', 'appointment').order_by('-created_at')

    hidden = Review.objects.filter(
        is_visible=False
    ).select_related('reviewer', 'vet__user').order_by('-created_at')

    # Rating breakdown
    from django.db.models import Avg
    avg_rating = Review.objects.filter(
        is_visible=True
    ).aggregate(avg=Avg('rating'))['avg']

    ctx = {
        **admin_context(request),
        'tab': tab,
        'visible': visible,
        'hidden': hidden,
        'visible_count': visible.count(),
        'hidden_count': hidden.count(),
        'avg_rating': round(avg_rating, 1) if avg_rating else None,
    }
    return render(request, 'dashboard/review_list.html', ctx)


@login_required_admin
def toggle_review(request, review_id):
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)
        review.is_visible = not review.is_visible
        review.save()
        status = "visible" if review.is_visible else "hidden"
        messages.success(request, f"Review has been set to {status}.")
    return redirect('dashboard:review_list')


@login_required_admin
def delete_review(request, review_id):
    if request.method == 'POST':
        review = get_object_or_404(Review, id=review_id)
        review.delete()
        messages.success(request, "Review deleted permanently.")
    return redirect('dashboard:review_list')

@login_required_admin
def site_settings(request):
    settings = SiteSettings.get()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'toggle_booking':
            settings.booking_enabled = not settings.booking_enabled
            settings.save()
            status = "enabled" if settings.booking_enabled else "disabled"
            messages.success(request, f"Booking system {status}.")

        elif action == 'update_message':
            settings.service_off_message = request.POST.get(
                'service_off_message', ''
            )
            settings.service_off_from = request.POST.get(
                'service_off_from'
            ) or None
            settings.service_off_until = request.POST.get(
                'service_off_until'
            ) or None
            settings.save()
            messages.success(request, "Service message updated.")

        elif action == 'update_fees':
            try:
                booking_fee = int(request.POST.get('booking_fee', 50))
                cancellation_deduction = int(
                    request.POST.get('cancellation_deduction', 10)
                )
                slot_duration = int(
                    request.POST.get('slot_duration_minutes', 15)
                )
                if booking_fee < 0 or cancellation_deduction < 0:
                    raise ValueError
                settings.booking_fee = booking_fee
                settings.cancellation_deduction = cancellation_deduction
                settings.slot_duration_minutes = slot_duration
                settings.bkash_merchant_number = request.POST.get(
                    'bkash_merchant_number', ''
                ).strip()
                settings.save()
                messages.success(request, "Fee settings updated.")
            except (ValueError, TypeError):
                messages.error(request, "Invalid values. Please enter positive numbers.")

        return redirect('dashboard:site_settings')

    ctx = {
        **admin_context(request),
        'settings': settings,
    }
    return render(request, 'dashboard/site_settings.html', ctx)

@login_required_admin
def admin_list(request):
    admins = User.objects.filter(
        Q(role='admin') | Q(is_superuser=True)
    ).order_by('date_joined')

    # All non-admin, non-vet users who could be promoted
    promotable_users = User.objects.filter(
        role='user',
        is_banned=False,
    ).order_by('first_name')

    ctx = {
        **admin_context(request),
        'admins': admins,
        'promotable_users': promotable_users,
    }
    return render(request, 'dashboard/admin_list.html', ctx)


@login_required_admin
def add_admin(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            user = User.objects.get(id=user_id, role='user')
            user.role = User.Role.ADMIN
            user.save()
            messages.success(
                request,
                f"{user.get_full_name() or user.email} has been made an admin."
            )
        except User.DoesNotExist:
            messages.error(request, "User not found.")
    return redirect('dashboard:admin_list')


@login_required_admin
def remove_admin(request, user_id):
    if request.method == 'POST':
        # Prevent removing yourself
        if str(request.user.id) == str(user_id):
            messages.error(request, "You cannot remove your own admin access.")
            return redirect('dashboard:admin_list')
        try:
            user = User.objects.get(id=user_id)
            if user.is_superuser:
                messages.error(
                    request,
                    "Cannot remove superuser admin access from here."
                )
                return redirect('dashboard:admin_list')
            user.role = User.Role.USER
            user.save()
            messages.success(
                request,
                f"{user.get_full_name() or user.email} has been removed as admin."
            )
        except User.DoesNotExist:
            messages.error(request, "User not found.")
    return redirect('dashboard:admin_list')

@login_required_admin
def admin_add_availability(request, vet_id):
    """
    Admin adds a single availability window for a vet.
    Simpler than the vet's own form — one window at a time,
    admin picks recurring or specific date.
    """
    from consultations.models import VetAvailability, BlockedDate
    from consultations.forms import BlockedDateForm

    vet = get_object_or_404(VetProfile, id=vet_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_window':
            is_recurring   = request.POST.get('is_recurring') == '1'
            start_time     = request.POST.get('start_time')
            end_time       = request.POST.get('end_time')
            day_of_week    = request.POST.get('day_of_week')
            specific_date  = request.POST.get('specific_date') or None
            end_date       = request.POST.get('end_date') or None

            if not start_time or not end_time:
                messages.error(request, "Start and end time are required.")
                return redirect('dashboard:vet_detail', vet_id=vet_id)

            if start_time >= end_time:
                messages.error(request, "End time must be after start time.")
                return redirect('dashboard:vet_detail', vet_id=vet_id)

            VetAvailability.objects.create(
                vet=vet,
                is_recurring=is_recurring,
                day_of_week=int(day_of_week) if is_recurring and day_of_week else None,
                specific_date=specific_date if not is_recurring else None,
                start_time=start_time,
                end_time=end_time,
                end_date=end_date if is_recurring else None,
                is_active=True,
            )
            messages.success(request, "Availability window added.")

        elif action == 'block_date':
            date_str = request.POST.get('block_date')
            reason   = request.POST.get('block_reason', '')
            if not date_str:
                messages.error(request, "Please provide a date to block.")
                return redirect('dashboard:vet_detail', vet_id=vet_id)
            from datetime import date as date_cls
            try:
                block_date = date_cls.fromisoformat(date_str)
                BlockedDate.objects.get_or_create(
                    vet=vet,
                    date=block_date,
                    defaults={'reason': reason}
                )
                messages.success(request, f"{block_date} blocked for {vet}.")
            except ValueError:
                messages.error(request, "Invalid date format.")

    return redirect('dashboard:vet_detail', vet_id=vet_id)


@login_required_admin
def admin_delete_availability(request, vet_id, window_id):
    """Admin removes a single availability window."""
    from consultations.models import VetAvailability
    vet    = get_object_or_404(VetProfile, id=vet_id)
    window = get_object_or_404(VetAvailability, id=window_id, vet=vet)
    if request.method == 'POST':
        window.delete()
        messages.success(request, "Availability window removed.")
    return redirect('dashboard:vet_detail', vet_id=vet_id)


@login_required_admin
def admin_delete_blocked(request, vet_id, blocked_id):
    """Admin removes a blocked date."""
    from consultations.models import BlockedDate
    vet     = get_object_or_404(VetProfile, id=vet_id)
    blocked = get_object_or_404(BlockedDate, id=blocked_id, vet=vet)
    if request.method == 'POST':
        date = blocked.date
        blocked.delete()
        messages.success(request, f"Block removed for {date}.")
    return redirect('dashboard:vet_detail', vet_id=vet_id)