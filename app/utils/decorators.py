import json
from functools import wraps

from flask import jsonify, redirect, request, session, url_for
from werkzeug.datastructures import ImmutableMultiDict

from ..utils.errors import UnauthorizedError
from ..utils.utils import get_portal_tokens, load_portal_client
from .. import logger

def authenticated(fn):
    """Mark a route as requiring authentication."""

    @wraps(fn)
    def decorated_function(*args, **kwargs):
        logger.info(f"Checking authentication for route: {request.path}")
        # log.info(f"Request headers: {request.headers}")
        # log.info(f"Cookies: {request.cookies}")
        # log.info(f"Session: {session}")
        tokens = request.cookies.get("tokens")
        # Handle the '/is_authenticated' endpoint
        if request.path.endswith("/is_authenticated"):
            return handle_is_authenticated(tokens)

        # Check if the user is trying to log out
        if request.path.endswith("/api/logout"):
            if session.get("tokens"):
                logger.info("User is authenticated, logging out")
                return fn(*args, **kwargs)
            else:
                logger.info("No user session found, redirecting to login")
                return redirect(url_for("home"))

        # Check for authentication in the headers or session
        if not tokens and not session.get("tokens"):
            logger.info("User is not authenticated")
            return redirect(url_for("login", next=request.url))

        return fn(*args, **kwargs)

    def handle_is_authenticated(tokens: str):
        """Handle the '/is_authenticated' endpoint with token introspection."""
        if not tokens:
            logger.info("No tokens found in request cookies")
            return jsonify({"is_authenticated": False}), 401
        try:
            tokens = json.loads(tokens)["value"]
            logger.debug(f"Tokens in is_authenticated: {tokens} for route: {request.path}")
            if not tokens:
                logger.info("No tokens available")
                return jsonify({"is_authenticated": False}), 401
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding tokens: {e}")
            return jsonify({"is_authenticated": False}), 401

        return jsonify({"is_authenticated": True})

    return decorated_function
