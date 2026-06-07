from django import template

register = template.Library()

SPECIES_EMOJI = {
    'cat':       '🐱',
    'dog':       '🐶',
    'bird':      '🐦',
    'rabbit':    '🐰',
    'livestock': '🐄',
    'other':     '🐾',
}


@register.filter
def species_emoji(species):
    """
    Returns the emoji for a given species string.
    Usage: {{ pet.species|species_emoji }}
    """
    return SPECIES_EMOJI.get(species, '🐾')

@register.simple_tag
def has_sitewide_discount():
    """Returns True if a sitewide discount is currently active and not expired."""
    from core.models import SiteSettings
    from django.utils import timezone
    try:
        settings = SiteSettings.get()
        if not settings.sitewide_discount_enabled:
            return False
        if not settings.sitewide_discount_value:
            return False
        if (settings.sitewide_discount_expiry and
                settings.sitewide_discount_expiry < timezone.localdate()):
            return False
        return True
    except Exception:
        return False


@register.simple_tag
def calc_discounted_fee(fee):
    """Returns the final fee after sitewide discount."""
    from core.models import SiteSettings
    try:
        settings  = SiteSettings.get()
        discount  = settings.calculate_sitewide_discount(fee)
        return max(0, int(fee) - discount)
    except Exception:
        return int(fee)


@register.simple_tag
def calc_discount_amount(fee):
    """Returns the Taka amount discounted by the sitewide discount."""
    from core.models import SiteSettings
    try:
        settings = SiteSettings.get()
        return settings.calculate_sitewide_discount(fee)
    except Exception:
        return 0