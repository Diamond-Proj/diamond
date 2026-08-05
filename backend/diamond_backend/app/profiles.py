import logging

from flask import jsonify, request

from diamond_backend.app import app, g_database
from diamond_backend.app.errors import RequestMalformed
from diamond_backend.app.utils.decorators import authenticated

logger = logging.getLogger(__name__)


def _serialize_profile(profile_model):
    return {
        "identityId": profile_model.identity_id,
        "name": profile_model.name,
        "email": profile_model.email,
        "institution": profile_model.institution,
        "is_initialized": profile_model.is_initialized,
    }


def _resolve_identity_id(requested_identity: str | None):
    cookie_identity = request.cookies.get("primary_identity")
    if not requested_identity and not cookie_identity:
        raise RequestMalformed("identity_id")

    if not requested_identity:
        return cookie_identity

    if cookie_identity and cookie_identity != requested_identity:
        logger.warning(
            "Identity ID mismatch between cookie (%s) and request (%s). "
            "Using identity from cookie.",
            cookie_identity,
            requested_identity,
        )
        return cookie_identity

    return requested_identity


@app.route("/api/profile", methods=["GET"])
@authenticated
def diamond_get_profile():
    """Fetch the profile for the authenticated identity."""
    identity_id = _resolve_identity_id(request.args.get("identity_id"))
    profile_record = g_database.load_profile(identity_id)

    if not profile_record:
        return jsonify({"profile": None, "message": "Profile not found"}), 200

    return (
        jsonify(
            {"profile": _serialize_profile(profile_record), "message": "Profile found"}
        ),
        200,
    )


@app.route("/api/profile", methods=["POST"])
@authenticated
def diamond_upsert_profile():
    """Create or update the authenticated user's profile."""
    body = request.get_json(silent=True) or {}
    identity_id = _resolve_identity_id(body.get("identity_id"))

    existing_profile = g_database.load_profile(identity_id)

    name = (
        body.get("name")
        if body.get("name") is not None
        else (existing_profile.name if existing_profile else None)
    )
    email = (
        body.get("email")
        if body.get("email") is not None
        else (existing_profile.email if existing_profile else None)
    )
    institution = (
        body.get("institution")
        if body.get("institution") is not None
        else (existing_profile.institution if existing_profile else None)
    )

    is_initialized = (
        existing_profile.is_initialized
        if existing_profile and existing_profile.is_initialized is not None
        else False
    )

    g_database.save_profile(
        identity_id=identity_id,
        name=name,
        email=email,
        institution=institution,
        is_initialized=is_initialized,
    )

    updated_profile = g_database.load_profile(identity_id)

    g_database.set_profile_initialization_state(identity_id, initialized=True)

    return (
        jsonify(
            {
                "profile": _serialize_profile(updated_profile),
                "message": "Profile created/updated successfully",
            }
        ),
        200,
    )
