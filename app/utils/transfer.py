import json
import urllib.parse

import globus_sdk

from .. import logger


def get_transfer_client(request):
    """
    Get a Globus Transfer client from the request's authentication tokens.

    Args:
        request: The Flask request object containing the tokens cookie

    Returns:
        globus_sdk.TransferClient: Authenticated transfer client

    Raises:
        globus_sdk.GlobusAPIError: When authentication tokens are missing or invalid
    """
    if not (tokens_cookie := request.cookies.get("tokens")):
        logger.error("No tokens cookie found in request")
        raise globus_sdk.GlobusAPIError(
            "No authentication tokens found",
            http_status=401,
        )

    try:
        # Parse tokens
        url_decoded = urllib.parse.unquote(tokens_cookie)
        tokens_data = json.loads(url_decoded)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding tokens: {e}")
        raise globus_sdk.GlobusAPIError(
            "Invalid token format",
            http_status=401,
        )

    # Find transfer token
    transfer_token = None
    for token_data in tokens_data.values():
        if "transfer.api.globus.org" in token_data.get("scope", ""):
            transfer_token = token_data.get("access_token")
            break

    if not transfer_token:
        logger.error("No transfer token found in tokens")
        raise globus_sdk.GlobusAPIError(
            "No transfer token found",
            http_status=401,
        )

    try:
        # Initialize Transfer client
        authorizer = globus_sdk.AccessTokenAuthorizer(transfer_token)
        transfer_client = globus_sdk.TransferClient(authorizer=authorizer)
        return transfer_client
    except Exception as e:
        logger.error(f"Error initializing transfer client: {e}")
        raise globus_sdk.GlobusAPIError(
            f"Error initializing transfer client: {str(e)}",
            http_status=500,
        )
