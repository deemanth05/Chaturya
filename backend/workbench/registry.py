import re
import os
from pathlib import Path

import yaml

from .network import origin


class Registry:
    def __init__(self, path: Path):
        self.config = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.models = self.config["models"]
        if len({m["id"] for m in self.models}) != len(self.models):
            raise ValueError("Duplicate model IDs")
        allowed = {origin(x) for x in self.config["network"]["allowed_origins"]}
        for model in self.models:
            if model.get("enabled") and origin(model["base_url"]) not in allowed:
                raise ValueError(f"Model {model['id']} points outside allowed origins")
            if model.get("reasoning_effort") is not None and model["reasoning_effort"] not in {"none", "minimal", "low", "medium", "high", "xhigh"}:
                raise ValueError("Unsupported reasoning_effort in model registry")

    def select(self, task, image=False):
        modality = "image" if image else "embedding" if task == "embedding" else "text"
        eligible = [m for m in self.models if m.get("enabled") and modality in m["modalities"]]
        if not eligible:
            raise ValueError(f"No enabled model supports {modality}; add one to config/registry.yaml")
        ranked = sorted(eligible, key=lambda m: m.get("strengths", {}).get(task, 0), reverse=True)
        return ranked[0], [{"model": m["id"], "score": m.get("strengths", {}).get(task, 0)} for m in ranked]

    @staticmethod
    def headers(model):
        key = os.getenv(model.get("api_key_env", "WORKBENCH_LM_STUDIO_API_KEY"), "")
        return {"Authorization": "Bearer " + key} if key else {}

    async def route(self, text, transport, job_id, task=None, image=False):
        reason, probabilities, method = "Explicit workflow step", None, "rules"
        if task is None:
            if image:
                task, reason = "extraction", "Image or scanned document requires image input"
            elif re.search(r"\b(code|python|script|debug|test)\b", text, re.I):
                task, reason = "code", "Request contains a code task"
            elif re.search(r"\b(transcribe|ocr|scan)\b", text, re.I):
                task, reason = "extraction", "Request requires document transcription"
            elif re.search(r"\b(letter|notice|lesson|quiz|draft)\b", text, re.I):
                task, reason = "writing", "Request requires an academic or administrative draft"
            else:
                cfg = self.config.get("router", {})
                if cfg.get("laya_url"):
                    try:
                        response = await transport.request("POST", cfg["laya_url"], body={"model": cfg.get("laya_model", "laya"),
                            "state": text[:900], "questions": {"task": {"type": "choice", "instructions": "Choose the workbench task",
                            "criteria": {"extraction": "Transcribe a document", "code": "Write or fix Python code",
                                         "writing": "Draft college correspondence or teaching material", "reasoning": "Explain or analyze evidence"}}}}, job_id=job_id)
                        answer = response["answers"]["task"]
                        probabilities = answer["probabilities"]
                        winner = max(probabilities, key=probabilities.get)
                        if winner not in {"extraction", "code", "writing", "reasoning"}:
                            raise ValueError("Unexpected Laya choice")
                        task = winner if probabilities[winner] >= cfg.get("minimum_probability", .75) else "reasoning"
                        method, reason = "laya", "Laya typed decision" if task == winner else "Low Laya probability; reasoning fallback"
                    except Exception as exc:
                        task, method, reason = "reasoning", "fallback", f"Laya unavailable ({type(exc).__name__}); registry reasoning fallback"
                else:
                    task, method, reason = "reasoning", "registry", "No matching rule; Laya is not configured"
        model, scores = self.select(task, image)
        trace = {"task": task, "model": model["id"], "method": method, "reason": reason,
                 "probabilities": probabilities, "registry_scores": scores,
                 "reasoning_effort": model.get("reasoning_effort", "server_default"),
                 "capabilities_verified": model.get("capabilities_verified", False)}
        transport.store.event("router.selected", trace, job_id)
        return model, trace

    async def chat(self, transport, model, messages, job_id, *, json_output=False, schema=None):
        body = {"model": model["id"], "messages": messages, "temperature": 0,
                "max_tokens": model.get("max_output_tokens", 3000), "stream": False}
        if model.get("reasoning_effort") is not None:
            body["reasoning_effort"] = model["reasoning_effort"]
        if json_output:
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "workbench_result", "strict": True,
                "schema": schema or {"type": "object"}}}
        result = await transport.request("POST", model["base_url"].rstrip("/") + "/chat/completions", body=body, job_id=job_id, headers=self.headers(model))
        usage = result.get("usage", {})
        transport.store.event("model.completed", {"model": model["id"],
            "usage": {key: usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens") if key in usage},
            "finish_reason": result["choices"][0].get("finish_reason")}, job_id)
        if result["choices"][0].get("finish_reason") == "length":
            raise ValueError("Model output reached the token limit; shorten the request or raise this model's max_output_tokens in the registry")
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Model returned no text content")
        return content
