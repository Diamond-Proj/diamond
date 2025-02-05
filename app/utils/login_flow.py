import json
import logging

import globus_sdk
from flask import request, session
from globus_compute_sdk import Client as GlobusComputeClient
from globus_compute_sdk.sdk.login_manager import AuthorizerLoginManager
from globus_compute_sdk.sdk.login_manager.manager import ComputeScopeBuilder
from globus_compute_sdk.serialize import CombinedCode
from globus_sdk.scopes import AuthScopes

from ..utils.utils import load_portal_client


class AuthClientManager:
    _instance = None
    _client = None

    @classmethod
    def get_client(cls):
        if not cls._client:
            cls._client = load_portal_client()
        return cls._client

    @classmethod
    def start_auth_flow(cls, redirect_uri, scopes, signup=False):
        client = cls.get_client()
        client.oauth2_start_flow(
            redirect_uri, refresh_tokens=True, requested_scopes=scopes
        )

        auth_uri = client.oauth2_get_authorize_url(
            query_params={"signup": "1"} if signup else {}
        )
        return auth_uri

    @classmethod
    def exchange_code(cls, code):
        client = cls.get_client()
        return client.oauth2_exchange_code_for_tokens(code)


def initialize_compute_login_manager() -> AuthorizerLoginManager:
    tokens_cookie = request.cookies.get("tokens")

    try:
        # Sanitize the cookie data
        sanitized_tokens_cookie = tokens_cookie.replace("'", '"').replace("\\054", ",")
        tokens_value = json.loads(sanitized_tokens_cookie)
        # tokens_value = json.loads(tokens['value'].replace("\\054", ","))
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from tokens cookie: {e}")
        raise

    openid_token = None
    funcx_service_token = None

    for key, value in tokens_value.items():
        if value.get("resource_server") == "funcx_service":
            funcx_service_token = value.get("access_token")
        if "openid" in value.get("scope", ""):
            openid_token = value.get("access_token")

    ComputeScopes = ComputeScopeBuilder()
    compute_auth = globus_sdk.AccessTokenAuthorizer(funcx_service_token)
    openid_auth = globus_sdk.AccessTokenAuthorizer(openid_token)

    compute_login_manager = AuthorizerLoginManager(
        authorizers={
            ComputeScopes.resource_server: compute_auth,
            AuthScopes.resource_server: openid_auth,
        }
    )
    compute_login_manager.ensure_logged_in()

    return compute_login_manager


def initialize_globus_compute_client() -> GlobusComputeClient:
    login_manager = initialize_compute_login_manager()
    return GlobusComputeClient(
        login_manager=login_manager, code_serialization_strategy=CombinedCode()
    )
