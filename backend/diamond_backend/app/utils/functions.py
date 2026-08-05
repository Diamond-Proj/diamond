# Globus compute helper functions
from globus_compute_sdk import ShellFunction

_GET_MACHINE_METADATA_CMD = r"""
set -euo pipefail
PYTHON_CMD="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON_CMD" ]; then
  cat <<'JSON'
{"error": "No python interpreter found on endpoint.", "batch_system": null, "partitions": [], "accounts": [], "home_directory": null, "python": null}
JSON
  exit 0
fi

"$PYTHON_CMD" <<'PYTHON'
import json
import os
import shutil
import subprocess
import sys
import getpass


def _env_with_user():
    env = os.environ.copy()
    if not env.get("USER"):
        try:
            env["USER"] = getpass.getuser()
        except Exception:
            pass
    return env


def run_command(cmd):
    shell = isinstance(cmd, str)
    env = _env_with_user()
    try:
        kwargs = dict(
            shell=shell,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        # Py3.7+: 'text', Py3.6: 'universal_newlines'
        if sys.version_info >= (3, 7):
            kwargs["text"] = True
        else:
            kwargs["universal_newlines"] = True
        result = subprocess.run(cmd, **kwargs)
        return {
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
            "returncode": result.returncode,
        }
    except Exception as exc:
        return {"stdout": "", "stderr": str(exc), "returncode": -1}


batch_system = None
partitions = []
partition_error = None

if shutil.which("sinfo"):
    batch_system = "slurm"
    # Get partition names; remove trailing '*' (default partition marker), dedupe, keep order
    sinfo_result = run_command('sinfo -h -o "%P"')
    if sinfo_result["returncode"] == 0:
        seen = set()
        for line in (sinfo_result["stdout"] or "").splitlines():
            p = line.strip()
            if not p:
                continue
            p = p.rstrip("*")
            if p and p not in seen:
                seen.add(p)
                partitions.append(p)
    else:
        partition_error = sinfo_result["stderr"] or sinfo_result["stdout"]
elif shutil.which("qstat"):
    batch_system = "pbs"
elif shutil.which("bqueues"):
    batch_system = "lsf"
else:
    batch_system = "unknown"

accounts = []
accounts_error = None

def try_sacctmgr(cmds):
    last_err = None
    for c in cmds:
        r = run_command(c)
        if r["returncode"] == 0 and r["stdout"]:
            lines = [x.strip() for x in r["stdout"].splitlines() if x.strip()]
            return lines, None
        last_err = r["stderr"] or r["stdout"] or f"exit {r['returncode']}"
    return [], last_err

if shutil.which("sacctmgr"):
    cmds = [
        # Your original:
        "sacctmgr show associations --noheader -P user=$USER format=Account",
        # Common minimal form:
        "sacctmgr -n -p show associations user=$USER format=Account",
        # Older/alternate syntax with 'where':
        "sacctmgr -n -p show associations where user=$USER format=Account",
    ]
    accounts, accounts_error = try_sacctmgr(cmds)
else:
    accounts_error = "sacctmgr command not available"

python_info = {
    "executable": sys.executable,
    "version": sys.version,
    "path_entries": sys.path,
}

home_directory = os.path.expanduser("~")

metadata = {
    "batch_system": batch_system,
    "partitions": partitions,
    "partition_error": partition_error,
    "accounts": accounts,
    "accounts_error": accounts_error,
    "home_directory": home_directory,
    "python": python_info,
}

print(json.dumps(metadata))
PYTHON
"""


def _escape_shell_braces(cmd: str) -> str:
    return cmd.replace("{", "{{").replace("}", "}}")


def _make_shell_function(cmd: str, **kwargs) -> ShellFunction:
    """Create a ShellFunction compatible with older endpoints."""
    shell_fn = ShellFunction(cmd, **kwargs)
    if not hasattr(shell_fn, "return_dict"):
        setattr(shell_fn, "return_dict", False)
    return shell_fn


get_machine_metadata = _make_shell_function(
    _escape_shell_braces(_GET_MACHINE_METADATA_CMD)
)


get_partitions = _make_shell_function('sinfo -h -o "%P"')


get_accounts = _make_shell_function(
    "sacctmgr show associations --noheader -P user=$USER format=Account"
)


get_container_status = _make_shell_function('squeue --name={name} -h -o "%T"')


fetch_task_status = _make_shell_function(
    "sacct -j {batch_job_id} -o State -n | head -n 1"
)

check_diamond_work_path = _make_shell_function(
    "if [ -d {diamond_work_path} ] && [ -w {diamond_work_path} ]; then echo 1; else echo 0; fi"
)


create_diamond_dir = _make_shell_function(
    "mkdir -p {diamond_dir} && mkdir -p {diamond_log_dir} && mkdir -p {diamond_image_dir}"
)


# TODO: merge two log reader functions
def log_reader_wrapper(log_file_path):
    """Wrapper function to read log file content"""
    import os

    abs_log_path = os.path.expanduser(os.path.expandvars(log_file_path))
    try:
        with open(abs_log_path, "r") as f:
            content = f.read()
            # Check if build is complete
            is_complete = "INFO:    Build complete:" in content
            return {"content": content, "is_complete": is_complete}
    except Exception as e:
        return {
            "content": f"Error reading log file: {str(e)}",
            "is_complete": False,
            "error": str(e),
        }


def get_task_log(log_file_path, eof_flag="EOF"):
    import os

    abs_log_path = os.path.expanduser(os.path.expandvars(log_file_path))
    try:
        with open(abs_log_path, "r") as f:
            content = f.read()
            is_complete = content.endswith(eof_flag)
            return {"content": content, "is_complete": is_complete}
    except Exception as e:
        return {
            "content": f"Error reading log file: {str(e)}",
            "is_complete": False,
            "error": str(e),
        }


def list_directory_entries(dir_path, max_entries=200):
    """List an artifact path on the endpoint, returning names, sizes, and types.

    The path may be a directory (inference output dir) or a single file (a
    finetuned model checkpoint); whether it is a file or directory is only
    knowable here on the endpoint. A file path lists as its single entry.
    """
    import os

    abs_path = os.path.expanduser(os.path.expandvars(dir_path))
    if os.path.isfile(abs_path):
        try:
            size = os.path.getsize(abs_path)
        except Exception:
            size = None
        return {
            "entries": [
                {"name": os.path.basename(abs_path), "is_dir": False, "size": size}
            ],
            "truncated": False,
        }

    try:
        names = sorted(os.listdir(abs_path))
    except Exception as e:
        return {"error": str(e), "entries": [], "truncated": False}

    entries = []
    for name in names[:max_entries]:
        full_path = os.path.join(abs_path, name)
        is_dir = os.path.isdir(full_path)
        size = None
        if not is_dir:
            try:
                size = os.path.getsize(full_path)
            except Exception:
                size = None
        entries.append({"name": name, "is_dir": is_dir, "size": size})
    return {"entries": entries, "truncated": len(names) > max_entries}


def read_file_base64(artifact_path, filename, max_bytes=5242880):
    """Read one artifact file on the endpoint, returned base64-encoded.

    `artifact_path` is the task's stored artifact path (a directory or a single
    file); `filename` names the entry to read. Resolution happens here because
    only the endpoint knows whether `artifact_path` is a file or a directory.
    Results travel back over the Globus Compute data plane (~10MB cap after
    another serialization pass), so max_bytes must stay well below that.
    """
    import base64
    import os

    if (
        not filename
        or filename in (".", "..")
        or ("/" in filename)
        or ("\\" in filename)
    ):
        return {"error": "Invalid filename"}

    abs_artifact = os.path.expanduser(os.path.expandvars(artifact_path))
    if os.path.isdir(abs_artifact):
        abs_path = os.path.join(abs_artifact, filename)
    elif os.path.isfile(abs_artifact) and os.path.basename(abs_artifact) == filename:
        abs_path = abs_artifact
    else:
        return {"error": f"{filename}: No such file or directory"}

    try:
        size = os.path.getsize(abs_path)
        if size > max_bytes:
            return {
                "error": f"File is {size} bytes and exceeds the {max_bytes} byte "
                "download limit"
            }
        with open(abs_path, "rb") as file_handle:
            content = file_handle.read(max_bytes + 1)
        return {
            "content_b64": base64.b64encode(content).decode("ascii"),
            "size": len(content),
        }
    except Exception as e:
        return {"error": str(e)}


def stage_base64_file(file_path, content_b64):
    """Write a base64-encoded payload to file_path on the endpoint.

    Runs as a registered Python function so the payload travels over the
    Globus Compute data plane instead of a shell command line, which is
    capped by MAX_ARG_STRLEN (~128KB).
    """
    import base64
    import os

    abs_path = os.path.expanduser(os.path.expandvars(file_path))
    parent_dir = os.path.dirname(abs_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(abs_path, "wb") as file_handle:
        file_handle.write(base64.b64decode(content_b64))
    return abs_path


write_file = _make_shell_function(
    r"""
set -euo pipefail
PYTHON_CMD="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON_CMD" ]; then
  echo "No python interpreter found on endpoint" >&2
  exit 1
fi

"$PYTHON_CMD" <<'PYTHON'
import base64
import os

file_path = base64.b64decode("{file_path_b64}").decode("utf-8")
content = base64.b64decode("{content_b64}").decode("utf-8")

parent_dir = os.path.dirname(file_path)
if parent_dir:
    os.makedirs(parent_dir, exist_ok=True)

with open(file_path, "w", encoding="utf-8") as file_handle:
    file_handle.write(content)
PYTHON
"""
)
