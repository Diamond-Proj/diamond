import importlib.resources as resources
from importlib.resources import as_file

from jinja2 import Environment, FileSystemLoader

with as_file(resources.files("diamond_backend").joinpath("app/data/template")) as fpath:
    env = Environment(loader=FileSystemLoader(fpath))


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
