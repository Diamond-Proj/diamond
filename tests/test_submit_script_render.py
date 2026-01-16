from diamond_backend.app.utils.scripts_render import render_submit_task_script

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
#SBATCH --exclusive

export DIAMOND_DATASET_PATH=
if [[ -z "" ]]; then
    echo "No dataset specified"
    mount_string=""
else
    mount_string="--bind "
fi


srun apptainer exec $mount_string --nv dummy.sif python test.py
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
#SBATCH --exclusive

export DIAMOND_DATASET_PATH=/home/test_user/dataset
if [[ -z "/home/test_user/dataset" ]]; then
    echo "No dataset specified"
    mount_string=""
else
    mount_string="--bind /home/test_user/dataset"
fi

module load apptainer
srun apptainer exec $mount_string --nv dummy.sif python test.py
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
