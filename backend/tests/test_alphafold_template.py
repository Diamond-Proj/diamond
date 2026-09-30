import os
import subprocess
from datetime import datetime
from uuid import uuid4

import pytest

from diamond_backend.app import g_database
from diamond_backend.app.tasks import (
    ALPHAFOLD_TASK_TEMPLATES,
    _build_alphafold_task_log_info,
    _parse_alphafold_task_log_info,
)
from diamond_backend.app.utils.functions import _escape_shell_braces
from diamond_backend.app.utils.scripts_render import render_task_template_script

ALPHAFOLD_TEMPLATE = "alphafold-colabfold-delta.j2"
DEFAULT_SIF = "/projects/bcrc/hxie6/alphafold/colabfold_1.6.2-cuda12.sif"

ALPHAFOLD_CONTEXT = {
    "location": "/tmp/diamond",
    "task_name": "af-demo",
    "stdout_path": "/tmp/diamond/logs/af-demo.stdout",
    "stderr_path": "/tmp/diamond/logs/af-demo.stderr",
    "num_of_nodes": 1,
    "time_duration": "01:00:00",
    "partition": "gpuA100x4",
    "account": "proj",
    "slurm_options": "#SBATCH --gpus-per-node=1",
    "reservation": "",
    "container_path": "",
    "sequence_upload": "",
    "sequence_text": "",
    "sequence_path": "",
    "out_dir": "",
    "weights_dir": "/projects/af/cache",
    "num_models": 5,
    "num_recycle": 3,
    "model_type": "auto",
    "msa_mode": "mmseqs2_uniref_env",
    "relax": "none",
    "use_templates": "no",
}


def _render(**overrides):
    return render_task_template_script(
        ALPHAFOLD_TEMPLATE, dict(ALPHAFOLD_CONTEXT, **overrides)
    )


def test_alphafold_template_is_tagged_as_alphafold_task():
    assert ALPHAFOLD_TASK_TEMPLATES[ALPHAFOLD_TEMPLATE] == "colabfold"


def test_render_alphafold_template_with_cluster_sequence_path():
    script = _render(sequence_path="/projects/proj/query.fasta")
    assert "af-demo.submit" in script
    assert DEFAULT_SIF in script
    assert "apptainer exec --nv" in script
    assert "colabfold_batch" in script
    assert "--data /cache/colabfold" in script
    assert "--num-models 5" in script
    assert "--num-recycle 3" in script
    assert "--model-type auto" in script
    assert "--msa-mode mmseqs2_uniref_env" in script
    assert "--templates" not in script
    assert "--amber" not in script
    assert '-B "$input_dir":/diamond_input' in script
    assert '-B "$resolved_out_dir":/diamond_output' in script
    assert '"/diamond_input/$input_file" /diamond_output' in script
    assert (
        "cat <<'DIAMOND_SEQUENCE_PATH'\n/projects/proj/query.fasta\nDIAMOND_SEQUENCE_PATH"
        in script
    )
    assert "DIAMOND_ARTIFACT_PATH=$resolved_out_dir" in script


def test_render_alphafold_template_prefers_selected_container():
    script = _render(container_path="/work/images/colabfold-custom.sif")
    assert "/work/images/colabfold-custom.sif" in script
    assert DEFAULT_SIF not in script


def test_render_alphafold_template_whitelists_enum_values():
    script = _render(
        model_type="alphafold2_ptm; rm -rf /",
        msa_mode="$(curl evil)",
        relax="`touch /tmp/pwned`",
        use_templates="maybe",
        num_models="99",
        num_recycle="-3",
    )
    assert "--model-type auto" in script
    assert "--msa-mode mmseqs2_uniref_env" in script
    assert "--num-models 5" in script
    assert "--num-recycle 0" in script
    assert "--amber" not in script
    assert "--templates" not in script
    assert "rm -rf" not in script
    assert "curl evil" not in script
    assert "touch /tmp/pwned" not in script


def test_render_alphafold_template_optional_flags():
    script = _render(
        use_templates="yes",
        relax="amber",
        model_type="alphafold2_multimer_v3",
        msa_mode="single_sequence",
        num_models=2,
        num_recycle="6",
    )
    assert "--templates \\" in script
    assert "--amber --use-gpu-relax --num-relax 1 \\" in script
    assert "--model-type alphafold2_multimer_v3" in script
    assert "--msa-mode single_sequence" in script
    assert "--num-models 2" in script
    assert "--num-recycle 6" in script


def test_render_alphafold_template_null_fields_do_not_leak_none():
    script = _render(
        sequence_upload=None,
        sequence_upload_filename=None,
        sequence_text=None,
        sequence_path="/projects/proj/query.fasta",
        out_dir=None,
        weights_dir=None,
        model_type=None,
        msa_mode=None,
        relax=None,
        use_templates=None,
        num_models=None,
        num_recycle=None,
    )
    assert "None" not in script
    assert "--num-models 5" in script
    assert "--num-recycle 3" in script


def test_render_alphafold_template_survives_shellfunction_formatting():
    script = _render(sequence_path="/projects/proj/query.fasta")
    formatted = _escape_shell_braces(script).format()
    assert "${" in formatted
    assert "colabfold_batch" in formatted


def _run_alphafold_outer_script(tmp_path, context_overrides, env_home=None):
    location = tmp_path / "diamond"
    (location / "logs").mkdir(parents=True, exist_ok=True)
    context = dict(
        ALPHAFOLD_CONTEXT,
        location=str(location),
        stdout_path=str(location / "logs" / "af-demo.stdout"),
        stderr_path=str(location / "logs" / "af-demo.stderr"),
        **context_overrides,
    )
    script = render_task_template_script(ALPHAFOLD_TEMPLATE, context)

    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    sbatch_stub = bindir / "sbatch"
    sbatch_stub.write_text("#!/bin/bash\necho 'Submitted batch job 123'\n")
    sbatch_stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
    if env_home is not None:
        env["HOME"] = env_home
    result = subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True
    )
    return result, location


def test_alphafold_outer_script_writes_fasta_from_raw_sequence(tmp_path):
    out_dir = tmp_path / "out"
    result, location = _run_alphafold_outer_script(
        tmp_path,
        {"out_dir": str(out_dir), "sequence_text": "MKTAYIAK\nQRQISFVK \n"},
    )
    assert result.returncode == 0, result.stderr
    assert f"DIAMOND_ARTIFACT_PATH={out_dir}\n" in result.stdout

    fasta = out_dir / "input" / "query.fasta"
    assert fasta.read_text() == ">af-demo\nMKTAYIAKQRQISFVK\n"

    submit = (location / "af-demo.submit").read_text()
    assert f'-B "{out_dir}/input":/diamond_input' in submit
    assert f'-B "{out_dir}":/diamond_output' in submit
    assert '"/diamond_input/query.fasta" /diamond_output' in submit
    assert '-B "/projects/af/cache":/cache' in submit
    assert "export MPLBACKEND=Agg" in submit


def test_alphafold_outer_script_keeps_fasta_header_and_chains(tmp_path):
    out_dir = tmp_path / "out"
    result, _location = _run_alphafold_outer_script(
        tmp_path,
        {"out_dir": str(out_dir), "sequence_text": ">dimer\nMKTAYIAK:QRQISFVK\n"},
    )
    assert result.returncode == 0, result.stderr
    fasta = out_dir / "input" / "query.fasta"
    assert fasta.read_text() == ">dimer\nMKTAYIAK:QRQISFVK\n"


def test_alphafold_outer_script_prefers_upload_over_text_and_path(tmp_path):
    staged = "/tmp/diamond/uploads/af-demo/abc123/sequence_upload/seq.fasta"
    out_dir = tmp_path / "out"
    result, location = _run_alphafold_outer_script(
        tmp_path,
        {
            "out_dir": str(out_dir),
            "sequence_upload": staged,
            "sequence_text": "MKTAYIAK",
            "sequence_path": "/projects/proj/other.fasta",
        },
    )
    assert result.returncode == 0, result.stderr
    submit = (location / "af-demo.submit").read_text()
    assert (
        '-B "/tmp/diamond/uploads/af-demo/abc123/sequence_upload":/diamond_input'
        in submit
    )
    assert '"/diamond_input/seq.fasta" /diamond_output' in submit
    assert "other.fasta" not in submit
    assert not (out_dir / "input" / "query.fasta").exists()


def test_alphafold_outer_script_without_weights_dir_skips_cache_bind(tmp_path):
    result, location = _run_alphafold_outer_script(
        tmp_path,
        {
            "out_dir": str(tmp_path / "out"),
            "weights_dir": "",
            "sequence_path": "/projects/proj/query.fasta",
        },
    )
    assert result.returncode == 0, result.stderr
    submit = (location / "af-demo.submit").read_text()
    assert ":/cache" not in submit
    assert '-B "/projects/proj":/diamond_input' in submit
    assert '"/diamond_input/query.fasta" /diamond_output' in submit


def test_alphafold_outer_script_fails_cleanly_without_input(tmp_path):
    result, location = _run_alphafold_outer_script(
        tmp_path, {"out_dir": str(tmp_path / "out"), "sequence_text": "  \n"}
    )
    assert result.returncode == 1
    assert "No sequence provided" in result.stderr
    assert not (location / "af-demo.submit").exists()


def test_alphafold_outer_script_executes_sequence_text_safely(tmp_path):
    sentinel = tmp_path / "pwned"
    out_dir = tmp_path / "out"
    sequence = f"MKTA`touch {sentinel}`$HOME$(id)YIAK"
    result, _location = _run_alphafold_outer_script(
        tmp_path, {"out_dir": str(out_dir), "sequence_text": sequence}
    )
    assert result.returncode == 0, result.stderr
    assert not sentinel.exists()
    fasta = (out_dir / "input" / "query.fasta").read_text()
    # A raw sequence is written literally (whitespace dropped), never evaluated:
    # the backticks, $HOME and $(id) survive as text.
    assert fasta == f">af-demo\n{''.join(sequence.split())}\n"


def test_alphafold_outer_script_empty_out_dir_defaults_under_diamond_dir(tmp_path):
    result, location = _run_alphafold_outer_script(
        tmp_path, {"out_dir": "", "sequence_path": "/projects/proj/query.fasta"}
    )
    assert result.returncode == 0, result.stderr
    expected_out = f"{location}/outputs/af-demo"
    assert f"DIAMOND_ARTIFACT_PATH={expected_out}\n" in result.stdout
    assert os.path.isdir(expected_out)


def test_alphafold_outer_script_relative_paths_resolve_under_diamond_dir(tmp_path):
    result, location = _run_alphafold_outer_script(
        tmp_path,
        {
            "out_dir": "results/af1",
            "sequence_path": "inputs/query.fasta",
            "weights_dir": "weights",
        },
    )
    assert result.returncode == 0, result.stderr
    assert f"DIAMOND_ARTIFACT_PATH={location}/results/af1\n" in result.stdout
    submit = (location / "af-demo.submit").read_text()
    assert f'-B "{location}/inputs":/diamond_input' in submit
    assert f'-B "{location}/weights":/cache' in submit


def test_alphafold_task_log_info_round_trip():
    assert _build_alphafold_task_log_info("colabfold") == (
        "alphafold_task|pipeline=colabfold"
    )
    assert _build_alphafold_task_log_info("  ") == "alphafold_task|pipeline=colabfold"
    assert _parse_alphafold_task_log_info("alphafold_task|pipeline=colabfold") == {
        "pipeline": "colabfold"
    }
    assert _parse_alphafold_task_log_info("vllm_task|model=qwen") is None
    assert _parse_alphafold_task_log_info("") is None
    assert _parse_alphafold_task_log_info(None) is None


def test_submit_task_tags_alphafold_template(client, monkeypatch, test_endpoint_delta):
    endpoint_uuid = test_endpoint_delta[2]
    captured = {}

    def fake_render_task_template_script(template_name, context):
        captured["template_name"] = template_name
        captured["context"] = context
        return "echo submit alphafold"

    def fake_submit_batch_script_task(**kwargs):
        captured["submission_kwargs"] = kwargs
        return {
            "task_id": "GC-TASK-AF-1",
            "batch_job_id": "654321",
            "task_name": kwargs["task_name"],
            "stdout_path": kwargs["stdout_path"],
            "stderr_path": kwargs["stderr_path"],
            "artifact_path": "",
        }

    monkeypatch.setattr(
        "diamond_backend.app.tasks.render_task_template_script",
        fake_render_task_template_script,
    )
    monkeypatch.setattr(
        "diamond_backend.app.tasks.submit_batch_script_task",
        fake_submit_batch_script_task,
    )
    monkeypatch.setattr(
        "diamond_backend.app.tasks.load_container_module_command",
        lambda _endpoint_host: "",
    )
    monkeypatch.setattr(
        g_database,
        "get_diamond_dir",
        lambda endpoint_uuid, identity_id: "/tmp/diamond",
    )

    response = client.post(
        "/api/submit_task",
        json={
            "endpoint": endpoint_uuid,
            "taskName": "af-demo",
            "partition": "gpuA100x4",
            "account": "proj",
            "time_duration": "01:00:00",
            "task_template": ALPHAFOLD_TEMPLATE,
            "task_define": {
                "sequence_text": "MKTAYIAK",
                "container_path": DEFAULT_SIF,
                "weights_dir": "/projects/af/cache",
                "num_models": 5,
                "num_recycle": 3,
                "model_type": "auto",
                "msa_mode": "mmseqs2_uniref_env",
                "relax": "none",
                "use_templates": "no",
            },
        },
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["task_id"] == "GC-TASK-AF-1"
    assert captured["template_name"] == ALPHAFOLD_TEMPLATE
    assert captured["context"]["container_path"] == DEFAULT_SIF
    assert captured["context"]["sequence_text"] == "MKTAYIAK"
    assert captured["submission_kwargs"]["log_path"] == (
        "alphafold_task|pipeline=colabfold"
    )


def test_get_task_status_marks_alphafold_tasks(
    client, monkeypatch, test_identity, test_endpoint_delta
):
    endpoint_uuid = test_endpoint_delta[2]
    task_id = f"GC-TASK-AF-{uuid4().hex[:8]}"
    g_database.save_task(
        task_id=task_id,
        batch_job_id="654321",
        task_name="af-demo",
        identity_id=test_identity,
        task_status="COMPLETED",
        task_create_time=datetime.now(),
        log_path=_build_alphafold_task_log_info("colabfold"),
        stdout_path="/tmp/diamond/logs/af-demo.stdout",
        stderr_path="/tmp/diamond/logs/af-demo.stderr",
        compute_endpoint_id=endpoint_uuid,
        checkpoint_path="/tmp/diamond/outputs/af-demo",
    )
    monkeypatch.setattr(
        "diamond_backend.app.tasks.refresh_identity_task_statuses",
        lambda identity_id: g_database.load_tasks(identity_id),
    )

    try:
        response = client.get("/api/get_task_status")
        assert response.status_code == 200
        task_payload = response.get_json()[task_id]
        assert task_payload["task_type"] == "alphafold"
        assert task_payload["alphafold"] == {"pipeline": "colabfold"}
        assert task_payload["chat"] is None
        assert task_payload["artifact_path"] == "/tmp/diamond/outputs/af-demo"
    finally:
        g_database.delete_task(task_id)


@pytest.mark.parametrize("raw", ["yes", "YES", " true ", "1"])
def test_render_alphafold_template_truthy_use_templates(raw):
    assert "--templates" in _render(use_templates=raw)
