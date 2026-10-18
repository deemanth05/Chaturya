import copy
import json
import httpx
import pytest
import yaml
from pydantic import ValidationError
from workbench.extraction import Extracted, extract, read_pages
from workbench.registry import Registry
from workbench.network import LocalTransport
from workbench.store import Store
from conftest import ROOT, MEASUREMENTS, model_handler


def test_fixture_is_a_real_scan(settings):
    from pypdf import PdfReader
    source = ROOT / "backend/tests/fixtures/reports/synthetic-inspection-scan.pdf"
    assert not (PdfReader(source).pages[0].extract_text() or "").strip()
    pages = read_pages(source, settings.data / "pages")
    assert len(pages) == 1
    assert pages[0]["text"] == ""


@pytest.mark.asyncio
async def test_extraction_rejects_nonexistent_source_pages(settings):
    store = Store(settings.data)
    values = copy.deepcopy(MEASUREMENTS)
    values[0]["page"] = 9
    network = LocalTransport(["http://127.0.0.1:1234"], store, client=httpx.AsyncClient(transport=httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"measurements": values})}}]}))))
    with pytest.raises(ValueError, match="nonexistent"):
        await extract([{"page": 1, "text": "P-101 thickness report "*5}], Registry(settings.registry), network, None)
    await network.close()


def test_measurements_reject_nan_negative_and_implicit_units():
    for change in ({"thickness": -1}, {"thickness": float("nan")}, {"thickness_unit": "unknown"}):
        with pytest.raises(ValidationError):
            Extracted.model_validate({"measurements": [{**MEASUREMENTS[0], **change}]})


@pytest.mark.asyncio
async def test_configuration_alone_adds_a_specialist(settings):
    data = yaml.safe_load(settings.registry.read_text())
    data["models"].append({"id": "local-coder", "enabled": True, "base_url": "http://127.0.0.1:1234/v1", "modalities": ["text"], "strengths": {"code": 1.0}})
    settings.registry.write_text(yaml.safe_dump(data))
    store = Store(settings.data)
    network = LocalTransport(["http://127.0.0.1:1234"], store, client=httpx.AsyncClient(transport=httpx.MockTransport(model_handler)))
    registry = Registry(settings.registry)
    coder, code_trace = await registry.route("Write Python code", network, None)
    vision, vision_trace = await registry.route("Read inspection report", network, None, image=True)
    assert coder["id"] == "local-coder"
    assert vision["id"] == "google/gemma-4-12b-qat"
    assert code_trace["reason"] and vision_trace["reason"]
    await network.close()


@pytest.mark.asyncio
async def test_laya_low_probability_falls_back_to_reasoning(settings):
    data = yaml.safe_load(settings.registry.read_text())
    data["router"]["laya_url"] = "http://127.0.0.1:1234/v1/systemone"
    settings.registry.write_text(yaml.safe_dump(data))
    store = Store(settings.data)
    result = {"answers": {"task": {"probabilities": {"code": .4, "reasoning": .3, "writing": .2, "extraction": .1}}}}
    network = LocalTransport(["http://127.0.0.1:1234"], store, client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=result))))
    _, trace = await Registry(settings.registry).route("Help me decide what to do", network, None)
    assert trace["task"] == "reasoning" and trace["method"] == "laya"
    assert trace["probabilities"]["code"] == .4
    await network.close()

