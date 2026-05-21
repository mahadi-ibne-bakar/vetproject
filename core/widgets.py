from django.forms.widgets import FileInput


class ImageUploadWidget(FileInput):
    """
    Minimal file input that:
    - Hides the default input with CSS
    - Adds onchange handler for preview
    - Gets styled by the image_upload_field template tag
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'accept': 'image/*',
            'style': 'display:none;',
        })

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs)
        # Add onchange — uses the input's id
        field_id = attrs.get('id', 'id_image')
        attrs['onchange'] = f"previewImage(this, '{field_id}')"
        return attrs