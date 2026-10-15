import os
import re
import subprocess
from uuid import uuid4

from diamond_backend.app import g_database
from diamond_backend.app.utils.scripts_render import render_task_template_script


class FakeShellResult:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _patch_work_path_round_trip(monkeypatch, result):
    """Replace the single Globus Compute round trip with a canned ShellResult."""
    from diamond_backend.app import endpoints as endpoints_module

    calls = []

    class FakeClient:
        def register_function(self, func):
            return "fn"

        def get_result(self, task_id):
            return result

    monkeypatch.setattr(
        endpoints_module, "initialize_globus_compute_client", FakeClient
    )
    monkeypatch.setattr(
        endpoints_module,
        "globus_compute_wrapped_run",
        lambda client, **kw: calls.append(kw["kwargs"]) or "task-1",
    )
    return calls


def test_set_work_path_resolves_and_creates_directory(
    client, monkeypatch, test_identity, test_endpoint_frontera
):
    endpoint_uuid = test_endpoint_frontera[2]
    calls = _patch_work_path_round_trip(
        monkeypatch, FakeShellResult(stdout="/u/alice/work/diamond\n")
    )

    response = client.post(
        "/api/set_diamond_work_path",
        json={"endpoint_uuid": endpoint_uuid, "diamond_work_path": "~/work"},
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["diamond_dir"] == "/u/alice/work/diamond"
    assert calls == [{"diamond_work_path": "~/work"}]
    assert (
        g_database.get_diamond_dir(
            identity_id=test_identity, endpoint_uuid=endpoint_uuid
        )
        == "/u/alice/work/diamond"
    )
    g_database.save_diamond_dir(
        identity_id=test_identity, endpoint_uuid=endpoint_uuid, diamond_dir=""
    )


def test_set_work_path_reports_endpoint_failure(
    client, monkeypatch, test_identity, test_endpoint_frontera
):
    endpoint_uuid = test_endpoint_frontera[2]
    _patch_work_path_round_trip(
        monkeypatch,
        FakeShellResult(stderr="mkdir: Permission denied", returncode=1),
    )
    response = client.post(
        "/api/set_diamond_work_path",
        json={"endpoint_uuid": endpoint_uuid, "diamond_work_path": "/projects/shared"},
    )
    assert response.status_code == 400
    assert "Permission denied" in response.get_json()["error"]
    assert not g_database.get_diamond_dir(
        identity_id=test_identity, endpoint_uuid=endpoint_uuid
    )


def test_submit_task_names_run_files_per_submission(
    client, monkeypatch, test_endpoint_delta
):
    captured = {}

    def fake_render(template_name, context):
        captured["context"] = context
        return "echo submit"

    def fake_submit(**kwargs):
        captured["submission"] = kwargs
        return {
            "task_id": "GC-1",
            "batch_job_id": "1",
            "task_name": kwargs["task_name"],
        }

    monkeypatch.setattr(
        "diamond_backend.app.tasks.render_task_template_script", fake_render
    )
    monkeypatch.setattr(
        "diamond_backend.app.tasks.submit_batch_script_task", fake_submit
    )
    monkeypatch.setattr(
        "diamond_backend.app.tasks.load_container_module_command", lambda host: ""
    )
    monkeypatch.setattr(
        g_database, "get_diamond_dir", lambda endpoint_uuid, identity_id: "/tmp/diamond"
    )

    response = client.post(
        "/api/submit_task",
        json={
            "endpoint": test_endpoint_delta[2],
            "taskName": "sam3-predict",
            "partition": "gpuA100x4",
            "account": "proj",
            "time_duration": "00:20:00",
            "task_template": "sam3-predict-delta.j2",
            "task_define": {
                "model_path": "/m.pt",
                "prompt": "lung",
                "image_path": "l1.jpg",
            },
        },
    )

    assert response.status_code == 200, response.get_json()
    run_name = captured["context"]["task_name"]
    assert re.fullmatch(r"sam3-predict-\d{8}-\d{6}-[0-9a-f]{6}", run_name)
    assert (
        captured["submission"]["stdout_path"] == f"/tmp/diamond/logs/{run_name}.stdout"
    )
    # The Task row keeps the name the user typed.
    assert captured["submission"]["task_name"] == "sam3-predict"


def test_image_builder_honors_build_location_and_refuses_foreign_names(
    client, monkeypatch, test_endpoint_anvil
):
    captured = {}

    def fake_render(template_name, context):
        captured["context"] = context
        return "echo"

    def fake_submit(**kwargs):
        captured["submission"] = kwargs
        return {
            "task_id": f"GC-{uuid4().hex[:6]}",
            "batch_job_id": "7",
            "task_name": kwargs["task_name"],
        }

    monkeypatch.setattr(
        "diamond_backend.app.images.render_task_template_script", fake_render
    )
    monkeypatch.setattr(
        "diamond_backend.app.images.submit_batch_script_task", fake_submit
    )
    monkeypatch.setattr(
        "diamond_backend.app.images.load_container_module_command", lambda host: ""
    )
    monkeypatch.setattr(
        g_database, "get_diamond_dir", lambda endpoint_uuid, identity_id: "/tmp/diamond"
    )
    request = {
        "endpoint": test_endpoint_anvil[2],
        "base_image": "ubuntu:22.04",
        "account": "proj",
        "partition": "gpu",
    }

    name = f"custom-loc-{uuid4().hex[:6]}"
    response = client.post(
        "/api/image_builder",
        json={**request, "name": name, "location": "/scratch/bcrc/alice/builds"},
    )
    assert response.status_code == 200, response.get_json()
    assert captured["context"]["location"] == "/scratch/bcrc/alice/builds"
    assert (
        captured["submission"]["checkpoint_path"]
        == f"/scratch/bcrc/alice/builds/{name}.sif"
    )
    assert captured["submission"]["stdout_path"] == f"/tmp/diamond/logs/{name}.stdout"
    g_database.delete_container(
        g_database.get_container_by_name(name).container_task_id
    )

    other = f"OTHER_{uuid4().hex[:6]}"
    g_database.save_profile(other, "Bob", "bob@tester.org")
    taken = f"taken-{uuid4().hex[:6]}"
    g_database.save_container(
        container_task_id="GC-OTHER",
        container_status="ACTIVE",
        identity_id=other,
        name=taken,
        base_image="ubuntu:22.04",
        location="/u/bob/diamond",
        endpoint_id="ep",
    )
    response = client.post("/api/image_builder", json={**request, "name": taken})
    assert response.status_code == 409
    assert g_database.get_container_by_name(taken).identity_id == other
    g_database.delete_container("GC-OTHER")


def test_deepspeed_outer_script_resolves_relative_output_and_creates_it(tmp_path):
    location = tmp_path / "diamond"
    (location / "logs").mkdir(parents=True)
    script = render_task_template_script(
        "deepspeed-sft-delta.j2",
        {
            "location": str(location),
            "task_name": "ds-demo",
            "stdout_path": "/tmp/ds.stdout",
            "stderr_path": "/tmp/ds.stderr",
            "num_of_nodes": 1,
            "time_duration": "00:10:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "",
            "reservation": "",
            "container_path": "",
            "model_path": "/projects/bcrc/diamond/Qwen3-0.6B/",
            "dataset_path": "/projects/bcrc/diamond/diamond-knowledge/",
            "finetuned_model_path": "runs/out",
            "finetuned_model_name": "demo-sft",
        },
    )
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "sbatch").write_text("#!/bin/bash\necho 'Submitted batch job 123'\n")
    (bindir / "sbatch").chmod(0o755)
    result = subprocess.run(
        ["bash", "-c", script],
        env={**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    out_dir = location / "runs" / "out"
    assert out_dir.is_dir()
    assert f"DIAMOND_ARTIFACT_PATH={out_dir}/demo-sft\n" in result.stdout
    assert f"--bind {out_dir}:/scratch" in (location / "ds-demo.submit").read_text()
