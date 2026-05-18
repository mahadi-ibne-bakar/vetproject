from .models import SiteSettings


def site_settings(request):
    """
    Makes site_settings available in every template automatically.
    """
    return {
        'site_settings': SiteSettings.get(),
    }