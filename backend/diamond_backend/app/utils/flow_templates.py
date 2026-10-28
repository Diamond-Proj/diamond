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
                    },
                },
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
