from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .decorators import login_required_user, login_required_vet, login_required_admin
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings

from .models import User, VetProfile
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    VetLoginForm,
    VetApplicationForm,
    PasswordResetRequestForm,
    SetNewPasswordForm,
)


# ─── User Registration ─────────────────────────────────────────────────────────

def register(request):
    """
    Pet owner registration.
    On GET: show the registration form.
    On POST: validate, create user, log them in, redirect to home.
    """
    # If already logged in, redirect away
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately after registration
            login(request, user)
            messages.success(request, f"Welcome, {user.first_name}! Your account has been created.")
            return redirect('core:home')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


# ─── User Login ────────────────────────────────────────────────────────────────

def user_login(request):
    """
    Pet owner login.
    Rejects vets — they must use the vet login URL.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    from core.ratelimit import RateLimiter

    if request.method == 'POST':
        # Rate limit: 10 login attempts per 5 minutes per IP
        limiter = RateLimiter(
            request,
            key='login_attempt',
            limit=10,
            window=300,
            by_user=False,  # Use IP since user isn't logged in yet
        )

        if limiter.is_exceeded():
            messages.error(
                request,
                "Too many login attempts. Please wait 5 minutes before trying again."
            )
            return render(request, 'accounts/login.html', {})
        
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Prevent vets from using the user login
            if user.role == User.Role.VET:
                messages.error(request, "Vets must log in through the vet login page.")
                return redirect('accounts:vet_login')
            # Prevent banned users
            if user.is_banned:
                messages.error(request, "Your account has been suspended. Please contact support.")
                return render(request, 'accounts/login.html', {'form': form})
            login(request, user)
            # Redirect to the page they were trying to visit, or home
            next_url = request.GET.get('next', 'core:home')
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect(next_url)
        else:
            limiter.increment()
            messages.error(request, "Invalid email or password.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


# ─── Logout ───────────────────────────────────────────────────────────────────

def user_logout(request):
    """Logs out any user (pet owner, vet, or admin) and redirects to home."""
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('core:home')


# ─── User Profile ─────────────────────────────────────────────────────────────

@login_required_user
def profile(request):
    from .forms import UserProfileForm
    from core.image_utils import compress_if_image, rename_image
    from core.storage_utils import delete_file

    if request.method == 'POST':
        form = UserProfileForm(
            request.POST,
            request.FILES,
            instance=request.user,
        )
        if form.is_valid():
            user = form.save(commit=False)
            if 'profile_photo' in request.FILES:
                if request.user.profile_photo:
                    delete_file(request.user.profile_photo)
                new_name = rename_image(
                    request.FILES['profile_photo'],
                    prefix='user',
                    identifier=request.user.username,
                )
                user.profile_photo = compress_if_image(
                    request.FILES['profile_photo'],
                    image_type='profile',
                    new_name=new_name,
                )
            elif request.POST.get('profile_photo-clear'):
                if request.user.profile_photo:
                    delete_file(request.user.profile_photo)
                user.profile_photo = None
            user.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = UserProfileForm(instance=request.user)

    from consultations.models import Pet, Appointment
    pets                  = Pet.objects.filter(owner=request.user).order_by('name')
    total_appointments    = Appointment.objects.filter(user=request.user).count()
    completed_appointments = Appointment.objects.filter(
        user=request.user, status='completed'
    ).count()

    return render(request, 'accounts/profile.html', {
        'form':                   form,
        'pets':                   pets,
        'total_appointments':     total_appointments,
        'completed_appointments': completed_appointments,
    })


# ─── Vet Login ────────────────────────────────────────────────────────────────

def vet_login(request):
    """
    Separate login for vets.
    Only allows users with role=VET to log in here.
    Redirects approved vets to vet dashboard,
    pending vets to application pending page.
    """
    if request.user.is_authenticated:
        if request.user.is_vet:
            return redirect('consultations:vet_dashboard')
        return redirect('core:home')

    if request.method == 'POST':
        form = VetLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role != User.Role.VET:
                messages.error(request, "No vet account found with these credentials.")
                return render(request, 'accounts/vet_login.html', {'form': form})
            if user.is_banned:
                messages.error(request, "Your account has been suspended.")
                return render(request, 'accounts/vet_login.html', {'form': form})
            login(request, user)
            # Check application status
            try:
                vet_profile = user.vet_profile
                if vet_profile.application_status == VetProfile.ApplicationStatus.APPROVED:
                    messages.success(request, f"Welcome back, Dr. {user.last_name}!")
                    return redirect('consultations:vet_dashboard')
                else:
                    return redirect('accounts:vet_application_pending')
            except VetProfile.DoesNotExist:
                return redirect('accounts:vet_application_pending')
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = VetLoginForm()

    return render(request, 'accounts/vet_login.html', {'form': form})


# ─── Vet Application ──────────────────────────────────────────────────────────

def vet_apply(request):
    """
    Public form for vets to apply to join the platform.
    Creates a User (role=VET) and a VetProfile (status=PENDING).
    Vet cannot log in until admin approves.
    """
    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':
        form = VetApplicationForm(request.POST)
        if form.is_valid():
            from core.image_utils import compress_if_image
            # Create the User first
            user = User.objects.create_user(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone_number=form.cleaned_data['phone_number'],
                role=User.Role.VET,
            )
            # Create the VetProfile linked to this user
            VetProfile.objects.create(
                user=user,
                bio=form.cleaned_data.get('bio', ''),
                bvc_registration_number=form.cleaned_data.get('bvc_registration_number', ''),
                education=form.cleaned_data.get('education', ''),
                years_of_experience=form.cleaned_data.get('years_of_experience', 0),
                specializations=form.cleaned_data.get('specializations', ''),
                application_status=VetProfile.ApplicationStatus.PENDING,
                is_active=False,
            )
            messages.success(
                request,
                "Your application has been submitted. "
                "We will review it and contact you within 2-3 business days."
            )
            return redirect('accounts:vet_application_pending')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = VetApplicationForm()

    return render(request, 'accounts/vet_apply.html', {'form': form})


def vet_application_pending(request):
    """Simple page shown after vet submits application."""
    return render(request, 'accounts/vet_application_pending.html')


# ─── Password Reset ───────────────────────────────────────────────────────────

def password_reset_request(request):
    """
    Step 1: User enters their email.
    If found, sends a reset link. We never confirm whether
    the email exists (security best practice).
    """
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Generate a secure one-time token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                # Build the reset link
                reset_link = request.build_absolute_uri(
                    f"/accounts/password-reset/confirm/{uid}/{token}/"
                )
                # Send the email
                send_mail(
                    subject="Reset your VetProject password",
                    message=(
                        f"Hi {user.first_name},\n\n"
                        f"Click the link below to reset your password:\n\n"
                        f"{reset_link}\n\n"
                        f"This link expires in 1 hour.\n\n"
                        f"If you didn't request this, ignore this email.\n\n"
                        f"— The VetProject Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except User.DoesNotExist:
                # Don't reveal whether the email exists
                pass
            # Always redirect to done page regardless
            return redirect('accounts:password_reset_done')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'accounts/password_reset.html', {'form': form})


def password_reset_done(request):
    """Step 2: Tell user to check their email."""
    return render(request, 'accounts/password_reset_done.html')


def password_reset_confirm(request, uidb64, token):
    """
    Step 3: User clicks link from email, enters new password.
    Validates the token before allowing password change.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Check token is valid
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "This password reset link is invalid or has expired.")
        return redirect('accounts:password_reset')

    if request.method == 'POST':
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['password1'])
            user.save()
            messages.success(request, "Your password has been reset. You can now log in.")
            return redirect('accounts:password_reset_complete')
    else:
        form = SetNewPasswordForm()

    return render(request, 'accounts/password_reset_confirm.html', {
        'form': form,
        'uidb64': uidb64,
        'token': token,
    })


def password_reset_complete(request):
    """Step 4: Confirmation that password was reset."""
    return render(request, 'accounts/password_reset_complete.html')