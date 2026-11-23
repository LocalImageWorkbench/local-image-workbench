# -*- coding: utf-8 -*-
"""V5 random prompt library: curated prompts + template combinations."""

from __future__ import annotations

import copy
import json
import random
import re
from pathlib import Path

MODES = ("混合", "精选", "模板")
MIXED = "混合"
MAX_PROMPTS = 5000
MAX_CATEGORY_NAME = 32
PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


class LibraryError(ValueError):
    pass


def default_library(categories, styles=None, templates=None):
    """Build a normalized library from the app's built-in constants."""
    styles = styles or {}
    out = {"version": 1, "categories": {}, "templates": {}}
    for name, prompts in categories.items():
        out["categories"][name] = {
            "style": styles.get(name, "写实"),
            "prompts": list(prompts),
        }
    for name, tpl in (templates or {}).items():
        out["templates"][name] = copy.deepcopy(tpl)
    return normalize(out)


def normalize(data):
    if not isinstance(data, dict):
        raise LibraryError("随机库必须是 JSON 对象")
    categories = data.get("categories")
    templates = data.get("templates", {})
    if not isinstance(categories, dict) or not categories:
        raise LibraryError("缺少 categories，或分类为空")
    if not isinstance(templates, dict):
        raise LibraryError("templates 必须是对象")

    out = {"version": 1, "categories": {}, "templates": {}}
    total = 0
    for raw_name, raw in categories.items():
        name = str(raw_name).strip()
        if not name or len(name) > MAX_CATEGORY_NAME:
            raise LibraryError("分类名不能为空且不超过 32 字符")
        if isinstance(raw, list):
            raw = {"prompts": raw}
        if not isinstance(raw, dict):
            raise LibraryError(f"分类“{name}”格式错误")
        prompts = []
        for item in raw.get("prompts", []):
            if not isinstance(item, str):
                continue
            item = item.strip()
            if not item:
                continue
            prompts.append(item)
        if not prompts:
            raise LibraryError(f"分类“{name}”没有有效提示词")
        total += len(prompts)
        if total > MAX_PROMPTS:
            raise LibraryError(f"提示词总数超过 {MAX_PROMPTS}")
        out["categories"][name] = {
            "style": str(raw.get("style") or "写实").strip() or "写实",
            "prompts": prompts,
        }

    for raw_name, raw in templates.items():
        name = str(raw_name).strip()
        if name not in out["categories"]:
            continue
        if not isinstance(raw, dict):
            continue
        fmt = str(raw.get("format") or "").strip()
        parts = raw.get("parts")
        if not fmt or not isinstance(parts, dict):
            continue
        clean_parts = {}
        for key, values in parts.items():
            if not isinstance(values, list):
                continue
            vals = [str(v).strip() for v in values if str(v).strip()]
            if vals:
                clean_parts[str(key)] = vals
        if not clean_parts:
            continue
        needed = set(PLACEHOLDER.findall(fmt))
        if not needed or not needed.issubset(clean_parts.keys()):
            continue
        out["templates"][name] = {
            "style": str(raw.get("style") or out["categories"][name]["style"]).strip(),
            "format": fmt,
            "parts": clean_parts,
        }
    if not out["categories"]:
        raise LibraryError("没有可用分类")
    return out


def load_user(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        raise LibraryError(f"无法读取随机库：{e}")
    return normalize(data)


def save_user(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(normalize(data), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _categories(data, category):
    cats = data["categories"]
    if category in cats:
        return [(category, cats[category])]
    return list(cats.items())


def _template_text(template, rng):
    values = {key: rng.choice(vals) for key, vals in template["parts"].items()}
    try:
        return template["format"].format(**values)
    except Exception:
        return ""


def pick(data, category=MIXED, mode="混合", rng=None):
    rng = rng or random
    data = normalize(data) if "version" not in data else data
    choices = _categories(data, category)
    if not choices:
        raise LibraryError("没有可用分类")
    if category == MIXED:
        name, cat = rng.choice(choices)
    else:
        name, cat = choices[0]

    template = data.get("templates", {}).get(name)
    use_template = template is not None and mode in ("模板", "混合")
    if mode == "混合" and template is not None:
        use_template = rng.random() < 0.5
    if use_template:
        text = _template_text(template, rng)
        if text:
            return {"text": text, "category": name,
                    "style": template.get("style") or cat.get("style", "写实"),
                    "mode": "模板"}
    return {"text": rng.choice(cat["prompts"]), "category": name,
            "style": cat.get("style", "写实"), "mode": "精选"}
