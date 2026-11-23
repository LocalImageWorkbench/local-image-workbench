# -*- coding: utf-8 -*-
"""Prompt Workbench release configuration.

All machine-specific paths live here. Nothing in this module assumes a
particular Windows user or ComfyUI installation.
"""

import json
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
CONFIG_VERSION = 2


def resource_path(relative=""):
    """Path to a bundled resource (works in source and PyInstaller onefile)."""
    base = Path(getattr(sys, "_MEIPASS", APP_ROOT))
    return (base / relative).resolve() if relative else base


def default_data_dir():
    override = os.environ.get("PROMPT_WORKBENCH_DATA")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / "PromptWorkbench"
    return Path.home() / ".config" / "prompt-workbench"


def default_output_dir():
    override = os.environ.get("PROMPT_WORKBENCH_OUTPUT")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Pictures" / "提示词工作台"


DEFAULTS = {
    "config_version": CONFIG_VERSION,
    "llm_type": "ollama",
    "llm_base_url": "http://127.0.0.1:11434",
    "llm_api_key": "",
    "llm_model": "huihui_ai/qwen3.5-abliterated:9b",
    "llm_timeout": 300,
    "llm_idle_unload_minutes": 5,
    "llm_extra_headers": {},
    "close_action": "minimize",
    "llm_extra_body": {},
    "ollama_url": "http://127.0.0.1:11434",
    "comfy_url": "http://127.0.0.1:18188",
    "comfy_start_script": "",
    "comfy_close_script": "",
    "comfy_workflows_dir": "",
    "checkpoint_dir": "",
    "civitai_api_key": "",
    "update_manifest_url": "https://raw.githubusercontent.com/LocalImageWorkbench/local-image-workbench/main/update.json",
    "lora_roots": [],
    "output_dir": str(default_output_dir()),
    "skills_dir": str(resource_path("skills")),
    "tool80_path": "",
    "prompt_library_dir": "",
    "prompt_library_workbench_dir": "",
    "prompt_models": [
        {"label": "9B · Qwen3.5 Abliterated", "id": "huihui_ai/qwen3.5-abliterated:9b"},
        {"label": "27B · Qwen3.8 Abliterated", "id": "qwen3.8:27b-abliterated"},
    ],
    "model_files": {
        "illustrious": {"ckpt_name": "waiIllustriousSDXL_v170.safetensors"},
        "krea2": {
            "unet_name": "krea2_turbo_nvfp4.safetensors",
            "clip_name": "qwen3vl_4b_fp8_scaled.safetensors",
            "vae_name": "qwen_image_vae.safetensors",
        },
        "qwen": {
            "unet_name": "qwen_image_2.1_turbo_int8_convrot.safetensors",
            "clip_name": "qwenImage21TextEncoderOriginal_v10.safetensors",
            "vae_name": "qwen_image_2.1_vae_bf16.safetensors",
        },
        "moss": {
            "unet_name": "moss\\PornMaster_Moss_MIX_V2_int8_convrot.safetensors",
            "clip_name": "qwen3.5_9b_int8_convrot.safetensors",
            "vae_name": "flux2-vae.safetensors",
        },
        "anima": {
            "unet_name": "anima-aesthetic-v1.1.safetensors",
            "clip_name": "qwen_3_06b_base.safetensors",
            "vae_name": "qwen_image_vae.safetensors",
        },
    },
}


class Config:
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.path = self.data_dir / "config.json"
        self.is_new = not self.path.exists()
        self.data = dict(DEFAULTS)
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except Exception:
                # Keep defaults; the settings UI can rewrite a broken file.
                self.is_new = True
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Schema migration: older configs are completed from new defaults.
        self.data["config_version"] = CONFIG_VERSION

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)
        self.is_new = False

    def paths(self, key):
        value = self.data.get(key, [])
        if isinstance(value, str):
            value = [v for v in value.split(";") if v.strip()]
        return [Path(v).expanduser() for v in value if str(v).strip()]


def load_config():
    return Config()


def model_options(cfg):
    out = []
    for item in cfg.get("prompt_models", []):
        if isinstance(item, dict) and item.get("label") and item.get("id"):
            out.append((str(item["label"]), str(item["id"])))
    return out or [("9B · Qwen3.5 Abliterated", "huihui_ai/qwen3.5-abliterated:9b")]
