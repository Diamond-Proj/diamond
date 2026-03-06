import json
import logging
import os
import re
import time
from datetime import datetime

from flask import jsonify, request
from globus_compute_sdk.errors import TaskPending
from globus_sdk.services.compute.errors import ComputeAPIError

from diamond_backend.app import app, g_database
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.functions import (
    _escape_shell_braces,
    _make_shell_function,
)
from diamond_backend.app.utils.login_flow import initialize_globus_compute_client

logger = logging.getLogger(__name__)

LLMFLUX_SUBMIT_WAIT_TIMEOUT_SECONDS = max(
    5, int(os.getenv("LLMFLUX_SUBMIT_WAIT_TIMEOUT_SECONDS", "90"))
)
LLMFLUX_SUBMIT_POLL_INITIAL_SECONDS = max(
    0.5, float(os.getenv("LLMFLUX_SUBMIT_POLL_INITIAL_SECONDS", "5"))
)
LLMFLUX_SUBMIT_POLL_MAX_SECONDS = max(
    LLMFLUX_SUBMIT_POLL_INITIAL_SECONDS,
    float(os.getenv("LLMFLUX_SUBMIT_POLL_MAX_SECONDS", "15")),
)
LLMFLUX_SUBMIT_POLL_BACKOFF_MULTIPLIER = max(
    1.0, float(os.getenv("LLMFLUX_SUBMIT_POLL_BACKOFF_MULTIPLIER", "1.5"))
)


def _resolve_path_for_endpoint(path_value, location):
    """Convert relative paths to endpoint workdir-local absolute paths."""
    if os.path.isabs(path_value):
        return path_value
    return os.path.join(location, path_value)


def _build_llmflux_bootstrap_lock_script(llmflux_version: str = "0.1.3"):
    """Build Python script that acquires lock and bootstraps llmflux runtime."""
    lines = [
        "import os",
        "import fcntl",
        "import subprocess",
        "import shutil",
        "import sys",
        "import time",
        "from pathlib import Path",
        "",
        "cwd = Path.cwd().resolve()",
        "runtime_dir = cwd / '.diamond_runtime'",
        f"venv_name = 'llmflux-{llmflux_version}'",
        "venv_dir = runtime_dir / venv_name",
        "venv_python = venv_dir / 'bin' / 'python'",
        "lock_path = runtime_dir / '.bootstrap.lock'",
        "",
        "runtime_dir.mkdir(parents=True, exist_ok=True)",
        "lock_path.touch(exist_ok=True)",
        "",
        "uv_cmd = None",
        "uv_path = shutil.which('uv')",
        "if uv_path:",
        "    uv_cmd = [uv_path]",
        "else:",
        "    print('`uv` not found on PATH; attempting install via pip', file=sys.stderr)",
        "    try:",
        "        subprocess.check_call(",
        "            [sys.executable, '-m', 'pip', 'install', '--user', '-q', 'uv']",
        "        )",
        "    except subprocess.CalledProcessError as exc:",
        "        raise RuntimeError(",
        "            'Could not install `uv` (Astral) via pip. '",
        "            'Ensure internet access to PyPI or preinstall uv on the endpoint.'",
        "        ) from exc",
        "    uv_cmd = [sys.executable, '-m', 'uv']",
        "",
        "try:",
        "    subprocess.check_call(uv_cmd + ['--version'])",
        "except subprocess.CalledProcessError as exc:",
        "    raise RuntimeError(",
        "        'Installed `uv` is not runnable. Ensure uv is properly installed '",
        "        'on the endpoint and retry.'",
        "    ) from exc",
        "",
        "with lock_path.open('a+', encoding='utf-8') as lock_file:",
        "    lock_file.seek(0)",
        "    lock_snapshot = lock_file.read().strip()",
        "    print(",
        "        f'Inspecting bootstrap lock {lock_path}: ',",
        "        f\"{lock_snapshot or 'empty'}\",",
        "        file=sys.stderr,",
        "    )",
        "",
        "    wait_start = time.time()",
        "    while True:",
        "        try:",
        "            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)",
        "            break",
        "        except BlockingIOError:",
        "            if time.time() - wait_start > 300:",
        "                raise TimeoutError(",
        "                    f'Timed out waiting for bootstrap lock: {lock_path}'",
        "                )",
        "            time.sleep(0.5)",
        "",
        "    lock_file.seek(0)",
        "    lock_file.truncate()",
        "    lock_file.write(",
        "        f'pid={os.getpid()} acquired_at={int(time.time())} '",
        "        f'venv={venv_dir}\\n'",
        "    )",
        "    lock_file.flush()",
        "    os.fsync(lock_file.fileno())",
        "",
        "    must_bootstrap = not venv_python.exists()",
        "",
        "    def install_llmflux():",
        "        subprocess.check_call(",
        "            uv_cmd",
        "            + [",
        "                'pip',",
        "                'install',",
        "                '--python',",
        "                str(venv_python),",
        "                '-q',",
        f"                'llmflux=={llmflux_version}',",
        "            ]",
        "        )",
        "",
        "    def validate_llmflux():",
        "        subprocess.check_call([str(venv_python), '-c', 'import llmflux'])",
        "",
        "    if must_bootstrap:",
        "        subprocess.check_call(",
        "            uv_cmd + ['venv', '--python', '3.11', str(venv_dir)]",
        "        )",
        "        install_llmflux()",
        "        validate_llmflux()",
        "    else:",
        "        try:",
        "            validate_llmflux()",
        "        except subprocess.CalledProcessError:",
        "            print(",
        "                'Existing llmflux runtime is missing/corrupt; reinstalling',",
        "                file=sys.stderr,",
        "            )",
        "            try:",
        "                install_llmflux()",
        "                validate_llmflux()",
        "            except subprocess.CalledProcessError:",
        "                print(",
        "                    'Reinstall failed; recreating llmflux runtime venv',",
        "                    file=sys.stderr,",
        "                )",
        "                shutil.rmtree(venv_dir, ignore_errors=True)",
        "                subprocess.check_call(",
        "                    uv_cmd + ['venv', '--python', '3.11', str(venv_dir)]",
        "                )",
        "                install_llmflux()",
        "                validate_llmflux()",
        "",
        "    venv_bin = str(venv_dir / 'bin')",
        "    path_value = os.environ.get('PATH', '')",
        "    path_parts = path_value.split(':') if path_value else []",
        "    if venv_bin not in path_parts:",
        "        os.environ['PATH'] = ':'.join([venv_bin] + path_parts)",
        "    os.environ['VIRTUAL_ENV'] = str(venv_dir)",
        "    os.environ['DIAMOND_RUNTIME_VENV'] = str(venv_dir)",
        "",
        "    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)",
    ]
    return "\n".join(lines) + "\n"


def _build_llmflux_runner_script(
    account,
    partition,
    hf_token,
    input_path,
    output_path,
    model,
    batch_size,
    engine,
    llmflux_version="0.1.3",
):
    """Build Python script that executes SlurmRunner and prints job id."""
    input_json = json.dumps(input_path)
    output_json = json.dumps(output_path)
    model_json = json.dumps(model)
    account_json = json.dumps(account)
    partition_json = json.dumps(partition)
    engine_json = json.dumps(engine)
    hf_token_json = json.dumps(hf_token)

    lines = [
        "import os",
        "from pathlib import Path",
        "from llmflux.core.config import Config, EngineConfig",
        "from llmflux.slurm.runner import SlurmRunner",
        "",
        "cwd = Path.cwd().resolve()",
        f"runtime_venv = str(cwd / '.diamond_runtime' / 'llmflux-{llmflux_version}')",
        "runtime_venv_bin = str(Path(runtime_venv) / 'bin')",
        "path_value = os.environ.get('PATH', '')",
        "path_parts = path_value.split(':') if path_value else []",
        "if runtime_venv_bin not in path_parts:",
        "    os.environ['PATH'] = ':'.join([runtime_venv_bin] + path_parts)",
        "os.environ['VIRTUAL_ENV'] = runtime_venv",
        "os.environ['DIAMOND_RUNTIME_VENV'] = runtime_venv",
        "hf_home = cwd / '.cache' / 'huggingface'",
        "hf_home.mkdir(parents=True, exist_ok=True)",
        "os.environ['HF_HOME'] = str(hf_home)",
        "logs_dir = cwd / 'logs'",
        "logs_dir.mkdir(parents=True, exist_ok=True)",
        "os.environ['LLMFLUX_LOGS_DIR'] = str(logs_dir)",
        "data_dir = cwd / 'data'",
        "data_dir.mkdir(parents=True, exist_ok=True)",
        "os.environ['LLMFLUX_DATA_DIR'] = str(data_dir)",
        "models_dir = cwd / 'models'",
        "models_dir.mkdir(parents=True, exist_ok=True)",
        "os.environ['LLMFLUX_MODELS_DIR'] = str(models_dir)",
        "containers_dir = cwd / 'containers'",
        "containers_dir.mkdir(parents=True, exist_ok=True)",
        "os.environ['LLMFLUX_CONTAINERS_DIR'] = str(containers_dir)",
        f"os.environ['SLURM_ENGINE'] = {engine_json}",
        f"input_path = {input_json}",
        f"output_path = {output_json}",
        f"model = {model_json}",
        f"engine = {engine_json}",
        f"batch_size = {int(batch_size)}",
        f"account = {account_json}",
        f"partition = {partition_json}",
        f"hf_token = {hf_token_json}",
        "",
        "config = Config()",
        "slurm_config = config.get_slurm_config()",
        "slurm_config.account = account or os.getenv('SLURM_ACCOUNT', 'bcqj-delta-gpu')",
        "slurm_config.partition = partition or os.getenv('SLURM_PARTITION', 'gpuA100x4')",
        "slurm_config.time = '01:00:00'",
        "slurm_config.mem = '16G'",
        "slurm_config.gpus_per_node = 1",
        "engine_home_dir = '.vllm' if engine == 'vllm' else '.ollama'",
        "engine_config = EngineConfig(engine=engine, home=str(cwd / engine_home_dir))",
        "runner = SlurmRunner(",
        "    config=slurm_config,",
        "    workspace=str(cwd),",
        "    engine_config=engine_config,",
        ")",
        "job_id = runner.run(",
        "    input_path=input_path,",
        "    output_path=output_path,",
        "    model=model,",
        "    batch_size=batch_size,",
        "    HF_TOKEN=hf_token,",
        ")",
        "print(job_id)",
    ]
    return "\n".join(lines) + "\n"


def _build_llmflux_completion_status_script():
    """Build Python script that executes runner script and returns final job id."""
    lines = [
        "runner_env = os.environ.copy()",
        "venv_bin = str(venv_dir / 'bin')",
        "path_value = runner_env.get('PATH', '')",
        "path_parts = path_value.split(':') if path_value else []",
        "if venv_bin not in path_parts:",
        "    runner_env['PATH'] = ':'.join([venv_bin] + path_parts)",
        "runner_env['VIRTUAL_ENV'] = str(venv_dir)",
        "runner_env['DIAMOND_RUNTIME_VENV'] = str(venv_dir)",
        "completed = subprocess.run(",
        "    [str(venv_python), '-c', runner_script],",
        "    check=True,",
        "    capture_output=True,",
        "    text=True,",
        "    env=runner_env,",
        ")",
        "if completed.stderr:",
        "    print(completed.stderr, file=sys.stderr, end='')",
        "stdout_lines = [line for line in completed.stdout.splitlines() if line.strip()]",
        "if not stdout_lines:",
        "    raise RuntimeError('llmflux runner returned no stdout output')",
        "print(stdout_lines[-1])",
    ]
    return "\n".join(lines) + "\n"


def _build_llmflux_submit_script(
    workspace,
    account,
    partition,
    hf_token,
    input_path="prompts.jsonl",
    output_path="results.json",
    model="Qwen2.5-3B-Instruct",
    batch_size=4,
    engine="vllm",
):
    """Build Python submit script matching test script: env vars, HF cache, workspace."""
    llmflux_version = "0.1.3"
    runtime_venv_path = os.path.join(
        workspace, ".diamond_runtime", f"llmflux-{llmflux_version}"
    )
    bootstrap_lock_script = _build_llmflux_bootstrap_lock_script(
        llmflux_version=llmflux_version
    )
    runner_script = _build_llmflux_runner_script(
        account=account,
        partition=partition,
        hf_token=hf_token,
        input_path=input_path,
        output_path=output_path,
        model=model,
        batch_size=batch_size,
        engine=engine,
        llmflux_version=llmflux_version,
    )
    completion_status_script = _build_llmflux_completion_status_script()
    python_submit_script = (
        f"{bootstrap_lock_script}\n"
        f"runner_script = {json.dumps(runner_script)}\n\n"
        f"{completion_status_script}"
    )

    return (
        "set -euo pipefail\n"
        f"cd {json.dumps(workspace)} || exit 1\n"
        f"RUNTIME_VENV={json.dumps(runtime_venv_path)}\n"
        'export DIAMOND_RUNTIME_VENV="$RUNTIME_VENV"\n'
        'export VIRTUAL_ENV="$RUNTIME_VENV"\n'
        'export PATH="$RUNTIME_VENV/bin:$PATH"\n'
        'PYTHON_CMD="$(command -v python3 || command -v python || true)"\n'
        'if [ -z "$PYTHON_CMD" ]; then\n'
        '  echo "No python interpreter found on endpoint" >&2\n'
        "  exit 1\n"
        "fi\n"
        "\"$PYTHON_CMD\" <<'PYTHON'\n"
        f"{python_submit_script}"
        "PYTHON\n"
    )


def launch_llmflux(
    endpoint_id,
    identity_id,
    task_name,
    account,
    partition,
    hf_token,
    input_path="prompts.jsonl",
    output_path="results.json",
    model="Qwen2.5-3B-Instruct",
    batch_size=4,
    engine="vllm",
):
    if not endpoint_id:
        raise ValueError("endpoint is required")
    if not identity_id:
        raise ValueError("identity is required")
    if not task_name:
        raise ValueError("task name is required")
    if not account:
        raise ValueError("account is required")
    if not partition:
        raise ValueError("partition is required")

    globus_compute_client = initialize_globus_compute_client()
    diamond_dir = g_database.get_diamond_dir(
        endpoint_uuid=endpoint_id,
        identity_id=identity_id,
    )
    if not diamond_dir:
        raise ValueError("Unable to resolve endpoint work directory")

    resolved_input_path = _resolve_path_for_endpoint(input_path, diamond_dir)
    resolved_output_path = _resolve_path_for_endpoint(output_path, diamond_dir)
    llmflux_submit_script = _build_llmflux_submit_script(
        workspace=diamond_dir,
        hf_token=hf_token,
        account=account,
        partition=partition,
        input_path=resolved_input_path,
        output_path=resolved_output_path,
        model=model,
        batch_size=batch_size,
        engine=engine,
    )
    llmflux_shell_function = _make_shell_function(
        _escape_shell_braces(llmflux_submit_script)
    )
    llmflux_function_id = globus_compute_client.register_function(
        llmflux_shell_function
    )
    llmflux_task_id = globus_compute_client.run(
        endpoint_id=endpoint_id, function_id=llmflux_function_id
    )

    submit_result = None
    poll_attempt = 0
    poll_interval_seconds = LLMFLUX_SUBMIT_POLL_INITIAL_SECONDS
    wait_deadline = time.monotonic() + LLMFLUX_SUBMIT_WAIT_TIMEOUT_SECONDS
    while time.monotonic() < wait_deadline:
        poll_attempt += 1
        try:
            submit_result = globus_compute_client.get_result(llmflux_task_id)
            logger.info(
                "LLMFlux submit result: %s",
                globus_compute_client.get_task(llmflux_task_id),
            )
        except TaskPending:
            remaining_seconds = max(0.0, wait_deadline - time.monotonic())
            sleep_seconds = min(poll_interval_seconds, remaining_seconds)
            if sleep_seconds <= 0:
                break
            if poll_attempt == 1 or poll_attempt % 5 == 0:
                logger.info(
                    (
                        "LLMFlux submit task %s still pending after %.1fs "
                        "(attempt=%d, next_poll=%.1fs)"
                    ),
                    llmflux_task_id,
                    LLMFLUX_SUBMIT_WAIT_TIMEOUT_SECONDS - remaining_seconds,
                    poll_attempt,
                    sleep_seconds,
                )
            time.sleep(sleep_seconds)
            poll_interval_seconds = min(
                LLMFLUX_SUBMIT_POLL_MAX_SECONDS,
                poll_interval_seconds * LLMFLUX_SUBMIT_POLL_BACKOFF_MULTIPLIER,
            )
            continue
        except Exception as e:
            logger.exception(
                "Failed to fetch llmflux results for task_id: %s", llmflux_task_id
            )
            raise RuntimeError(
                "Failed to submit llmflux job - could not fetch results from endpoint"
            ) from e
        else:
            break

    if submit_result is None:
        logger.warning(
            (
                "LLMFlux submit task %s did not complete within %.1fs; "
                "continuing with async submission state."
            ),
            llmflux_task_id,
            LLMFLUX_SUBMIT_WAIT_TIMEOUT_SECONDS,
        )

    submit_stdout = getattr(submit_result, "stdout", "")
    submit_stderr = getattr(submit_result, "stderr", "")
    submit_returncode = getattr(submit_result, "returncode", None)

    if submit_result is not None and submit_returncode not in (None, 0):
        logger.error(
            "LLMFlux submit task failed with return code %s. stdout=%s stderr=%s",
            submit_returncode,
            submit_stdout,
            submit_stderr,
        )
        raise RuntimeError(
            "Failed to submit llmflux job - sbatch returned a non-zero exit code"
        )

    # LLMFlux runner prints the final job id on the last stdout line.
    stdout_lines = [line.strip() for line in submit_stdout.splitlines() if line.strip()]
    slurm_job_id = None
    if stdout_lines:
        last_stdout_line = stdout_lines[-1]
        if re.fullmatch(r"\d+", last_stdout_line):
            slurm_job_id = last_stdout_line
        else:
            match = re.search(r"Submitted batch job (\d+)", last_stdout_line)
            if match:
                slurm_job_id = match.group(1)

    if submit_result is not None and not slurm_job_id:
        logger.warning(
            (
                "Could not parse LLMFlux job ID from stdout: %s stderr: %s. "
                "Task will remain pending until status polling resolves it."
            ),
            submit_stdout,
            submit_stderr,
        )

    if slurm_job_id is not None:
        stdout_path = os.path.join(diamond_dir, "logs", slurm_job_id + ".out")
        stderr_path = os.path.join(diamond_dir, "logs", slurm_job_id + ".err")
    else:
        stdout_path = os.path.join(diamond_dir, "logs", task_name + ".stdout")
        stderr_path = os.path.join(diamond_dir, "logs", task_name + ".stderr")
    g_database.save_task(
        task_id=llmflux_task_id,
        batch_job_id=slurm_job_id,
        task_name=task_name,
        identity_id=identity_id,
        task_status="PENDING",
        task_create_time=datetime.now(),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        compute_endpoint_id=endpoint_id,
        checkpoint_path="",
    )

    logger.info(
        "LLMFlux job submitted via Globus Compute task %s with SLURM job %s",
        llmflux_task_id,
        slurm_job_id,
    )
    if submit_result is None:
        submission_status = "submitted_async"
    elif slurm_job_id is None:
        submission_status = "submitted_pending_confirmation"
    else:
        submission_status = "submitted"

    return {
        "task_id": llmflux_task_id,
        "batch_job_id": slurm_job_id,
        "task_name": task_name,
        "submission_status": submission_status,
        "compute_task_status": "PENDING",
        "input_path": resolved_input_path,
        "output_path": resolved_output_path,
    }


@app.route("/api/launch_llmflux", methods=["POST"])
@authenticated
def diamond_launch_llmflux():
    payload = request.get_json(silent=True) or {}
    endpoint_id = payload.get("endpoint")
    identity_id = request.cookies.get("primary_identity")
    task_name = payload.get("taskName", "launch-llmflux")
    account = payload.get("account")
    partition = payload.get("partition")
    input_path = payload.get("input_path", "prompts.jsonl")
    output_path = payload.get("output_path", "results.json")
    model = payload.get("model", "Qwen2.5-3B-Instruct")
    engine = payload.get("engine", "vllm")
    hf_token = payload.get("hf_token", "")
    try:
        batch_size = int(payload.get("batch_size", 4))
    except (TypeError, ValueError):
        return jsonify({"error": "batch_size must be an integer"}), 400
    if batch_size < 1:
        return jsonify({"error": "batch_size must be >= 1"}), 400
    if not isinstance(input_path, str) or not input_path.strip():
        return jsonify({"error": "input_path must be a non-empty string"}), 400
    if not isinstance(output_path, str) or not output_path.strip():
        return jsonify({"error": "output_path must be a non-empty string"}), 400
    if not isinstance(model, str) or not model.strip():
        return jsonify({"error": "model must be a non-empty string"}), 400
    if not isinstance(engine, str) or engine not in ("vllm", "ollama"):
        return jsonify({"error": "engine must be 'vllm' or 'ollama'"}), 400
    if account is not None and not isinstance(account, str):
        return jsonify({"error": "account must be a string"}), 400
    if partition is not None and not isinstance(partition, str):
        return jsonify({"error": "partition must be a string"}), 400
    if hf_token is not None and not isinstance(hf_token, str):
        return jsonify({"error": "hf_token must be a string"}), 400
    if not isinstance(task_name, str) or not task_name.strip():
        return jsonify({"error": "taskName must be a non-empty string"}), 400
    task_name = task_name.strip()
    try:
        submission = launch_llmflux(
            endpoint_id=endpoint_id,
            identity_id=identity_id,
            task_name=task_name,
            account=account,
            partition=partition,
            hf_token=hf_token,
            input_path=input_path,
            output_path=output_path,
            model=model,
            batch_size=batch_size,
            engine=engine,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ComputeAPIError as e:
        logger.exception("Failed to submit llmflux task to Globus Compute: %s", e)
        return jsonify(
            {"status": e.http_status, "messages": e.messages, "error": str(e)}
        ), e.http_status
    except RuntimeError as e:
        logger.exception("Failed to launch llmflux task: %s", e)
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.exception("Failed to submit llmflux task to Globus Compute: %s", e)
        return jsonify(
            {
                "status": 500,
                "messages": ["Failed to submit llmflux task to Globus Compute"],
                "error": str(e),
            }
        ), 500

    return jsonify(
        {
            "task_id": submission["task_id"],
            "batch_job_id": submission["batch_job_id"],
            "task_name": submission["task_name"],
            "submission_status": submission["submission_status"],
            "compute_task_status": submission["compute_task_status"],
            "input_path": submission["input_path"],
            "output_path": submission["output_path"],
        }
    )
