"""JSON API blueprint.

This thin layer translates between HTTP and the framework-agnostic controller:
it parses the request body, delegates to the controller, and maps domain
errors to the correct HTTP status codes. All business logic lives in the
services/controllers, keeping this module trivial and secure.
"""

from flask import Blueprint, jsonify, request

from app.controllers import chat_controller, footprint_controller
from app.utils.validation import ValidationError

api_bp = Blueprint("api", __name__)


@api_bp.route("/assess", methods=["POST"])
def assess():
    """Assess a user's carbon footprint.

    Expects a JSON body with the lifestyle fields (see ``validation.py``).

    Returns:
        ``200`` with the full assessment result, or ``400`` with an error
        message if the input is invalid.
    """
    # ``silent=True`` prevents Flask from raising on malformed JSON; we return
    # a clean 400 instead of leaking a stack trace.
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    try:
        result = footprint_controller.assess(payload)
    except ValidationError as exc:
        # Expected, user-facing validation problem -> 400 Bad Request.
        return jsonify({"error": str(exc)}), 400

    return jsonify(result.as_dict()), 200


@api_bp.route("/baseline", methods=["GET"])
def baseline():
    """Return the average-person baseline used in explanations."""
    return jsonify(footprint_controller.baseline_profile()), 200


@api_bp.route("/chat", methods=["POST"])
def chat():
    """Answer a free-text carbon-footprint question.

    Expects ``{"message": "..."}``. Returns the assistant's reply along with the
    answer source, matched topic, confidence and (when relevant) suggestions.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    message = payload.get("message", "")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "'message' is required."}), 400

    try:
        return jsonify(chat_controller.ask(message)), 200
    except Exception:  # noqa: BLE001 - never leak a crash page to the client
        # Return JSON (not an HTML 500) so the UI can show a clear message.
        return jsonify({
            "reply": "Sorry, the assistant hit an internal error. Please try "
                     "again.",
            "source": "error",
            "topic": None,
            "confidence": 0.0,
            "suggestions": [],
        }), 200


@api_bp.route("/chat/suggestions", methods=["GET"])
def chat_suggestions():
    """Return seed topics to display in the chat UI."""
    return jsonify(chat_controller.suggestions()), 200
