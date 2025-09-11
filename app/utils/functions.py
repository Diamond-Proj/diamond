# Globus compute helper functions
from globus_compute_sdk import ShellFunction

get_partitions = ShellFunction('sinfo -h -o "%P"')


get_accounts = ShellFunction(
    "sacctmgr show associations --noheader -P user=$USER format=Account"
)


get_container_status = ShellFunction('squeue --name={name} -h -o "%T"')


get_task_status = ShellFunction('squeue --name={task_name} -h -o "%T"')


check_diamond_work_path = ShellFunction('if [ -d {diamond_work_path} ] && [ -w {diamond_work_path} ]; then echo 1; else echo 0; fi')


create_diamond_dir = ShellFunction('mkdir -p {diamond_dir} && mkdir -p {diamond_log_dir} && mkdir -p {diamond_image_dir}')


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
