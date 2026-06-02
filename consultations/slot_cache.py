"""
Slot generation cache layer.
Wraps get_available_slots with database cache to avoid
repeated queries for the same vet/date combination.

Cache is invalidated when:
- A new appointment is created
- An appointment is cancelled
- A vet updates their availability
"""

from django.core.cache import cache
from datetime import date as date_cls
import logging

logger = logging.getLogger(__name__)

SLOT_CACHE_TIMEOUT = 300  # 5 minutes


def _slot_cache_key(vet_id: int, date: date_cls) -> str:
    return f"slots:v{vet_id}:d{date.isoformat()}"


def _available_dates_cache_key(vet_id: int) -> str:
    return f"available_dates:v{vet_id}"


def get_slots_cached(vet, date: date_cls) -> list:
    """
    Returns available slots for a vet on a date.
    Uses cache — falls back to live computation on miss.
    """
    key    = _slot_cache_key(vet.id, date)
    cached = cache.get(key)

    if cached is not None:
        return cached

    from consultations.slots import get_available_slots
    slots = get_available_slots(vet, date)
    cache.set(key, slots, SLOT_CACHE_TIMEOUT)
    return slots


def get_available_dates_cached(vet, days_ahead: int = 30) -> list:
    """
    Returns available dates for a vet.
    Uses cache — falls back to live computation on miss.
    """
    key    = _available_dates_cache_key(vet.id)
    cached = cache.get(key)

    if cached is not None:
        return cached

    from consultations.slots import get_available_dates
    dates = get_available_dates(vet, days_ahead=days_ahead)
    cache.set(key, dates, SLOT_CACHE_TIMEOUT)
    return dates


def invalidate_vet_slots(vet_id: int, date: date_cls = None):
    """
    Invalidates cached slots for a vet.
    Called when an appointment is created or cancelled.

    If date is provided, only invalidates that specific date.
    If date is None, invalidates available dates cache too.
    """
    if date:
        key = _slot_cache_key(vet_id, date)
        cache.delete(key)
        logger.info(f"Invalidated slot cache for vet {vet_id} on {date}")
    else:
        # Invalidate available dates cache
        key = _available_dates_cache_key(vet_id)
        cache.delete(key)
        logger.info(f"Invalidated available dates cache for vet {vet_id}")


def invalidate_all_vet_slots(vet_id: int):
    """
    Invalidates all cached slots for a vet.
    Called when vet updates their availability schedule.
    """
    invalidate_vet_slots(vet_id)
    logger.info(f"Invalidated all slot caches for vet {vet_id}")