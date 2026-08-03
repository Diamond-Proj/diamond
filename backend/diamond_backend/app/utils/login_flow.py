import json
import logging
import os
import urllib.parse  # Add this import for URL decoding

import globus_sdk
from flask import request
from globus_compute_sdk import Client as GlobusComputeClient
from globus_compute_sdk.serialize import AllCodeStrategies

logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%dT%H:%M:%S",
    format="%(asctime)-15s.%(msecs)03dZ %(levelname)-7s : %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AuthClientManager:
    _instance = None
    _client = None

    @classmethod
    def get_client(cls):
        if not cls._client:
            cls._client = load_portal_client()
        return cls._client


def load_portal_client():
    """Create an AuthClient for the portal"""
    return globus_sdk.ConfidentialAppAuthClient(
        os.environ["PORTAL_CLIENT_ID"], os.environ["PORTAL_CLIENT_SECRET"]
    )


def initialize_token_authorizer():
    tokens_cookie = request.cookies.get("tokens")

    if not tokens_cookie:
        logger.error("No tokens cookie found in request")
        raise ValueError("No authentication tokens found. Please log in again.")

    try:
        # First URL-decode the cookie value
        url_decoded = urllib.parse.unquote(tokens_cookie)

        # Then sanitize and parse as JSON
        sanitized_tokens_cookie = url_decoded.replace("'", '"').replace("\\054", ",")

        # Log for debugging
        logger.debug(
            f"Sanitized tokens cookie (first 100 chars): {sanitized_tokens_cookie[:100]}..."
        )

        tokens_value = json.loads(sanitized_tokens_cookie)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from tokens cookie: {e}")
        raise

    # Log the structure that was successfully parsed
    if tokens_value:
        logger.debug(
            f"Successfully parsed tokens with keys: {list(tokens_value.keys())}"
        )

    funcx_service_token = None

    for key, value in tokens_value.items():
        if value.get("resource_server") == "funcx_service":
            funcx_service_token = value.get("access_token")

    return globus_sdk.AccessTokenAuthorizer(access_token=funcx_service_token)


def initialize_globus_compute_client() -> GlobusComputeClient:
    token_authorizer = initialize_token_authorizer()
    return GlobusComputeClient(
        authorizer=token_authorizer, code_serialization_strategy=AllCodeStrategies()
    )
