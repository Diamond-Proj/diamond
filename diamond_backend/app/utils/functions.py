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


get_machine_metadata = ShellFunction(_escape_shell_braces(_GET_MACHINE_METADATA_CMD))


get_partitions = ShellFunction('sinfo -h -o "%P"')


get_accounts = ShellFunction(
    "sacctmgr show associations --noheader -P user=$USER format=Account"
)


get_container_status = ShellFunction('squeue --name={name} -h -o "%T"')


get_task_status = ShellFunction('squeue --name={task_name} -h -o "%T"')


check_diamond_work_path = ShellFunction(
    "if [ -d {diamond_work_path} ] && [ -w {diamond_work_path} ]; then echo 1; else echo 0; fi"
)


create_diamond_dir = ShellFunction(
    "mkdir -p {diamond_dir} && mkdir -p {diamond_log_dir} && mkdir -p {diamond_image_dir}"
)


# TODO: merge two log reader functions
def log_reader_wrapper(log_file_path):
    """Wrapper function to read log file content"""
    try:
        with open(log_file_path, "r") as f:
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
    try:
        with open(log_file_path, "r") as f:
            content = f.read()
            is_complete = content.endswith(eof_flag)
            return {"content": content, "is_complete": is_complete}
    except Exception as e:
        return {
            "content": f"Error reading log file: {str(e)}",
            "is_complete": False,
            "error": str(e),
        }
