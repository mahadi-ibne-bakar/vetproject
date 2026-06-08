from .models import SiteSettings


def site_settings(request):
    """
    Makes site_settings available in every template automatically.
    """
    return {
        'site_settings': SiteSettings.get(),
    }

def csp_nonce(request):
    """
    Makes the CSP nonce available in all templates as {{ csp_nonce }}.
    Falls back to empty string if CSP middleware isn't active.
    """
    return {
        'csp_nonce': getattr(request, 'csp_nonce', ''),
    }