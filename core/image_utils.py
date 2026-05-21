"""
Image Utilities
===============
Compresses and resizes images before saving to storage.
Reduces file sizes significantly while maintaining visual quality.

Usage:
    from core.image_utils import compress_image
    compressed = compress_image(image_file, max_width=800)
"""

from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


# Maximum dimensions for each image type
IMAGE_SIZES = {
    'profile':  (400, 400),   # Square crop for profile photos
    'pet':      (600, 600),   # Square-ish for pet photos
    'blog':     (1200, 600),  # Wide banner for blog images
    'symptom':  (800, 800),   # Symptom photos — keep reasonable size
    'default':  (800, 800),   # Fallback
}

# Quality setting (1-95, higher = better quality but larger file)
JPEG_QUALITY = 82
WEBP_QUALITY = 80


def compress_image(
    image_file,
    image_type: str = 'default',
    output_format: str = 'JPEG',
    new_name: str = None,
) -> InMemoryUploadedFile:
    """
    Compresses and resizes an uploaded image.

    Args:
        image_file: The uploaded file object
        image_type: One of 'profile', 'pet', 'blog', 'symptom', 'default'
        output_format: 'JPEG' or 'WEBP' (JPEG for max compatibility)

    Returns:
        InMemoryUploadedFile ready to save to storage
    """
    max_size = IMAGE_SIZES.get(image_type, IMAGE_SIZES['default'])

    # Open image with Pillow
    img = Image.open(image_file)

    # Convert to RGB — handles PNG with transparency, CMYK, etc.
    if img.mode in ('RGBA', 'LA', 'P'):
        # Create white background for transparent images
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize maintaining aspect ratio — never upscale
    original_width, original_height = img.size
    max_width, max_height = max_size

    if original_width > max_width or original_height > max_height:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Save to buffer
    output = BytesIO()
    img.save(output, format=output_format, quality=JPEG_QUALITY, optimize=True)
    output.seek(0)

    # Use provided name or keep original
    if new_name:
        ext = 'jpg' if output_format == 'JPEG' else 'webp'
        final_name = f"{new_name.rsplit('.', 1)[0]}.{ext}"
    else:
        original_name    = getattr(image_file, 'name', 'image.jpg')
        name_without_ext = original_name.rsplit('.', 1)[0]
        ext              = 'jpg' if output_format == 'JPEG' else 'webp'
        final_name       = f"{name_without_ext}.{ext}"

    content_type = 'image/jpeg' if output_format == 'JPEG' else 'image/webp'

    return InMemoryUploadedFile(
        output,
        'ImageField',
        final_name,
        content_type,
        sys.getsizeof(output),
        None,
    )


def compress_if_image(image_file, image_type: str = 'default', new_name: str = None):
    """
    Safe wrapper — compresses if it's an image, returns as-is otherwise.
    Use this in views when you're not 100% sure the field has an image.
    """
    if not image_file:
        return image_file
    try:
        return compress_image(image_file, image_type=image_type, new_name=new_name)
    except Exception:
        return image_file
    
import uuid
from django.utils.text import slugify


def rename_image(image_file, prefix: str, identifier: str = '') -> str:
    """
    Generates a clean filename for an uploaded image.

    Examples:
        rename_image(file, 'vet', 'dr-ahmed')  → 'vet_dr-ahmed_a3f2b1.jpg'
        rename_image(file, 'pet', 'max')        → 'pet_max_7d2e4c.jpg'
        rename_image(file, 'user', 'mahadi')    → 'user_mahadi_9f1a2b.jpg'
    """
    ext = image_file.name.rsplit('.', 1)[-1].lower() if '.' in image_file.name else 'jpg'
    if ext not in ('jpg', 'jpeg', 'png', 'webp', 'gif'):
        ext = 'jpg'

    # Clean identifier
    clean_id = slugify(identifier)[:20] if identifier else ''
    uid      = uuid.uuid4().hex[:6]

    if clean_id:
        filename = f"{prefix}_{clean_id}_{uid}.{ext}"
    else:
        filename = f"{prefix}_{uid}.{ext}"

    return filename