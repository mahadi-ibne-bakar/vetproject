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