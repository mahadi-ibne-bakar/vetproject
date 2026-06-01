"""
Rate limiting utilities using Django's database cache.

Usage:
    from core.ratelimit import RateLimiter, rate_limit

    # In a view:
    limiter = RateLimiter(request, 'payment_submit', limit=5, window=3600)
    if limiter.is_exceeded():
        # block the request

    # Or use the decorator:
    @rate_limit(key='login', limit=10, window=300)
    def my_view(request):
        ...
"""

from django.core.cache import cache
from django.utils import timezone
import hashlib
import logging

logger = logging.getLogger(__name__)


def _make_cache_key(identifier: str, key: str) -> str:
    """
    Creates a unique cache key from an identifier (IP or user ID) and action key.
    Hashed to keep it short and safe.
    """
    raw = f"ratelimit:{key}:{identifier}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_client_ip(request) -> str:
    """Extract the real client IP, accounting for Render's proxy."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


class RateLimiter:
    """
    Token bucket rate limiter backed by Django's database cache.

    Args:
        request:    Django request object
        key:        Unique identifier for the action (e.g. 'payment_submit')
        limit:      Maximum number of attempts allowed
        window:     Time window in seconds
        by_user:    If True, limit per user ID; if False, limit per IP
    """

    def __init__(
        self,
        request,
        key: str,
        limit: int,
        window: int,
        by_user: bool = True,
    ):
        self.limit  = limit
        self.window = window

        # Use user ID if authenticated, otherwise fall back to IP
        if by_user and request.user.is_authenticated:
            identifier = f"user_{request.user.id}"
        else:
            identifier = f"ip_{get_client_ip(request)}"

        self.cache_key = _make_cache_key(identifier, key)

    def get_attempts(self) -> int:
        return cache.get(self.cache_key, 0)

    def increment(self) -> int:
        """
        Increments the attempt counter and returns the new count.
        Sets the expiry on first increment.
        """
        attempts = cache.get(self.cache_key, 0)
        attempts += 1
        cache.set(self.cache_key, attempts, self.window)
        return attempts

    def is_exceeded(self) -> bool:
        return self.get_attempts() >= self.limit

    def remaining(self) -> int:
        return max(0, self.limit - self.get_attempts())

    def reset(self):
        cache.delete(self.cache_key)