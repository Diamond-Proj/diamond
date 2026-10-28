from diamond_backend.app.utils.functions import (
    get_user_home_directory,
    submit_slurm_job,
)

STARTUP_FUNCTION_TEMPLATES = {
    "submit_slurm_job": submit_slurm_job,
    "get_user_home_directory": get_user_home_directory,
}

# Add ADHOC_FUNCTION_TEMPLATES here later : eg accounts, partitions, image_builder, etc.
