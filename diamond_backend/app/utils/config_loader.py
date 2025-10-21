import importlib.resources as resources
import json
import logging

logger = logging.getLogger(__name__)


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


def load_partitions(machine):
    try:
        fpath = resources.files("diamond_backend").joinpath(
            f"app/data/config/{machine}.json"
        )
        with open(fpath, "r") as f:
            config = json.load(f)
            return config.get("partitions", None)
    except FileNotFoundError:
        logger.error(f"Config file not found for machine: {machine}")
        return None
