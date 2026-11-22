#!/usr/bin/env python3
"""Lightweight structural checks for Anima prompt text files."""

from __future__ import annotations

import re
import sys
from pathlib import Path


FORBIDDEN_NORMAL_FIELDS = (
    "aspect ratio",
    "aspect_ratio",
    "width:",
    "height:",
    "seed:",
    "cfg:",
    "steps:",
    "sampler:",
    "scheduler:",
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_anima_prompt.py <prompt.txt>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()

    problems: list[str] = []
    if "positive prompt" not in lowered and "global prompt" not in lowered and "whole image context" not in lowered:
        problems.append("missing Positive prompt, Global prompt, or Whole image context label")
    if "negative prompt" not in lowered:
        problems.append("missing Negative prompt label")

    for field in FORBIDDEN_NORMAL_FIELDS:
        if field in lowered:
            problems.append(f"normal prompt appears to include generation parameter: {field}")

    if re.search(r"\b(photo|photograph|dslr|realistic photography)\b", lowered) and not re.search(
        r"\b(anime|illustration|cel shading|manga|key visual)\b", lowered
    ):
        problems.append("prompt looks photographic without an Anima/anime illustration anchor")

    if problems:
        print("Anima prompt validation failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("Anima prompt validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
