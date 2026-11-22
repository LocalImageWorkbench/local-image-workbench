# -*- coding: utf-8 -*-
"""Unified LLM client for Ollama and OpenAI-compatible endpoints."""

import json
import urllib.error
import urllib.request

import config as appconfig


def settings(cfg):
    provider = str(cfg.get("llm_type", "ollama")).lower()
    base = str(cfg.get("llm_base_url", "http://127.0.0.1:11434")).rstrip("/")
    key = str(cfg.get("llm_api_key", "") or "")
    model = str(cfg.get("llm_model", "") or "")
    timeout = int(cfg.get("llm_timeout", 300) or 300)
    return provider, base, key, model, timeout


def _endpoint(base, suffix):
    base = base.rstrip("/")
    if base.endswith("/v1"):
        return base + suffix
    return base + "/v1" + suffix


def _headers(key, extra=None):
    out = {"Content-Type": "application/json; charset=utf-8"}
    if key:
        out["Authorization"] = "Bearer " + key
    if isinstance(extra, dict):
        out.update({str(k): str(v) for k, v in extra.items()})
    return out


def _extra_body(cfg):
    value = cfg.get("llm_extra_body", {})
    return value if isinstance(value, dict) else {}


def list_models(cfg):
    provider, base, key, configured_model, timeout = settings(cfg)
    extra_headers = cfg.get("llm_extra_headers", {})
    if not isinstance(extra_headers, dict):
        extra_headers = {}
    if provider == "ollama":
        req = urllib.request.Request(base + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        out = []
        for item in data.get("models", []):
            name = item.get("name", "")
            if not name:
                continue
            caps = []
            try:
                show_req = urllib.request.Request(
                    base + "/api/show",
                    data=json.dumps({"model": name}).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    method="POST")
                with urllib.request.urlopen(show_req, timeout=8) as r:
                    show = json.loads(r.read().decode("utf-8"))
                caps = show.get("capabilities") or []
            except Exception:
                caps = []
            if caps:
                if "completion" not in caps:
                    continue
            elif any(x in name.lower() for x in ("embedding", "embed", "rerank")):
                continue
            out.append({"name": name, "size": item.get("size", 0), "capabilities": caps})
        return out

    # OpenAI-compatible: LM Studio, vLLM, llama.cpp server, OpenAI, OpenRouter...
    req = urllib.request.Request(_endpoint(base, "/models"), headers=_headers(key, extra_headers), method="GET")
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    out = []
    for item in data.get("data", []):
        name = item.get("id")
        if name and not any(x in name.lower() for x in ("embedding", "embed", "rerank")):
            out.append({"name": name, "size": 0, "capabilities": ["completion"]})
    if configured_model and all(x["name"] != configured_model for x in out):
        out.insert(0, {"name": configured_model, "size": 0, "capabilities": ["completion"]})
    return out


def chat(cfg, messages, model=None, temperature=0.6, num_ctx=32768,
         num_predict=2048, keep_alive="10m"):
    provider, base, key, configured_model, timeout = settings(cfg)
    model = model or configured_model
    extra_headers = cfg.get("llm_extra_headers", {})
    if not isinstance(extra_headers, dict):
        extra_headers = {}
    extra_body = _extra_body(cfg)
    if not model:
        raise RuntimeError("未选择 LLM 模型")
    if provider == "ollama":
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": keep_alive,
            "options": {"temperature": temperature, "num_ctx": num_ctx,
                        "num_predict": num_predict},
        }
        payload.update(extra_body)
        req = urllib.request.Request(
            base + "/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=_headers("", extra_headers),
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        text = (data.get("message") or {}).get("content", "")
    else:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": num_predict,
            "stream": False,
        }
        payload.update(extra_body)
        req = urllib.request.Request(
            _endpoint(base, "/chat/completions"),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=_headers(key, extra_headers),
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content", "")
        text = content if isinstance(content, str) else str(content)
    if not str(text).strip():
        raise RuntimeError("模型返回为空")
    return text


def unload(cfg, model):
    provider, base, key, configured_model, timeout = settings(cfg)
    if provider != "ollama":
        return
    payload = {"model": model, "prompt": "", "stream": False, "keep_alive": 0}
    req = urllib.request.Request(
        base + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers=_headers(""),
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()
