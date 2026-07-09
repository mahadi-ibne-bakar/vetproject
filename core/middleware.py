"""
Content Security Policy middleware for Amarvet.

Uses a per-request nonce for inline scripts.
Inline styles use unsafe-inline until the template refactor (Phase 7).

To switch from report-only to enforcing mode, change the header name in settings:
    CSP_REPORT_ONLY = False
"""

import secrets
import logging

logger = logging.getLogger(__name__)


class CSPMiddleware:
    """
    Adds Content-Security-Policy header to every response.
    Generates a unique nonce per request for inline scripts.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Generate a fresh nonce for every request
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce

        response = self.get_response(request)

        # Don't add CSP to streaming responses or non-HTML responses
        content_type = response.get('Content-Type', '')
        if 'text/html' not in content_type:
            return response

        # Don't add CSP to admin responses (Django's built-in admin has
        # its own inline scripts that would need separate handling)
        if request.path.startswith('/django-admin/'):
            return response

        from django.conf import settings as django_settings
        report_only = getattr(django_settings, 'CSP_REPORT_ONLY', True)

        policy = self._build_policy(nonce, request)

        header = (
            'Content-Security-Policy-Report-Only'
            if report_only
            else
            'Content-Security-Policy'
        )
        response[header] = policy
        return response

    def _build_policy(self, nonce, request):
        from django.conf import settings as django_settings

        # Build the report URI if Sentry DSN is configured
        report_uri = ''
        sentry_dsn = getattr(django_settings, 'SENTRY_DSN', '')
        if sentry_dsn and not getattr(django_settings, 'CSP_REPORT_ONLY', True):
            # Sentry accepts CSP reports at a dedicated endpoint
            # Format: https://sentry.io/api/<project>/security/?sentry_key=<key>
            report_uri = ''  # Add your Sentry CSP report URL here if needed

        directives = {
            # Default: only same origin
            'default-src': ["'self'"],

            # Scripts: self + this request's nonce only
            # No unsafe-inline — the nonce replaces it
            'script-src': [
                "'self'",
                f"'nonce-{nonce}'",
            ],

            # Styles: self + unsafe-inline (until Phase 7 template refactor)
            'style-src': [
                "'self'",
                "'unsafe-inline'",
            ],

            # Images: self + data URIs (for base64 images) + Supabase storage
            'img-src': [
                "'self'",
                "data:",
                "blob:",
                "*.supabase.co",
                "supabase.co",
            ],

            # Fonts: self only (all fonts are self-hosted via Whitenoise)
            'font-src': ["'self'"],

            # Connections: self + Supabase + Sentry (for error reporting)
            'connect-src': [
                "'self'",
                "*.supabase.co",
                "*.sentry.io",
                "sentry.io",
            ],

            # Forms: self only
            'form-action': ["'self'"],

            # Frames: none (no iframes needed except Meet — handled separately)
            'frame-src': [
                "'self'",
                "meet.google.com",
            ],

            # Frame ancestors: none (replaces X-Frame-Options)
            'frame-ancestors': ["'none'"],

            # Base tag: self only (prevent base tag injection)
            'base-uri': ["'self'"],

            # Objects: none (no Flash/Java)
            'object-src': ["'none'"],

            # Manifest: self (for PWA)
            'manifest-src': ["'self'"],

            # Media: self
            'media-src': ["'self'"],

            # Workers: self (for service worker)
            'worker-src': ["'self'"],
        }

        parts = []
        for directive, sources in directives.items():
            parts.append(f"{directive} {' '.join(sources)}")

        if report_uri:
            # At the end of directives, replace the empty report_uri with:
            parts.append("report-uri /csp-report/")

        return '; '.join(parts)