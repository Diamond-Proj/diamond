import os
import subprocess
from datetime import datetime, timedelta
from threading import Lock

import globus_sdk
import jwt
from flask import current_app, request
import logger

try:
    from urllib.parse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse


def get_git_info():
    """Get the latest git commit SHA and commit time from the main branch."""
    try:
        # Get the latest commit SHA from main branch
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], 
            cwd=current_app.root_path, 
            stderr=subprocess.PIPE,
            text=True
        ).strip()
        
        # Get the commit time
        commit_time = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "HEAD"], 
            cwd=current_app.root_path, 
            stderr=subprocess.PIPE,
            text=True
        ).strip()
        
        return {
            "commit_sha": commit_sha,
            "commit_time": commit_time
        }
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.warning(f"Could not get git information: {e}")
        return {
            "commit_sha": "unknown",
            "commit_time": "unknown"
        }


def load_portal_client():
    """Create an AuthClient for the portal"""
    return globus_sdk.ConfidentialAppAuthClient(
        os.environ["PORTAL_CLIENT_ID"], os.environ["PORTAL_CLIENT_SECRET"]
    )


def is_safe_redirect_url(target):
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return (
        redirect_url.scheme in ("http", "https")
        and host_url.netloc == redirect_url.netloc
    )


def get_safe_redirect():
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    url = request.args.get("next")
    if url and is_safe_redirect_url(url):
        return url

    url = request.referrer
    if url and is_safe_redirect_url(url):
        return url

    return "/"


def get_portal_tokens(
    scopes=[
        "openid",
        "urn:globus:auth:scope:demo-resource-server:all",
        "urn:globus:auth:scope:demo-resource-server:all[https://auth.globus.org/scopes/"
        + "os.environ['GRAPH_ENDPOINT_ID']"
        + "/https]",
    ]
):
    """
    Uses the client_credentials grant to get access tokens on the
    Portal's "client identity."
    """
    with get_portal_tokens.lock:
        if not get_portal_tokens.access_tokens:
            get_portal_tokens.access_tokens = {}

        scope_string = " ".join(scopes)

        client = load_portal_client()
        tokens = client.oauth2_client_credentials_tokens(requested_scopes=scope_string)

        # walk all resource servers in the token response (includes the
        # top-level server, as found in tokens.resource_server), and store the
        # relevant Access Tokens
        for resource_server, token_info in tokens.by_resource_server.items():
            get_portal_tokens.access_tokens.update(
                {
                    resource_server: {
                        "token": token_info["access_token"],
                        "scope": token_info["scope"],
                        "expires_at": token_info["expires_at_seconds"],
                    }
                }
            )

        return get_portal_tokens.access_tokens


get_portal_tokens.lock = Lock()
get_portal_tokens.access_tokens = None
