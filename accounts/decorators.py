from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def login_required_user(view_func):
    """
    Restricts view to logged-in pet owners only.
    Redirects vets and unauthenticated users away.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to continue.")
            return redirect('accounts:login')
        if request.user.is_vet:
            messages.error(request, "This area is for pet owners only.")
            return redirect('consultations:vet_dashboard')
        if request.user.is_admin_user:
            return redirect('dashboard:home')
        if request.user.is_banned:
            messages.error(request, "Your account has been suspended.")
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_vet(view_func):
    """
    Restricts view to approved, active vets only.
    Handles every failure case with a clear message.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to continue.")
            return redirect('accounts:vet_login')
        if not request.user.is_vet:
            messages.error(request, "This area is for vets only.")
            return redirect('core:home')
        if request.user.is_banned:
            messages.error(request, "Your account has been suspended.")
            return redirect('accounts:vet_login')
        # Check vet profile exists and is approved
        try:
            vet_profile = request.user.vet_profile
            if vet_profile.application_status != 'approved':
                return redirect('accounts:vet_application_pending')
            if not vet_profile.is_active:
                messages.error(
                    request,
                    "Your account has been deactivated. Please contact support."
                )
                return redirect('accounts:vet_login')
        except Exception:
            return redirect('accounts:vet_application_pending')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_admin(view_func):
    """
    Restricts view to admin users only.
    Uses is_admin_user property from our custom User model.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to continue.")
            return redirect('accounts:login')
        if not request.user.is_admin_user and not request.user.is_superuser:
            messages.error(request, "You don't have permission to access this area.")
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper