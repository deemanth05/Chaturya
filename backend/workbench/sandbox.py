import asyncio
import json
import os
import subprocess
import time
import uuid
from pathlib import Path


class Sandbox:
    def __init__(self, settings):
        self.settings = settings

    def execute(self, folder: Path, code: str, inputs=None, verifier="", timeout=25):
        if not self.settings.sandbox_enabled:
            raise RuntimeError("Docker sandbox disabled; host execution is never used as fallback")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "solution.py").write_text(code, encoding="utf-8")
        (folder / "input.json").write_text(json.dumps(inputs or {}), encoding="utf-8")
        (folder / "verify.py").write_text(verifier, encoding="utf-8")
        runner = "import runpy,os; ns=runpy.run_path('/input/solution.py'); os.chdir('/work'); exec(compile(open('/input/verify.py').read(),'/input/verify.py','exec'),ns)"
        name = "chaturya-" + uuid.uuid4().hex
        mount_source = folder.resolve()
        if os.getenv("WORKBENCH_SANDBOX_MOUNT_ROOT"):
            relative = folder.resolve().relative_to(self.settings.data.resolve())
            mount_source = Path(os.environ["WORKBENCH_SANDBOX_MOUNT_ROOT"]) / relative
        command = ["docker", "run", "--rm", "--pull=never", "--name", name, "--network", "none",
            "--memory", "256m", "--memory-swap", "256m", "--cpus", "1", "--pids-limit", "64",
            "--read-only", "--user", "65534:65534", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--tmpfs", "/work:rw,nosuid,nodev,noexec,size=64m,mode=1777", "--workdir", "/work",
            "--mount", f"type=bind,source={mount_source},target=/input,readonly",
            "--env", "PYTHONDONTWRITEBYTECODE=1", self.settings.sandbox_image, "python", "-I", "-c", runner]
        stdout, stderr = folder / "stdout.txt", folder / "stderr.txt"
        started = time.monotonic()
        with stdout.open("wb") as out, stderr.open("wb") as err:
            process = subprocess.Popen(command, stdout=out, stderr=err, stdin=subprocess.DEVNULL)
            error = None
            while process.poll() is None:
                if time.monotonic()-started > timeout:
                    error = "Sandbox time limit exceeded"
                if stdout.stat().st_size + stderr.stat().st_size > 1_000_000:
                    error = "Sandbox output limit exceeded"
                if error:
                    try:
                        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
                    finally:
                        process.kill()
                        process.wait(timeout=5)
                    break
                time.sleep(.1)
        return {"exit_code": process.returncode, "stdout": stdout.read_text(errors="replace")[:16000],
                "stderr": (error or stderr.read_text(errors="replace"))[:8000],
                "latency_ms": round((time.monotonic()-started)*1000), "network": "none"}

    async def run(self, *args, **kwargs):
        return await asyncio.to_thread(self.execute, *args, **kwargs)


SUMMARY_CODE = '''import json, statistics
data = json.load(open('/input/input.json'))
values = [row['thickness_mm'] for row in data['measurements']]
print(json.dumps({'count': len(values), 'minimum_thickness_mm': min(values),
                  'mean_thickness_mm': statistics.mean(values), 'maximum_thickness_mm': max(values)}))
'''


def verify_summary(result, measurements):
    if result["exit_code"] != 0:
        raise ValueError("Sandbox execution failed: " + result["stderr"][:400])
    summary = json.loads(result["stdout"].strip())
    values = [row["thickness_mm"] for row in measurements]
    expected = {"count": len(values), "minimum_thickness_mm": min(values),
                "mean_thickness_mm": sum(values)/len(values), "maximum_thickness_mm": max(values)}
    for key, value in expected.items():
        if key not in summary or isinstance(summary[key], bool) or not isinstance(summary[key], (int, float)) or abs(summary[key]-value) > 1e-6:
            raise ValueError("Independent summary verification failed")
    return summary

