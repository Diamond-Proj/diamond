import importlib.resources as resources
import json

from diamond_backend.app import logger


def load_container_module_command(machine):
    try:
        fpath = resources.files("diamond_backend").joinpath(
            f"app/data/config/{machine}.json"
        )
        with open(fpath, "r") as f:
            return json.load(f)["container_module_command"]
    except FileNotFoundError:
        logger.error(f"Config file not found for machine: {machine}")
        return ""
