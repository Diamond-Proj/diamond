# Globus compute helper functions
import os
from globus_compute_sdk import ShellFunction
from globus_compute_sdk import Executor as GlobusComputeExecutor


get_partitions = ShellFunction('sinfo -h -o "%P"')


get_accounts = ShellFunction('sacctmgr show associations --noheader -P user=$USER format=Account')


get_container_status = ShellFunction('squeue --name={name} -h -o "%T"')


get_task_status = ShellFunction('squeue --name={task_name} -h -o "%T"')


apptainer_def_file_creation = ShellFunction(
"""
cat << EOF > {location}/{container_name}.def
Bootstrap: docker
From: {base_image}

%post
    echo "post section"
    apt-get -y update
    apt-get -y install apt-utils
    apt-get -y install python3-pip
    mkdir -p /app
    cd /app
    echo $PWD
    echo "{commands}" > commands.sh
    chmod +x commands.sh

%environment
    export {environment}

%runscript
    /bin/bash /app/commands.sh
EOF
"""
)


container_builder_wrapper_shell = ShellFunction(
"""
cat << EOF > test.submit
#!/bin/bash

#SBATCH --job-name={container_name}
#SBATCH --output={location}/{container_name}_apptainer_build_log.stdout
#SBATCH --error={location}/{container_name}_apptainer_build_log.stderr
#SBATCH --nodes=1
#SBATCH --time=00:10:00
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --partition={partition}  
#SBATCH --account={account}

{sc_config_commands}
echo $PWD
srun apptainer build {location}/{container_name}.sif {location}/{container_name}.def

EOF

sbatch $PWD/test.submit
echo "SHELL ECHO"
"""
)


def log_reader_wrapper(log_file_path):
    """Wrapper function to read log file content"""
    try:
        with open(log_file_path, 'r') as f:
            content = f.read()
            # Check if build is complete
            is_complete = 'INFO:    Build complete:' in content
            return {
                'content': content,
                'is_complete': is_complete
            }
    except Exception as e:
        return {
            'content': f"Error reading log file: {str(e)}",
            'is_complete': False,
            'error': str(e)
        }


submit_task = ShellFunction(
"""
cat << EOF > diamond_task.submit
#!/bin/bash

#SBATCH --job-name={task_name}
#SBATCH --output={log_path}/{task_name}_task_log.stdout
#SBATCH --error={log_path}/{task_name}_task_log.stderr
#SBATCH --nodes={num_of_nodes}
#SBATCH --time=01:00:00
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --partition={partition}
#SBATCH --account={account}

{sc_config_commands}
echo $PWD                       
srun apptainer exec --nv {container} {task}

EOF

sbatch $PWD/diamond_task.submit
"""
)
