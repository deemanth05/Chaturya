"""Run natively on the inference Mac, outside Docker. Checkpoints must be local."""
import asyncio
import os
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
lock = asyncio.Lock()
agent = None


class Decision(BaseModel):
    model: str = "laya"
    state: str = Field(max_length=1200)
    questions: dict


@app.post("/v1/systemone")
async def predict(body: Decision):
    if body.model != "laya" or len(body.questions) > 5:
        raise HTTPException(400, "Unsupported model or too many questions")
    async with lock:
        global agent
        if agent is None:
            path = Path(os.environ.get("LAYA_MODEL_PATH", "./models/laya"))
            if not path.is_dir():
                raise HTTPException(503, "Prepare a local Laya MLX checkpoint and set LAYA_MODEL_PATH")
            import laya_mlx as laya
            agent = await asyncio.to_thread(laya.load, str(path))
        return await asyncio.to_thread(agent.predict, body.state, body.questions)


if __name__ == "__main__":
    import uvicorn
    # Bind loopback by default. Configure a LAN binding and firewall explicitly when remote.
    uvicorn.run(app, host=os.getenv("LAYA_HOST", "127.0.0.1"), port=int(os.getenv("LAYA_PORT", "1235")))

