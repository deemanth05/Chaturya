import os
from dataclasses import dataclass, field
from pathlib import Path

# Set before importing model/framework packages. These complement OS isolation.
for key, value in {
    "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
    "TRANSFORMERS_OFFLINE": "1", "DO_NOT_TRACK": "1",
    "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false",
    "OTEL_SDK_DISABLED": "true", "ANONYMIZED_TELEMETRY": "false",
}.items():
    os.environ[key] = value

ROOT = Path(os.getenv("WORKBENCH_ROOT", str(Path.cwd() if (Path.cwd() / "config").is_dir() else Path(__file__).resolve().parents[2]))).resolve()

# A simple local dotenv reader; values are data and are never executed as shell code.
if (ROOT / ".env").is_file():
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.startswith(("WORKBENCH_", "DOCLING_", "LAYA_")):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass
class Settings:
    profile: str = field(default_factory=lambda: os.getenv("WORKBENCH_PROFILE", "college"))
    college_config: Path = field(default_factory=lambda: Path(os.getenv("WORKBENCH_COLLEGE_CONFIG", ROOT / "config/college.yaml")).resolve())
    data: Path = field(default_factory=lambda: Path(os.getenv("WORKBENCH_DATA", ROOT / "data")).resolve())
    registry: Path = field(default_factory=lambda: Path(os.getenv("WORKBENCH_REGISTRY", ROOT / "config/registry.yaml")).resolve())
    origins: tuple[str, ...] = field(default_factory=lambda: tuple(os.getenv(
        "WORKBENCH_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")))
    workers: int = field(default_factory=lambda: min(2, max(1, int(os.getenv("WORKBENCH_WORKERS", "2")))))
    model_concurrency: int = field(default_factory=lambda: max(1, int(os.getenv("WORKBENCH_MODEL_CONCURRENCY", "1"))))
    model_timeout: int = field(default_factory=lambda: max(30, int(os.getenv("WORKBENCH_MODEL_TIMEOUT", "600"))))
    queue_total: int = field(default_factory=lambda: max(1, int(os.getenv("WORKBENCH_QUEUE_TOTAL", "50"))))
    queue_per_user: int = field(default_factory=lambda: max(1, int(os.getenv("WORKBENCH_QUEUE_PER_USER", "10"))))
    secure_cookies: bool = field(default_factory=lambda: os.getenv("WORKBENCH_SECURE_COOKIES", "false").lower() == "true")
    sandbox_enabled: bool = field(default_factory=lambda: os.getenv("WORKBENCH_SANDBOX_ENABLED", "true").lower() == "true")
    sandbox_image: str = field(default_factory=lambda: os.getenv("WORKBENCH_SANDBOX_IMAGE", "chaturya-sandbox:local"))
    max_upload: int = 20 * 1024 * 1024
    max_pages: int = 10

    def prepare(self):
        if self.profile not in {"college", "industry"}:
            raise ValueError("WORKBENCH_PROFILE must be college or industry")
        for folder in (self.data, self.data / "jobs", self.data / "knowledge"):
            folder.mkdir(parents=True, exist_ok=True)

