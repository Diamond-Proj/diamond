import logging

import globus_sdk
from flask import Flask
from globus_compute_sdk import Client as GlobusComputeClient
from globus_compute_sdk.serialize import AllCodeStrategies

from diamond_backend.app.database.db import db
from diamond_backend.app.database.models.flow import Flows
from diamond_backend.app.database.models.function import Functions
from diamond_backend.app.utils.login_flow import (
    load_portal_client,  # Assuming this is used for auth
)

logger = logging.getLogger(__name__)

RECREATE_FLOWS = False  # delete and recreate flows on startup (requires new Globus login after for auth)
RECREATE_FUNCTIONS = True  # delete and recreate functions on startup


FLOW_TEMPLATES = {
    "run_function": {
        "definition": {
            "States": {
                "run_function": {
                    "Type": "Action",
                    "ActionUrl": "https://compute.actions.globus.org/v3",
                    "Parameters": {
                        "endpoint_id.$": "$.endpoint_id",
                        "user_endpoint_config.$": "$.user_endpoint_config",
                        "user_runtime.$": "$.user_runtime",
                        "tasks": [
                            {
                                "function_id.$": "$.function_id",
                                "kwargs.$": "$.function_kwargs",
                            }
                        ],
                    },
                    "ResultPath": "$.run_function",
                    "End": True,
                }
            },
            "StartAt": "run_function",
        },
        "input_schema": {
            "type": "object",
            "properties": {
                "endpoint_id": {"type": "string", "format": "uuid"},
                "function_id": {"type": "string", "format": "uuid"},
                "function_kwargs": {"type": "object"},
                "user_endpoint_config": {
                    "type": "object",
                    "properties": {
                        "account": {"type": "string"},
                        "partition": {"type": "string"},
                    },
                },
                "user_runtime": {
                    "type": "object",
                    "properties": {
                        "globus_compute_sdk_version": {"type": "string"},
                        "python": {"type": "object"},
                    }
                }
            },
            "required": [
                "endpoint_id",
                "function_id",
                "function_kwargs",
                "user_endpoint_config",
                "user_runtime",
            ],
        },
        "title_prefix": "Run Function Flow",
    }
}


def get_startup_flow_client():
    client = load_portal_client()

    try:
        # Request a token for the Flow management scope
        token_response = client.oauth2_client_credentials_tokens(
            requested_scopes="https://auth.globus.org/scopes/eec9b274-0c81-4334-bdc2-54e90e689b9a/all"
        )
        access_token = token_response.by_resource_server["flows.globus.org"][
            "access_token"
        ]
        authorizer = globus_sdk.AccessTokenAuthorizer(access_token)
        return globus_sdk.FlowsClient(authorizer=authorizer)
    except Exception as e:
        logger.error(f"Failed to get startup Globus Flows client: {e}")
        raise


def check_and_create_flows(app: Flask):
    with app.app_context():
        try:
            print("Checking and creating flows if necessary...")
            gfc = get_startup_flow_client()
        except Exception as e:
            logger.error(
                f"Skipping flow creation due to client initialization error: {e}"
            )
            return

        for template_name, flow_data in FLOW_TEMPLATES.items():
            existing_flow = Flows.query.filter_by(template=template_name).first()

            if existing_flow and RECREATE_FLOWS:
                try:
                    gfc.delete_flow(existing_flow.flow_id)
                except Exception as e:
                    logger.error(f"Error deleting existing flow: {e}")
                    pass
                Flows.query.filter_by(template=template_name).delete()
                existing_flow = None

            if not existing_flow:
                logger.info(
                    f"Flow for template '{template_name}' not found. Creating..."
                )
                try:
                    flow_title = f"Diamond - {flow_data['title_prefix']}"

                    flow_create_response = gfc.create_flow(
                        title=flow_title,
                        definition=flow_data["definition"],
                        input_schema=flow_data["input_schema"],
                        flow_viewers=["public"],
                        flow_starters=["all_authenticated_users"],
                    )
                    flow_id = flow_create_response["id"]

                    new_flow_entry = Flows(template=template_name, flow_id=flow_id)
                    db.session.add(new_flow_entry)
                    db.session.commit()
                    logger.info(f"Created flow '{template_name}' with ID: {flow_id}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error creating flow '{template_name}': {e}"
                    )
                    db.session.rollback()
            else:
                logger.info(
                    f"Flow '{template_name}' already exists: {existing_flow.flow_id}"
                )


def get_startup_function_client():
    client = load_portal_client()

    try:
        # Request a token for the Flow management scope
        token_response = client.oauth2_client_credentials_tokens(
            requested_scopes="https://auth.globus.org/scopes/facd7ccc-c5f4-42aa-916b-a0e270e2c2a9/all"
        )
        access_token = token_response.by_resource_server["funcx_service"][
            "access_token"
        ]
        authorizer = globus_sdk.AccessTokenAuthorizer(access_token)
        return GlobusComputeClient(
            authorizer=authorizer, code_serialization_strategy=AllCodeStrategies()
        )
    except Exception as e:
        logger.error(f"Failed to get startup Globus Compute client: {e}")
        raise


# FUNCTION DEFINITIONS
def submit_slurm_job(**params):
    import subprocess
    from pathlib import Path

    from jinja2 import Template

    submit_task_j2 = """
cat << EOF > {{ location }}/{{ task_name }}.submit
#!/bin/bash

#SBATCH --job-name={{ task_name }}
#SBATCH --output={{ stdout_path }}
#SBATCH --error={{ stderr_path }}
#SBATCH --nodes={{ num_of_nodes }}
#SBATCH --time={{ time_duration }}
#SBATCH --partition={{ partition }}
#SBATCH --account={{ account }}
#SBATCH --ntasks-per-node=1
{%- if slurm_options %}
{{ slurm_options }}
{%- endif %}

export DIAMOND_DATASET_PATH={{ dataset_system_path }}
if [[ -z "{{ dataset_system_path }}" ]]; then
echo "No dataset specified"
mount_string=""
else
mount_string="--bind {{ dataset_system_path }}"
fi

{{ container_module_command }}
srun --cpu-bind=none apptainer exec \$mount_string --nv {{ container }} {{ task_command }}
echo "EOF" >> {{ stdout_path }}
echo "EOF" >> {{ stderr_path }}
EOF

sbatch {{ reservation }} {{ location }}/{{ task_name }}.submit
"""
    template = Template(submit_task_j2)
    script = template.render(**params)

    submit_file = Path(params["location"]) / f"{params['task_name']}.sh"
    submit_file.write_text(script)
    result = subprocess.run(
        ["bash", submit_file],
        capture_output=True,
        text=True,
    )
    return result.stdout


FUNCTION_TEMPLATES = {"submit_slurm_job": submit_slurm_job}


def check_and_create_functions(app: Flask):
    with app.app_context():
        try:
            print("Checking and creating functions if necessary...")
            gfc = get_startup_function_client()
        except Exception as e:
            logger.error(
                f"Skipping function creation due to client initialization error: {e}"
            )
            return

        # Register SLURM shell script
        for fn_name, fn_def in FUNCTION_TEMPLATES.items():
            existing_fn = Functions.query.filter_by(name=fn_name).first()

            if existing_fn and RECREATE_FUNCTIONS:
                try:
                    gfc.delete_function(existing_fn.function_id)
                except Exception as e:
                    logger.error(f"Error deleting existing function: {e}")
                    pass
                Functions.query.filter_by(name=fn_name).delete()
                existing_fn = None

            if not existing_fn:
                logger.info(f"Function for '{fn_name}' not found. Creating...")
                try:
                    fn_id = gfc.register_function(fn_def, public=True)

                    new_fn_entry = Functions(name=fn_name, function_id=fn_id)
                    db.session.add(new_fn_entry)
                    db.session.commit()
                    logger.info(f"Created function '{fn_name}' with ID: {fn_id}")
                except Exception as e:
                    logger.error(f"Unexpected error creating function '{fn_name}': {e}")
                    db.session.rollback()
            else:
                logger.info(
                    f"Function '{fn_name}' already exists: {existing_fn.function_id}"
                )
