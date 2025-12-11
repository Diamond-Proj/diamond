import logging

import globus_sdk
from flask import jsonify, request

from diamond_backend.app import app
from diamond_backend.app.utils.decorators import authenticated
from diamond_backend.app.utils.transfer import get_transfer_client

logger = logging.getLogger(__name__)


@app.route("/api/transfers", methods=["GET"])
@authenticated
def list_transfer_tasks():
    """List the authenticated user's current transfer tasks."""
    try:
        transfer_client = get_transfer_client(request)

        # Get current transfer tasks prefixed with "Diamond:" label
        tasks = []
        for task in transfer_client.task_list(
            filter="status:ACTIVE,INACTIVE,FAILED/label:~Diamond:*"
        ):
            tasks.append(task)

        logger.info(f"Found {len(tasks)} Diamond transfer tasks")
        return jsonify(tasks)

    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus API error: {e}")
        return jsonify({"error": str(e)}), e.http_status
    except Exception as e:
        logger.error(f"Error listing active transfer tasks: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/transfers", methods=["POST"])
@authenticated
def initiate_transfer():
    """Initiate a Globus transfer between two endpoints on behalf of the authenticated user.

    Expected JSON body:
    {
        "source_endpoint": "source_endpoint_id",
        "destination_endpoint": "destination_endpoint_id",
        "source_path": "source_path",
        "destination_path": "destination_path",
        "label": "optional_label"
    }

    (Following the same format as the Globus Transfer API)
    """
    try:
        transfer_client = get_transfer_client(request)

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        required_fields = [
            "source_endpoint",
            "destination_endpoint",
            "source_path",
            "destination_path",
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Get the user's identity ID from cookies
        identity_id = request.cookies.get("primary_identity")
        if not identity_id:
            return jsonify({"error": "No identity ID found in cookies"}), 400

        source, destination = data["source_endpoint"], data["destination_endpoint"]

        transfer_data = globus_sdk.TransferData(
            source_endpoint=source,
            destination_endpoint=destination,
            label=f"Diamond:{source}->{destination}",  # label task as diamond-related
        )
        transfer_data.add_item(
            source_path=data["source_path"], destination_path=data["destination_path"]
        )

        transfer_result = transfer_client.submit_transfer(transfer_data)

        return jsonify(
            {
                "message": "Transfer initiated successfully",
                "task_id": transfer_result["task_id"],
            }
        ), 200

    except globus_sdk.GlobusAPIError as e:
        logger.error(f"Globus API error: {str(e)}")
        return jsonify({"error": f"Globus API error: {str(e)}"}), e.http_status
    except Exception as e:
        logger.error(f"Error initiating transfer: {str(e)}")
        return jsonify({"error": f"Error initiating transfer: {str(e)}"}), 500
