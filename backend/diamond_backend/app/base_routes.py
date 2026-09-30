import logging
import sys
from datetime import datetime
from importlib import metadata

from flask import current_app, jsonify, redirect, request

from diamond_backend.app import app, g_database
from diamond_backend.app.errors import DiamondResponseError
from diamond_backend.app.utils.decorators import authenticated

logger = logging.getLogger(__name__)

GLOBUS_COMPUTE_SDK_VERSION = metadata.version("globus-compute-sdk")

HOST = app.config.get("HOST")
AUTH_URL = app.config.get("AUTH_URL")
NEXT_URL = app.config.get("NEXT_URL")
RAILWAY_GIT_COMMIT_SHA = app.config.get("RAILWAY_GIT_COMMIT_SHA")

logger.info(f"HOST in routes.py: {HOST}")
logger.info(f"AUTH_URL in routes.py: {AUTH_URL}")
logger.info(f"NEXT_URL in routes.py: {NEXT_URL}")
logger.info(f"RAILWAY_GIT_COMMIT_SHA in routes.py: {RAILWAY_GIT_COMMIT_SHA}")


def get_git_info():
    """Get the latest git commit SHA and commit time from the main branch."""
    # Check if RAILWAY_GIT_COMMIT_SHA exists and is a string
    railway_commit_sha = current_app.config.get("RAILWAY_GIT_COMMIT_SHA")
    if (
        railway_commit_sha
        and isinstance(railway_commit_sha, str)
        and len(railway_commit_sha) == 40
    ):
        return {"commit_sha": railway_commit_sha}
    else:
        return {"commit_sha": "unknown"}


@app.errorhandler(DiamondResponseError)
def handle_custom_api_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.http_status_code
    return response


@app.route("/api/home", methods=["GET"])
def home():
    """Home route."""
    logger.info(f"Home route redirecting to {NEXT_URL}/sign-in")
    return redirect(NEXT_URL + "/sign-in")


@app.route("/api/healthcheck", methods=["GET"])
def healthcheck():
    """Health check endpoint."""
    logger.info("Health check route")

    version_info = str(sys.version_info)
    # Get git information
    git_info = get_git_info()
    common_fields = {
        "timestamp": datetime.utcnow().isoformat(),
        "git": git_info,
        "python_version": version_info,
        "globus_compute_sdk_version": GLOBUS_COMPUTE_SDK_VERSION,
    }
    if git_info["commit_sha"] == "unknown":
        return jsonify({"status": "unhealthy", **common_fields}), 500
    else:
        return jsonify({"status": "healthy", **common_fields}), 200


@app.route("/api/is_authenticated", methods=["GET"])
@authenticated
def is_authenticated():
    return jsonify({"is_authenticated": True})


@app.route("/api/list_accounts", methods=["POST"])
@authenticated
def diamond_get_accounts():
    account_list = g_database.get_accounts(
        identity_id=request.cookies.get("primary_identity"),
        endpoint_uuid=request.json.get("endpoint"),
    )
    return jsonify(account_list)


@app.route("/api/stats", methods=["GET"])
@authenticated
def diamond_get_stats():
    identity_id = request.cookies.get("primary_identity")
    stats = g_database.get_stats(identity_id=identity_id)
    return jsonify(stats)


@app.route("/api/globus_login_scopes", methods=["GET"])
def globus_login_scopes():
    from diamond_backend.app.database.models.flow import Flows

    # Default scopes required for the application
    default_scopes = [
        "openid",
        "profile",
        "email",
        "urn:globus:auth:scope:transfer.api.globus.org:all",
        "urn:globus:auth:scope:auth.globus.org:view_identity_set",
    ]

    # Dynamically add scopes for all registered flows
    flow_scopes = []
    with app.app_context():
        all_flows = Flows.query.all()
        for flow in all_flows:
            # Construct the flow-specific scope pattern
            # Example: https://auth.globus.org/scopes/FLOW_ID/flow_FLOW_ID_user
            flow_id_underscores = flow.flow_id.replace("-", "_")
            flow_scope = f"https://auth.globus.org/scopes/{flow.flow_id}/flow_{flow_id_underscores}_user"
            flow_scopes.append(flow_scope)

    all_required_scopes = default_scopes + flow_scopes
    logger.info(f"Returning required Globus login scopes: {all_required_scopes}")
    return jsonify({"scopes": all_required_scopes})


if __name__ == "__main__":
    app.run()
