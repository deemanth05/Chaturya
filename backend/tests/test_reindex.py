import httpx
import pytest
from workbench.knowledge import Knowledge
from workbench.network import LocalTransport
from workbench.registry import Registry
from workbench.store import Store
from conftest import ROOT, model_handler


@pytest.mark.asyncio
async def test_existing_sparse_chunks_can_be_reindexed_without_source_changes(settings):
    store = Store(settings.data)
    registry = Registry(settings.registry)
    transport = LocalTransport(["http://127.0.0.1:1234"], store, client=httpx.AsyncClient(transport=httpx.MockTransport(model_handler)))
    kb = Knowledge(store, registry, transport)
    try:
        await kb.ingest(ROOT / "backend/tests/fixtures/knowledge/SYNTHETIC-inspection-review.md", "fixture.md", None, synthetic=True)
        before = await kb.search("thickness pressure")
        assert before["mode"] == "bm25_only"
        registry.models[1]["enabled"] = True
        result = await kb.reindex_dense(None)
        after = await kb.search("thickness pressure")
        assert result["chunks"] > 0 and after["mode"] == "hybrid"
        assert {s["id"] for s in before["sources"]}.issubset({s["id"] for s in after["sources"]})
    finally:
        kb.close()
        await transport.close()
