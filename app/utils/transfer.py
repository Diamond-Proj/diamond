import urllib.parse
import json
import globus_sdk

from .. import logger

def get_transfer_client(request):
    """
    Get a Globus Transfer client from the request's authentication tokens.
    
    Args:
        request: The Flask request object containing the tokens cookie
        
    Returns:
        tuple: (transfer_client, error_response) where error_response is None if successful
    """
    try:
        if not (tokens_cookie := request.cookies.get("tokens")):
            logger.error("No tokens cookie found in request")
            return None, ({"error": "No authentication tokens found"}, 401)

        # Parse tokens
        url_decoded = urllib.parse.unquote(tokens_cookie)
        tokens_data = json.loads(url_decoded)

        # Find transfer token
        transfer_token = None
        for token_data in tokens_data.values():
            if "transfer.api.globus.org" in token_data.get("scope", ""):
                transfer_token = token_data.get("access_token")
                break

        if not transfer_token:
            logger.error("No transfer token found in tokens")
            return None, ({"error": "No transfer token found"}, 401)

        # Initialize Transfer client
        authorizer = globus_sdk.AccessTokenAuthorizer(transfer_token)
        transfer_client = globus_sdk.TransferClient(authorizer=authorizer)
        
        return transfer_client, None

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding tokens: {e}")
        return None, ({"error": "Invalid token format"}, 401)
    except Exception as e:
        logger.error(f"Error initializing transfer client: {e}")
        return None, ({"error": str(e)}, 500) 