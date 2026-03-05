import pytest

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


srun --cpu-bind=none apptainer exec $mount_string --nv dummy.sif python test.py
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
srun --cpu-bind=none apptainer exec $mount_string --nv dummy.sif python test.py
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
        },
    )
    assert "demo-task.submit" in script
    assert "/models/qwen" in script
    assert "/data/scifact" in script
    assert "--bind /finetuned/model/path:" in script


def test_render_task_template_script_rejects_invalid_name():
    with pytest.raises(ValueError):
        render_task_template_script("../submit_task.j2", {})
