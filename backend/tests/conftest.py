import json
from pathlib import Path

import httpx
import pytest
import yaml

from workbench.settings import Settings


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings(tmp_path):
    config = yaml.safe_load((ROOT / "config/registry.yaml").read_text())
    config["network"]["allowed_origins"] = ["http://127.0.0.1:1234"]
    config["models"][0]["base_url"] = "http://127.0.0.1:1234/v1"
    config["models"][1]["base_url"] = "http://127.0.0.1:1234/v1"
    config["models"] = config["models"][:2]
    registry = tmp_path / "registry.yaml"
    registry.write_text(yaml.safe_dump(config))
    return Settings(profile="industry", data=tmp_path / "data", registry=registry, origins=("http://testserver", "http://localhost:8000"))


MEASUREMENTS = [
    {"tag": "P-101", "thickness": 5.8, "thickness_unit": "mm", "pressure": 12, "pressure_unit": "bar", "page": 1, "quote": "P-101 5.8 mm 12 bar", "confidence": .93},
    {"tag": "P-101", "thickness": 5.6, "thickness_unit": "mm", "pressure": 12, "pressure_unit": "bar", "page": 1, "quote": "P-101 5.6 mm 12 bar", "confidence": .91},
    {"tag": "P-202", "thickness": 7.2, "thickness_unit": "mm", "pressure": 8, "pressure_unit": "bar", "page": 1, "quote": "P-202 7.2 mm 8 bar", "confidence": .94},
]


def model_handler(request):
    if request.url.path.endswith("/models"):
        return httpx.Response(200, json={"data": [{"id": "google/gemma-4-12b-qat"}]})
    body = json.loads(request.content)
    if request.url.path.endswith("/embeddings"):
        text = body["input"].lower()
        return httpx.Response(200, json={"data": [{"embedding": [1.0, float("thickness" in text), float("pressure" in text), .2]}]})
    if "response_format" in body:
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["schema"]["type"] == "object"
    if body["messages"][0]["role"] == "system":
        previous = "Previous verification failure" in body["messages"][-1]["content"]
        code = "import json\ndata=json.load(open('/input/input.json'))\nprint(json.dumps({'total':sum(data.get('values',[]))}))" if previous else "print('{\"total\":999}')"
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"code": code})}}]})
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"measurements": MEASUREMENTS, "observations": []})}}]})

