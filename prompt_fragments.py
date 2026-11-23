# -*- coding: utf-8 -*-
"""Prompt fragment helpers: split/join comma-separated prompt pieces."""

from __future__ import annotations

import re

_SPLIT = re.compile(r"[，,；;\n\r]+")


def split_fragments(text):
    """Return non-empty trimmed fragments, keeping order."""
    return [x.strip() for x in _SPLIT.split(str(text or "")) if x.strip()]


def join_fragments(fragments):
    return "，".join(str(x).strip() for x in fragments if str(x).strip())


def replace_fragment(fragments, index, value):
    value = str(value).strip()
    if not value:
        raise ValueError("片段不能为空")
    if _SPLIT.search(value):
        raise ValueError("单个片段里不要再包含逗号或换行")
    out = list(fragments)
    if index < 0 or index >= len(out):
        raise IndexError("片段索引越界")
    out[index] = value
    return out


def delete_fragment(fragments, index):
    out = list(fragments)
    if index < 0 or index >= len(out):
        raise IndexError("片段索引越界")
    out.pop(index)
    return out


def add_fragment(fragments, value):
    value = str(value).strip()
    if not value:
        raise ValueError("片段不能为空")
    if _SPLIT.search(value):
        raise ValueError("单个片段里不要再包含逗号或换行")
    out = list(fragments)
    out.append(value)
    return out
