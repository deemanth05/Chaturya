import httpx
import pytest
import yaml
from workbench.knowledge import Knowledge
from workbench.network import LocalTransport
from workbench.registry import Registry
from workbench.store import Store
from conftest import ROOT, model_handler


@pytest.mark.asyncio
@pytest.mark.parametrize("dense", [False, True])
async def test_local_retrieval_preserves_sources_and_discloses_mode(settings, dense):
    config = yaml.safe_load(settings.registry.read_text())
    config["models"][1]["enabled"] = dense
    settings.registry.write_text(yaml.safe_dump(config))
    store = Store(settings.data)
    registry = Registry(settings.registry)
    transport = LocalTransport(config["network"]["allowed_origins"], store, client=httpx.AsyncClient(transport=httpx.MockTransport(model_handler)))
    kb = Knowledge(store, registry, transport)
    try:
        for path in (ROOT / "backend/tests/fixtures/knowledge").glob("*.md"):
            await kb.ingest(path, path.name, None, synthetic=True)
        result = await kb.search("inspection thickness pressure source verification")
        assert result["mode"] == ("hybrid" if dense else "bm25_only")
        assert result["sources"]
        assert all(s["page"] >= 0 and s["section"] and s["sha256"] and s["synthetic"] for s in result["sources"])
        no_overlap = await kb.search("zzzzunrelatedword")
        if not dense:
            assert no_overlap["sources"] == []
    finally:
        kb.close()
        await transport.close()

