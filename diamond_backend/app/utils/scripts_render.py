import importlib.resources as resources
import re
from importlib.resources import as_file
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

with as_file(resources.files("diamond_backend").joinpath("app/data/template")) as fpath:
    env = Environment(loader=FileSystemLoader(fpath))

with as_file(
    resources.files("diamond_backend").joinpath("app/data/task_templates")
) as task_templates_fpath:
    task_templates_env = Environment(
        loader=FileSystemLoader(task_templates_fpath),
        undefined=StrictUndefined,
    )

TASK_TEMPLATE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def render_apptainer_build_script(
    container_name,
    location,
    base_image,
    commands,
    environment,
):
    apptainer_build_template = env.get_template("create_apptainer_def.j2")
    apptainer_build_script = apptainer_build_template.render(
        container_name=container_name,
        location=location,
        base_image=base_image,
        commands=commands,
        environment=environment,
    )
    return apptainer_build_script


def render_build_container_script(
    container_name,
    stdout_path,
    stderr_path,
    location,
    time_duration,
    partition,
    account,
    reservation,
    container_module_command,
):
    build_container_template = env.get_template("build_container.j2")
    build_container_script = build_container_template.render(
        container_name=container_name,
        location=location,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        time_duration=time_duration,
        partition=partition,
        account=account,
        reservation=reservation,
        container_module_command=container_module_command,
    )
    return build_container_script


def render_submit_task_script(
    task_name,
    location,
    stdout_path,
    stderr_path,
    time_duration,
    partition,
    account,
    reservation,
    num_of_nodes,
    container_module_command,
    container,
    dataset_system_path,
    task_command,
    slurm_options,
):
    submit_task_template = env.get_template("submit_task.j2")
    submit_task_script = submit_task_template.render(
        task_name=task_name,
        location=location,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        time_duration=time_duration,
        partition=partition,
        account=account,
        reservation=reservation,
        num_of_nodes=num_of_nodes,
        container_module_command=container_module_command,
        container=container,
        dataset_system_path=dataset_system_path,
        task_command=task_command,
        slurm_options=slurm_options,
    )
    return submit_task_script


def render_task_template_script(template_name: str, context: dict[str, Any]):
    if not template_name or not TASK_TEMPLATE_NAME_PATTERN.fullmatch(template_name):
        raise ValueError("Invalid task template name")

    task_template = task_templates_env.get_template(template_name)
    return task_template.render(**context)
