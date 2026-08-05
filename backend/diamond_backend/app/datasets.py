import json
import logging
import os

import globus_sdk
from flask import jsonify, request

from diamond_backend.app import app, g_database
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.host_machine_mapping import KNOWN_MACHINES
from diamond_backend.app.utils.transfer import get_transfer_client

logger = logging.getLogger(__name__)


def _validate_dataset_registration(
    data: dict, transfer_client
) -> tuple[str, int] | None:
    """Validate user dataset registration data."""
    if not data:
        return "No JSON data provided", 400

    required_fields = ["collection_uuid", "globus_path", "system_path", "machine_name"]
    for field in required_fields:
        if field not in data:
            return f"Missing required field: {field}", 400

    valid_machines = dict(KNOWN_MACHINES).values()
    if data["machine_name"] not in valid_machines:
        return f"Invalid machine_name. Must be one of: {', '.join(valid_machines)}", 400

    # dataset_metadata is valid JSON if provided
    dataset_metadata = data.get("dataset_metadata", "{}")
    if dataset_metadata:
        try:
            json.loads(dataset_metadata) if isinstance(
                dataset_metadata, str
            ) else dataset_metadata
        except json.JSONDecodeError:
            return "Metadata must be valid JSON", 400

    # ensure user can actually access the collection
    try:
        transfer_client.get_endpoint(data["collection_uuid"])
        logger.info(f"Collection {data['collection_uuid']} validation successful")
    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus collection validation failed: {e}")
        if os.environ.get("FLASK_ENV") == "development":
            logger.warning(
                f"Ignoring failed access to collection {data['collection_uuid']} in development mode."
            )
            return None
        return f"Cannot access collection {data['collection_uuid']}: {str(e)}", 400

    return None


@app.route("/api/datasets", methods=["POST"])
@authenticated
def register_user_dataset():
    """Register a new user dataset."""
    try:
        data = request.get_json()

        identity_id = request.cookies.get("primary_identity")
        if not identity_id:
            return jsonify({"error": "No identity ID found"}), 400

        # Validate input data
        transfer_client = get_transfer_client(request)
        validation_error = _validate_dataset_registration(data, transfer_client)
        if validation_error is not None:
            error_msg, status_code = validation_error
            return jsonify({"error": error_msg}), status_code

        # Save dataset (public is always False for user datasets)
        g_database.save_dataset(
            collection_uuid=data["collection_uuid"],
            globus_path=data["globus_path"],
            system_path=data["system_path"],
            machine_name=data["machine_name"],
            dataset_metadata=data.get("dataset_metadata", "{}"),
            identity_id=identity_id,
            public=False,
            dataset_name=data.get("dataset_name"),
        )

        return jsonify(
            {"status": "accepted", "message": "Dataset registered successfully"}
        ), 201

    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus API error: {e}")
        return jsonify({"error": str(e)}), e.http_status
    except Exception as e:
        logger.error(f"Error registering dataset: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/datasets", methods=["GET"])
@authenticated
def list_registered_datasets():
    """Fetch all datasets registered by user plus diamond-owned (public) datasets."""
    try:
        identity_id = request.cookies.get("primary_identity")
        if not identity_id:
            return jsonify({"error": "No identity ID found"}), 400

        datasets = g_database.get_datasets(identity_id)

        # Format datasets for JSON response
        datasets_data = []
        for dataset in datasets:
            datasets_data.append(
                {
                    "id": dataset.id,
                    "collection_uuid": dataset.collection_uuid,
                    "globus_path": dataset.globus_path,
                    "system_path": dataset.system_path,
                    "public": dataset.public,
                    "machine_name": dataset.machine_name,
                    "dataset_name": dataset.dataset_name,
                    "dataset_metadata": dataset.dataset_metadata,
                }
            )

        return jsonify({"datasets": datasets_data}), 200

    except Exception as e:
        logger.error(f"Error fetching datasets: {e}")
        return jsonify({"error": str(e)}), 500
