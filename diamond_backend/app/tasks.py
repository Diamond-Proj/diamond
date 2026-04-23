import logging
import os
import re
import time

from flask import jsonify, request
from globus_compute_sdk.errors import TaskPending

from diamond_backend.app import app, g_database
from diamond_backend.app.task_runtime import (
    TaskSubmissionError,
    read_remote_task_log,
    refresh_identity_task_statuses,
    submit_batch_script_task,
)
from diamond_backend.app.utils.config_loader import (
    load_container_module_command,
)
from diamond_backend.app.utils.data_prep import globus_compute_wrapped_run
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client
from diamond_backend.app.utils.scripts_render import (
    render_submit_task_script,
    render_task_template_script,
)

logger = logging.getLogger(__name__)
FINETUNED_MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
ARTIFACT_PATH_MARKER_PATTERN = re.compile(r"^DIAMOND_ARTIFACT_PATH=(.+)$", re.MULTILINE)
VLLM_TASK_LOG_PREFIX = "vllm_task|"
VLLM_READY_STATES = {"PENDING", "RUNNING", "COMPLETING"}
VLLM_OPTIONAL_CHAT_FIELDS = (
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "max_tokens",
)
VLLM_CONNECT_RETRY_INITIAL_SECONDS = max(
    0.5, float(os.getenv("VLLM_CONNECT_RETRY_INITIAL_SECONDS", "1"))
)
VLLM_CONNECT_RETRY_MAX_SECONDS = max(
    VLLM_CONNECT_RETRY_INITIAL_SECONDS,
    float(os.getenv("VLLM_CONNECT_RETRY_MAX_SECONDS", "5")),
)
VLLM_CONNECT_RETRY_BACKOFF_MULTIPLIER = max(
    1.0, float(os.getenv("VLLM_CONNECT_RETRY_BACKOFF_MULTIPLIER", "1.5"))
)
VLLM_CHAT_RESULT_GRACE_SECONDS = max(
    30, int(os.getenv("VLLM_CHAT_RESULT_GRACE_SECONDS", "120"))
)


def _validate_finetuned_model_name(value):
    if not isinstance(value, str):
        raise ValueError("finetuned_model_name must be a non-empty string")

    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError("finetuned_model_name must be a non-empty string")
    if normalized_value in {".", ".."}:
        raise ValueError("finetuned_model_name cannot be '.' or '..'")
    if "/" in normalized_value or "\\" in normalized_value:
        raise ValueError("finetuned_model_name cannot contain path separators")
    if not FINETUNED_MODEL_NAME_PATTERN.fullmatch(normalized_value):
        raise ValueError(
            "finetuned_model_name can only contain letters, numbers, '.', '-', '_'"
        )

    return normalized_value


def _build_finetuned_artifact_path(*, finetuned_model_path, finetuned_model_name):
    if not finetuned_model_path or not finetuned_model_name:
        return ""
    return os.path.join(str(finetuned_model_path).strip(), finetuned_model_name)


def _extract_artifact_path_from_submit_stdout(submit_stdout):
    if not isinstance(submit_stdout, str):
        return ""
    match = ARTIFACT_PATH_MARKER_PATTERN.search(submit_stdout)
    if not match:
        return ""
    return match.group(1).strip()


def _parse_delimited_key_value_string(raw_value, prefix):
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    if not normalized.startswith(prefix):
        return None

    parsed_values = {}
    for item in normalized.split("|")[1:]:
        key, separator, value = item.partition("=")
        if not separator:
            continue
        parsed_values[key.strip()] = value.strip()
    return parsed_values


def _parse_vllm_task_log_info(log_path):
    parsed_values = _parse_delimited_key_value_string(log_path, VLLM_TASK_LOG_PREFIX)
    if not parsed_values:
        return None
    return {"model": parsed_values.get("model", "").strip()}


def _build_vllm_task_log_info(model):
    normalized_model = str(model or "").strip() or "diamond-assistant"
    return f"{VLLM_TASK_LOG_PREFIX}model={normalized_model}"


def _derive_vllm_port_from_batch_job_id(batch_job_id):
    normalized_job_id = str(batch_job_id or "").strip()
    if not normalized_job_id.isdigit():
        return None

    try:
        tail = int(normalized_job_id[-4:])
    except (TypeError, ValueError):
        return None
    return 40000 + tail


def _build_vllm_host_candidates(compute_host, endpoint_host):
    normalized_compute_host = str(compute_host or "").strip()
    if not normalized_compute_host:
        return []

    candidates = [normalized_compute_host]
    normalized_endpoint_host = str(endpoint_host or "").strip()
    if "." not in normalized_compute_host and "." in normalized_endpoint_host:
        domain_suffix = normalized_endpoint_host.split(".", 1)[1].strip()
        if domain_suffix:
            candidates.append(f"{normalized_compute_host}.{domain_suffix}")

    deduped_candidates = []
    seen = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            deduped_candidates.append(candidate)
    return deduped_candidates


def _validate_vllm_chat_messages(messages):
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty array")

    for idx, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ValueError(f"messages[{idx}] must be a JSON object")
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not role.strip():
            raise ValueError(f"messages[{idx}].role must be a non-empty string")
        if not isinstance(content, (str, list)):
            raise ValueError(f"messages[{idx}].content must be a string or array")


def invoke_vllm_chat_completion(
    batch_job_id, port, payload, timeout_seconds=120, endpoint_host=""
):
    import json
    import subprocess
    import time
    from urllib import error as urllib_error
    from urllib import request as urllib_request

    def _run_command(command):
        result = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return {
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
            "returncode": result.returncode,
        }

    def _resolve_first_host(nodelist):
        cleaned = (nodelist or "").strip()
        if not cleaned:
            return ""
        cleaned = cleaned.split()[0]
        if cleaned in {"(null)", "None", "N/A"}:
            return ""

        if "[" in cleaned and "]" in cleaned:
            expanded = _run_command(["scontrol", "show", "hostnames", cleaned])
            if expanded["returncode"] == 0 and expanded["stdout"]:
                return expanded["stdout"].splitlines()[0].strip()
            return ""

        return cleaned.split(",")[0].strip()

    def _is_retryable_http_status(status_code):
        return status_code in {408, 425, 429, 500, 502, 503, 504}

    def _default_host_candidates(compute_host, endpoint_host_name):
        normalized_compute_host = str(compute_host or "").strip()
        if not normalized_compute_host:
            return []

        candidates = [normalized_compute_host]
        normalized_endpoint_host = str(endpoint_host_name or "").strip()
        if "." not in normalized_compute_host and "." in normalized_endpoint_host:
            domain_suffix = normalized_endpoint_host.split(".", 1)[1].strip()
            if domain_suffix:
                candidates.append(f"{normalized_compute_host}.{domain_suffix}")

        deduped = []
        seen = set()
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                deduped.append(candidate)
        return deduped

    host_candidate_builder = globals().get("_build_vllm_host_candidates")
    if not callable(host_candidate_builder):
        host_candidate_builder = _default_host_candidates

    try:
        retry_initial_seconds = float(
            globals().get("VLLM_CONNECT_RETRY_INITIAL_SECONDS", 1.0)
        )
    except (TypeError, ValueError):
        retry_initial_seconds = 1.0
    retry_initial_seconds = max(0.5, retry_initial_seconds)

    try:
        retry_max_seconds = float(globals().get("VLLM_CONNECT_RETRY_MAX_SECONDS", 5.0))
    except (TypeError, ValueError):
        retry_max_seconds = 5.0
    retry_max_seconds = max(retry_initial_seconds, retry_max_seconds)

    try:
        retry_backoff_multiplier = float(
            globals().get("VLLM_CONNECT_RETRY_BACKOFF_MULTIPLIER", 1.5)
        )
    except (TypeError, ValueError):
        retry_backoff_multiplier = 1.5
    retry_backoff_multiplier = max(1.0, retry_backoff_multiplier)

    try:
        normalized_port = int(port)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "error": "Invalid vLLM port",
            "details": str(port),
            "state": "INVALID_PORT",
        }

    try:
        normalized_timeout_seconds = max(10, int(timeout_seconds))
    except (TypeError, ValueError):
        normalized_timeout_seconds = 120

    deadline = time.time() + normalized_timeout_seconds
    encoded_payload = json.dumps(payload).encode("utf-8")
    backoff_delay_seconds = retry_initial_seconds
    attempt_count = 0
    last_failure = {
        "ok": False,
        "error": "Failed to connect to vLLM service on compute node",
        "details": "No connection attempts were made",
        "state": "CONNECTION_FAILED",
        "port": normalized_port,
    }

    while time.time() < deadline:
        attempt_count += 1
        squeue_result = _run_command(
            ["squeue", "-h", "-j", str(batch_job_id), "-o", "%N"]
        )
        nodelist = squeue_result["stdout"]
        if not nodelist:
            last_failure = {
                "ok": False,
                "error": "SLURM job has no assigned node yet",
                "details": squeue_result["stderr"],
                "state": "NO_ASSIGNED_NODE",
                "port": normalized_port,
                "attempts": attempt_count,
            }
        else:
            host = _resolve_first_host(nodelist)
            if not host:
                last_failure = {
                    "ok": False,
                    "error": "Failed to resolve compute node from SLURM nodelist",
                    "details": nodelist,
                    "state": "NODE_RESOLUTION_FAILED",
                    "port": normalized_port,
                    "attempts": attempt_count,
                }
            else:
                host_candidates = host_candidate_builder(host, endpoint_host)
                if not host_candidates:
                    host_candidates = [host]

                for candidate_host in host_candidates:
                    url = (
                        f"http://{candidate_host}:{normalized_port}/v1/chat/completions"
                    )
                    request_object = urllib_request.Request(
                        url,
                        data=encoded_payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    remaining_attempt_budget = deadline - time.time()
                    if remaining_attempt_budget <= 0:
                        break
                    per_attempt_timeout = min(10.0, max(1.0, remaining_attempt_budget))

                    try:
                        with urllib_request.urlopen(
                            request_object, timeout=per_attempt_timeout
                        ) as response:
                            body = response.read().decode("utf-8")
                    except urllib_error.HTTPError as exc:
                        body = exc.read().decode("utf-8", errors="replace")
                        last_failure = {
                            "ok": False,
                            "error": "vLLM returned an HTTP error",
                            "details": body,
                            "http_status": exc.code,
                            "node": candidate_host,
                            "url": url,
                            "port": normalized_port,
                            "attempts": attempt_count,
                        }
                        if not _is_retryable_http_status(exc.code):
                            return last_failure
                        continue
                    except Exception as exc:
                        last_failure = {
                            "ok": False,
                            "error": "Failed to connect to vLLM service on compute node",
                            "details": str(exc),
                            "state": "CONNECTION_FAILED",
                            "node": candidate_host,
                            "url": url,
                            "port": normalized_port,
                            "attempts": attempt_count,
                        }
                        continue

                    try:
                        parsed_response = json.loads(body)
                    except json.JSONDecodeError:
                        last_failure = {
                            "ok": False,
                            "error": "vLLM returned a non-JSON response",
                            "details": body,
                            "state": "INVALID_RESPONSE",
                            "node": candidate_host,
                            "url": url,
                            "port": normalized_port,
                            "attempts": attempt_count,
                        }
                        continue

                    return {
                        "ok": True,
                        "node": candidate_host,
                        "port": normalized_port,
                        "base_url": f"http://{candidate_host}:{normalized_port}/v1",
                        "response": parsed_response,
                        "attempts": attempt_count,
                    }

        remaining_seconds = deadline - time.time()
        if remaining_seconds <= 0:
            break
        sleep_seconds = min(backoff_delay_seconds, remaining_seconds)
        time.sleep(sleep_seconds)
        backoff_delay_seconds = min(
            backoff_delay_seconds * retry_backoff_multiplier,
            retry_max_seconds,
        )

    if "attempts" not in last_failure:
        last_failure["attempts"] = attempt_count
    return last_failure


@app.route("/api/submit_task", methods=["POST"])
@authenticated
def diamond_endpoint_submit_job():
    request_data = request.get_json(silent=True) or {}
    task_define = request_data.get("task_define") or {}
    if not isinstance(task_define, dict):
        return jsonify({"error": "task_define must be a JSON object"}), 400

    def pick_field(*keys, default=None):
        for key in keys:
            value = request_data.get(key)
            if value not in (None, ""):
                return value
        for key in keys:
            value = task_define.get(key)
            if value not in (None, ""):
                return value
        return default

    def pick_raw_field(*keys):
        for key in keys:
            if key in request_data:
                return True, request_data.get(key)
        for key in keys:
            if key in task_define:
                return True, task_define.get(key)
        return False, None

    endpoint_id = pick_field("endpoint")
    task_name = pick_field("taskName", "task_name")
    partition = pick_field("partition")
    account = pick_field("account")
    reservation = pick_field("reservation", default="")
    container_name = pick_field("container", "container_name")
    task_command = pick_field("task", "task_command", default="")
    num_of_nodes = pick_field("num_of_nodes", default="1")  # 1 node is a safe default
    time_duration = pick_field("time_duration")
    slurm_options = pick_field("slurm_options", default="")
    task_template_name = pick_field("task_template")
    identity_id = request.cookies.get("primary_identity")
    dataset_id = pick_field("dataset_id")
    finetuned_model_path = pick_field("finetuned_model_path", default="")
    finetuned_model_name_present, raw_finetuned_model_name = pick_raw_field(
        "finetuned_model_name"
    )
    finetuned_model_name = None
    if finetuned_model_name_present:
        try:
            finetuned_model_name = _validate_finetuned_model_name(
                raw_finetuned_model_name
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    artifact_path = _build_finetuned_artifact_path(
        finetuned_model_path=finetuned_model_path,
        finetuned_model_name=finetuned_model_name,
    )
    vllm_task_log_info = None
    if str(task_template_name or "").strip() == "vllm-inference.j2":
        vllm_task_log_info = _build_vllm_task_log_info(
            pick_field("served_model_name", default="diamond-assistant")
        )

    if not endpoint_id:
        return jsonify({"error": "endpoint is required"}), 400
    if not task_name:
        return jsonify({"error": "taskName is required"}), 400

    if reservation and reservation != "":
        reservation = str(reservation)
        if not reservation.startswith("--reservation="):
            reservation = "--reservation=" + reservation

    dataset_path = pick_field("dataset_path", "dataset_system_path", default="")

    if dataset_id:
        dataset_system_path = g_database.get_dataset_by_id(dataset_id).system_path
    else:
        dataset_system_path = dataset_path

    if not dataset_path:
        dataset_path = dataset_system_path

    container_path = ""
    if task_template_name:
        container_path = pick_field("container_path", default="")
        if not container_path and container_name:
            try:
                container_dir_path = g_database.get_container_path_by_name(
                    container_name
                )
                container_path = os.path.join(
                    container_dir_path, container_name + ".sif"
                )
                logger.info(f"Submit task container path: {container_path}")
            except Exception:
                container_path = str(container_name)
    elif container_name:
        container_dir_path = g_database.get_container_path_by_name(container_name)
        container_path = os.path.join(container_dir_path, container_name + ".sif")
        logger.info(f"Submit task container path: {container_path}")

    if not task_template_name:
        missing_fields = []
        if not partition:
            missing_fields.append("partition")
        if not account:
            missing_fields.append("account")
        if not container_name:
            missing_fields.append("container")
        if not time_duration:
            missing_fields.append("time_duration")
        if missing_fields:
            return (
                jsonify(
                    {
                        "error": "Missing required fields for default submit_task template",
                        "missing_fields": missing_fields,
                    }
                ),
                400,
            )

    task_name = str(task_name)

    location = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id, identity_id=identity_id
    )
    stdout_path = os.path.join(location, "logs", task_name + ".stdout")
    stderr_path = os.path.join(location, "logs", task_name + ".stderr")

    endpoint_host = g_database.get_endpoint_host(endpoint_uuid=endpoint_id)
    container_module_command = load_container_module_command(endpoint_host)
    if task_template_name:
        render_context = {
            **task_define,
            "task_name": task_name,
            "taskName": task_name,
            "location": location,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "time_duration": time_duration,
            "partition": partition,
            "account": account,
            "reservation": reservation,
            "num_of_nodes": num_of_nodes,
            "container": container_path,
            "container_name": container_name,
            "container_path": container_path,
            "container_module_command": container_module_command,
            "dataset_system_path": dataset_system_path,
            "dataset_path": dataset_path,
            "task_command": task_command,
            "slurm_options": slurm_options,
        }
        if finetuned_model_name is not None:
            render_context["finetuned_model_name"] = finetuned_model_name
        if finetuned_model_path:
            render_context["finetuned_model_path"] = str(finetuned_model_path).strip()
        try:
            submit_task_script = render_task_template_script(
                str(task_template_name), render_context
            )
        except Exception as e:
            logger.exception("Failed to render task template: %s", task_template_name)
            return jsonify({"error": f"Failed to render task template: {e}"}), 400
    else:
        submit_task_script = render_submit_task_script(
            task_name=task_name,
            location=location,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            time_duration=time_duration,
            partition=partition,
            account=account,
            reservation=reservation,
            num_of_nodes=num_of_nodes,
            container_module_command=container_module_command,
            container=container_path,
            dataset_system_path=dataset_system_path,
            task_command=task_command,
            slurm_options=slurm_options,
        )
    logger.info(f"Submit task script: {submit_task_script}")
    try:
        submission = submit_batch_script_task(
            endpoint_id=endpoint_id,
            identity_id=identity_id,
            task_name=task_name,
            submit_script=submit_task_script,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            log_path=vllm_task_log_info,
            checkpoint_path=artifact_path,
            checkpoint_path_extractor=_extract_artifact_path_from_submit_stdout,
        )
    except TaskSubmissionError as exc:
        return jsonify(exc.to_response_payload()), exc.http_status

    return jsonify(
        {
            "task_id": submission["task_id"],
            "batch_job_id": submission["batch_job_id"],
            "task_name": submission["task_name"],
            "message": "Task submitted successfully",
        }
    )


@app.route("/api/get_task_status", methods=["GET"])
@authenticated
def diamond_get_task_status():
    identity_id = request.cookies.get("primary_identity")
    updated_tasks = refresh_identity_task_statuses(identity_id)

    # Format tasks data for JSON response
    tasks_data = {}
    for task in updated_tasks:
        vllm_task_info = _parse_vllm_task_log_info(task.log_path)
        vllm_port = _derive_vllm_port_from_batch_job_id(task.batch_job_id)
        task_type = "vllm_chat" if vllm_task_info else "default"
        tasks_data[task.task_id] = {
            "task_id": task.task_id,
            "identity_id": task.identity_id,
            "task_name": task.task_name,
            "status": task.task_status,
            "task_type": task_type,
            "details": {
                "endpoint_id": task.compute_endpoint_id or "N/A",
                "task_create_time": task.task_create_time,
            },
            "result": task.stdout_path,
            "error": task.stderr_path,
            "artifact_path": task.checkpoint_path,
            "chat": (
                {
                    "port": vllm_port,
                    "model": vllm_task_info.get("model", ""),
                }
                if vllm_task_info
                else None
            ),
        }

    logger.debug(f"Updated task status response: {tasks_data}")
    return jsonify(tasks_data)


@app.route("/api/vllm_chat", methods=["POST"])
@authenticated
def diamond_vllm_chat():
    identity_id = request.cookies.get("primary_identity")
    payload = request.get_json(silent=True) or {}

    task_id = str(payload.get("task_id", "")).strip()
    if not task_id:
        return jsonify({"error": "task_id is required"}), 400

    task = g_database.get_task(task_id=task_id, identity_id=identity_id)
    if not task:
        return jsonify({"error": f"Task {task_id} not found"}), 404

    service_info = _parse_vllm_task_log_info(task.log_path)
    if not service_info:
        return jsonify({"error": "Task is not a vLLM service task"}), 400
    service_port = _derive_vllm_port_from_batch_job_id(task.batch_job_id)
    if service_port is None:
        return jsonify({"error": "Could not derive vLLM port from SLURM job id"}), 400

    if task.task_status not in VLLM_READY_STATES:
        return (
            jsonify(
                {
                    "error": "vLLM service task is not in a chat-ready state",
                    "task_status": task.task_status,
                    "required_status": sorted(VLLM_READY_STATES),
                }
            ),
            409,
        )

    messages = payload.get("messages")
    try:
        _validate_vllm_chat_messages(messages)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    resolved_model = str(
        payload.get("model") or service_info.get("model") or "diamond-assistant"
    ).strip()
    if not resolved_model:
        return jsonify({"error": "model is required"}), 400

    chat_payload = {
        "model": resolved_model,
        "messages": messages,
        "stream": False,
    }
    for field in VLLM_OPTIONAL_CHAT_FIELDS:
        if field in payload and payload[field] not in (None, ""):
            chat_payload[field] = payload[field]

    timeout_seconds_raw = payload.get("timeout_seconds", 180)
    try:
        timeout_seconds = int(timeout_seconds_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "timeout_seconds must be an integer"}), 400
    timeout_seconds = min(max(timeout_seconds, 10), 600)

    globus_compute_client = initialize_globus_compute_client()
    vllm_chat_function_id = globus_compute_client.register_function(
        invoke_vllm_chat_completion
    )
    user_endpoint_config = g_database.get_endpoint_user_config(
        identity_id=identity_id, endpoint_uuid=task.compute_endpoint_id
    )

    try:
        endpoint_host = g_database.get_endpoint_host(
            endpoint_uuid=task.compute_endpoint_id
        )
        vllm_chat_task_id = globus_compute_wrapped_run(
            globus_compute_client,
            endpoint_id=task.compute_endpoint_id,
            function_id=vllm_chat_function_id,
            user_endpoint_config=user_endpoint_config,
            kwargs={
                "batch_job_id": task.batch_job_id,
                "port": service_port,
                "payload": chat_payload,
                "timeout_seconds": timeout_seconds,
                "endpoint_host": endpoint_host,
            },
        )
    except Exception as e:
        logger.exception("Failed to submit vLLM chat request for task %s", task.task_id)
        return jsonify(
            {"error": "Failed to submit vLLM chat request", "details": str(e)}
        ), 502

    wait_deadline = time.time() + timeout_seconds + VLLM_CHAT_RESULT_GRACE_SECONDS
    vllm_chat_result = None
    while time.time() < wait_deadline:
        try:
            vllm_chat_result = globus_compute_client.get_result(vllm_chat_task_id)
            break
        except TaskPending:
            time.sleep(1)
            continue
        except Exception as e:
            logger.exception(
                "Failed to fetch vLLM chat result for endpoint task %s",
                vllm_chat_task_id,
            )
            return (
                jsonify(
                    {"error": "Failed to retrieve vLLM chat result", "details": str(e)}
                ),
                502,
            )

    if vllm_chat_result is None:
        return (
            jsonify(
                {
                    "error": "Timed out waiting for vLLM chat response",
                    "timeout_seconds": timeout_seconds,
                }
            ),
            504,
        )

    if not isinstance(vllm_chat_result, dict):
        return (
            jsonify(
                {
                    "error": "Unexpected vLLM chat response format from endpoint",
                    "details": str(vllm_chat_result),
                }
            ),
            502,
        )

    if not vllm_chat_result.get("ok"):
        response_status = vllm_chat_result.get("http_status")
        if not isinstance(response_status, int) or not (400 <= response_status <= 599):
            response_status = 503
        return (
            jsonify(
                {
                    "error": vllm_chat_result.get("error", "vLLM chat request failed"),
                    "details": vllm_chat_result.get("details", ""),
                    "service": {
                        "node": vllm_chat_result.get("node", ""),
                        "port": service_port,
                        "model": resolved_model,
                        "attempts": vllm_chat_result.get("attempts"),
                    },
                    "task_status": task.task_status,
                }
            ),
            response_status,
        )

    return jsonify(
        {
            "task_id": task.task_id,
            "batch_job_id": task.batch_job_id,
            "task_status": task.task_status,
            "completion": vllm_chat_result.get("response", {}),
            "service": {
                "node": vllm_chat_result.get("node", ""),
                "port": service_port,
                "model": resolved_model,
                "base_url": vllm_chat_result.get("base_url", ""),
                "attempts": vllm_chat_result.get("attempts"),
            },
        }
    )


@app.route("/api/get_task_log", methods=["GET"])
@authenticated
def diamond_get_task_log():
    identity_id = request.cookies.get("primary_identity")
    endpoint_id = request.args.get("endpoint_id")
    log_path = request.args.get("log_path")

    log_result = read_remote_task_log(
        identity_id=identity_id, endpoint_id=endpoint_id, log_path=log_path
    )
    logger.info("Loaded task log for endpoint %s path %s", endpoint_id, log_path)
    return jsonify({"log_content": log_result.get("content", "")})


@app.route("/api/delete_task", methods=["POST"])
@authenticated
def diamond_delete_task():
    # TODO: Does this need to talk to Globus at all?
    task_id = request.json.get("taskId")
    g_database.delete_task(task_id)
    logger.info(f"task {task_id} deleted")
    return jsonify({"message": "Task deleted successfully"})
