import json

from diamond_backend.app import logger


def load_container_module_command(machine):
    try:
        with open(f"app/data/config/{machine}.json", "r") as f:
            return json.load(f)["container_module_command"]
    except FileNotFoundError:
        logger.error(f"Config file not found for machine: {machine}")
        return ""
