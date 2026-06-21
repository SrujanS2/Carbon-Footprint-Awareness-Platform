"""Security helpers: input sanitisation.

The frontend never renders raw user strings without escaping, but we sanitise
on the server as defence-in-depth against stored/reflected XSS. We deliberately
keep this dependency-free (no bleach/lxml) to stay lightweight and under the
10 MB repository budget.
"""

import html
import re

# Characters that have no business appearing in the small set of free-text
# fields this app accepts (region / notes). Anything outside a conservative
# allow-list is stripped.
_DISALLOWED_PATTERN = re.compile(r"[{}\[\];$`\\]")


def sanitize_text(value: str, max_length: int = 120) -> str:
    """Return an HTML-safe, length-bounded version of ``value``.

    The function performs three defensive steps:

    1. Trim surrounding whitespace and hard-cap the length (anti-DoS).
    2. Strip characters commonly used in injection payloads.
    3. HTML-escape the remainder so it is inert if ever echoed into markup.

    Args:
        value: Raw user-supplied string.
        max_length: Maximum number of characters to retain.

    Returns:
        A sanitised string safe to store and to render after escaping.
    """
    if not isinstance(value, str):
        return ""
    trimmed = value.strip()[:max_length]
    stripped = _DISALLOWED_PATTERN.sub("", trimmed)
    return html.escape(stripped, quote=True)
