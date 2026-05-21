"""
Storage cleanup utilities.
Deletes old files from Supabase storage when they are replaced or cleared.
"""

import logging
logger = logging.getLogger(__name__)


def delete_file(file_field):
    """
    Deletes a file from storage.
    Accepts a FieldFile (e.g. instance.profile_photo).
    Safe to call even if the file doesn't exist.
    """
    if not file_field:
        return
    try:
        storage = file_field.storage
        name    = file_field.name
        if name and storage.exists(name):
            storage.delete(name)
            logger.info(f"Deleted file: {name}")
    except Exception as e:
        logger.warning(f"Could not delete file {file_field}: {e}")


def replace_file(instance, field_name: str, new_file):
    """
    Deletes the old file for a model instance field before saving the new one.

    Usage:
        old_photo = instance.profile_photo
        replace_file(instance, 'profile_photo', new_file)
        instance.profile_photo = new_file
        instance.save()
    """
    old_file = getattr(instance, field_name, None)
    if old_file:
        delete_file(old_file)