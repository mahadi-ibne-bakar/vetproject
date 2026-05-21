from django import template
register = template.Library()

@register.inclusion_tag('core/image_upload_widget.html')
def image_upload_field(field, label="Upload photo"):
    """
    Renders a styled image upload field.
    Usage: {% image_upload_field form.profile_photo "Upload photo" %}
    """
    has_image = bool(
        field.value() and
        hasattr(field.value(), 'url')
    )
    return {
        'field': field,
        'label': label,
        'has_image': has_image,
        'image_url': field.value().url if has_image else '',
        'field_name': field.html_name,
        'field_id': field.id_for_label,
    }