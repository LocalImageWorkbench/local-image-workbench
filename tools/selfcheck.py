# -*- coding: utf-8 -*-
"""Small environment self-check for the release build."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import llm_client


def main():
    cfg = config.load_config()
    print("配置目录：", cfg.path)
    print("LLM 类型：", cfg.get("llm_type"))
    print("LLM 地址：", cfg.get("llm_base_url"))
    print("ComfyUI：", cfg.get("comfy_url"))
    print("输出目录：", cfg.get("output_dir"))
    print()
    failed = 0
    try:
        models = llm_client.list_models(cfg)
        print(f"LLM 连接：OK，{len(models)} 个模型")
    except Exception as e:
        failed += 1
        print("LLM 连接：失败", str(e)[:120])
    try:
        import urllib.request
        with urllib.request.urlopen(str(cfg.get("comfy_url")).rstrip("/") + "/system_stats", timeout=5) as r:
            print("ComfyUI 连接：OK" if r.status < 500 else f"ComfyUI HTTP {r.status}")
    except Exception as e:
        failed += 1
        print("ComfyUI 连接：失败", str(e)[:120])
    roots = cfg.paths("lora_roots")
    if roots:
        for root in roots:
            print(f"LoRA 根目录：{'OK' if root.exists() else '缺失'}  {root}")
    else:
        print("LoRA 根目录：未配置（可以无 LoRA 出图）")
    skills = Path(cfg.get("skills_dir") or "")
    print(f"skills：{'OK' if skills.exists() else '缺失'}  {skills}")
    print()
    print("自检完成；失败项需要到环境设置里补齐。" if failed else "自检完成，基础连接正常。")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
