"""Application factory.

This module wires the application together following a clean / MVC-style
separation:

* ``models``      - plain data structures (no framework dependencies)
* ``services``    - business logic & the AI insight/chat engines
* ``controllers`` - orchestrate services for a request (no Flask in here)
* ``routes``      - the thin Flask layer (HTTP <-> controller)
* ``utils``       - cross-cutting helpers (validation, security)

Keeping Flask confined to the ``routes`` layer means the core logic is fully
unit-testable without spinning up a web server.

Static serving note: we deliberately do NOT use Flask's default root static
handler (``static_url_path=""``), because it registers a greedy
``/<path:filename>`` catch-all that can shadow API routes and cause confusing
405s. Instead the frontend's CSS/JS are served through explicit, scoped routes
(``/css/...`` and ``/js/...``), so ``/api/*`` can never be intercepted.
"""

import os

from flask import Flask, jsonify, request, send_from_directory

from app.config import Config, SECURITY_HEADERS
from app.routes.api import api_bp

# Absolute path to the bundled frontend (one level up from this package).
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


def create_app(config_object: type = Config) -> Flask:
    """Build and configure a Flask application instance.

    Args:
        config_object: Configuration class to load. Injectable so tests can
            supply an alternative configuration.

    Returns:
        A fully configured :class:`flask.Flask` application.
    """
    # ``static_folder=None`` disables the default catch-all static route; we
    # serve assets via explicit routes below.
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_object)

    # Register the JSON API blueprint under the ``/api`` prefix.
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.after_request
    def _apply_security_headers(response):
        """Attach hardened security headers to every outgoing response."""
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    # ---- Frontend (explicit, scoped static serving) -----------------------
    @app.route("/")
    def index():
        """Serve the single-page accessible frontend."""
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/css/<path:filename>")
    def css(filename):
        """Serve stylesheets from frontend/css."""
        return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)

    @app.route("/js/<path:filename>")
    def js(filename):
        """Serve scripts from frontend/js."""
        return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)

    @app.route("/health")
    def health():
        """Lightweight liveness probe for the hosting platform."""
        return {"status": "ok"}, 200

    # ---- API error handlers: always JSON under /api, never an HTML page ----
    def _wants_json() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(404)
    def _not_found(error):
        if _wants_json():
            return jsonify({
                "error": "API endpoint not found. If you just added a feature, "
                         "restart the Flask server so new routes load."
            }), 404
        return error

    @app.errorhandler(405)
    def _method_not_allowed(error):
        if _wants_json():
            return jsonify({"error": "Method not allowed for this endpoint."}), 405
        return error

    @app.errorhandler(500)
    def _server_error(error):
        if _wants_json():
            return jsonify({"error": "Internal server error."}), 500
        return error

    return app
