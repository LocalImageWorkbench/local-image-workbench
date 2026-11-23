# -*- coding: utf-8 -*-
"""V5.1 LoRA roles: character / pose / style and same-base theme selection."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

ROLES = ("character", "pose", "style", "other")
ROLE_LABELS = {"character": "角色", "pose": "姿势", "style": "风格", "other": "其他"}
GENERIC = {
    "style", "pose", "detail", "skin", "texture", "light", "lighting", "realism",
    "slider", "frame", "expression", "clothing", "outfit", "effect", "anime",
    "portrait", "realistic", "quality", "lora", "sdxl", "xl", "il", "v1", "v2",
    "v3", "v4", "v5", "v6", "krea", "krea2", "qwen", "moss", "anima",
    "illustrious", "noob", "pornmaster", "base", "mix", "xl",
}


def _tokens(text):
    return set(re.findall(r"[a-z]{3,}|[\u4e00-\u9fff]{2,}", str(text).lower()))


def guess_role(item):
    """Heuristic only; the user can always override it in the UI."""
    blob = " ".join(str(item.get(k, "")) for k in ("name", "label", "trigger")).lower()
    words = _tokens(blob)
    if words & {"pose", "position", "action", "姿势", "动作"}:
        return "pose"
    if words & {"style", "artstyle", "artist", "风格", "画风", "水彩", "油画"}:
        return "style"
    if words & {"outfit", "clothing", "dress", "uniform", "服装", "衣服"}:
        return "other"
    if words & GENERIC:
        return "style"
    return "character"


class RoleStore:
    def __init__(self, path):
        self.path = Path(path)
        self._data = {}
        self.load()

    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._data = raw if isinstance(raw, dict) else {}
        except Exception:
            self._data = {}

    def key(self, path):
        try:
            return str(Path(path).resolve()).casefold()
        except Exception:
            return str(path).casefold()

    def role_for(self, item):
        key = self.key(item.get("path", ""))
        rec = self._data.get(key)
        if rec and rec.get("role") in ROLES:
            return rec["role"]
        return guess_role(item)

    def record_for(self, item):
        key = self.key(item.get("path", ""))
        rec = self._data.get(key, {})
        role = rec.get("role") if rec.get("role") in ROLES else guess_role(item)
        return {"role": role, "path": str(item.get("path", "")),
                "base": item.get("base", ""), "trigger": item.get("trigger", "")}

    def set_role(self, item, role):
        if role not in ROLES:
            return
        key = self.key(item.get("path", ""))
        rec = self._data.get(key, {})
        rec.update({"role": role, "path": str(item.get("path", "")),
                    "base": item.get("base", ""), "trigger": item.get("trigger", "")})
        self._data[key] = rec
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)


def same_base(items, base):
    return [x for x in items if str(x.get("base", "")) == str(base)]


def choose_theme(items, store, base=None, pose=True, style=True, rng=None):
    """Pick one character, then same-base pose/style from the supplied LoRAs."""
    rng = rng or random
    records = []
    for item in items:
        rec = store.record_for(item)
        rec["item"] = item
        records.append(rec)
    chars = [r for r in records if r["role"] == "character"]
    if base:
        chars = [r for r in chars if str(r["base"]) == str(base)]
    if not chars:
        return None
    character = rng.choice(chars)
    theme_base = character["base"]
    poses = same_base([r for r in records if r["role"] == "pose"], theme_base)
    styles = same_base([r for r in records if r["role"] == "style"], theme_base)
    return {
        "character": character,
        "pose": rng.choice(poses) if pose and poses else None,
        "style": rng.choice(styles) if style and styles else None,
        "base": theme_base,
    }
