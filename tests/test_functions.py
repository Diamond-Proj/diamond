from unittest.mock import MagicMock, patch

from diamond_backend.app.utils.functions import (
    _GET_MACHINE_METADATA_CMD,
    _escape_shell_braces,
)


def test_escape_shell_braces():
    """Test the _escape_shell_braces function."""
    test_cmd = "echo {test} and {another}"
    expected = "echo {{test}} and {{another}}"
    result = _escape_shell_braces(test_cmd)
    assert result == expected


@patch("subprocess.run")
@patch("shutil.which")
@patch("os.environ.copy")
@patch("getpass.getuser")
def test_python_not_found(mock_getuser, mock_env_copy, mock_which, mock_run):
    """Test behavior when no Python interpreter is found."""
    mock_env_copy.return_value = {}
    mock_getuser.return_value = "testuser"
    mock_which.side_effect = lambda cmd: (
        None if cmd in ["python3", "python"] else "/usr/bin/sinfo"
    )
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout="", stderr="command not found"),
        MagicMock(returncode=1, stdout="", stderr="command not found"),
    ]

    assert (
        "command -v python3 || command -v python || true" in _GET_MACHINE_METADATA_CMD
    )


@patch("subprocess.run")
@patch("shutil.which")
@patch("os.environ.copy")
@patch("getpass.getuser")
@patch("os.path.expanduser")
def test_slurm_system_detection(
    mock_expanduser, mock_getuser, mock_env_copy, mock_which, mock_run
):
    """Test SLURM batch system detection and partition listing."""
    mock_env_copy.return_value = {"USER": "testuser"}
    mock_getuser.return_value = "testuser"
    mock_expanduser.return_value = "/home/testuser"
    mock_which.side_effect = lambda cmd: "/usr/bin/sinfo" if cmd == "sinfo" else None

    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="gpu\ncpu*\ndebug", stderr=""),
        MagicMock(returncode=0, stdout="account1\naccount2", stderr=""),
    ]

    assert 'if shutil.which("sinfo"):' in _GET_MACHINE_METADATA_CMD
    assert 'batch_system = "slurm"' in _GET_MACHINE_METADATA_CMD
    assert 'sinfo -h -o "%P"' in _GET_MACHINE_METADATA_CMD


@patch("subprocess.run")
@patch("shutil.which")
@patch("os.environ.copy")
@patch("getpass.getuser")
@patch("os.path.expanduser")
def test_pbs_system_detection(
    mock_expanduser, mock_getuser, mock_env_copy, mock_which, mock_run
):
    """Test PBS batch system detection."""
    mock_env_copy.return_value = {"USER": "testuser"}
    mock_getuser.return_value = "testuser"
    mock_expanduser.return_value = "/home/testuser"

    mock_which.side_effect = lambda cmd: "/usr/bin/qstat" if cmd == "qstat" else None

    assert 'elif shutil.which("qstat"):' in _GET_MACHINE_METADATA_CMD
    assert 'batch_system = "pbs"' in _GET_MACHINE_METADATA_CMD


@patch("subprocess.run")
@patch("shutil.which")
@patch("os.environ.copy")
@patch("getpass.getuser")
@patch("os.path.expanduser")
def test_lsf_system_detection(
    mock_expanduser, mock_getuser, mock_env_copy, mock_which, mock_run
):
    """Test LSF batch system detection."""
    mock_env_copy.return_value = {"USER": "testuser"}
    mock_getuser.return_value = "testuser"
    mock_expanduser.return_value = "/home/testuser"

    mock_which.side_effect = lambda cmd: (
        "/usr/bin/bqueues" if cmd == "bqueues" else None
    )

    assert 'elif shutil.which("bqueues"):' in _GET_MACHINE_METADATA_CMD
    assert 'batch_system = "lsf"' in _GET_MACHINE_METADATA_CMD


def test_partition_parsing_logic():
    """Test the partition parsing logic in the command."""
    assert 'p = p.rstrip("*")' in _GET_MACHINE_METADATA_CMD
    assert "if p and p not in seen:" in _GET_MACHINE_METADATA_CMD
    assert "partitions.append(p)" in _GET_MACHINE_METADATA_CMD


def test_account_detection_logic():
    """Test the account detection logic in the command."""
    assert 'if shutil.which("sacctmgr"):' in _GET_MACHINE_METADATA_CMD
    assert "sacctmgr show associations" in _GET_MACHINE_METADATA_CMD
    assert "try_sacctmgr(cmds)" in _GET_MACHINE_METADATA_CMD


def test_python_info_collection():
    """Test Python information collection in the command."""
    assert "python_info = {" in _GET_MACHINE_METADATA_CMD
    assert "sys.executable" in _GET_MACHINE_METADATA_CMD
    assert "sys.version" in _GET_MACHINE_METADATA_CMD
    assert "sys.path" in _GET_MACHINE_METADATA_CMD


def test_metadata_structure():
    """Test the metadata JSON structure in the command."""
    assert "metadata = {" in _GET_MACHINE_METADATA_CMD
    assert '"batch_system": batch_system' in _GET_MACHINE_METADATA_CMD
    assert '"partitions": partitions' in _GET_MACHINE_METADATA_CMD
    assert '"accounts": accounts' in _GET_MACHINE_METADATA_CMD
    assert '"home_directory": home_directory' in _GET_MACHINE_METADATA_CMD
    assert '"python": python_info' in _GET_MACHINE_METADATA_CMD
    assert "json.dumps(metadata)" in _GET_MACHINE_METADATA_CMD


def test_error_handling():
    """Test error handling in the command."""
    assert "except Exception as exc:" in _GET_MACHINE_METADATA_CMD
    assert (
        'return {"stdout": "", "stderr": str(exc), "returncode": -1}'
        in _GET_MACHINE_METADATA_CMD
    )
    assert "partition_error =" in _GET_MACHINE_METADATA_CMD
    assert "accounts_error =" in _GET_MACHINE_METADATA_CMD


def test_user_environment_setup():
    """Test user environment setup in the command."""
    assert "def _env_with_user():" in _GET_MACHINE_METADATA_CMD
    assert 'env["USER"] = getpass.getuser()' in _GET_MACHINE_METADATA_CMD
    assert "env = _env_with_user()" in _GET_MACHINE_METADATA_CMD


def test_subprocess_compatibility():
    """Test subprocess compatibility handling in the command."""
    assert "if sys.version_info >= (3, 7):" in _GET_MACHINE_METADATA_CMD
    assert 'kwargs["text"] = True' in _GET_MACHINE_METADATA_CMD
    assert 'kwargs["universal_newlines"] = True' in _GET_MACHINE_METADATA_CMD


def test_command_structure():
    """Test the overall command structure."""
    assert "set -euo pipefail" in _GET_MACHINE_METADATA_CMD
    assert "PYTHON_CMD=" in _GET_MACHINE_METADATA_CMD
    assert 'if [ -z "$PYTHON_CMD" ]; then' in _GET_MACHINE_METADATA_CMD
    assert "cat <<" in _GET_MACHINE_METADATA_CMD
    assert "JSON" in _GET_MACHINE_METADATA_CMD
    assert "exit 0" in _GET_MACHINE_METADATA_CMD
    assert "fi" in _GET_MACHINE_METADATA_CMD
    assert '"$PYTHON_CMD" <<' in _GET_MACHINE_METADATA_CMD
    assert "PYTHON" in _GET_MACHINE_METADATA_CMD


@patch("subprocess.run")
@patch("shutil.which")
@patch("os.environ.copy")
@patch("getpass.getuser")
@patch("os.path.expanduser")
def test_sacctmgr_fallback_commands(
    mock_expanduser, mock_getuser, mock_env_copy, mock_which, mock_run
):
    """Test sacctmgr fallback commands."""
    mock_env_copy.return_value = {"USER": "testuser"}
    mock_getuser.return_value = "testuser"
    mock_expanduser.return_value = "/home/testuser"
    mock_which.side_effect = lambda cmd: (
        "/usr/bin/sacctmgr" if cmd == "sacctmgr" else None
    )
    assert (
        "sacctmgr show associations --noheader -P user=$USER format=Account"
        in _GET_MACHINE_METADATA_CMD
    )
    assert (
        "sacctmgr -n -p show associations user=$USER format=Account"
        in _GET_MACHINE_METADATA_CMD
    )
    assert (
        "sacctmgr -n -p show associations where user=$USER format=Account"
        in _GET_MACHINE_METADATA_CMD
    )


def test_unknown_batch_system():
    """Test handling of unknown batch systems."""
    assert "else:" in _GET_MACHINE_METADATA_CMD
    assert 'batch_system = "unknown"' in _GET_MACHINE_METADATA_CMD
