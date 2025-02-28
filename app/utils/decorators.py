import json
import logging
import urllib.parse  # Add this import for URL decoding
from functools import wraps

from flask import jsonify, redirect, request, session, url_for
from werkzeug.datastructures import ImmutableMultiDict

from ..utils.errors import UnauthorizedError
from ..utils.utils import get_portal_tokens, load_portal_client

# create and configure logger
logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
# create log object with current module name
log = logging.getLogger(__name__)


def authenticated(fn):
    """Mark a route as requiring authentication."""

    @wraps(fn)
    def decorated_function(*args, **kwargs):
        log.info(f"Checking authentication for route: {request.path}")
        log.info(f"Request headers: {request.headers}")
        log.info(f"Cookies: {request.cookies}")
        # log.info(f"Session: {session}")
        tokens = request.cookies.get("tokens")
        # Handle the '/is_authenticated' endpoint
        if request.path.endswith("/is_authenticated"):
            return handle_is_authenticated(tokens)

        # Check if the user is trying to log out
        if request.path.endswith("/api/logout"):
            if session.get("tokens"):
                log.info("User is authenticated, logging out")
                return fn(*args, **kwargs)
            else:
                log.info("No user session found, redirecting to login")
                return redirect(url_for("home"))

        # Check for authentication in the headers or session
        if not tokens and not session.get("tokens"):
            log.info("User is not authenticated")
            return redirect(url_for("login", next=request.url))

        return fn(*args, **kwargs)

    def handle_is_authenticated(tokens: str):
        """Handle the '/is_authenticated' endpoint with token introspection."""
        if not tokens:
            log.info("No tokens found in request cookies")
            return jsonify({"is_authenticated": False}), 401
        try:
            # First URL-decode the cookie value
            url_decoded = urllib.parse.unquote(tokens)

            # Try to parse the tokens
            tokens_data = json.loads(url_decoded)

            # Check for valid tokens structure
            # The format we're now storing is a direct map of resource_server -> token_data
            if isinstance(tokens_data, dict) and tokens_data:
                log.debug(
                    f"Successfully parsed tokens with keys: {list(tokens_data.keys())}"
                )
                return jsonify({"is_authenticated": True})
            else:
                log.info("Invalid tokens structure")
                return jsonify({"is_authenticated": False}), 401

        except json.JSONDecodeError as e:
            log.error(f"Error decoding tokens: {e}")
            log.error(f"Tokens string (first 100 chars): {tokens[:100]}...")
            return jsonify({"is_authenticated": False}), 401

        return jsonify({"is_authenticated": True})

    return decorated_function
