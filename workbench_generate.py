# -*- coding: utf-8 -*-
"""工作台出图后端：底模校验 + LoRA 过滤 + ComfyUI API + 自动启停。"""

import json
import os
import random
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests

import config as appconfig
import workflow_import as wfimport

CFG = appconfig.load_config()
COMFY = str(CFG.get("comfy_url", "http://127.0.0.1:18188")).rstrip("/")
OUT_DIR = Path(CFG.get("output_dir") or appconfig.default_output_dir())
COMFY_HELPER = str(CFG.get("comfy_start_script") or "")
COMFY_CLOSE = str(CFG.get("comfy_close_script") or "")
MODEL_FILES = CFG.get("model_files") or {}


def _mf(profile, key, fallback):
    value = (MODEL_FILES.get(profile) or {}).get(key)
    return str(value) if value else fallback

WORKFLOWS = {
    "illustrious": {
        "name": "Illustrious · WAI",
        "base": "Illustrious/SDXL",
        "size": (832, 1216),
    },
    "krea2": {
        "name": "Krea2 · Turbo",
        "base": "Krea2",
        "size": (1024, 1024),
    },
    "qwen": {
        "name": "Qwen 2.1 · Turbo",
        "base": "Qwen",
        "size": (1024, 1024),
    },
    "moss": {
        "name": "MOSS · PornMaster",
        "base": "MOSS",
        "size": (800, 1200),
    },
    "anima": {
        "name": "Anima · Aesthetic",
        "base": "Anima",
        "size": (1024, 1024),
    },
}


def workflow_for_target(target):
    t = str(target)
    if t.startswith("MOSS"):
        return "moss"
    if t.startswith("Anima"):
        return "anima"
    if t.startswith("Qwen"):
        return "qwen"
    if t.startswith("Illustrious"):
        return "illustrious"
    if t.startswith("Krea"):
        return "krea2"
    if t.startswith("H3"):
        return "moss"
    return "illustrious"


def base_for_lora(path):
    s = str(path).lower().replace("\\", "/")
    if "krea2" in s:
        return "Krea2"
    if "moss" in s:
        return "MOSS"
    if "qwen" in s or "qi2.1" in s or "qwen2.1" in s:
        return "Qwen"
    if "anima" in s:
        return "Anima"
    if "pony" in s:
        return "Pony"
    if "sd15" in s or "sd1.5" in s:
        return "SD15"
    if "illustrious" in s or "sdxl" in s:
        return "Illustrious/SDXL"
    return "Unknown"


def lora_widget_path(path):
    s = str(path)
    low = s.lower().replace("\\", "/")
    marker = "/models/loras/"
    i = low.find(marker)
    if i >= 0:
        return s.replace("\\", "/")[i + len(marker):].replace("/", "\\")
    return Path(s).name


def compatible_loras(workflow_key, loras):
    base = WORKFLOWS[workflow_key]["base"]
    out, skipped = [], []
    for item in loras:
        path = item.get("path") if isinstance(item, dict) else str(item)
        if base_for_lora(path) == base:
            out.append(item)
        else:
            skipped.append(item)
    return out, skipped


def _ready():
    try:
        return requests.get(COMFY + "/system_stats", timeout=3).ok
    except Exception:
        return False


def comfy_is_up():
    return _ready()


def ensure_comfy():
    if _ready():
        return False
    if not COMFY_HELPER:
        raise RuntimeError(
            "ComfyUI 未运行。请先在环境设置里选择 ComfyUI 启动脚本，或手动启动 ComfyUI。"
        )
    cmd = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
        f". '{COMFY_HELPER}'; Ensure-C8188Engine -Want desktop -WaitSec 240"
    ]
    subprocess.run(cmd, timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(60):
        if _ready():
            return True
        time.sleep(2)
    raise RuntimeError("ComfyUI 启动超时")


def close_comfy():
    if not COMFY_CLOSE:
        return
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", COMFY_CLOSE],
        timeout=90,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def interrupt():
    """Ask ComfyUI to stop the currently executing prompt."""
    try:
        requests.post(COMFY + "/interrupt", timeout=5)
    except Exception:
        pass


def _n(ct, **kw):
    return {"class_type": ct, "inputs": kw}


def build_graph(workflow_key, positive, negative, loras, count=1, width=None, height=None):
    spec = WORKFLOWS[workflow_key]
    count = max(1, min(4, int(count)))
    chosen = []
    for item in loras:
        if isinstance(item, dict) and item.get("enabled", True) is False:
            continue
        path = item.get("path") if isinstance(item, dict) else str(item)
        try:
            strength = float(item.get("strength", 0.7)) if isinstance(item, dict) else 0.7
        except Exception:
            strength = 0.7
        chosen.append((lora_widget_path(path), max(0.0, min(1.2, strength))))
    wf = {}
    next_id = 1

    def add(ct, **kw):
        nonlocal next_id
        nid = str(next_id)
        next_id += 1
        wf[nid] = _n(ct, **kw)
        return nid

    def chain_model(start):
        last = [start, 0]
        for f, strength in chosen:
            nid = add("LoraLoaderModelOnly", model=last, lora_name=f, strength_model=strength)
            last = [nid, 0]
        return last

    if workflow_key == "illustrious":
        ck = add("CheckpointLoaderSimple", ckpt_name=_mf("illustrious", "ckpt_name", "waiIllustriousSDXL_v170.safetensors"))
        model = chain_model(ck)
        clip = [ck, 1]
        vae = [ck, 2]
        steps, cfg, sampler, scheduler = 20, 6.0, "euler_ancestral", "normal"
        latent_cls = "EmptyLatentImage"
    elif workflow_key == "krea2":
        un = add("UNETLoader", unet_name=_mf("krea2", "unet_name", "krea2_turbo_nvfp4.safetensors"), weight_dtype="default")
        model = chain_model(un)
        clip_n = add("CLIPLoader", clip_name=_mf("krea2", "clip_name", "qwen3vl_4b_fp8_scaled.safetensors"), type="krea2", device="default")
        vae_n = add("VAELoader", vae_name=_mf("krea2", "vae_name", "qwen_image_vae.safetensors"))
        clip, vae = [clip_n, 0], [vae_n, 0]
        steps, cfg, sampler, scheduler = 8, 1.0, "euler", "simple"
        latent_cls = "EmptyLatentImage"
    elif workflow_key == "qwen":
        un = add("UNETLoader", unet_name=_mf("qwen", "unet_name", "qwen_image_2.1_turbo_int8_convrot.safetensors"), weight_dtype="default")
        model = chain_model(un)
        ms = add("ModelSamplingAuraFlow", model=model, shift=3.0)
        model = [ms, 0]
        clip_n = add("CLIPLoader", clip_name=_mf("qwen", "clip_name", "qwenImage21TextEncoderOriginal_v10.safetensors"), type="qwen_image", device="default")
        vae_n = add("VAELoader", vae_name=_mf("qwen", "vae_name", "qwen_image_2.1_vae_bf16.safetensors"))
        clip, vae = [clip_n, 0], [vae_n, 0]
        steps, cfg, sampler, scheduler = 8, 2.5, "euler", "simple"
        latent_cls = "EmptySD3LatentImage"
    elif workflow_key == "moss":
        un = add("UNETLoader", unet_name=_mf("moss", "unet_name", "moss\\PornMaster_Moss_MIX_V2_int8_convrot.safetensors"), weight_dtype="default")
        model = chain_model(un)
        ms = add("ModelSamplingAuraFlow", model=model, shift=5.0)
        model = [ms, 0]
        clip_n = add("CLIPLoader", clip_name=_mf("moss", "clip_name", "qwen3.5_9b_int8_convrot.safetensors"), type="moss_image", device="default")
        vae_n = add("VAELoader", vae_name=_mf("moss", "vae_name", "flux2-vae.safetensors"))
        clip, vae = [clip_n, 0], [vae_n, 0]
        steps, cfg, sampler, scheduler = 12, 3.0, "euler", "beta"
        latent_cls = "EmptyLatentImage"
    elif workflow_key == "anima":
        un = add("UNETLoader", unet_name=_mf("anima", "unet_name", "anima-aesthetic-v1.1.safetensors"), weight_dtype="default")
        model = chain_model(un)
        clip_n = add("CLIPLoader", clip_name=_mf("anima", "clip_name", "qwen_3_06b_base.safetensors"), type="stable_diffusion", device="default")
        vae_n = add("VAELoader", vae_name=_mf("anima", "vae_name", "qwen_image_vae.safetensors"))
        clip, vae = [clip_n, 0], [vae_n, 0]
        steps, cfg, sampler, scheduler = 30, 4.0, "er_sde", "simple"
        latent_cls = "EmptyLatentImage"
    else:
        raise ValueError("未知工作流")

    pos = add("CLIPTextEncode", clip=clip, text=positive)
    neg = add("CLIPTextEncode", clip=clip, text=negative)
    w, h = spec["size"]
    if width:
        w = max(256, min(2048, int(width)))
    if height:
        h = max(256, min(2048, int(height)))
    if latent_cls == "EmptySD3LatentImage":
        latent = add("EmptySD3LatentImage", width=w, height=h, batch_size=count)
    else:
        latent = add("EmptyLatentImage", width=w, height=h, batch_size=count)
    seed = random.randint(1, 2**31 - 1)
    if workflow_key == "moss":
        ks = add("KSamplerAdvanced", model=model, positive=[pos, 0], negative=[neg, 0],
                 latent_image=[latent, 0], add_noise="enable", noise_seed=seed,
                 steps=steps, cfg=cfg, sampler_name=sampler, scheduler=scheduler,
                 start_at_step=0, end_at_step=steps, return_with_leftover_noise="disable")
    else:
        ks = add("KSampler", model=model, positive=[pos, 0], negative=[neg, 0],
                 latent_image=[latent, 0], seed=seed, steps=steps, cfg=cfg,
                 sampler_name=sampler, scheduler=scheduler, denoise=1.0)
    dec = add("VAEDecode", samples=[ks, 0], vae=vae)
    add("SaveImage", images=[dec, 0], filename_prefix="workbench")
    add("PreviewImage", images=[dec, 0])
    return wf


def generate(workflow_key, positive, negative, loras, count=1, close_after=True, out_dir=None,
             width=None, height=None):
    if not positive.strip():
        raise ValueError("正向提示词为空")
    started = ensure_comfy()
    wf = build_graph(workflow_key, positive, negative, loras, count, width=width, height=height)
    output_dir = Path(out_dir) if out_dir else OUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.post(COMFY + "/prompt", json={"prompt": wf, "client_id": "workbench"}, timeout=30)
        r.raise_for_status()
        pid = r.json()["prompt_id"]
        hist = None
        for _ in range(240):
            time.sleep(2)
            h = requests.get(COMFY + f"/history/{pid}", timeout=20).json()
            if pid in h:
                hist = h[pid]
                break
        if not hist:
            raise RuntimeError("ComfyUI 超时或未返回结果")
        if hist.get("status", {}).get("status_str") != "success":
            raise RuntimeError("ComfyUI 执行失败：" + json.dumps(hist.get("status", {}), ensure_ascii=False)[:300])
        files = []
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        all_imgs = []
        for _, out in hist.get("outputs", {}).items():
            all_imgs.extend(out.get("images", []))
        # SaveImage 是 output，PreviewImage 是 temp；有 output 时不要重复保存 temp
        images = [im for im in all_imgs if im.get("type") == "output"] or all_imgs
        for im in images:
            q = requests.get(COMFY + "/view", params={
                "filename": im["filename"], "type": im.get("type", "temp"),
                "subfolder": im.get("subfolder", "")
            }, timeout=60)
            if q.ok and q.content[:4] not in (b"<!DO", b"<htm"):
                p = output_dir / f"workbench-{stamp}-{len(files)+1}.png"
                p.write_bytes(q.content)
                files.append(str(p))
        if not files:
            raise RuntimeError("没有拿到图片")
        return {"images": files, "started": started, "closed": False}
    finally:
        if close_after and started:
            try:
                close_comfy()
            except Exception:
                pass


def generate_imported(path, positive, negative, count=1, close_after=True, out_dir=None):
    imp = wfimport.load_workflow(path)
    api = wfimport.prepare(imp, positive, negative, count)
    plan = None
    plan_summary = None
    lora_count = sum(1 for n in api.values() if n.get("class_type") in wfimport.LORA_TYPES)
    if lora_count > 3:
        plan, plan_summary = wfimport.plan_loras(api, positive, negative)
        api = wfimport.apply_lora_plan(api, plan)
    started = ensure_comfy()
    output_dir = Path(out_dir) if out_dir else OUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.post(COMFY + "/prompt", json={"prompt": api, "client_id": "workbench-imported"}, timeout=30)
        r.raise_for_status()
        pid = r.json()["prompt_id"]
        hist = None
        for _ in range(240):
            time.sleep(2)
            h = requests.get(COMFY + f"/history/{pid}", timeout=20).json()
            if pid in h:
                hist = h[pid]
                break
        if not hist:
            raise RuntimeError("ComfyUI 超时或未返回结果")
        if hist.get("status", {}).get("status_str") != "success":
            raise RuntimeError("ComfyUI 执行失败：" + json.dumps(hist.get("status", {}), ensure_ascii=False)[:300])
        files = []
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        all_imgs = []
        for _, out in hist.get("outputs", {}).items():
            all_imgs.extend(out.get("images", []))
        images = [im for im in all_imgs if im.get("type") == "output"] or all_imgs
        for im in images:
            q = requests.get(COMFY + "/view", params={
                "filename": im["filename"], "type": im.get("type", "temp"),
                "subfolder": im.get("subfolder", "")
            }, timeout=60)
            if q.ok and q.content[:4] not in (b"<!DO", b"<htm"):
                p = output_dir / f"imported-{stamp}-{len(files)+1}.png"
                p.write_bytes(q.content)
                files.append(str(p))
        if not files:
            raise RuntimeError("没有拿到图片")
        return {"images": files, "started": started, "closed": False,
                "workflow": imp, "lora_plan": plan, "lora_plan_summary": plan_summary}
    finally:
        if close_after and started:
            try:
                close_comfy()
            except Exception:
                pass
