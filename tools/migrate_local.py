# -*- coding: utf-8 -*-
"""One-off migration from the archived local workbench to the release build."""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=r"D:\prompt-workbench\data")
    args = parser.parse_args()
    src = Path(args.source)
    if not src.exists():
        raise SystemExit(f"source not found: {src}")
    cfg = config.load_config()
    dest = cfg.data_dir
    dest.mkdir(parents=True, exist_ok=True)
    backup = dest / ("migration-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir()
    for name in ("history.json", "settings.json", "imported-workflows.json", "lucifie-trigger-words.json"):
        target = dest / name
        if target.exists():
            shutil.copy2(target, backup / name)

    # Merge UI settings, preserving release-only beginner mode.
    local_settings = load(src / "settings.json", {})
    release_settings = load(dest / "settings.json", {})
    if isinstance(local_settings, dict):
        for key in ("model", "model_id", "target", "generation_workflow", "mode", "nsfw",
                    "output_dir", "auto_pick"):
            if key in local_settings:
                release_settings[key] = local_settings[key]
    release_settings.setdefault("beginner_mode", True)
    (dest / "settings.json").write_text(
        json.dumps(release_settings, ensure_ascii=False, indent=2), encoding="utf-8")

    # Merge history by id, newest first.
    local_history = load(src / "history.json", [])
    release_history = load(dest / "history.json", [])
    if not isinstance(local_history, list):
        local_history = []
    if not isinstance(release_history, list):
        release_history = []
    merged = {}
    for rec in release_history + local_history:
        if isinstance(rec, dict) and rec.get("id") is not None:
            merged[rec["id"]] = rec
    history = sorted(merged.values(), key=lambda x: x.get("id", 0), reverse=True)
    (dest / "history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    # Merge imported workflow registrations by path.
    local_wf = load(src / "imported-workflows.json", [])
    release_wf = load(dest / "imported-workflows.json", [])
    if not isinstance(local_wf, list):
        local_wf = []
    if not isinstance(release_wf, list):
        release_wf = []
    workflows = {}
    for item in release_wf + local_wf:
        if isinstance(item, dict) and item.get("path"):
            workflows[item["path"]] = item
    (dest / "imported-workflows.json").write_text(
        json.dumps(list(workflows.values()), ensure_ascii=False, indent=2), encoding="utf-8")

    trigger_src = src / "lucifie-trigger-words.json"
    if trigger_src.exists():
        shutil.copy2(trigger_src, dest / "lucifie-trigger-words.json")

    print("迁移完成")
    print("来源：", src)
    print("目标：", dest)
    print("备份：", backup)
    print("历史条数：", len(history))
    print("导入工作流：", len(workflows))


if __name__ == "__main__":
    main()
