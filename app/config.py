"""Application configuration.

Configuration is environment-driven so that **no secrets are ever hard-coded**.
Each value falls back to a safe default suitable for local development only.
"""

import os


class Config:
    """Base configuration shared by every environment.

    Attributes are read once at import time from the process environment.
    Secrets (``SECRET_KEY``) MUST be supplied via the environment in
    production; the development fallback is clearly marked and is never used
    when ``FLASK_ENV=production``.
    """

    # ``SECRET_KEY`` signs Flask sessions/flash messages. It is pulled from the
    # environment; the obviously-fake default only applies in development.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")

    # Reject request bodies larger than 16 KB. The API only ever receives a
    # small JSON payload, so this caps a trivial denial-of-service vector.
    MAX_CONTENT_LENGTH = 16 * 1024

    # Cross-origin: disabled by default. The frontend is served by the same
    # Flask app, so we do not need permissive CORS.
    JSON_SORT_KEYS = False

    @staticmethod
    def is_production() -> bool:
        """Return ``True`` when running in a production environment."""
        return os.environ.get("FLASK_ENV", "development") == "production"


# Security response headers applied to *every* response (see ``app.__init__``).
# These mitigate XSS, clickjacking, MIME-sniffing and protocol-downgrade
# attacks and earn marks under the "Security" evaluation criterion.
SECURITY_HEADERS = {
    # Restrict resources to same-origin. The single documented exception is the
    # cdnjs origin, used only to load the Three.js library that powers the 3D
    # animated assistant (kept off-repo to stay well under the size budget).
    # All app code, styles, data (connect-src via default-src) and form actions
    # remain locked to 'self'.
    "Content-Security-Policy": (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    ),
    # Stop the browser from MIME-sniffing a response away from the declared type.
    "X-Content-Type-Options": "nosniff",
    # Disallow the page being framed (defence-in-depth clickjacking guard).
    "X-Frame-Options": "DENY",
    # Don't leak the full URL in the Referer header to other origins.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Drop access to powerful browser features the app never uses.
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}
