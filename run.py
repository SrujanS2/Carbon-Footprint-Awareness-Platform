"""Application entry point.

Run locally with::

    python run.py

In production the WSGI server (gunicorn) imports the ``app`` object exposed
here, e.g.::

    gunicorn run:app

Keeping the entry point thin (it only wires the factory to a server) is part of
the clean-architecture separation: all behaviour lives inside the ``app``
package, never in this launcher.
"""

import os
import socket
import sys

# Load environment variables from a local ``.env`` file if present, so secrets
# like the optional LLM API key can be supplied without being committed. This is
# best-effort: if python-dotenv is not installed, the app still runs and reads
# variables straight from the environment.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass

from app import create_app

# The WSGI server looks for a module-level callable named ``app``.
app = create_app()


def _print_routes() -> None:
    """Print the registered routes so a stale server is immediately obvious.

    If you run ``python run.py`` and do NOT see ``POST /api/chat`` in this list,
    you are running old code - stop the server and start it again.
    """
    print("-" * 60)
    print("Registered routes:")
    interesting = ("GET", "POST", "PUT", "DELETE", "PATCH")
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r)):
        methods = ",".join(sorted(m for m in rule.methods if m in interesting))
        print("  %-12s %s" % (methods, rule))
    print("-" * 60)


if __name__ == "__main__":
    # ``PORT`` is provided by most PaaS platforms (Render, Heroku). Fall back to
    # 5000 for local development.
    port = int(os.environ.get("PORT", 5000))

    # Auto-reload during local development so newly added routes/code load
    # without a manual restart (this avoids "stale server" 404/405s on /api/*).
    # In production we serve via gunicorn (``gunicorn run:app``), which never
    # executes this block, so debug is never enabled in production. An explicit
    # FLASK_DEBUG value always wins.
    is_production = os.environ.get("FLASK_ENV", "development") == "production"
    debug_env = os.environ.get("FLASK_DEBUG")
    debug = (debug_env == "1") if debug_env is not None else (not is_production)

    # Guard against the most common confusion: an OLD server still holding the
    # port. If we did not catch this, a second 'python run.py' would fail to
    # bind and you would keep talking to the stale server (seeing 404/405s).
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        already_running = probe.connect_ex(("127.0.0.1", port)) == 0
        probe.close()
        if already_running:
            print("=" * 64)
            print("ERROR: port %d is already in use." % port)
            print("Another server is still running and would keep serving OLD code.")
            print("Stop it first, then run 'python run.py' again:")
            print("  PowerShell:  Stop-Process -Name python -Force")
            print("  (or close the other terminal window running the server)")
            print("Tip: set a different port with  $env:PORT=5001 ; python run.py")
            print("=" * 64)
            sys.exit(1)

    _print_routes()
    print("Carbon Footprint Assistant running at http://localhost:%d "
          "(debug=%s)" % (port, debug))
    print("LLM brain: %s" % ("ENABLED" if os.environ.get("LLM_API_KEY")
                             else "disabled (using built-in knowledge base)"))
    app.run(host="0.0.0.0", port=port, debug=debug)
