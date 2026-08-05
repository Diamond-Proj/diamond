from datetime import datetime
from uuid import uuid4

from diamond_backend.app import g_database


def test_image_builder_submits_container_build_as_task(
    client, monkeypatch, test_identity, test_endpoint_anvil
):
    endpoint_uuid = test_endpoint_anvil[2]
    container_name = f"image-build-{uuid4().hex[:8]}"
    captured = {}

    def fake_render_task_template_script(template_name, context):
        captured["template_name"] = template_name
        captured["template_context"] = context
        return "echo submit container build"

    def fake_submit_batch_script_task(**kwargs):
        captured["submission_kwargs"] = kwargs
        return {
            "task_id": "GC-TASK-IMAGE-1",
            "batch_job_id": "123456",
            "task_name": kwargs["task_name"],
        }

    monkeypatch.setattr(
        "diamond_backend.app.images.render_task_template_script",
        fake_render_task_template_script,
    )
    monkeypatch.setattr(
        "diamond_backend.app.images.submit_batch_script_task",
        fake_submit_batch_script_task,
    )
    monkeypatch.setattr(
        "diamond_backend.app.images.load_container_module_command",
        lambda _endpoint_host: "module load apptainer",
    )
    monkeypatch.setattr(
        g_database,
        "get_diamond_dir",
        lambda endpoint_uuid, identity_id: "/tmp/diamond",
    )

    response = client.post(
        "/api/image_builder",
        json={
            "endpoint": endpoint_uuid,
            "name": container_name,
            "base_image": "ubuntu:22.04",
            "dependencies": "torch",
            "environment": "HF_HOME=/tmp/hf",
            "commands": "python -m pip install torch",
            "account": "proj",
            "partition": "gpu",
        },
    )

    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["task_id"] == "GC-TASK-IMAGE-1"
    assert response_data["batch_job_id"] == "123456"
    assert response_data["container_name"] == container_name

    assert captured["template_name"] == "container-build.j2"
    assert captured["template_context"]["container_name"] == container_name
    assert captured["template_context"]["location"] == "/tmp/diamond"
    assert captured["submission_kwargs"]["task_name"] == container_name
    assert captured["submission_kwargs"]["checkpoint_path"].endswith(
        f"/{container_name}.sif"
    )

    container = g_database.get_container_by_name(container_name)
    assert container is not None
    assert container.identity_id == test_identity
    assert container.container_task_id == "GC-TASK-IMAGE-1"
    assert container.container_status == "PENDING"

    g_database.delete_container("GC-TASK-IMAGE-1")


def test_get_all_containers_uses_linked_task_status(
    client, monkeypatch, test_identity, test_endpoint_anvil
):
    endpoint_uuid = test_endpoint_anvil[2]
    endpoint_host = test_endpoint_anvil[1]
    container_name = f"linked-image-{uuid4().hex[:8]}"
    task_id = f"GC-TASK-{uuid4().hex[:8]}"

    g_database.save_task(
        task_id=task_id,
        batch_job_id="123456",
        task_name=container_name,
        identity_id=test_identity,
        task_status="COMPLETED",
        task_create_time=datetime.now(),
        log_path="",
        stdout_path="/tmp/diamond/logs/stdout",
        stderr_path="/tmp/diamond/logs/stderr",
        compute_endpoint_id=endpoint_uuid,
        checkpoint_path=f"/tmp/diamond/{container_name}.sif",
    )
    g_database.save_container(
        container_task_id=task_id,
        container_status="PENDING",
        identity_id=test_identity,
        name=container_name,
        base_image="ubuntu:22.04",
        location="/tmp/diamond",
        endpoint_id=endpoint_uuid,
        host=endpoint_host,
    )

    monkeypatch.setattr(
        "diamond_backend.app.containers.refresh_identity_task_statuses",
        lambda identity_id: g_database.load_tasks(identity_id),
    )

    response = client.get("/api/get_all_containers")

    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["containers"][container_name]["status"] == "ACTIVE"
    assert response_data["containers"][container_name]["container_task_id"] == task_id

    g_database.delete_task(task_id)
    g_database.delete_container(task_id)
