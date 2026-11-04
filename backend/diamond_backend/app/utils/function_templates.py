from diamond_backend.app.utils.functions import (
    get_user_slurm_info,
    submit_slurm_job,
)

STARTUP_FUNCTION_TEMPLATES = {
    "submit_slurm_job": submit_slurm_job,
    "get_user_slurm_info": get_user_slurm_info,
}

# Add ADHOC_FUNCTION_TEMPLATES here later : eg accounts, partitions, image_builder, etc.
