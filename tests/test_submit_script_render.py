import pytest

from diamond_backend.app.tasks import (
    _build_finetuned_artifact_path,
    _build_vllm_host_candidates,
    _build_vllm_task_log_info,
    _derive_vllm_port_from_batch_job_id,
    _extract_artifact_path_from_submit_stdout,
    _parse_vllm_task_log_info,
    _validate_finetuned_model_name,
)
from diamond_backend.app.utils.functions import _escape_shell_braces
from diamond_backend.app.utils.scripts_render import (
    render_submit_task_script,
    render_task_template_script,
)

expected_output_1 = """cat << EOF > /dev/shm/Foo.submit
#!/bin/bash

#SBATCH --job-name=Foo
#SBATCH --output=/dev/shm/stdout
#SBATCH --error=/dev/shm/stderr
#SBATCH --nodes=1
#SBATCH --time=00:10:00
#SBATCH --partition=development
#SBATCH --account=testing_account
#SBATCH --ntasks-per-node=1

export DIAMOND_DATASET_PATH=
if [[ -z "" ]]; then
    echo "No dataset specified"
    mount_string=""
else
    mount_string="--bind "
fi


srun --cpu-bind=none apptainer exec \\$mount_string --nv dummy.sif python test.py
echo "EOF" >> /dev/shm/stdout
echo "EOF" >> /dev/shm/stderr
EOF

sbatch /dev/shm/Foo.submit"""


def test_render():
    script = render_submit_task_script(
        task_name="Foo",
        location="/dev/shm",
        stdout_path="/dev/shm/stdout",
        stderr_path="/dev/shm/stderr",
        time_duration="00:10:00",
        partition="development",
        account="testing_account",
        reservation="",
        num_of_nodes=1,
        container="dummy.sif",
        container_module_command="",
        dataset_system_path="",
        task_command="python test.py",
        slurm_options="",
    )
    assert script.replace(" ", "") == expected_output_1.replace(" ", "")


expected_output_2 = """cat << EOF > /dev/shm/Foo.submit
#!/bin/bash

#SBATCH --job-name=Foo
#SBATCH --output=/dev/shm/stdout
#SBATCH --error=/dev/shm/stderr
#SBATCH --nodes=1
#SBATCH --time=00:10:00
#SBATCH --partition=development
#SBATCH --account=testing_account
#SBATCH --ntasks-per-node=1

export DIAMOND_DATASET_PATH=/home/test_user/dataset
if [[ -z "/home/test_user/dataset" ]]; then
    echo "No dataset specified"
    mount_string=""
else
    mount_string="--bind /home/test_user/dataset"
fi

module load apptainer
srun --cpu-bind=none apptainer exec \\$mount_string --nv dummy.sif python test.py
echo "EOF" >> /dev/shm/stdout
echo "EOF" >> /dev/shm/stderr
EOF

sbatch None /dev/shm/Foo.submit"""


def test_render_with_dataset():
    container_module_command = "module load apptainer"
    dataset_system_path = "/home/test_user/dataset"
    script = render_submit_task_script(
        task_name="Foo",
        location="/dev/shm",
        stdout_path="/dev/shm/stdout",
        stderr_path="/dev/shm/stderr",
        time_duration="00:10:00",
        partition="development",
        account="testing_account",
        num_of_nodes=1,
        reservation=None,
        container="dummy.sif",
        container_module_command=container_module_command,
        dataset_system_path=dataset_system_path,
        task_command="python test.py",
        slurm_options="",
    )
    assert container_module_command in script
    assert dataset_system_path in script
    assert script.replace(" ", "") == expected_output_2.replace(" ", "")


def test_render_task_template_script():
    script = render_task_template_script(
        "deepspeed-sft-delta.j2",
        {
            "location": "/tmp",
            "task_name": "demo-task",
            "stdout_path": "/tmp/demo.stdout",
            "stderr_path": "/tmp/demo.stderr",
            "num_of_nodes": 1,
            "time_duration": "00:10:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "--gpus-per-node=1",
            "model_path": "/models/qwen",
            "dataset_path": "/data/scifact",
            "scratch_path": "/scratch/run",
            "reservation": "",
            "finetuned_model_path": "/finetuned/model/path",
            "finetuned_model_name": "demo-sft-model",
        },
    )
    assert "demo-task.submit" in script
    assert "/models/qwen" in script
    assert "/data/scifact" in script
    assert "--bind $resolved_finetuned_model_path:/scratch" in script
    assert "/scratch/demo-sft-model" in script
    assert "DIAMOND_ARTIFACT_PATH=$resolved_artifact_path" in script
    assert "cat << EOF" in script
    assert "export MASTER_PORT=\\$(( 50000 + \\${SLURM_JOB_ID: -4} ))" in script


def test_render_container_build_template_script():
    script = render_task_template_script(
        "container-build.j2",
        {
            "task_name": "image-build-demo",
            "container_name": "image-build-demo",
            "location": "/tmp/diamond",
            "stdout_path": "/tmp/diamond/logs/image-build-demo.stdout",
            "stderr_path": "/tmp/diamond/logs/image-build-demo.stderr",
            "time_duration": "00:30:00",
            "partition": "gpu",
            "account": "proj",
            "reservation": "",
            "container_module_command": "module load apptainer",
            "base_image": "ubuntu:22.04",
            "commands": "python -m pip install torch",
            "environment": "HF_HOME=/tmp/hf",
        },
    )
    assert "image-build-demo.def" in script
    assert "image-build-demo.submit" in script
    assert "Bootstrap: docker" in script
    assert "From: ubuntu:22.04" in script
    assert "cat << 'COMMANDS_EOF' > commands.sh" in script
    assert "python -m pip install torch" in script
    assert "module load apptainer" in script
    assert (
        "apptainer build /tmp/diamond/image-build-demo.sif /tmp/diamond/image-build-demo.def"
        in script
    )


def test_render_task_template_script_survives_shellfunction_formatting():
    script = render_task_template_script(
        "deepspeed-sft-delta.j2",
        {
            "location": "/tmp",
            "task_name": "demo-task",
            "stdout_path": "/tmp/demo.stdout",
            "stderr_path": "/tmp/demo.stderr",
            "num_of_nodes": 1,
            "time_duration": "00:10:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "--gpus-per-node=1",
            "model_path": "/models/qwen",
            "dataset_path": "/data/scifact",
            "scratch_path": "/scratch/run",
            "reservation": "",
            "finetuned_model_path": "/finetuned/model/path",
            "finetuned_model_name": "demo-sft-model",
        },
    )
    escaped_script = _escape_shell_braces(script)
    formatted = escaped_script.format()
    assert "export MASTER_PORT=\\$(( 50000 + \\${SLURM_JOB_ID: -4} ))" in formatted


def test_render_task_template_script_rejects_invalid_name():
    with pytest.raises(ValueError):
        render_task_template_script("../submit_task.j2", {})


def test_validate_finetuned_model_name_accepts_valid_value():
    assert _validate_finetuned_model_name(" qwen3-0.6B-sft ") == "qwen3-0.6B-sft"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        ".",
        "..",
        "../model",
        "model/name",
        "model\\name",
        "name with space",
        "name$",
        None,
    ],
)
def test_validate_finetuned_model_name_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        _validate_finetuned_model_name(value)


def test_build_finetuned_artifact_path():
    assert (
        _build_finetuned_artifact_path(
            finetuned_model_path="/work/models",
            finetuned_model_name="qwen-sft-v1",
        )
        == "/work/models/qwen-sft-v1"
    )
    assert (
        _build_finetuned_artifact_path(
            finetuned_model_path="",
            finetuned_model_name="qwen-sft-v1",
        )
        == ""
    )


def test_extract_artifact_path_from_submit_stdout():
    stdout = """
Some logs
Submitted batch job 123456
DIAMOND_ARTIFACT_PATH=/work/nvme/bcrc/hxie6/test2/demo-sft
"""
    assert (
        _extract_artifact_path_from_submit_stdout(stdout)
        == "/work/nvme/bcrc/hxie6/test2/demo-sft"
    )
    assert _extract_artifact_path_from_submit_stdout("Submitted batch job 123456") == ""


def test_render_vllm_template_script():
    script = render_task_template_script(
        "vllm-inference.j2",
        {
            "location": "/tmp",
            "task_name": "vllm-demo",
            "stdout_path": "/tmp/vllm.stdout",
            "stderr_path": "/tmp/vllm.stderr",
            "num_of_nodes": 1,
            "time_duration": "08:00:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "#SBATCH --gpus-per-node=1",
            "reservation": "",
            "container_module_command": "module load apptainer",
            "model_path": "/work/model/path",
            "container_path": "/work/images/vllm.sif",
            "served_model_name": "diamond-assistant",
            "max_model_len": 2048,
            "vllm_extra_args": "--gpu-memory-utilization 0.95",
        },
    )
    assert "vllm-demo.submit" in script
    assert "--bind /work/model/path:/model" in script
    assert "/work/images/vllm.sif" in script
    assert "VLLM_PORT=\\$(( 40000 + 10#\\${SLURM_JOB_ID: -4} ))" in script
    assert '--served-model-name "diamond-assistant"' in script
    assert 'sbatch_output="$(sbatch' in script


def test_parse_vllm_task_log_info():
    assert _parse_vllm_task_log_info("vllm_task|model=diamond-assistant") == {
        "model": "diamond-assistant",
    }
    assert _parse_vllm_task_log_info("something-else") is None
    assert _build_vllm_task_log_info("  ") == "vllm_task|model=diamond-assistant"
    assert _build_vllm_task_log_info("qwen") == "vllm_task|model=qwen"
    assert _derive_vllm_port_from_batch_job_id("123456") == 43456
    assert _derive_vllm_port_from_batch_job_id("84") == 40084
    assert _derive_vllm_port_from_batch_job_id("abc") is None


def test_build_vllm_host_candidates():
    assert _build_vllm_host_candidates("gpu001", "delta.ncsa.illinois.edu") == [
        "gpu001",
        "gpu001.ncsa.illinois.edu",
    ]
    assert _build_vllm_host_candidates(
        "gpu001.ncsa.illinois.edu", "delta.ncsa.illinois.edu"
    ) == ["gpu001.ncsa.illinois.edu"]
    assert _build_vllm_host_candidates("", "delta.ncsa.illinois.edu") == []


def test_render_vllm_template_survives_shellfunction_formatting():
    script = render_task_template_script(
        "vllm-inference.j2",
        {
            "location": "/tmp",
            "task_name": "vllm-demo",
            "stdout_path": "/tmp/vllm.stdout",
            "stderr_path": "/tmp/vllm.stderr",
            "num_of_nodes": 1,
            "time_duration": "08:00:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "",
            "reservation": "",
            "container_module_command": "",
            "model_path": "/work/model/path",
            "container_path": "/work/images/vllm.sif",
            "served_model_name": "diamond-assistant",
            "max_model_len": 2048,
            "vllm_extra_args": "",
        },
    )
    escaped_script = _escape_shell_braces(script)
    formatted = escaped_script.format()
    assert "VLLM_PORT=\\$(( 40000 + 10#\\${SLURM_JOB_ID: -4} ))" in formatted
