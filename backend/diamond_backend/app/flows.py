import ast
import json
import logging
import urllib
from importlib.resources import as_file, files

import globus_sdk
from flask import jsonify
from jinja2 import Environment, FileSystemLoader

from diamond_backend.app.database.models.flow import Flows
from diamond_backend.app.utils.login_flow import load_portal_client

with as_file(files("diamond_backend").joinpath("app/data/template")) as fpath:
    env = Environment(loader=FileSystemLoader(fpath))

logger = logging.getLogger(__name__)


def _validate_source(source: str):
    """Return the function name if valid, otherwise raise ValueError."""
    tree = ast.parse(source)
    funcs = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(funcs) != 1:
        raise ValueError("Source must contain exactly one top-level function.")
    func = funcs[0]

    # No exec, eval, or open calls
    forbidden_calls = {"exec", "eval", "open", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in forbidden_calls:
                raise ValueError(f"Use of '{node.func.id}' is not allowed.")

    return func.name


def get_flow_client(request_cookies):
    if not (tokens_cookie := request_cookies.get("tokens")):
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

    try:
        client = load_portal_client()
        flow = Flows.query.filter_by(template="run_function").first()
        flow_id = flow.flow_id

        flow_token = None
        if flow_id in tokens_data:
            flow_token = tokens_data[flow_id]
        else:
            logger.error("No flow token found in tokens")
            raise globus_sdk.GlobusAPIError("No flow token found", http_status=401)

        # token_data = tokens_data.get("flows.globus.org")
        authorizer = globus_sdk.RefreshTokenAuthorizer(
            flow_token["refresh_token"],
            client,
            access_token=flow_token["access_token"],
            expires_at=flow_token["expires_at_seconds"],
        )
        flow_client = globus_sdk.FlowsClient(authorizer=authorizer)
        return flow_client
    except Exception as e:
        logger.error(f"Error initializing transfer client: {e}")
        raise globus_sdk.GlobusAPIError(
            f"Error initializing transfer client: {str(e)}",
            http_status=500,
        )


def get_specific_flow_client(request_cookies, flow_id) -> globus_sdk.SpecificFlowClient:
    if not (tokens_cookie := request_cookies.get("tokens")):
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

    client = load_portal_client()
    flow = Flows.query.filter_by(template="run_function").first()
    flow_id = flow.flow_id
    token_data = tokens_data.get(flow_id)
    authorizer = globus_sdk.RefreshTokenAuthorizer(
        token_data["refresh_token"],
        client,
        access_token=token_data["access_token"],
        expires_at=token_data["expires_at_seconds"],
    )
    return globus_sdk.SpecificFlowClient(flow_id, authorizer=authorizer)


def submit_flow(request_json, request_cookies, function_id, fn_params):
    endpoint_id = request_json.get("endpoint")
    task_name = request_json.get("taskName")

    flow_entry = Flows.query.filter_by(template="run_function").first()
    if not flow_entry:
        logger.error("Run function flow not found in database.")
        return jsonify({"error": "Run function flow not initialized"})

    flow_id = flow_entry.flow_id
    logger.info(f"Using existing flow definition with ID: {flow_id}")

    try:
        gsfc = get_specific_flow_client(request_cookies, flow_id)
        try:
            flow_run_response = gsfc.run_flow(
                body={
                    "endpoint_id": endpoint_id,
                    "function_id": function_id,
                    "function_kwargs": fn_params,
                    "user_endpoint_config": {
                        "account": fn_params.get("account"),
                        "partition": fn_params.get("partition"),
                        "worker_init": 'export PATH="$HOME/.local/bin:$PATH"; if ! command -v uv &> /dev/null; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi; VENV="$HOME/.globus_compute/.venvs/py3139-delta-4150"; uv venv --allow-existing "$VENV" --python 3.13.9; source "$VENV/bin/activate"; uv pip install globus-compute-endpoint==4.15.0',
                    },
                },
                label=task_name,
                tags=[task_name, endpoint_id],
            )
        except globus_sdk.FlowsAPIError as e:
            if e.code == "MISSING_SCOPE":
                required_scopes = [
                    e.message.replace("The following scope is required: ", "")
                ]
                return jsonify(
                    {
                        "flow_run_id": None,
                        "flow_id": None,
                        "required_scopes": required_scopes,
                    }
                )
            else:
                return jsonify(
                    {"error": str(e), "messages": e.messages, "code": e.http_status}
                ), e.http_status

        flow_run_id = flow_run_response["run_id"]
        logger.info(f"Globus Flow started with run_id: {flow_run_id}")
        return jsonify({"flow_run_id": flow_run_id, "flow_id": flow_id})

    except globus_sdk.GlobusAPIError as e:
        logger.exception("Globus API error when creating or running flow.")
        return jsonify(
            {"error": str(e), "messages": e.messages, "code": e.http_status}
        ), e.http_status
    except Exception as e:
        logger.exception("An unexpected error occurred during flow submission.")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


def get_flow_result(request_cookies, flow_run_id):
    try:
        gfc = get_flow_client(request_cookies)
    except globus_sdk.GlobusAPIError as e:
        return jsonify({"error": str(e), "messages": e.messages}), e.http_status
    except Exception as e:
        logger.exception("Failed to get Globus Flows client.")
        return jsonify({"error": f"Failed to get Globus Flows client: {str(e)}"}), 500

    flow_status = gfc.get_run(flow_run_id)
    return flow_status
