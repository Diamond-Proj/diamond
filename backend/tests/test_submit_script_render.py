import os

import pytest

from diamond_backend.app.tasks import (
    _build_finetuned_artifact_path,
    _build_vllm_host_candidates,
    _build_vllm_task_log_info,
    _derive_vllm_port_from_batch_job_id,
    _extract_artifact_path_from_submit_stdout,
    _is_safe_path_component,
    _parse_vllm_task_log_info,
    _validate_finetuned_model_name,
)
from diamond_backend.app.utils.functions import _escape_shell_braces
from diamond_backend.app.utils.scripts_render import (
    render_submit_task_script,
    render_task_template_script,
)

expected_output_1 = """cat << EOF > /dev/shm/Foo.submit
#!/bin/bash

#SBATCH --job-name=Foo
#SBATCH --output=/dev/shm/stdout
#SBATCH --error=/dev/shm/stderr
#SBATCH --nodes=1
#SBATCH --time=00:10:00
#SBATCH --partition=development
#SBATCH --account=testing_account
#SBATCH --ntasks-per-node=1

export DIAMOND_DATASET_PATH=
if [[ -z "" ]]; then
    echo "No dataset specified"
    mount_string=""
else
    mount_string="--bind "
fi


srun --cpu-bind=none apptainer exec \\$mount_string --nv dummy.sif python test.py
echo "EOF" >> /dev/shm/stdout
echo "EOF" >> /dev/shm/stderr
EOF

sbatch /dev/shm/Foo.submit"""


def test_render():
    script = render_submit_task_script(
        task_name="Foo",
        location="/dev/shm",
        stdout_path="/dev/shm/stdout",
        stderr_path="/dev/shm/stderr",
        time_duration="00:10:00",
        partition="development",
        account="testing_account",
        reservation="",
        num_of_nodes=1,
        container="dummy.sif",
        container_module_command="",
        dataset_system_path="",
        task_command="python test.py",
        slurm_options="",
    )
    assert script.replace(" ", "") == expected_output_1.replace(" ", "")


expected_output_2 = """cat << EOF > /dev/shm/Foo.submit
#!/bin/bash

#SBATCH --job-name=Foo
#SBATCH --output=/dev/shm/stdout
#SBATCH --error=/dev/shm/stderr
#SBATCH --nodes=1
#SBATCH --time=00:10:00
#SBATCH --partition=development
#SBATCH --account=testing_account
#SBATCH --ntasks-per-node=1

export DIAMOND_DATASET_PATH=/home/test_user/dataset
if [[ -z "/home/test_user/dataset" ]]; then
    echo "No dataset specified"
    mount_string=""
else
    mount_string="--bind /home/test_user/dataset"
fi

module load apptainer
srun --cpu-bind=none apptainer exec \\$mount_string --nv dummy.sif python test.py
echo "EOF" >> /dev/shm/stdout
echo "EOF" >> /dev/shm/stderr
EOF

sbatch None /dev/shm/Foo.submit"""


def test_render_with_dataset():
    container_module_command = "module load apptainer"
    dataset_system_path = "/home/test_user/dataset"
    script = render_submit_task_script(
        task_name="Foo",
        location="/dev/shm",
        stdout_path="/dev/shm/stdout",
        stderr_path="/dev/shm/stderr",
        time_duration="00:10:00",
        partition="development",
        account="testing_account",
        num_of_nodes=1,
        reservation=None,
        container="dummy.sif",
        container_module_command=container_module_command,
        dataset_system_path=dataset_system_path,
        task_command="python test.py",
        slurm_options="",
    )
    assert container_module_command in script
    assert dataset_system_path in script
    assert script.replace(" ", "") == expected_output_2.replace(" ", "")


def test_render_task_template_script():
    script = render_task_template_script(
        "deepspeed-sft-delta.j2",
        {
            "location": "/tmp",
            "task_name": "demo-task",
            "stdout_path": "/tmp/demo.stdout",
            "stderr_path": "/tmp/demo.stderr",
            "num_of_nodes": 1,
            "time_duration": "00:10:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "--gpus-per-node=1",
            "model_path": "/models/qwen",
            "dataset_path": "/data/scifact",
            "scratch_path": "/scratch/run",
            "reservation": "",
            "finetuned_model_path": "/finetuned/model/path",
            "finetuned_model_name": "demo-sft-model",
        },
    )
    assert "demo-task.submit" in script
    assert "/models/qwen" in script
    assert "/data/scifact" in script
    assert "--bind $resolved_finetuned_model_path:/scratch" in script
    assert "/scratch/demo-sft-model" in script
    assert "DIAMOND_ARTIFACT_PATH=$resolved_artifact_path" in script
    assert "cat << EOF" in script
    assert "export MASTER_PORT=\\$(( 50000 + 10#\\${SLURM_JOB_ID: -4} ))" in script


def test_render_container_build_template_script():
    script = render_task_template_script(
        "container-build.j2",
        {
            "task_name": "image-build-demo",
            "container_name": "image-build-demo",
            "location": "/tmp/diamond",
            "stdout_path": "/tmp/diamond/logs/image-build-demo.stdout",
            "stderr_path": "/tmp/diamond/logs/image-build-demo.stderr",
            "time_duration": "00:30:00",
            "partition": "gpu",
            "account": "proj",
            "reservation": "",
            "container_module_command": "module load apptainer",
            "base_image": "ubuntu:22.04",
            "commands": "python -m pip install torch",
            "environment": "HF_HOME=/tmp/hf",
        },
    )
    assert "image-build-demo.def" in script
    assert "image-build-demo.submit" in script
    assert "Bootstrap: docker" in script
    assert "From: ubuntu:22.04" in script
    assert "cat << 'COMMANDS_EOF' > commands.sh" in script
    assert "python -m pip install torch" in script
    assert "module load apptainer" in script
    assert (
        "apptainer build /tmp/diamond/image-build-demo.sif /tmp/diamond/image-build-demo.def"
        in script
    )


def test_render_task_template_script_survives_shellfunction_formatting():
    script = render_task_template_script(
        "deepspeed-sft-delta.j2",
        {
            "location": "/tmp",
            "task_name": "demo-task",
            "stdout_path": "/tmp/demo.stdout",
            "stderr_path": "/tmp/demo.stderr",
            "num_of_nodes": 1,
            "time_duration": "00:10:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "--gpus-per-node=1",
            "model_path": "/models/qwen",
            "dataset_path": "/data/scifact",
            "scratch_path": "/scratch/run",
            "reservation": "",
            "finetuned_model_path": "/finetuned/model/path",
            "finetuned_model_name": "demo-sft-model",
        },
    )
    escaped_script = _escape_shell_braces(script)
    formatted = escaped_script.format()
    assert "export MASTER_PORT=\\$(( 50000 + 10#\\${SLURM_JOB_ID: -4} ))" in formatted


def test_render_task_template_script_rejects_invalid_name():
    with pytest.raises(ValueError):
        render_task_template_script("../submit_task.j2", {})


def test_validate_finetuned_model_name_accepts_valid_value():
    assert _validate_finetuned_model_name(" qwen3-0.6B-sft ") == "qwen3-0.6B-sft"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        ".",
        "..",
        "../model",
        "model/name",
        "model\\name",
        "name with space",
        "name$",
        None,
    ],
)
def test_validate_finetuned_model_name_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        _validate_finetuned_model_name(value)


def test_build_finetuned_artifact_path():
    assert (
        _build_finetuned_artifact_path(
            finetuned_model_path="/work/models",
            finetuned_model_name="qwen-sft-v1",
        )
        == "/work/models/qwen-sft-v1"
    )
    assert (
        _build_finetuned_artifact_path(
            finetuned_model_path="",
            finetuned_model_name="qwen-sft-v1",
        )
        == ""
    )


def test_extract_artifact_path_from_submit_stdout():
    stdout = """
Some logs
Submitted batch job 123456
DIAMOND_ARTIFACT_PATH=/work/nvme/bcrc/hxie6/test2/demo-sft
"""
    assert (
        _extract_artifact_path_from_submit_stdout(stdout)
        == "/work/nvme/bcrc/hxie6/test2/demo-sft"
    )
    assert _extract_artifact_path_from_submit_stdout("Submitted batch job 123456") == ""


def test_render_vllm_template_script():
    script = render_task_template_script(
        "vllm-inference.j2",
        {
            "location": "/tmp",
            "task_name": "vllm-demo",
            "stdout_path": "/tmp/vllm.stdout",
            "stderr_path": "/tmp/vllm.stderr",
            "num_of_nodes": 1,
            "time_duration": "08:00:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "#SBATCH --gpus-per-node=1",
            "reservation": "",
            "container_module_command": "module load apptainer",
            "model_path": "/work/model/path",
            "container_path": "/work/images/vllm.sif",
            "served_model_name": "diamond-assistant",
            "max_model_len": 2048,
            "vllm_extra_args": "--gpu-memory-utilization 0.95",
        },
    )
    assert "vllm-demo.submit" in script
    assert '--bind "/work/model/path":/model' in script
    assert "/work/images/vllm.sif" in script
    assert "VLLM_PORT=\\$(( 40000 + 10#\\${SLURM_JOB_ID: -4} ))" in script
    assert '--served-model-name "diamond-assistant"' in script
    assert 'sbatch_output="$(sbatch' in script


def test_parse_vllm_task_log_info():
    assert _parse_vllm_task_log_info("vllm_task|model=diamond-assistant") == {
        "model": "diamond-assistant",
    }
    assert _parse_vllm_task_log_info("something-else") is None
    assert _build_vllm_task_log_info("  ") == "vllm_task|model=diamond-assistant"
    assert _build_vllm_task_log_info("qwen") == "vllm_task|model=qwen"
    assert _derive_vllm_port_from_batch_job_id("123456") == 43456
    assert _derive_vllm_port_from_batch_job_id("84") == 40084
    assert _derive_vllm_port_from_batch_job_id("abc") is None


def test_build_vllm_host_candidates():
    assert _build_vllm_host_candidates("gpu001", "delta.ncsa.illinois.edu") == [
        "gpu001",
        "gpu001.ncsa.illinois.edu",
    ]
    assert _build_vllm_host_candidates(
        "gpu001.ncsa.illinois.edu", "delta.ncsa.illinois.edu"
    ) == ["gpu001.ncsa.illinois.edu"]
    assert _build_vllm_host_candidates("", "delta.ncsa.illinois.edu") == []


def test_render_vllm_template_survives_shellfunction_formatting():
    script = render_task_template_script(
        "vllm-inference.j2",
        {
            "location": "/tmp",
            "task_name": "vllm-demo",
            "stdout_path": "/tmp/vllm.stdout",
            "stderr_path": "/tmp/vllm.stderr",
            "num_of_nodes": 1,
            "time_duration": "08:00:00",
            "partition": "gpu",
            "account": "proj",
            "slurm_options": "",
            "reservation": "",
            "container_module_command": "",
            "model_path": "/work/model/path",
            "container_path": "/work/images/vllm.sif",
            "served_model_name": "diamond-assistant",
            "max_model_len": 2048,
            "vllm_extra_args": "",
        },
    )
    escaped_script = _escape_shell_braces(script)
    formatted = escaped_script.format()
    assert "VLLM_PORT=\\$(( 40000 + 10#\\${SLURM_JOB_ID: -4} ))" in formatted


SAM3_FINETUNE_CONTEXT = {
    "location": "/tmp/diamond",
    "task_name": "sam3-ft-demo",
    "stdout_path": "/tmp/diamond/logs/sam3-ft-demo.stdout",
    "stderr_path": "/tmp/diamond/logs/sam3-ft-demo.stderr",
    "num_of_nodes": 1,
    "time_duration": "01:00:00",
    "partition": "gpu",
    "account": "proj",
    "slurm_options": "#SBATCH --gpus-per-node=1",
    "reservation": "",
    "container_path": "",
    "base_model_path": "/projects/sam3/sam3.pt",
    "dataset_path": "/projects/sam3/data/montgomery_extracted",
    "finetuned_model_path": "/projects/sam3/models",
    "finetuned_model_name": "sam3_lung_finetuned",
    "epochs": 4,
    "category": "lung",
}


def test_render_sam3_finetune_template_script():
    script = render_task_template_script(
        "sam3-finetune-delta.j2", dict(SAM3_FINETUNE_CONTEXT)
    )
    assert "sam3-ft-demo.submit" in script
    assert "/projects/bcrc/hxie6/sam3_ft/sam3lung.sif" in script
    assert '--model "/projects/sam3/sam3.pt"' in script
    assert '--dataset "/projects/sam3/data/montgomery_extracted"' in script
    assert '--output "$resolved_artifact_path"' in script
    assert "--epochs 4" in script
    assert "--category $category_quoted" in script
    assert "cat <<'DIAMOND_CATEGORY'\nlung\nDIAMOND_CATEGORY" in script
    assert (
        'resolved_artifact_path="$resolved_finetuned_model_path/sam3_lung_finetuned.pt"'
        in script
    )
    assert "DIAMOND_ARTIFACT_PATH=$resolved_artifact_path" in script


def test_render_sam3_finetune_template_prefers_selected_container():
    context = dict(SAM3_FINETUNE_CONTEXT, container_path="/work/images/custom.sif")
    script = render_task_template_script("sam3-finetune-delta.j2", context)
    assert "/work/images/custom.sif" in script
    assert "/projects/bcrc/hxie6/sam3_ft/sam3lung.sif" not in script


SAM3_PREDICT_CONTEXT = {
    "location": "/tmp/diamond",
    "task_name": "sam3-predict-demo",
    "stdout_path": "/tmp/diamond/logs/sam3-predict-demo.stdout",
    "stderr_path": "/tmp/diamond/logs/sam3-predict-demo.stderr",
    "num_of_nodes": 1,
    "time_duration": "00:20:00",
    "partition": "gpu",
    "account": "proj",
    "slurm_options": "#SBATCH --gpus-per-node=1",
    "reservation": "",
    "container_path": "",
    "model_path": "/projects/sam3/models/sam3_lung_finetuned.pt",
    "prompt": "lung",
    "out_dir": "/work/out_l1",
}


def test_render_sam3_predict_template_with_cluster_image_path():
    context = dict(SAM3_PREDICT_CONTEXT, image_path="/work/images/l1.jpg")
    script = render_task_template_script("sam3-predict-delta.j2", context)
    assert "sam3-predict-demo.submit" in script
    assert (
        "cat <<'DIAMOND_IMAGE_PATH'\n/work/images/l1.jpg\nDIAMOND_IMAGE_PATH" in script
    )
    assert '--model "/projects/sam3/models/sam3_lung_finetuned.pt"' in script
    assert "--prompt $prompt_quoted" in script
    assert "cat <<'DIAMOND_PROMPT'\nlung\nDIAMOND_PROMPT" in script
    assert "--out-dir /diamond_output" in script
    assert '-B "$image_dir":/diamond_input' in script
    assert '-B "$resolved_out_dir":/diamond_output' in script
    assert "DIAMOND_ARTIFACT_PATH=$resolved_out_dir" in script


def test_render_sam3_predict_template_with_staged_uploaded_image():
    context = dict(
        SAM3_PREDICT_CONTEXT,
        image_upload="/tmp/diamond/uploads/sam3-predict-demo/l1.jpg",
        image_upload_filename="l1.jpg",
    )
    script = render_task_template_script("sam3-predict-delta.j2", context)
    assert (
        'resolved_image_path="/tmp/diamond/uploads/sam3-predict-demo/l1.jpg"' in script
    )
    # The staged path must be inlined as a path, never as embedded base64 content.
    assert "base64" not in script


def test_render_sam3_predict_template_prefers_uploaded_image_over_path():
    context = dict(
        SAM3_PREDICT_CONTEXT,
        image_upload="/tmp/diamond/uploads/sam3-predict-demo/l1.jpg",
        image_path="/work/images/other.jpg",
    )
    script = render_task_template_script("sam3-predict-delta.j2", context)
    staged_index = script.index("/tmp/diamond/uploads/sam3-predict-demo/l1.jpg")
    fallback_index = script.index("/work/images/other.jpg")
    assert staged_index < fallback_index


def test_render_sam3_templates_survive_shellfunction_formatting():
    finetune_script = render_task_template_script(
        "sam3-finetune-delta.j2", dict(SAM3_FINETUNE_CONTEXT)
    )
    predict_script = render_task_template_script(
        "sam3-predict-delta.j2",
        dict(SAM3_PREDICT_CONTEXT, image_path="/work/images/l1.jpg"),
    )
    for script in (finetune_script, predict_script):
        escaped_script = _escape_shell_braces(script)
        formatted = escaped_script.format()
        assert "${" in formatted


def test_stage_base64_file_writes_bytes(tmp_path):
    from diamond_backend.app.utils.functions import stage_base64_file

    destination = tmp_path / "uploads" / "demo-task" / "l1.jpg"
    result = stage_base64_file(str(destination), "aGVsbG8=")
    assert result == str(destination)
    assert destination.read_bytes() == b"hello"


def test_stage_task_define_uploads_replaces_base64_with_path(monkeypatch):
    from diamond_backend.app import tasks as tasks_module

    staged_calls = []

    def fake_stage(**kwargs):
        staged_calls.append(kwargs)
        return kwargs["file_path"]

    monkeypatch.setattr(tasks_module, "stage_base64_file_on_endpoint", fake_stage)

    task_define = {
        "image_upload": "aGVsbG8=",
        "image_upload_filename": "l1.jpg",
        "image_path": "",
        "prompt": "lung",
    }
    staged = tasks_module._stage_task_define_uploads(
        task_define,
        endpoint_id="ep",
        identity_id="id",
        location="/u/demo/diamond",
        task_name="sam3-predict",
    )
    # <location>/uploads/<task_name>/<submission_id>/<key>/<filename>
    assert staged["image_upload"].startswith("/u/demo/diamond/uploads/sam3-predict/")
    assert staged["image_upload"].endswith("/image_upload/l1.jpg")
    assert staged["prompt"] == "lung"
    assert len(staged_calls) == 1
    assert staged_calls[0]["content_b64"] == "aGVsbG8="
    assert staged_calls[0]["file_path"] == staged["image_upload"]
    # The original mapping must not be mutated.
    assert task_define["image_upload"] == "aGVsbG8="


def test_stage_task_define_uploads_isolates_multiple_uploads(monkeypatch):
    from diamond_backend.app import tasks as tasks_module

    monkeypatch.setattr(
        tasks_module,
        "stage_base64_file_on_endpoint",
        lambda **kwargs: kwargs["file_path"],
    )
    task_define = {
        "image_upload": "aGVsbG8=",
        "image_upload_filename": "scan.png",
        "mask_upload": "d29ybGQ=",
        "mask_upload_filename": "scan.png",
    }
    staged = tasks_module._stage_task_define_uploads(
        task_define,
        endpoint_id="ep",
        identity_id="id",
        location="/u/demo/diamond",
        task_name="t1",
    )
    # Same filename, different fields must not collide.
    assert staged["image_upload"] != staged["mask_upload"]
    assert staged["image_upload"].endswith("/image_upload/scan.png")
    assert staged["mask_upload"].endswith("/mask_upload/scan.png")
    # Both share the one per-submission directory.
    assert os.path.dirname(os.path.dirname(staged["image_upload"])) == os.path.dirname(
        os.path.dirname(staged["mask_upload"])
    )


def test_stage_task_define_uploads_rejects_bad_task_name(monkeypatch):
    from diamond_backend.app import tasks as tasks_module

    monkeypatch.setattr(
        tasks_module,
        "stage_base64_file_on_endpoint",
        lambda **kwargs: kwargs["file_path"],
    )
    with pytest.raises(ValueError):
        tasks_module._stage_task_define_uploads(
            {"image_upload": "aGVsbG8=", "image_upload_filename": "l1.jpg"},
            endpoint_id="ep",
            identity_id="id",
            location="/u/demo/diamond",
            task_name="lung test 1",
        )


def test_stage_task_define_uploads_skips_empty_fields(monkeypatch):
    from diamond_backend.app import tasks as tasks_module

    def fail_stage(**kwargs):
        raise AssertionError("staging should not run for empty upload fields")

    monkeypatch.setattr(tasks_module, "stage_base64_file_on_endpoint", fail_stage)

    task_define = {"image_upload": "", "image_path": "/work/l1.jpg"}
    staged = tasks_module._stage_task_define_uploads(
        task_define,
        endpoint_id="ep",
        identity_id="id",
        location="/u/demo/diamond",
        task_name="sam3-predict",
    )
    assert staged == task_define


@pytest.mark.parametrize(
    "filename",
    ["../escape.jpg", "a b.jpg", "bad$name.jpg", "path/name.jpg", ".", ".."],
)
def test_stage_task_define_uploads_rejects_bad_filenames(monkeypatch, filename):
    from diamond_backend.app import tasks as tasks_module

    monkeypatch.setattr(
        tasks_module,
        "stage_base64_file_on_endpoint",
        lambda **kwargs: kwargs["file_path"],
    )
    with pytest.raises(ValueError):
        tasks_module._stage_task_define_uploads(
            {"image_upload": "aGVsbG8=", "image_upload_filename": filename},
            endpoint_id="ep",
            identity_id="id",
            location="/u/demo/diamond",
            task_name="sam3-predict",
        )


@pytest.mark.parametrize(
    "name,expected",
    [
        ("mask.png", True),
        ("sam3_lung.finetuned-1.pt", True),
        ("", False),
        (".", False),
        ("..", False),
        ("../etc/passwd", False),
        ("a/b.png", False),
        ("seg mask.png", False),
        ("résumé.png", False),
    ],
)
def test_is_safe_path_component(name, expected):
    assert _is_safe_path_component(name) is expected


def test_stage_task_define_uploads_rejects_invalid_base64(monkeypatch):
    from diamond_backend.app import tasks as tasks_module

    monkeypatch.setattr(
        tasks_module,
        "stage_base64_file_on_endpoint",
        lambda **kwargs: kwargs["file_path"],
    )
    with pytest.raises(ValueError):
        tasks_module._stage_task_define_uploads(
            {"image_upload": "not base64!!", "image_upload_filename": "l1.jpg"},
            endpoint_id="ep",
            identity_id="id",
            location="/u/demo/diamond",
            task_name="sam3-predict",
        )


def test_stage_task_define_uploads_rejects_oversized_payload(monkeypatch):
    import base64 as b64

    from diamond_backend.app import tasks as tasks_module

    monkeypatch.setattr(
        tasks_module,
        "stage_base64_file_on_endpoint",
        lambda **kwargs: kwargs["file_path"],
    )
    oversized = b64.b64encode(
        b"x" * (tasks_module.MAX_UPLOAD_CONTENT_BYTES + 1)
    ).decode("ascii")
    with pytest.raises(ValueError):
        tasks_module._stage_task_define_uploads(
            {"image_upload": oversized, "image_upload_filename": "l1.jpg"},
            endpoint_id="ep",
            identity_id="id",
            location="/u/demo/diamond",
            task_name="sam3-predict",
        )


def test_render_sam3_predict_template_null_fields_do_not_leak_none():
    context = dict(
        SAM3_PREDICT_CONTEXT,
        image_upload=None,
        image_upload_filename=None,
        image_path="/work/images/l1.jpg",
    )
    script = render_task_template_script("sam3-predict-delta.j2", context)
    assert "None" not in script


def test_render_sam3_finetune_template_coerces_epochs():
    context = dict(SAM3_FINETUNE_CONTEXT, epochs="not-a-number; rm -rf /")
    script = render_task_template_script("sam3-finetune-delta.j2", context)
    assert "--epochs 4" in script
    assert "rm -rf" not in script


def test_sam3_predict_outer_script_executes_prompt_safely(tmp_path):
    import os
    import re as regex
    import subprocess

    location = tmp_path / "diamond"
    (location / "logs").mkdir(parents=True)
    out_dir = tmp_path / "out"
    sentinel = tmp_path / "pwned"
    prompt = f"lung $region `touch {sentinel}`"

    context = dict(
        SAM3_PREDICT_CONTEXT,
        location=str(location),
        out_dir=str(out_dir),
        image_path="/work/images/l1.jpg",
        prompt=prompt,
        stdout_path=str(location / "logs" / "demo.stdout"),
        stderr_path=str(location / "logs" / "demo.stderr"),
    )
    script = render_task_template_script("sam3-predict-delta.j2", context)

    bindir = tmp_path / "bin"
    bindir.mkdir()
    sbatch_stub = bindir / "sbatch"
    sbatch_stub.write_text("#!/bin/bash\necho 'Submitted batch job 123'\n")
    sbatch_stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}

    result = subprocess.run(
        ["bash", "-c", script], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert f"DIAMOND_ARTIFACT_PATH={out_dir}" in result.stdout

    submit = (location / "sam3-predict-demo.submit").read_text()
    # The backtick command must not have run at submit time.
    assert not sentinel.exists()
    # $region must survive as literal text instead of expanding to nothing.
    assert "region" in submit

    # Round-trip: the job shell must parse the %q-quoted argument back to the
    # exact original prompt without executing anything. (The unquoted heredoc
    # splices backslash-newline continuations, so the apptainer command is a
    # single line in the .submit file.)
    match = regex.search(r"--prompt (.+?)\s+--out-dir", submit)
    assert match
    parsed = subprocess.run(
        ["bash", "-c", f'printf "%s" {match.group(1)}'],
        capture_output=True,
        text=True,
    )
    assert parsed.stdout == prompt
    assert not sentinel.exists()


def test_sam3_predict_outer_script_fails_cleanly_without_image(tmp_path):
    import os
    import subprocess

    location = tmp_path / "diamond"
    (location / "logs").mkdir(parents=True)
    context = dict(
        SAM3_PREDICT_CONTEXT,
        location=str(location),
        out_dir=str(tmp_path / "out"),
        stdout_path=str(location / "logs" / "demo.stdout"),
        stderr_path=str(location / "logs" / "demo.stderr"),
    )
    script = render_task_template_script("sam3-predict-delta.j2", context)
    result = subprocess.run(
        ["bash", "-c", script], env=dict(os.environ), capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "No image provided" in result.stderr
    assert not (location / "sam3-predict-demo.submit").exists()


def _run_predict_outer_script(tmp_path, context_overrides, env_home=None):
    import subprocess

    location = tmp_path / "diamond"
    (location / "logs").mkdir(parents=True, exist_ok=True)
    context = dict(
        SAM3_PREDICT_CONTEXT,
        location=str(location),
        stdout_path=str(location / "logs" / "demo.stdout"),
        stderr_path=str(location / "logs" / "demo.stderr"),
        **context_overrides,
    )
    script = render_task_template_script("sam3-predict-delta.j2", context)

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


def test_sam3_predict_empty_out_dir_defaults_under_diamond_dir(tmp_path):
    result, location = _run_predict_outer_script(
        tmp_path, {"out_dir": "", "image_path": "/work/images/l1.jpg"}
    )
    assert result.returncode == 0, result.stderr
    expected_out = f"{location}/outputs/sam3-predict-demo"
    assert f"DIAMOND_ARTIFACT_PATH={expected_out}" in result.stdout
    submit = (location / "sam3-predict-demo.submit").read_text()
    assert f'-B "{expected_out}":/diamond_output' in submit


def test_sam3_predict_relative_out_dir_resolves_under_diamond_dir(tmp_path):
    result, location = _run_predict_outer_script(
        tmp_path, {"out_dir": "results/run1", "image_path": "/work/images/l1.jpg"}
    )
    assert result.returncode == 0, result.stderr
    expected_out = f"{location}/results/run1"
    assert f"DIAMOND_ARTIFACT_PATH={expected_out}" in result.stdout


def test_sam3_predict_absolute_out_dir_used_as_is(tmp_path):
    out_dir = tmp_path / "absolute-out"
    result, _location = _run_predict_outer_script(
        tmp_path, {"out_dir": str(out_dir), "image_path": "/work/images/l1.jpg"}
    )
    assert result.returncode == 0, result.stderr
    assert f"DIAMOND_ARTIFACT_PATH={out_dir}" in result.stdout


def test_sam3_predict_relative_image_path_resolves_under_diamond_dir(tmp_path):
    result, location = _run_predict_outer_script(
        tmp_path, {"out_dir": str(tmp_path / "out"), "image_path": "uploads/l1.jpg"}
    )
    assert result.returncode == 0, result.stderr
    submit = (location / "sam3-predict-demo.submit").read_text()
    assert f'-B "{location}/uploads":/diamond_input' in submit
    assert '--image "/diamond_input/l1.jpg"' in submit


def test_list_directory_entries(tmp_path):
    from diamond_backend.app.utils.functions import list_directory_entries

    (tmp_path / "overlay.png").write_bytes(b"png-bytes")
    (tmp_path / "sub").mkdir()
    result = list_directory_entries(str(tmp_path))
    assert result.get("error") is None
    assert result["truncated"] is False
    by_name = {entry["name"]: entry for entry in result["entries"]}
    assert by_name["overlay.png"]["is_dir"] is False
    assert by_name["overlay.png"]["size"] == len(b"png-bytes")
    assert by_name["sub"]["is_dir"] is True

    missing = list_directory_entries(str(tmp_path / "missing"))
    assert missing["error"]
    assert missing["entries"] == []


def test_list_directory_entries_file_artifact_lists_itself(tmp_path):
    """A finetune artifact is a single .pt file, not a directory."""
    from diamond_backend.app.utils.functions import list_directory_entries

    model_file = tmp_path / "sam3_lung_finetuned.pt"
    model_file.write_bytes(b"model-bytes")
    result = list_directory_entries(str(model_file))
    assert result.get("error") is None
    assert result["entries"] == [
        {"name": "sam3_lung_finetuned.pt", "is_dir": False, "size": len(b"model-bytes")}
    ]


def test_read_file_base64_from_directory_and_file_artifacts(tmp_path):
    import base64 as b64

    from diamond_backend.app.utils.functions import read_file_base64

    # Directory artifact: resolve <dir>/<filename>.
    (tmp_path / "mask.png").write_bytes(b"mask-bytes")
    result = read_file_base64(str(tmp_path), "mask.png")
    assert result.get("error") is None
    assert b64.b64decode(result["content_b64"]) == b"mask-bytes"
    assert result["size"] == len(b"mask-bytes")

    oversized = read_file_base64(str(tmp_path), "mask.png", max_bytes=4)
    assert "download limit" in oversized["error"]

    # File artifact: filename must equal the artifact's basename.
    model_file = tmp_path / "model.pt"
    model_file.write_bytes(b"weights")
    got = read_file_base64(str(model_file), "model.pt")
    assert b64.b64decode(got["content_b64"]) == b"weights"

    # Traversal and mismatches are rejected.
    assert read_file_base64(str(tmp_path), "../secret")["error"]
    assert read_file_base64(str(model_file), "other.pt")["error"]
    assert read_file_base64(str(tmp_path), "missing.png")["error"]


def test_sam3_predict_trailing_whitespace_out_dir_is_trimmed(tmp_path):
    result, location = _run_predict_outer_script(
        tmp_path,
        {"out_dir": "results/run1 ", "image_path": "/work/images/l1.jpg"},
    )
    assert result.returncode == 0, result.stderr
    expected_out = f"{location}/results/run1"
    assert f"DIAMOND_ARTIFACT_PATH={expected_out}\n" in result.stdout
    import os

    assert os.path.isdir(expected_out)
    assert not os.path.isdir(f"{expected_out} ")


def test_resolve_artifact_mimetype():
    from diamond_backend.app.tasks import _resolve_artifact_mimetype

    assert _resolve_artifact_mimetype("overlay.png") == ("image/png", True)
    assert _resolve_artifact_mimetype("OVERLAY.JPG") == ("image/jpeg", True)
    assert _resolve_artifact_mimetype("mask.bmp") == ("image/bmp", True)
    assert _resolve_artifact_mimetype("chart.svg") == (
        "application/octet-stream",
        False,
    )
    assert _resolve_artifact_mimetype("report.html") == (
        "application/octet-stream",
        False,
    )
    assert _resolve_artifact_mimetype("no_extension") == (
        "application/octet-stream",
        False,
    )


def test_load_task_with_artifact_requires_identity():
    from diamond_backend.app import app as flask_app
    from diamond_backend.app.tasks import _load_task_with_artifact

    with flask_app.test_request_context():
        task, artifact_path, error_response = _load_task_with_artifact(
            "some-task-id", None
        )
    assert task is None
    assert artifact_path == ""
    assert error_response is not None
    body, status = error_response
    assert status == 400
    assert "primary_identity" in body.get_json()["error"]


def test_sam3_predict_tilde_paths_expand_to_home(tmp_path):
    home = tmp_path / "home"
    (home / "lung").mkdir(parents=True)
    result, location = _run_predict_outer_script(
        tmp_path,
        {"out_dir": "~/out", "image_path": "~/lung/l1.jpg"},
        env_home=str(home),
    )
    assert result.returncode == 0, result.stderr
    submit = (location / "sam3-predict-demo.submit").read_text()
    assert f'-B "{home}/lung":/diamond_input' in submit
    assert f"DIAMOND_ARTIFACT_PATH={home}/out\n" in result.stdout


def test_sam3_finetune_relative_output_dir_resolves_under_diamond_dir():
    context = dict(SAM3_FINETUNE_CONTEXT, finetuned_model_path="models/run1")
    import os
    import subprocess
    import tempfile

    location = SAM3_FINETUNE_CONTEXT["location"]
    script = render_task_template_script("sam3-finetune-delta.j2", context)
    with tempfile.TemporaryDirectory() as tmp:
        bindir = os.path.join(tmp, "bin")
        os.makedirs(bindir)
        sbatch = os.path.join(bindir, "sbatch")
        with open(sbatch, "w") as fh:
            fh.write("#!/bin/bash\necho 'Submitted batch job 1'\n")
        os.chmod(sbatch, 0o755)
        # Point the diamond location at a writable temp dir for mkdir -p.
        script = script.replace(location, os.path.join(tmp, "diamond"))
        os.makedirs(os.path.join(tmp, "diamond"))
        env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
        result = subprocess.run(
            ["bash", "-c", script], env=env, capture_output=True, text=True
        )
    assert result.returncode == 0, result.stderr
    expected = os.path.join(tmp, "diamond", "models", "run1", "sam3_lung_finetuned.pt")
    assert f"DIAMOND_ARTIFACT_PATH={expected}\n" in result.stdout
