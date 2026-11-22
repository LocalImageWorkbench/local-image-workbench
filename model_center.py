# -*- coding: utf-8 -*-
"""Civitai search and guarded download helpers for the model center."""

import hashlib
import os
import re
from pathlib import Path

import requests

CIVITAI_API = "https://civitai.com/api/v1/models"


def _headers(api_key=""):
    headers = {"User-Agent": "PromptWorkbench/0.1 (+https://github.com/)"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    return headers


def _version_for(item, base=""):
    versions = item.get("modelVersions") or []
    if base:
        for version in versions:
            if str(version.get("baseModel", "")).lower() == base.lower():
                return version
    return versions[0] if versions else {}


def _pick_file(version):
    files = version.get("files") or []
    for f in files:
        if f.get("type") == "Model" and str(f.get("name", "")).lower().endswith(".safetensors"):
            return f
    for f in files:
        if f.get("type") == "Model":
            return f
    return files[0] if files else {}


def search_civitai(query, kind="lora", base="", api_key="", limit=12):
    """Return normalized model records. kind: lora or checkpoint."""
    query = str(query or "").strip()
    if not query:
        raise ValueError("搜索词为空")
    params = {
        "query": query,
        "limit": max(1, min(30, int(limit))),
        "types": "LORA" if str(kind).lower() == "lora" else "Checkpoint",
        "sort": "Most Downloaded",
        "period": "AllTime",
        "nsfw": "true",
    }
    if base and base != "全部":
        params["baseModels"] = base
    res = requests.get(CIVITAI_API, params=params, headers=_headers(api_key), timeout=25)
    res.raise_for_status()
    data = res.json()
    out = []
    for item in data.get("items", []):
        version = _version_for(item, "" if base == "全部" else base)
        if not version:
            continue
        file_info = _pick_file(version)
        out.append({
            "id": item.get("id"),
            "name": item.get("name") or "",
            "type": item.get("type") or "",
            "nsfw": bool(item.get("nsfw")),
            "creator": (item.get("creator") or {}).get("username", ""),
            "base": version.get("baseModel", ""),
            "version_name": version.get("name", ""),
            "version_id": version.get("id"),
            "download_url": file_info.get("downloadUrl") or version.get("downloadUrl") or "",
            "file_name": file_info.get("name") or f"{item.get('name','model')}.safetensors",
            "size_kb": float(file_info.get("sizeKB") or 0),
            "sha256": ((file_info.get("hashes") or {}).get("SHA256") or "").lower(),
            "page_url": f"https://civitai.com/models/{item.get('id')}",
            "trained_words": version.get("trainedWords") or [],
            "downloads": (item.get("stats") or {}).get("downloadCount", 0),
        })
    return out


def safe_filename(name):
    name = Path(str(name)).name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name or "model.safetensors"


def comfy_models_root(cfg):
    for root in cfg.paths("lora_roots"):
        if root.name.lower() in ("loras", "lora"):
            return root.parent
        return root.parent
    checkpoint = cfg.get("checkpoint_dir")
    if checkpoint:
        p = Path(checkpoint).expanduser()
        return p.parent if p.name.lower() == "checkpoints" else p
    return None


def find_model_file(cfg, role, filename):
    if not filename:
        return None
    rel = Path(str(filename).replace("\\", "/"))
    models = comfy_models_root(cfg)
    candidates = []
    if role == "checkpoint":
        cp = cfg.get("checkpoint_dir")
        if cp:
            candidates.append(Path(cp).expanduser() / rel)
        if models:
            candidates.append(models / "checkpoints" / rel)
    elif role == "unet":
        if models:
            candidates += [models / "diffusion_models" / rel, models / "unet" / rel,
                           models / "checkpoints" / rel]
    elif role == "clip":
        if models:
            candidates += [models / "text_encoders" / rel, models / "clip" / rel]
    elif role == "vae":
        if models:
            candidates.append(models / "vae" / rel)
    return next((p for p in candidates if p.exists()), None)


def missing_profile_files(cfg, profile, model_files):
    files = model_files.get(profile) or {}
    if profile == "illustrious":
        required = [("checkpoint", "ckpt_name")]
    else:
        required = [("unet", "unet_name"), ("clip", "clip_name"), ("vae", "vae_name")]
    missing = []
    for role, key in required:
        filename = files.get(key)
        if not filename or not find_model_file(cfg, role, filename):
            missing.append({"role": role, "key": key, "filename": filename or "(未配置)"})
    return missing


def destination_dir(cfg, kind):
    if str(kind).lower() == "lora":
        roots = cfg.paths("lora_roots")
        if not roots:
            raise ValueError("还没有配置 LoRA 根目录")
        return roots[0]
    configured = cfg.get("checkpoint_dir")
    if configured:
        path = Path(configured).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    roots = cfg.paths("lora_roots")
    if roots:
        candidate = roots[0].parent.parent / "checkpoints"
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    raise ValueError("还没有配置底模目录（checkpoint_dir）")


def download_model(record, cfg, progress=None, cancel=None):
    """Download one record to the configured model folder. Caller must confirm first.

    An interrupted download leaves a .part file; the next attempt resumes with
    an HTTP Range request when the server supports it.
    """
    url = str(record.get("download_url") or "")
    if not url:
        raise ValueError("该版本没有可用下载地址")
    kind = "lora" if str(record.get("type", "")).lower() == "lora" else "checkpoint"
    dest_dir = destination_dir(cfg, kind)
    filename = safe_filename(record.get("file_name") or "model.safetensors")
    if not filename.lower().endswith(".safetensors"):
        filename += ".safetensors"
    target = dest_dir / filename
    temp = target.with_suffix(target.suffix + ".part")
    api_key = str(cfg.get("civitai_api_key", "") or "")
    headers = _headers(api_key)
    if api_key:
        url = url + ("&" if "?" in url else "?") + "token=" + api_key
    existing = temp.stat().st_size if temp.exists() else 0
    if existing:
        headers["Range"] = f"bytes={existing}-"
    digest = hashlib.sha256()
    if existing:
        with temp.open("rb") as old:
            for chunk in iter(lambda: old.read(1024 * 1024), b""):
                digest.update(chunk)
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        if existing and r.status_code == 416:
            # Already complete; validate and promote.
            expected = str(record.get("sha256") or "").lower()
            if expected and digest.hexdigest() != expected:
                temp.unlink(missing_ok=True)
                raise RuntimeError("SHA256 校验失败，文件已删除")
            os.replace(temp, target)
            return target
        r.raise_for_status()
        append = bool(existing and r.status_code == 206)
        remaining = int(r.headers.get("Content-Length") or 0)
        total = remaining + existing if append else remaining
        done = existing if append else 0
        mode = "ab" if append else "wb"
        if not append:
            digest = hashlib.sha256()
        with temp.open(mode) as out:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if cancel and cancel.is_set():
                    raise RuntimeError("已取消；下次会尝试续传")
                if not chunk:
                    continue
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    expected = str(record.get("sha256") or "").lower()
    if expected and digest.hexdigest() != expected:
        temp.unlink(missing_ok=True)
        raise RuntimeError("SHA256 校验失败，文件已删除")
    os.replace(temp, target)
    return target

