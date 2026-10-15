"""The sole Blender executable discovery and subprocess boundary."""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from ..core.project import REPOSITORY
from ..core.errors import BlenderError
from ..core.manifest import write_json


def discover(explicit=None):
    candidates = [explicit, os.environ.get("VEHICLERECON_BLENDER"), shutil.which("blender")]
    candidates += sorted(Path(os.environ.get("ProgramFiles", "C:/Program Files")).glob(
        "Blender Foundation/Blender */blender.exe"), reverse=True)
    for path in candidates:
        if path and Path(path).is_file():
            return Path(path).resolve()
    raise BlenderError("Blender not found; set VEHICLERECON_BLENDER or supply --blender")

def version(executable=None):
    exe=discover(executable)
    return subprocess.run([str(exe),'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]


def run(project, stage, *, source=None, executable=None, extra=None):
    exe = discover(executable)
    runtime_version = version(exe)
    command = [str(exe), "--background"]
    if source:
        command.append(str(source))
    command += ["--python-exit-code", "1", "--python", str(REPOSITORY / "vehiclerecon/blender/entry.py"),
                "--", str(project.root), stage]
    if extra:
        command += list(extra)
    result = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True, encoding="utf-8", errors="replace")
    logs = project.path("validation/execution")
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{stage}.stdout.txt").write_text(result.stdout, encoding="utf-8", newline="\n")
    (logs / f"{stage}.stderr.txt").write_text(result.stderr, encoding="utf-8", newline="\n")
    evidence = {"project": project.data["project_id"], "stage": stage, "command": command,
                "blender_version": runtime_version, "returncode": result.returncode}
    write_json(logs / f"{stage}.json", evidence)
    if result.returncode:
        raise BlenderError(f"{stage} failed ({result.returncode}); see {logs}\n{result.stdout[-3000:]}\n{result.stderr[-1500:]}")
    return evidence
