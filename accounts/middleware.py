from django.shortcuts import redirect
from django.urls import reverse


class BannedUserMiddleware:
    """
    Checks on every request whether the logged-in user is banned.
    If banned, logs them out and redirects to login with a message.
    This runs globally so a ban takes effect immediately on
    the user's next request, even mid-session.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_banned:
            # Allow access to logout URL so they can be properly logged out
            logout_url = reverse('accounts:logout')
            if request.path != logout_url:
                from django.contrib.auth import logout
                from django.contrib import messages
                logout(request)
                messages.error(
                    request,
                    "Your account has been suspended. Please contact support."
                )
                return redirect('accounts:login')

        response = self.get_response(request)
        return response


class RoleRedirectMiddleware:
    """
    Redirects users who are on the wrong section of the site.
    For example, a vet who tries to visit a pet-owner-only page
    gets redirected to their dashboard instead of a confusing error.

    This is a soft guard — the decorators on views are the hard guard.
    This just improves the user experience for accidental navigation.
    """

    # URL prefixes that belong to each role
    VET_ONLY_PREFIXES = ['/consultations/vet/']
    ADMIN_ONLY_PREFIXES = ['/dashboard/']
    USER_ONLY_PREFIXES = ['/consultations/my/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path

            # Vet trying to access user-only area
            if any(path.startswith(p) for p in self.USER_ONLY_PREFIXES):
                if request.user.is_vet:
                    return redirect('consultations:vet_dashboard')

            # Regular user trying to access vet-only area
            if any(path.startswith(p) for p in self.VET_ONLY_PREFIXES):
                if request.user.is_pet_owner:
                    return redirect('core:home')

            # Non-admin trying to access admin area
            if any(path.startswith(p) for p in self.ADMIN_ONLY_PREFIXES):
                if not request.user.is_admin_user and not request.user.is_superuser:
                    return redirect('core:home')

        response = self.get_response(request)
        return response