# -*- coding: utf-8 -*-
"""本地出图工作台 — 本地 9B/27B 提示词生成、编辑、历史与 8.0 精修入口。"""

import json
import os
import queue
import random
import re
import struct
import subprocess
import sys
import platform
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import ctypes
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinter.scrolledtext import ScrolledText

import workbench_generate as wbgen
import workflow_import as wfimport
import lora_match
import config as appconfig
import llm_client
import model_guide
import model_center

APP_NAME = "本地出图工作台"
DISPLAY_TAGLINE = "提示词工作台 · 快捷本地出图"
CFG = appconfig.load_config()
APP_DIR = appconfig.resource_path("")
try:
    APP_VERSION = (APP_DIR / "VERSION").read_text(encoding="utf-8").strip()
except Exception:
    APP_VERSION = "0.2.0-beta"
DEFAULT_UPDATE_MANIFEST = (
    "https://raw.githubusercontent.com/wangzimu2007/local-image-workbench/main/update.json"
)
DATA_DIR = Path(CFG.data_dir)
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
APP_LOG = logging.getLogger("prompt_workbench")
APP_LOG.setLevel(logging.INFO)
if not APP_LOG.handlers:
    _log_handler = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=2 * 1024 * 1024,
                                      backupCount=3, encoding="utf-8")
    _log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    APP_LOG.addHandler(_log_handler)
HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
IMPORTED_WORKFLOWS_FILE = DATA_DIR / "imported-workflows.json"
PROMPT_LIBRARY = Path(CFG.get("prompt_library_dir") or (DATA_DIR / "prompt-library"))
WORKBENCH_LIBRARY = PROMPT_LIBRARY / "工作台"
TOOL80 = Path(CFG.get("tool80_path")).expanduser() if CFG.get("tool80_path") else None
APP_ICON = APP_DIR / "prompt-workbench.ico"
ICON_DIR = APP_DIR / "assets" / "icons"
CIVITAI_GUIDE_STEPS = [
    (APP_DIR / "assets" / "civitai-guide" / "step1-full.png",
     "① 点右上角眼睛，打开 Browsing Level 菜单",
     "最上面是完整页头，红框为右上角区域；中间放大眼睛；下面是官方菜单，红框为 Browsing Level。"),
    (APP_DIR / "assets" / "civitai-guide" / "step2-full.png",
     "② 打开 Show mature content，并勾选需要的分级",
     "上半张是右上角眼睛放大；下半张是官方菜单原图，红框是分级和 Blur。"),
    (APP_DIR / "assets" / "civitai-guide" / "step3-full.png",
     "③ Account Settings → Content Moderation",
     "官方账号设置原图，红框是 Show mature content 开关；不要模糊就关闭 Blur。"),
]
SKILLS = Path(CFG.get("skills_dir") or appconfig.resource_path("skills"))
OLLAMA = str(CFG.get("ollama_url", "http://127.0.0.1:11434")).rstrip("/")
LORA_ROOTS = CFG.paths("lora_roots")
KNOWN_TRIGGERS_FILE = DATA_DIR / "lucifie-trigger-words.json"
EMPTY_WORKFLOW_LABEL = "空工作流 · 不预置 LoRA"
BEGINNER_BASES = [
    {"key": "illustrious", "icon": "✦", "label": "Illustrious", "target": "Illustrious / SDXL（tag）",
     "workflow": "illustrious", "note": "二次元通用；NSFW 加同底模 LoRA"},
    {"key": "moss", "icon": "●", "label": "MOSS", "target": "MOSS Image（PornMaster Skill）",
     "workflow": "moss", "note": "成人向 MOSS/PornMaster"},
    {"key": "krea2", "icon": "▣", "label": "Krea2", "target": "Krea 2（自然语言）",
     "workflow": "krea2", "note": "摄影感；NSFW 需测试"},
    {"key": "qwen", "icon": "◐", "label": "Qwen 2.1", "target": "Qwen-Image 2.1（自然语言）",
     "workflow": "qwen", "note": "通用/写实；NSFW 不保证"},
    {"key": "anima", "icon": "✿", "label": "Anima", "target": "Anima（Danbooru tag）",
     "workflow": "anima", "note": "二次元；NSFW 需适配 LoRA"},
]
STYLE_BASE_RECOMMENDATIONS = {
    "无风格": ("illustrious", "通用默认"),
    "二次元": ("illustrious", "二次元生态最稳"),
    "插画": ("illustrious", "插画和 tag 系更匹配"),
    "水彩": ("illustrious", "浅色和柔和质感"),
    "电影感": ("krea2", "摄影感更强"),
    "写实": ("qwen", "通用写实更稳"),
    "赛博朋克": ("krea2", "霓虹和电影光效"),
}
NSFW_STYLE_BASE_RECOMMENDATIONS = {
    "写实": ("moss", "成人写实更直接"),
    "电影感": ("moss", "成人电影感更稳"),
    "赛博朋克": ("moss", "成人夜景和光效"),
    "二次元": ("illustrious", "加匹配 NSFW LoRA"),
    "插画": ("illustrious", "加匹配 NSFW LoRA"),
    "水彩": ("illustrious", "加匹配 NSFW LoRA"),
    "无风格": ("moss", "成人向默认"),
}
BASE_VRAM_REQUIREMENTS = {
    "illustrious": 12_000,
    "anima": 8_000,
    "krea2": 18_000,
    "qwen": 18_000,
    "moss": 22_000,
}
BEGINNER_RATIOS = {
    "竖图": (832, 1216),
    "方图": (1024, 1024),
    "横图": (1216, 832),
}
BEGINNER_INSPIRATION = {
    "随机": [
        "银发成年女性，雨夜霓虹街头，黑色风衣，温柔地看着镜头，电影感人像",
        "成年男性，白色衬衫，海边黄昏，侧脸逆光，安静的氛围感照片",
        "成年女性，白色长裙，森林晨雾，回眸微笑，柔和的自然光",
        "银发成年女性，未来城市天台，机械耳机，俯瞰城市灯光，赛博朋克插画",
    ],
    "人物": [
        "银发成年女性，神情温柔，五官清晰",
        "成年男性，短发，眼神坚定，自然肤质",
        "成年女性，长发扎起，侧脸，微笑着看向远处",
    ],
    "服装": [
        "黑色长款风衣",
        "白色针织衫和深色长裙",
        "复古西装，领口微敞",
        "轻薄的夏日连衣裙",
    ],
    "场景": [
        "雨夜霓虹街头",
        "安静的海边黄昏",
        "森林晨雾中的木屋",
        "未来城市的高层天台",
    ],
    "光线": [
        "电影感侧逆光",
        "柔和的窗边自然光",
        "霓虹灯与雨水反射",
        "黄昏暖色轮廓光",
    ],
}
CIVITAI_BASE_LABELS = {
    "illustrious": "Illustrious",
    "moss": "MOSS",
    "krea2": "Krea 2",
    "qwen": "Qwen",
    "anima": "Anima",
}


def detect_comfy_installations():
    """Best-effort scan for common ComfyUI roots without recursive crawling."""
    candidates = []
    env = os.environ.get("COMFYUI_DIR")
    if env:
        candidates.append(Path(env).expanduser())
    home = Path.home()
    candidates += [home / "ComfyUI", home / "Desktop" / "ComfyUI"]
    for drive in ("C:/", "D:/", "E:/"):
        candidates += [Path(drive) / "ComfyUI", Path(drive) / "ComfyUI" / "ComfyUI"]
    candidates += [Path("D:/ComfyUI-aki-v3.2/ComfyUI"), Path("D:/ComfyUI-aki-v3.2")]
    installs = Path("D:/Comfy-Desktop/ComfyUI-Installs")
    if installs.exists():
        try:
            candidates += [p / "ComfyUI" for p in installs.iterdir() if p.is_dir()]
        except Exception:
            pass
    out = []
    seen = set()
    for root in candidates:
        try:
            root = root.resolve()
            if root in seen:
                continue
            seen.add(root)
            loras = root / "models" / "loras"
            if not loras.exists():
                continue
            out.append({
                "root": str(root),
                "loras": str(loras),
                "checkpoints": str(root / "models" / "checkpoints"),
                "workflows": str(root / "user" / "default" / "workflows"),
                "start": str(root / "run_nvidia_gpu.bat")
                if (root / "run_nvidia_gpu.bat").exists() else "",
            })
        except Exception:
            continue
    def _mtime(item):
        try:
            return Path(item["loras"]).stat().st_mtime
        except Exception:
            return 0
    out.sort(key=_mtime, reverse=True)
    return out


def detect_gpu_memory():
    """Return (gpu name, total VRAM MiB). Unknown VRAM returns 0."""
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, creationflags=flags)
        if proc.returncode == 0:
            line = (proc.stdout or "").strip().splitlines()[0]
            name, mb = line.rsplit(",", 1)
            return name.strip(), int(float(mb.strip()))
    except Exception:
        pass
    # AMD/Intel: identify the adapter; VRAM is intentionally not guessed.
    if os.name == "nt":
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            ps = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_VideoController | "
                 "Where-Object {$_.Name -notmatch 'Microsoft|Remote|Basic'} | "
                 "Select-Object -First 1 -ExpandProperty Name"],
                capture_output=True, text=True, timeout=5, creationflags=flags)
            name = (ps.stdout or "").strip().splitlines()
            if name:
                return name[0].strip(), 0
        except Exception:
            pass
    return "", 0

BASE_FILTERS = ["全部", "Illustrious/SDXL", "SD15", "Pony", "Anima", "MOSS", "Krea2", "Qwen", "FLUX", "Wan/H3", "未识别"]

TARGET_LORA_FILTER = {
    "MOSS Image（自然语言）": "MOSS",
    "MOSS Image（PornMaster Skill）": "MOSS",
    "MOSS 布局 / 分镜": "MOSS",
    "Anima（Danbooru tag）": "Anima",
    "Qwen-Image 2.1（自然语言）": "Qwen",
    "H3（视频结构化）": "Wan/H3",
    "Illustrious / SDXL（tag）": "Illustrious/SDXL",
    "Krea 2（自然语言）": "Krea2",
}

BASE_TARGET = {
    "MOSS": "MOSS Image（PornMaster Skill）",
    "Anima": "Anima（Danbooru tag）",
    "Qwen": "Qwen-Image 2.1（自然语言）",
    "Wan/H3": "H3（视频结构化）",
    "Illustrious/SDXL": "Illustrious / SDXL（tag）",
    "Krea2": "Krea 2（自然语言）",
}

BASE_WORKFLOW = {
    "MOSS": "moss",
    "Anima": "anima",
    "Qwen": "qwen",
    "Illustrious/SDXL": "illustrious",
    "Krea2": "krea2",
}

MODEL_OPTIONS = appconfig.model_options(CFG)

TARGETS = {
    "MOSS Image（自然语言）": {
        "skill": "moss-anime-prompt/SKILL.md",
        "extra": None,
        "desc": "MOSS Image：自然语言为主，强调人物、服装、姿势、场景和质感。",
        "format": "用完整的自然语言描述，最后可附少量关键英文 tag。不要只堆 Danbooru 标签。",
    },
    "MOSS Image（PornMaster Skill）": {
        "skill": "pornmaster-moss-prompt/SKILL.md",
        "extra": None,
        "desc": "MOSS Image + 作者 PornMaster Skill：Caption / Tag / Layout，按官方 MOSS 规范。",
        "format": "普通场景优先连贯英文 caption；需要精确文字/物体位置时输出 Layout JSON；不要堆无意义质量词。",
    },
    "MOSS 布局 / 分镜": {
        "skill": "moss-image-prompt-skill/SKILL.md",
        "extra": "moss-image-prompt-skill/references/layout-from-enhancer.md",
        "desc": "MOSS Layout：Caption / Layout / bbox / 图内文字，适合多人物和分镜。",
        "format": "输出结构化的 Layout 描述；必要时包含 bbox 和文字位置说明。",
    },
    "Anima（Danbooru tag）": {
        "skill": "anima-prompt-crafter-skill/SKILL.md",
        "extra": None,
        "desc": "Anima：Danbooru tags、角色特征、画风 tag，适合二次元。",
        "format": "Positive 用逗号分隔的 Danbooru tags；Negative 用质量/结构负词。",
    },
    "Qwen-Image 2.1（自然语言）": {
        "skill": "qwen-image-2-1-prompter/SKILL.md",
        "extra": None,
        "desc": "Qwen-Image：自然语言长描述，少用纯 tag 堆叠。",
        "format": "用自然语言完整描述主体、动作、服装、环境、光线和镜头。",
    },
    "H3（视频结构化）": {
        "skill": "h3-prompt-writing/SKILL.md",
        "extra": "h3-prompt-writing/references/base-en.txt",
        "desc": "MiniMax H3：镜头、时间轴、动作、声音和参考素材的结构化视频提示词。",
        "format": "按 H3 的结构输出；Positive 可以包含分段/时间轴/声音描述。",
    },
    "Illustrious / SDXL（tag）": {
        "skill": "anima-prompt-crafter-skill/SKILL.md",
        "extra": None,
        "desc": "Illustrious / SDXL：Danbooru tag、质量词、角色特征，适合 WAI/NoobAI。",
        "format": "Positive 用 Danbooru tags，按主体、服装、姿势、背景、质量排序；Negative 要完整。",
    },
    "Krea 2（自然语言）": {
        "skill": "qwen-image-2-1-prompter/SKILL.md",
        "extra": None,
        "desc": "Krea 2：自然语言、风格和镜头描述，避免大量二次元 tag。",
        "format": "用自然的视觉描述，突出风格、材质、光线和镜头；可附少量风格关键词。",
    },
}

COLORS = {
    "bg": "#f4f6fa",
    "panel": "#ffffff",
    "card": "#ffffff",
    "card2": "#eef1f7",
    "text": "#1f2937",
    "muted": "#5f6b7b",
    "accent": "#6d5dfc",
    "accent2": "#5b4bd6",
    "green": "#0f9d78",
    "red": "#d9485f",
    "line": "#dce2ec",
    "input": "#ffffff",
}

FONT = ("Microsoft YaHei UI", 10)
FONT_SMALL = ("Microsoft YaHei UI", 10)
FONT_TITLE = ("Microsoft YaHei UI", 20, "bold")
FONT_SUB = ("Microsoft YaHei UI", 10)
FONT_MONO = ("Cascadia Mono", 10)


def enable_dpi_awareness():
    """Make Tk render at native DPI instead of Windows bitmap-scaling it."""
    if os.name != "nt":
        return
    try:
        # Per-monitor v2 (Windows 10 1703+).
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def center_window_adaptive(root: tk.Tk, base_w=1320, base_h=860):
    """居中到鼠标所在显示器的工作区，并按 DPI/任务栏/小屏自适应。"""
    root.update_idletasks()
    work_x, work_y, work_w, work_h = 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()
    scale = 1.0
    try:
        if sys.platform == "win32":
            user32 = ctypes.windll.user32

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                            ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            user32.MonitorFromPoint.argtypes = [POINT, ctypes.c_ulong]
            user32.MonitorFromPoint.restype = ctypes.c_void_p
            user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
            user32.GetMonitorInfoW.restype = ctypes.c_bool
            user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
            user32.FindWindowW.restype = ctypes.c_void_p
            user32.GetDpiForWindow.argtypes = [ctypes.c_void_p]
            user32.GetDpiForWindow.restype = ctypes.c_uint
            hmon = user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if hmon and user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                r = mi.rcWork
                # 目标显示器 DPI（失败则回退窗口/系统 DPI）
                dpi = 0
                try:
                    shcore = ctypes.windll.shcore
                    dx, dy = ctypes.c_uint(), ctypes.c_uint()
                    if shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dx), ctypes.byref(dy)) == 0:
                        dpi = dx.value
                except Exception:
                    pass
                if not dpi:
                    hwnd = user32.FindWindowW(None, APP_NAME)
                    dpi = user32.GetDpiForWindow(hwnd) if hwnd else 0
                if not dpi:
                    dpi = user32.GetDpiForSystem()
                if not dpi:
                    dpi = round(root.winfo_fpixels("1i"))
                scale = max(1.0, dpi / 96.0)
                work_x = r.left / scale
                work_y = r.top / scale
                work_w = (r.right - r.left) / scale
                work_h = (r.bottom - r.top) / scale
    except Exception:
        scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
        work_x, work_y, work_w, work_h = 0, 0, root.winfo_screenwidth(), root.winfo_screenheight()

    margin = 32
    w = max(640, min(base_w, int(work_w - margin)))
    h = max(480, min(base_h, int(work_h - margin)))
    x = int(round(work_x + (work_w - w) / 2))
    y = int(round(work_y + (work_h - h) / 2))
    try:
        root.state("normal")
    except Exception:
        pass
    root.geometry(f"{w}x{h}{x:+d}{y:+d}")
    root.minsize(min(1100, w), min(720, h))
    return w, h, x, y


def center_dialog_over(parent, dialog, width, height):
    """Place a Toplevel in the middle of the main window, not screen (0,0)."""
    parent.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    if pw <= 1 or ph <= 1:
        pw, ph = 1320, 860
    x = px + max(0, (pw - width) // 2)
    y = py + max(0, (ph - height) // 2)
    sw = parent.winfo_screenwidth()
    sh = parent.winfo_screenheight()
    x = max(0, min(x, sw - width))
    y = max(0, min(y, sh - height))
    dialog.geometry(f"{width}x{height}{x:+d}{y:+d}")
    try:
        dialog.lift()
    except Exception:
        pass


def apply_dark_titlebar(root: tk.Tk) -> None:
    """Windows：把原生标题栏和边框改成亮色，和亮色 UI 匹配。"""
    try:
        root.update_idletasks()
        hwnd = ctypes.windll.user32.FindWindowW(None, APP_NAME)
        if not hwnd:
            return
        dwm = ctypes.windll.dwmapi

        def set_attr(attr, value):
            v = ctypes.c_int(value)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))

        # 关闭沉浸式深色模式；旧版属性也关掉
        set_attr(20, 0)
        set_attr(19, 0)
        # DWMWA_BORDER_COLOR / CAPTION_COLOR / TEXT_COLOR（Windows 11）
        set_attr(34, 0x00ECE2DC)  # 浅灰边框
        set_attr(35, 0x00FAF6F4)  # #F4F6FA 的 COLORREF
        set_attr(36, 0x0037291F)  # #1F2937 的 COLORREF
    except Exception:
        pass


def strip_frontmatter(text: str) -> str:
    text = re.sub(r"(?s)^---.*?---\s*", "", text)
    return text.strip()


def read_text(path: Path, limit: int = 24000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = strip_frontmatter(text)
    if len(text) > limit:
        text = text[:limit] + "\n\n[模板已截断，保留前部关键规则]"
    return text


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def humanize_error(message):
    raw = str(message or "").strip()
    low = raw.lower()
    if any(x in low for x in ("connection refused", "failed to establish", "actively refused",
                              "max retries exceeded", "connection error", "transport")):
        return ("连接失败：ComfyUI 或 LLM 服务没有启动，或地址/端口不对。\n"
                "先点“一键准备”或到环境设置检查地址。\n\n原始信息：" + raw[:400])
    if any(x in low for x in ("out of memory", "cuda out of memory", "oom",
                              "allocation on device", "not enough memory")):
        return ("显存不足：当前底模/分辨率超出显卡容量。\n"
                "建议改用 Anima/Illustrious，或降低画幅和同时加载的 LLM。\n\n原始信息：" + raw[:400])
    if any(x in low for x in ("not in (", "not in list", "value not in", "model not found",
                              "checkpoint", "unet_name", "clip_name", "vae_name")):
        return ("模型文件不匹配或缺失：ComfyUI 找不到工作流需要的文件。\n"
                "点缺模型红色提示里的“生成 DSH”或“去下载/管理”。\n\n原始信息：" + raw[:400])
    if any(x in low for x in ("timed out", "timeout", "超时")):
        return ("等待超时：ComfyUI 可能还在加载模型，或请求卡住。\n"
                "先看显存和 ComfyUI 日志，必要时降低分辨率后重试。\n\n原始信息：" + raw[:400])
    if any(x in low for x in ("prompt outputs failed validation", "failed validation",
                              "missing required input", "invalid input")):
        return ("工作流参数不匹配：节点缺少输入或模型名称不正确。\n"
                "检查工作流和模型文件；可以生成 DSH 提示词做环境诊断。\n\n原始信息：" + raw[:400])
    if any(x in low for x in ("unauthorized", "401", "403", "invalid api key", "api key")):
        return ("LLM 鉴权失败：API Key 不正确或无权限。\n"
                "到环境设置检查 Key，不要把 Key 发到聊天里。\n\n原始信息：" + raw[:400])
    return raw[:600] or "未知错误"


def parse_sections(raw: str):
    text = raw.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    def grab(label):
        pattern = rf"(?:【|\*\*)?{label}(?:】|\*\*)?\s*[:：]?\s*(.*?)(?=(?:【|\*\*)?(?:Positive|Negative|Notes|正向|负向|备注)(?:】|\*\*)?\s*[:：]?|$)"
        m = re.search(pattern, text, re.S | re.I)
        return m.group(1).strip() if m else ""

    pos = grab("Positive") or grab("正向")
    neg = grab("Negative") or grab("负向")
    notes = grab("Notes") or grab("备注")

    if not pos:
        pos = text
    return pos.strip(), neg.strip(), notes.strip()


def load_known_triggers():
    data = load_json(KNOWN_TRIGGERS_FILE, [])
    mapping = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("fileName"):
                mapping[item["fileName"].lower()] = item.get("trainedWords") or []
    return mapping


def fetch_llm_models():
    """通过当前 LLM 提供方返回可用模型。"""
    return llm_client.list_models(CFG)


def fetch_prompt_bases():
    """底模提示词模板接口：返回目标底模名称与 LoRA 分类映射。"""
    return {
        "targets": list(TARGETS.keys()),
        "lora_filter": dict(TARGET_LORA_FILTER),
        "filters": list(BASE_FILTERS),
    }


def infer_lora_base(path: Path):
    s = str(path).lower().replace("\\", "/")
    name = path.stem.lower()
    if "/krea" in s or "krea" in name:
        return "Krea2"
    if "/moss" in s or "moss" in name:
        return "MOSS"
    if "/anima" in s or "anima" in name:
        return "Anima"
    if "/qwen" in s or "qwen" in name:
        return "Qwen"
    if "/flux" in s or "flux" in name:
        return "FLUX"
    if any(x in s for x in ("/wan", "/h3", "hunyuan", "ltx")):
        return "Wan/H3"
    if "/pony" in s or "pony" in name:
        return "Pony"
    if any(x in s for x in ("/sd15", "/sd1.5", "meinamix")) or any(x in name for x in ("sd15", "sd1.5")):
        return "SD15"
    if any(x in s for x in ("/illustrious", "/sdxl", "noobai")) or "illustrious" in name:
        return "Illustrious/SDXL"
    if re.search(r"(^|[-_])xl([-_.]|$)", name) or name.endswith("-il") or name.endswith("_il"):
        return "Illustrious/SDXL"

    # 文件名看不出来时，读 safetensors 头部元数据补判（约 1 秒/177 个）
    meta = read_safetensors_metadata(path)
    blob = " ".join(str(meta.get(k, "")) for k in (
        "ss_base_model_version", "modelspec.architecture", "ss_sd_model_name"
    )).lower()
    if "krea" in blob:
        return "Krea2"
    if "moss" in blob:
        return "MOSS"
    if "anima" in blob:
        return "Anima"
    if "qwen" in blob:
        return "Qwen"
    if "flux" in blob:
        return "FLUX"
    if any(x in blob for x in ("wan", "h3", "hunyuan", "ltx")):
        return "Wan/H3"
    if "pony" in blob:
        return "Pony"
    if "illustrious" in blob or "noob" in blob:
        return "Illustrious/SDXL"
    if any(x in blob for x in ("sdxl", "stable-diffusion-xl")):
        return "Illustrious/SDXL"
    if any(x in blob for x in ("sd15", "sd1.5", "stable-diffusion-v1", "sd-v1", "anythingv5", "animefull")):
        return "SD15"
    return "未识别"


def scan_lora_files():
    found = []
    seen = set()
    for root in LORA_ROOTS:
        if not root.exists():
            continue
        prefix = root.name or "LoRA"
        for path in root.rglob("*.safetensors"):
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            found.append({
                "label": f"{prefix}/{path.relative_to(root)}",
                "path": path,
                "name": path.name,
                "base": infer_lora_base(path),
            })
    found.sort(key=lambda x: x["label"].lower())
    return found


def read_safetensors_metadata(path: Path):
    try:
        with path.open("rb") as f:
            raw = f.read(8)
            if len(raw) != 8:
                return {}
            n = struct.unpack("<Q", raw)[0]
            if n <= 0 or n > 64 * 1024 * 1024:
                return {}
            header = json.loads(f.read(n).decode("utf-8"))
            meta = header.get("__metadata__", {})
            return meta if isinstance(meta, dict) else {}
    except Exception:
        return {}


def normalize_triggers(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            items = parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            items = re.split(r"[,，\n]+", s)
    else:
        items = [str(value)]
    out = []
    for x in items:
        x = str(x).strip()
        if x and x.lower() not in [y.lower() for y in out]:
            out.append(x)
    return out


def detect_triggers(path: Path, known):
    hit = known.get(path.name.lower())
    if hit:
        return hit, "已知触发词表"
    meta = read_safetensors_metadata(path)
    for key in ("modelspec.trigger_phrase", "ss_trigger_words", "trigger_words", "trigger_phrase"):
        if key in meta:
            vals = normalize_triggers(meta[key])
            if vals:
                return vals, f"元数据 {key}"
    return [], "未检测到明确触发词，可手动填写"


class PromptWorkbench:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1320x860")
        center_window_adaptive(self.root, 1320, 860)
        self.root.configure(bg=COLORS["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Control-Return>", lambda e: self.generate())

        try:
            self.root.iconbitmap(str(APP_ICON))
        except Exception:
            pass

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        WORKBENCH_LIBRARY.mkdir(parents=True, exist_ok=True)

        self.settings = load_json(SETTINGS_FILE, {})
        self.records = load_json(HISTORY_FILE, [])
        if not isinstance(self.records, list):
            self.records = []
        self.imported_workflows = load_json(IMPORTED_WORKFLOWS_FILE, [])
        if not isinstance(self.imported_workflows, list):
            self.imported_workflows = []
        self.output_dir = Path(self.settings.get("output_dir") or wbgen.OUT_DIR)
        self.known_triggers = load_known_triggers()
        self.lora_files = []
        self.all_lora_files = []
        self.selected_loras = []
        self.model_map = {label: model_id for label, model_id in MODEL_OPTIONS}
        self.desired_model_id = None
        self.used_models = set()
        self.lora_filter = tk.StringVar(value="全部")
        self.lora_strength = tk.DoubleVar(value=0.7)
        self.generation_workflow_var = tk.StringVar(value="")
        self.workflow_search_var = tk.StringVar(value="")
        self.lora_rec_rows = []
        self._manual_links = set()
        self._link_done = False
        self.refine_history = []
        self.beginner_mode_var = tk.BooleanVar(value=bool(self.settings.get("beginner_mode", True)))
        self.beginner_base_key = self.settings.get("beginner_base", "illustrious")
        if self.beginner_base_key not in [x["key"] for x in BEGINNER_BASES]:
            self.beginner_base_key = "illustrious"
        try:
            beginner_count_saved = int(self.settings.get("beginner_count", 1) or 1)
        except Exception:
            beginner_count_saved = 1
        if beginner_count_saved not in (1, 2, 4):
            beginner_count_saved = 1
        self.beginner_count_var = tk.IntVar(value=beginner_count_saved)
        self.beginner_style = tk.StringVar(value=self.settings.get("beginner_style", "无风格"))
        if self.beginner_style.get() not in ("二次元", "电影感", "插画", "写实", "赛博朋克", "水彩", "无风格"):
            self.beginner_style.set("无风格")
        self.beginner_ratio = tk.StringVar(value=self.settings.get("beginner_ratio", "竖图"))
        if self.beginner_ratio.get() not in BEGINNER_RATIOS:
            self.beginner_ratio.set("竖图")
        self.beginner_base_reco_key = None
        self.gpu_name, self.gpu_vram_mb = detect_gpu_memory()
        self.gen_cancel = threading.Event()
        self.env_queue = queue.Queue()
        self.beginner_pinned_lora = None
        self.beginner_character_trigger = ""
        self.civitai_guide_seen = bool(self.settings.get("civitai_guide_seen", False))
        self.beginner_pending = False

        self.mode = tk.StringVar(value="SFW")
        self.model_var = tk.StringVar()
        self.target_var = tk.StringVar()
        self.status_var = tk.StringVar(value="正在检查 LLM…")
        self.queue = queue.Queue()
        self.gen_queue = queue.Queue()
        self.match_queue = queue.Queue()
        self.gen_count_var = tk.IntVar(value=1)
        self.gen_close_var = tk.BooleanVar(value=True)
        self.auto_pick_var = tk.BooleanVar(value=bool(self.settings.get("auto_pick", False)))
        self.busy = False
        self.generating = False

        self._build_style()
        self._build_ui()
        self._auto_iconize()
        apply_dark_titlebar(self.root)
        self.root.after(250, lambda: apply_dark_titlebar(self.root))
        self._load_settings()
        self.root.after(150, self._poll_queue)
        self.root.after(300, self._bind_left_mousewheel)
        if CFG.is_new or not CFG.paths("lora_roots"):
            self.root.after(700, self.open_first_run_wizard)
        threading.Thread(target=self._check_health, daemon=True).start()

    # ---------- UI ----------
    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TCombobox", fieldbackground=COLORS["input"], background=COLORS["card2"],
                        foreground=COLORS["text"], arrowcolor=COLORS["text"], bordercolor=COLORS["line"])
        style.map("TCombobox", fieldbackground=[("readonly", COLORS["input"])],
                  foreground=[("readonly", COLORS["text"])])
        style.configure("TNotebook", background=COLORS["panel"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["card"], foreground=COLORS["muted"],
                        padding=(10, 5), borderwidth=0, font=("Microsoft YaHei UI", 9),
                        focuscolor=COLORS["card"])
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["card2"]), ("!selected", COLORS["panel"])],
                  foreground=[("selected", COLORS["accent2"]), ("!selected", COLORS["muted"])],
                  padding=[("selected", (18, 9)), ("!selected", (9, 4))],
                  font=[("selected", ("Microsoft YaHei UI", 11, "bold")),
                        ("!selected", ("Microsoft YaHei UI", 9))],
                  expand=[("selected", (1, 1, 1, 0)), ("!selected", (0, 0, 0, 0))])
        style.configure("TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"])
        style.configure("TFrame", background=COLORS["bg"])

    def _icon(self, name, color="accent"):
        key = (name, color)
        cache = getattr(self, "_icon_cache", None)
        if cache is None:
            cache = {}
            self._icon_cache = cache
        if key in cache:
            return cache[key]
        suffix = "-white" if color == "white" else ""
        path = ICON_DIR / f"{name}{suffix}.png"
        if not path.exists():
            return None
        try:
            img = tk.PhotoImage(file=str(path))
            factor = max(1, img.width() // 24)
            if factor > 1:
                img = img.subsample(factor, factor)
            cache[key] = img
            return img
        except Exception:
            return None

    def _decorate_button(self, button, icon, color="accent"):
        img = self._icon(icon, color)
        if img is not None:
            button.configure(image=img, compound="left", anchor="w")
            button.image = img
        return button

    def _auto_iconize(self):
        """Give common action buttons a consistent icon without changing layout."""
        mapping = {
            "打开输出目录": ("folder", "accent"),
            "打开输出": ("folder", "accent"),
            "再来一张": ("refresh", "accent"),
            "环境设置": ("settings", "accent"),
            "换底模": ("edit", "accent"),
            "采用推荐": ("play", "accent"),
            "下载/管理": ("download", "accent"),
            "去下载/管理": ("download", "accent"),
            "生成 DSH": ("help", "accent"),
            "复制": ("library", "accent"),
            "复制正向": ("library", "accent"),
            "复制负向": ("library", "accent"),
            "保存版本": ("edit", "accent"),
            "8.0 精修": ("edit", "accent"),
            "清空": ("stop", "accent"),
            "清除": ("stop", "accent"),
            "导入…": ("download", "accent"),
            "载入": ("download", "accent"),
            "加入": ("edit", "white"),
            "更换…": ("folder", "accent"),
            "更改…": ("folder", "accent"),
            "撤销选中调整": ("refresh", "accent"),
            "移除选中 LoRA": ("stop", "accent"),
            "开/旁": ("stop", "accent"),
            "浏览器挑选": ("browser", "accent"),
            "下载并接入": ("download", "white"),
            "保存到网盘": ("download", "white"),
            "打开 civitai.red": ("browser", "accent"),
        }

        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)

        for child in walk(self.root):
            if not isinstance(child, tk.Button) or child.cget("image"):
                continue
            text = str(child.cget("text") or "").strip()
            spec = mapping.get(text)
            if not spec:
                continue
            icon, color = spec
            if child.cget("bg") in (COLORS["accent"], COLORS["accent2"]):
                color = "white"
            self._decorate_button(child, icon, color)

    def _btn(self, parent, text, command, bg=None, fg=None, width=None, font=None, icon=None):
        b = tk.Button(parent, text=text, command=command,
                      bg=bg or COLORS["card2"], fg=fg or COLORS["text"],
                      activebackground=COLORS["accent2"], activeforeground="#fff",
                      relief="flat", bd=0, padx=12, pady=7,
                      font=font or FONT_SMALL, cursor="hand2",
                      width=width)
        if icon:
            self._decorate_button(b, icon, "white" if (fg or "").lower() in ("#fff", "#ffffff") else "accent")
        return b

    def _disable_combo_wheel(self, combo):
        """滚轮不切换选项，避免鼠标经过时误触。"""
        combo.bind("<MouseWheel>", lambda e: "break")
        combo.bind("<Button-4>", lambda e: "break")
        combo.bind("<Button-5>", lambda e: "break")

    def _build_ui(self):
        root = self.root

        # 侧栏
        sidebar = tk.Frame(root, bg=COLORS["panel"], width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = tk.Frame(sidebar, bg=COLORS["panel"])
        brand.pack(fill="x", padx=20, pady=(22, 6))
        tk.Label(brand, text="✦", bg=COLORS["panel"], fg=COLORS["accent"],
                 font=("Segoe UI Symbol", 24)).pack(side="left")
        tk.Label(brand, text=APP_NAME, bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 15, "bold")).pack(side="left", padx=(6, 0))

        tk.Label(sidebar, text="LOCAL PROMPT STUDIO", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=("Consolas", 8)).pack(anchor="w", padx=22)

        nav = tk.Frame(sidebar, bg=COLORS["panel"])
        nav.pack(fill="x", padx=12, pady=(24, 0))

        self.mode_switch_canvas = tk.Canvas(nav, height=38, bg=COLORS["panel"],
                                            highlightthickness=0, cursor="hand2")
        self.mode_switch_canvas.pack(fill="x", pady=(0, 10))
        self._switch_pos = 0.0 if self.beginner_mode_var.get() else 1.0
        self._switch_anim_job = None
        self.mode_switch_canvas.bind("<Button-1>", lambda e: self.toggle_beginner_mode())
        self.mode_switch_canvas.bind("<Configure>", lambda e: self._draw_mode_switch(self._switch_pos))

        self.nav_generate = self._btn(nav, "生成提示词", self._focus_generate, COLORS["card2"], COLORS["text"], icon="sparkles")
        self.nav_generate.pack(fill="x", pady=3)
        self.nav_history = self._btn(nav, "历史版本", self._show_history_tab, COLORS["panel"], COLORS["muted"], icon="history")
        self.nav_history.pack(fill="x", pady=3)
        self.nav_library = self._btn(nav, "提示词库", self.open_library, COLORS["panel"], COLORS["muted"], icon="library")
        self.nav_library.pack(fill="x", pady=3)
        self.nav_tool80 = self._btn(nav, "8.0 精修", self.open_tool80, COLORS["panel"], COLORS["muted"], icon="edit")
        self.nav_tool80.pack(fill="x", pady=3)
        self._btn(nav, "环境设置", self.open_settings_dialog, COLORS["panel"], COLORS["muted"], icon="settings").pack(fill="x", pady=3)
        self._btn(nav, "模型指南", self.open_model_guide, COLORS["panel"], COLORS["muted"], icon="help").pack(fill="x", pady=3)
        self._btn(nav, "模型中心", self.open_model_center, COLORS["panel"], COLORS["muted"], icon="cloud").pack(fill="x", pady=3)
        self._btn(nav, "检查更新", self.check_updates, COLORS["panel"], COLORS["muted"], icon="refresh").pack(fill="x", pady=3)
        self.advanced_nav_widgets = [self.nav_generate, self.nav_history, self.nav_library, self.nav_tool80]

        tk.Frame(sidebar, bg=COLORS["line"], height=1).pack(fill="x", padx=16, pady=18)

        info = tk.Frame(sidebar, bg=COLORS["panel"])
        info.pack(fill="x", padx=18)
        tk.Label(info, text="LLM 模型", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(anchor="w")
        tk.Label(info, textvariable=self.status_var, bg=COLORS["panel"], fg=COLORS["green"],
                 font=FONT_SMALL, wraplength=170, justify="left").pack(anchor="w", pady=(2, 10))
        tk.Label(info, text="仅调用 LLM 生成提示词\n不启动/停止 LLM 服务", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), justify="left").pack(anchor="w")

        tk.Label(sidebar, text=f"{APP_NAME}\nv{APP_VERSION}  ·  快捷本地出图", bg=COLORS["panel"],
                 fg="#8a93a6", font=("Microsoft YaHei UI", 9), justify="left").pack(side="bottom", anchor="w", padx=20, pady=18)

        # 主区域
        main = tk.Frame(root, bg=COLORS["bg"])
        main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(main, bg=COLORS["bg"])
        header.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(header, text=APP_NAME, bg=COLORS["bg"], fg=COLORS["text"], font=FONT_TITLE).pack(side="left")
        tk.Label(header, text=DISPLAY_TAGLINE, bg=COLORS["bg"],
                 fg=COLORS["muted"], font=FONT_SUB).pack(side="left", padx=14, pady=(6, 0))

        # 顶部控制
        top = tk.Frame(main, bg=COLORS["card"], highlightbackground=COLORS["line"], highlightthickness=1)
        top.pack(fill="x", padx=24, pady=(4, 12))

        row = tk.Frame(top, bg=COLORS["card"])
        row.pack(fill="x", padx=14, pady=12)

        tk.Label(row, text="LLM 模型", bg=COLORS["card"], fg=COLORS["muted"], font=FONT_SMALL).pack(side="left")
        self.model_combo = ttk.Combobox(row, textvariable=self.model_var, state="readonly",
                                        values=[x[0] for x in MODEL_OPTIONS], width=26)
        self.model_combo.pack(side="left", padx=(6, 18))
        self.model_combo.bind("<<ComboboxSelected>>", lambda e: self._on_model_change())
        self._disable_combo_wheel(self.model_combo)

        tk.Label(row, text="目标底模", bg=COLORS["card"], fg=COLORS["muted"], font=FONT_SMALL).pack(side="left")
        self.target_combo = ttk.Combobox(row, textvariable=self.target_var, state="readonly",
                                         values=list(TARGETS.keys()), width=25)
        self.target_combo.pack(side="left", padx=(6, 14))
        self.target_combo.bind("<<ComboboxSelected>>", lambda e: self._on_target_change())
        self._disable_combo_wheel(self.target_combo)

        tk.Label(row, text="工作流", bg=COLORS["card"], fg=COLORS["muted"], font=FONT_SMALL).pack(side="left")
        self.generation_workflow_combo = ttk.Combobox(
            row, textvariable=self.generation_workflow_var, state="readonly",
            values=self._workflow_labels(), width=19)
        self.generation_workflow_combo.pack(side="left", padx=(6, 4))
        self.generation_workflow_combo.bind("<<ComboboxSelected>>", lambda e: self._on_generation_workflow_change())
        self._disable_combo_wheel(self.generation_workflow_combo)
        self._btn(row, "导入…", self._import_workflow, COLORS["card2"], COLORS["text"]).pack(side="left", padx=(0, 10))
        tk.Label(row, text="搜索", bg=COLORS["card"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.workflow_search_entry = tk.Entry(row, textvariable=self.workflow_search_var, width=13,
                                              bg=COLORS["input"], fg=COLORS["text"],
                                              insertbackground=COLORS["text"], relief="flat", bd=0,
                                              highlightbackground=COLORS["line"], highlightthickness=1,
                                              font=("Microsoft YaHei UI", 9))
        self.workflow_search_entry.pack(side="left", padx=(4, 2), ipady=3)
        self.workflow_search_entry.bind("<KeyRelease>", lambda e: self._apply_workflow_filter())
        self._btn(row, "清", self.clear_workflow_search, COLORS["panel"], COLORS["muted"]).pack(side="left")

        self.mode_btn = tk.Button(row, text="SFW", command=self.toggle_mode,
                                  bg=COLORS["green"], fg="#fff", activebackground=COLORS["green"],
                                  relief="flat", bd=0, padx=14, pady=6, font=("Microsoft YaHei UI", 9, "bold"),
                                  cursor="hand2", width=8)
        self.mode_btn.pack(side="left")
        self.mode_hint = tk.Label(row, text="默认 SFW", bg=COLORS["card"], fg=COLORS["muted"],
                                  font=("Microsoft YaHei UI", 9))
        self.mode_hint.pack(side="left", padx=(6, 0))


        self.target_desc = tk.Label(top, text="", bg=COLORS["card"], fg=COLORS["muted"],
                                    font=("Microsoft YaHei UI", 9), anchor="w",
                                    justify="left", wraplength=1250)
        self.target_desc.pack(fill="x", padx=16, pady=(0, 10))

        # 工作区
        body = tk.Frame(main, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=(0, 8))
        body.grid_columnconfigure(0, weight=42)
        body.grid_columnconfigure(1, weight=58)
        body.grid_rowconfigure(0, weight=1)

        # 左：需求与操作
        left_shell = tk.Frame(body, bg=COLORS["panel"], highlightbackground=COLORS["line"], highlightthickness=1)
        left_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left_canvas = tk.Canvas(left_shell, bg=COLORS["panel"], highlightthickness=0)
        left_scroll = ttk.Scrollbar(left_shell, orient="vertical", command=self.left_canvas.yview)
        self.left_canvas.configure(yscrollcommand=left_scroll.set)
        left_scroll.pack(side="right", fill="y")
        self.left_canvas.pack(side="left", fill="both", expand=True)
        left = tk.Frame(self.left_canvas, bg=COLORS["panel"])
        left_window = self.left_canvas.create_window((0, 0), window=left, anchor="nw")

        def _left_inner_config(_):
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))

        def _left_canvas_config(e):
            self.left_canvas.itemconfigure(left_window, width=e.width)

        left.bind("<Configure>", _left_inner_config)
        self.left_canvas.bind("<Configure>", _left_canvas_config)
        tk.Label(left, text="你想要的画面 / 人物 / 场景", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        tk.Label(left, text="可以写中文，越具体越好；留空会提示。", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=14, pady=(0, 8))
        self.brief_text = ScrolledText(left, wrap="word", height=4, bg=COLORS["input"],
                                       fg=COLORS["text"], insertbackground=COLORS["text"],
                                       relief="flat", bd=0, font=FONT, padx=10, pady=10)
        self.brief_text.pack(fill="x", padx=12, pady=(0, 6))

        adjust_row = tk.Frame(left, bg=COLORS["panel"])
        adjust_row.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(adjust_row, text="继续调整", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(0, 5))
        self.refine_entry = tk.Entry(adjust_row, bg=COLORS["input"], fg=COLORS["text"],
                                     insertbackground=COLORS["text"], relief="flat", bd=0,
                                     highlightbackground=COLORS["line"], highlightcolor=COLORS["accent"],
                                     highlightthickness=1, font=FONT_SMALL)
        self.refine_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.refine_btn = self._btn(adjust_row, "继续调整", self.refine_prompt,
                                     COLORS["accent"], "#fff", icon="edit")
        self.refine_btn.pack(side="left", padx=(6, 0))
        self.root.bind("<Control-Shift-Return>", lambda e: self.refine_prompt())

        refine_hist_box = tk.Frame(left, bg=COLORS["panel"])
        refine_hist_box.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(refine_hist_box, text="调整记录（选中可撤销该次及之后）", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        self.refine_log_list = tk.Listbox(refine_hist_box, height=1, bg=COLORS["input"],
                                          fg=COLORS["text"], selectbackground=COLORS["accent2"],
                                          selectforeground="#fff", relief="flat", bd=0,
                                          font=("Microsoft YaHei UI", 9))
        self.refine_log_list.pack(fill="x", pady=(2, 2))
        self._btn(refine_hist_box, "撤销选中调整", self._undo_refine,
                  COLORS["card2"], COLORS["text"]).pack(anchor="e")

        lora_box = tk.Frame(left, bg=COLORS["card2"], highlightbackground=COLORS["line"], highlightthickness=1)
        lora_box.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(lora_box, text="LoRA 触发词（可选）", bg=COLORS["card2"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 2))
        filter_row = tk.Frame(lora_box, bg=COLORS["card2"])
        filter_row.pack(fill="x", padx=8, pady=(2, 3))
        tk.Label(filter_row, text="底模", bg=COLORS["card2"], fg=COLORS["muted"],
                 font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(0, 4))
        self.lora_filter_combo = ttk.Combobox(filter_row, textvariable=self.lora_filter,
                                              state="readonly", values=BASE_FILTERS, width=22)
        self.lora_filter_combo.pack(side="left", fill="x", expand=True)
        self.lora_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._on_lora_filter_change())
        self._disable_combo_wheel(self.lora_filter_combo)
        lora_row = tk.Frame(lora_box, bg=COLORS["card2"])
        lora_row.pack(fill="x", padx=8, pady=(2, 3))
        self.lora_combo = ttk.Combobox(lora_row, state="readonly", width=30)
        self.lora_combo.pack(side="left", fill="x", expand=True)
        self.lora_combo.bind("<<ComboboxSelected>>", lambda e: self._on_lora_select())
        self._disable_combo_wheel(self.lora_combo)
        self._btn(lora_row, "载入", self._on_lora_select, COLORS["card"], COLORS["text"]).pack(side="left", padx=(4, 0))
        trigger_row = tk.Frame(lora_box, bg=COLORS["card2"])
        trigger_row.pack(fill="x", padx=8, pady=(2, 3))
        tk.Label(trigger_row, text="触发词", bg=COLORS["card2"], fg=COLORS["muted"],
                 font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(0, 4))
        self.lora_trigger = tk.Entry(trigger_row, bg=COLORS["input"], fg=COLORS["text"],
                                     insertbackground=COLORS["text"], relief="flat", bd=0, font=FONT_SMALL)
        self.lora_trigger.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Label(trigger_row, text="强度", bg=COLORS["card2"], fg=COLORS["muted"],
                 font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(6, 3))
        tk.Spinbox(trigger_row, from_=0.1, to=1.2, increment=0.05, textvariable=self.lora_strength,
                   width=4, bg=COLORS["input"], fg=COLORS["text"], relief="flat", bd=0).pack(side="left")
        self._btn(trigger_row, "加入", self._add_lora, COLORS["accent"], "#fff").pack(side="left", padx=(4, 0))
        self.lora_selected_list = tk.Listbox(lora_box, height=2, bg=COLORS["input"], fg=COLORS["text"],
                                             selectbackground=COLORS["accent2"], selectforeground="#fff",
                                             relief="flat", bd=0, font=("Microsoft YaHei UI", 9))
        self.lora_selected_list.pack(fill="x", padx=8, pady=(2, 2))
        self.lora_recommend_frame = tk.Frame(lora_box, bg=COLORS["panel"],
                                             highlightbackground=COLORS["line"], highlightthickness=1)
        self.lora_status = tk.Label(lora_box, text="可手动填写触发词；未选择时不注入", bg=COLORS["card2"],
                                    fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), anchor="w")
        self.lora_status.pack(fill="x", padx=8, pady=(0, 5))
        lora_actions = tk.Frame(lora_box, bg=COLORS["card2"])
        lora_actions.pack(fill="x", padx=8, pady=(0, 6))
        self.lora_recommend_btn = self._btn(lora_actions, "推荐 LoRA", self._recommend_lora_inline,
                                            COLORS["accent"], "#fff")
        self.lora_recommend_btn.pack(side="left")
        ttk.Checkbutton(lora_actions, text="自动选 LoRA", variable=self.auto_pick_var,
                        command=self._save_settings).pack(side="left", padx=(8, 0))
        self._btn(lora_actions, "开/旁", self._toggle_lora_enabled, COLORS["panel"], COLORS["muted"]).pack(side="left", padx=(4, 0))
        self._btn(lora_actions, "移除选中 LoRA", self._remove_lora, COLORS["panel"], COLORS["muted"]).pack(side="right")

        tk.Frame(left, bg=COLORS["panel"]).pack(fill="both", expand=True)

        tip = tk.Label(left, text="Ctrl + Enter 生成  ·  结果可直接编辑", bg=COLORS["panel"],
                       fg="#8a93a6", font=("Microsoft YaHei UI", 9))
        tip.pack(anchor="w", padx=14, pady=(0, 6))

        self.generate_btn = self._btn(left, "新开一个", self.generate,
                                      COLORS["accent"], "#fff", font=("Microsoft YaHei UI", 10, "bold"),
                                      icon="sparkles")
        self.generate_btn.configure(pady=9)
        self.generate_btn.pack(fill="x", padx=12, pady=(0, 10))
        self.generate_btn.bind("<Control-Return>", lambda e: self.generate())

        # 右：输出 / 历史
        right = tk.Frame(body, bg=COLORS["panel"], highlightbackground=COLORS["line"], highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        gen_bar = tk.Frame(right, bg=COLORS["panel"])
        gen_bar.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        tk.Label(gen_bar, text="张数", bg=COLORS["panel"], fg=COLORS["muted"], font=FONT_SMALL).pack(side="left")
        self._btn(gen_bar, "−", lambda: self.adjust_gen_count(-1),
                  COLORS["card2"], COLORS["text"], font=("Microsoft YaHei UI", 12, "bold")).pack(
                      side="left", padx=(5, 2), ipadx=4, ipady=1)
        tk.Label(gen_bar, textvariable=self.gen_count_var, width=3, bg=COLORS["input"],
                 fg=COLORS["text"], font=("Microsoft YaHei UI", 10, "bold"),
                 relief="flat", bd=0, pady=4).pack(side="left")
        self._btn(gen_bar, "+", lambda: self.adjust_gen_count(1),
                  COLORS["card2"], COLORS["text"], font=("Microsoft YaHei UI", 12, "bold")).pack(
                      side="left", padx=(2, 12), ipadx=4, ipady=1)
        ttk.Checkbutton(gen_bar, text="完成后关 ComfyUI", variable=self.gen_close_var).pack(side="left")
        self.gen_btn = self._btn(gen_bar, "生成并出图", self.generate_images,
                                 COLORS["accent"], "#fff", font=("Microsoft YaHei UI", 9, "bold"),
                                 icon="play")
        self.gen_btn.pack(side="right")
        self.auto_match_btn = self._btn(gen_bar, "自动匹配", self.auto_match_loras,
                                        COLORS["card2"], COLORS["text"])
        self.auto_match_btn.pack(side="right", padx=(0, 6))

        out_row = tk.Frame(right, bg=COLORS["panel"])
        out_row.pack(side="bottom", fill="x", padx=8, pady=(0, 4))
        tk.Label(out_row, text="输出目录", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.outdir_label = tk.Label(out_row, text=self._output_dir_text(), bg=COLORS["panel"],
                                     fg=COLORS["text"], font=("Microsoft YaHei UI", 9),
                                     anchor="w")
        self.outdir_label.pack(side="left", fill="x", expand=True, padx=(6, 6))
        self._btn(out_row, "更改…", self.choose_output_dir, COLORS["card2"], COLORS["text"]).pack(side="right")

        self.tab = ttk.Notebook(right)
        self.tab.pack(fill="both", expand=True, padx=8, pady=8)

        out_tab = tk.Frame(self.tab, bg=COLORS["panel"])
        self.tab.add(out_tab, text="提 示 词")
        out_tab.grid_columnconfigure(0, weight=1)
        out_tab.grid_rowconfigure(1, weight=1)
        out_tab.grid_rowconfigure(3, weight=1)

        tk.Label(out_tab, text="Positive / 正向", bg=COLORS["panel"], fg=COLORS["green"],
                 font=("Microsoft YaHei UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=4, pady=(4, 2))
        self.positive_text = ScrolledText(out_tab, wrap="word", height=9, bg=COLORS["input"],
                                          fg=COLORS["text"], insertbackground=COLORS["text"],
                                          relief="flat", bd=0, font=FONT_MONO, padx=8, pady=8)
        self.positive_text.grid(row=1, column=0, sticky="nsew", padx=2, pady=(0, 6))

        tk.Label(out_tab, text="Negative / 负向", bg=COLORS["panel"], fg=COLORS["red"],
                 font=("Microsoft YaHei UI", 9, "bold")).grid(row=2, column=0, sticky="w", padx=4, pady=(0, 2))
        self.negative_text = ScrolledText(out_tab, wrap="word", height=6, bg=COLORS["input"],
                                          fg=COLORS["text"], insertbackground=COLORS["text"],
                                          relief="flat", bd=0, font=FONT_MONO, padx=8, pady=8)
        self.negative_text.grid(row=3, column=0, sticky="nsew", padx=2, pady=(0, 6))

        actions = tk.Frame(out_tab, bg=COLORS["panel"])
        actions.grid(row=4, column=0, sticky="ew", pady=(2, 2))
        self._btn(actions, "复制正向", self.copy_positive, COLORS["card2"], COLORS["text"]).pack(side="left", padx=(0, 6))
        self._btn(actions, "复制负向", self.copy_negative, COLORS["card2"], COLORS["text"]).pack(side="left", padx=(0, 6))
        self._btn(actions, "保存版本", self.save_version, COLORS["card2"], COLORS["text"]).pack(side="left", padx=(0, 6))
        self._btn(actions, "8.0 精修", self.open_tool80, COLORS["card2"], COLORS["text"]).pack(side="left", padx=(0, 6))
        self._btn(actions, "清空", self.clear, COLORS["panel"], COLORS["muted"]).pack(side="right")

        hist_tab = tk.Frame(self.tab, bg=COLORS["panel"])
        self.tab.add(hist_tab, text="历 史")
        hist_bar = tk.Frame(hist_tab, bg=COLORS["panel"])
        hist_bar.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(hist_bar, text="单击选中 · 双击打开到左侧 · Ctrl/Shift 多选",
                 bg=COLORS["panel"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.history_delete_btn = self._btn(hist_bar, "删除选中", self.delete_selected_history,
                                            COLORS["panel"], COLORS["muted"])
        self.history_delete_btn.pack(side="right", padx=(6, 0))
        self.history_delete_btn.configure(state="disabled")
        self._btn(hist_bar, "删除这条", self.delete_active_history,
                  COLORS["panel"], COLORS["muted"]).pack(side="right", padx=(6, 0))
        self._btn(hist_bar, "全选", self._select_all_history,
                  COLORS["panel"], COLORS["muted"]).pack(side="right")
        self.history_list = tk.Listbox(hist_tab, bg=COLORS["input"], fg=COLORS["text"],
                                       selectbackground=COLORS["accent2"], selectforeground="#fff",
                                       relief="flat", bd=0, font=FONT_SMALL, activestyle="none",
                                       selectmode="extended", exportselection=False)
        self.history_list.pack(fill="both", expand=True, padx=8, pady=8)
        self.history_list.bind("<<ListboxSelect>>", self._on_history_select)
        self.history_list.bind("<Double-Button-1>", self._open_history_record)
        self.history_list.bind("<Button-3>", self._history_context_menu)
        self.history_list.bind("<Delete>", lambda e: self.delete_selected_history())
        self.history_list.bind("<Control-a>", self._select_all_history)
        self.history_menu = tk.Menu(self.root, tearoff=0, bg=COLORS["panel"], fg=COLORS["text"],
                                    activebackground=COLORS["accent2"], activeforeground="#fff")
        self.history_menu.add_command(label="打开到左侧", command=self.open_active_history)
        self.history_menu.add_separator()
        self.history_menu.add_command(label="删除这条", command=self.delete_active_history)
        self.history_menu.add_command(label="删除选中", command=self.delete_selected_history)

        self.results_tab = tk.Frame(self.tab, bg=COLORS["panel"])
        self.tab.add(self.results_tab, text="生成结果")
        result_head = tk.Frame(self.results_tab, bg=COLORS["panel"])
        result_head.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(result_head, text="最近生成", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 9, "bold")).pack(side="left")
        self._btn(result_head, "打开输出目录", self.open_output_dir,
                  COLORS["card2"], COLORS["text"]).pack(side="right")
        self.result_note = tk.Label(self.results_tab, text="", bg=COLORS["panel"], fg=COLORS["muted"],
                                    font=("Microsoft YaHei UI", 9), anchor="w", justify="left",
                                    wraplength=620)
        self.result_note.pack(fill="x", padx=8, pady=(0, 4))
        self.result_progress = tk.Label(self.results_tab, text="等待生成", bg=COLORS["panel"],
                                        fg=COLORS["accent2"], font=("Microsoft YaHei UI", 10, "bold"),
                                        anchor="w")
        self.result_progress.pack(fill="x", padx=8, pady=(0, 3))
        self.result_progressbar = ttk.Progressbar(self.results_tab, orient="horizontal",
                                                   mode="determinate", maximum=8, value=0)
        self.result_progressbar.pack(fill="x", padx=8, pady=(0, 6))
        result_body = tk.Frame(self.results_tab, bg=COLORS["panel"])
        result_body.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        self.results_canvas = tk.Canvas(result_body, bg=COLORS["panel"], highlightthickness=0)
        result_scroll = ttk.Scrollbar(result_body, orient="vertical", command=self.results_canvas.yview)
        self.results_canvas.configure(yscrollcommand=result_scroll.set)
        result_scroll.pack(side="right", fill="y")
        self.results_canvas.pack(side="left", fill="both", expand=True)
        self.results_inner = tk.Frame(self.results_canvas, bg=COLORS["panel"])
        self._results_window = self.results_canvas.create_window((0, 0), window=self.results_inner, anchor="nw")

        def _results_inner_config(_):
            self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))

        def _results_canvas_config(e):
            self.results_canvas.itemconfigure(self._results_window, width=e.width)

        self.results_inner.bind("<Configure>", _results_inner_config)
        self.results_canvas.bind("<Configure>", _results_canvas_config)
        self.result_paths = []
        self._result_photos = []

        # 底部安全备注
        footer = tk.Frame(main, bg=COLORS["bg"])
        footer.pack(fill="x", padx=24, pady=(0, 12))
        tk.Label(footer, text="备注：仅限 18+ 角色；禁止未成年/幼态；禁止真实人物性化。",
                 bg=COLORS["bg"], fg="#8a93a6", font=("Microsoft YaHei UI", 9)).pack(side="left")
        tk.Label(footer, text="历史自动保存 · 关闭时释放本次用过的模型", 
                 bg=COLORS["bg"], fg="#8a93a6", font=("Microsoft YaHei UI", 9)).pack(side="right")

        self.advanced_surfaces = [top, body, footer]
        self.beginner_outer = tk.Frame(main, bg=COLORS["bg"])
        self.beginner_canvas = tk.Canvas(self.beginner_outer, bg=COLORS["bg"], highlightthickness=0)
        beginner_scroll = ttk.Scrollbar(self.beginner_outer, orient="vertical",
                                        command=self.beginner_canvas.yview)
        self.beginner_canvas.configure(yscrollcommand=beginner_scroll.set)
        beginner_scroll.pack(side="right", fill="y")
        self.beginner_canvas.pack(side="left", fill="both", expand=True)
        self.beginner_frame = tk.Frame(self.beginner_canvas, bg=COLORS["bg"])
        beginner_window = self.beginner_canvas.create_window((0, 0), window=self.beginner_frame,
                                                             anchor="nw")
        self.beginner_frame.bind(
            "<Configure>",
            lambda e: self.beginner_canvas.configure(scrollregion=self.beginner_canvas.bbox("all")))
        self.beginner_canvas.bind(
            "<Configure>",
            lambda e: self.beginner_canvas.itemconfigure(beginner_window, width=e.width))
        hero = tk.Frame(self.beginner_frame, bg=COLORS["bg"])
        hero.pack(fill="x", padx=24, pady=(18, 8))
        tk.Label(hero, text="一键出图", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 24, "bold")).pack(anchor="w")
        tk.Label(hero, text="写中文就行。默认一套 Illustrious 底模；NSFW 加同底模 LoRA。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 10)).pack(
                     anchor="w", pady=(4, 0))
        status_row = tk.Frame(hero, bg=COLORS["bg"])
        status_row.pack(fill="x", pady=(8, 0))
        self.beginner_llm_status = tk.Label(status_row, text="LLM …", bg=COLORS["bg"],
                                            fg=COLORS["muted"], font=("Microsoft YaHei UI", 9))
        self.beginner_llm_status.pack(side="left", padx=(0, 10))
        self.beginner_comfy_status = tk.Label(status_row, text="ComfyUI …", bg=COLORS["bg"],
                                              fg=COLORS["muted"], font=("Microsoft YaHei UI", 9))
        self.beginner_comfy_status.pack(side="left", padx=(0, 10))
        self.beginner_model_status = tk.Label(status_row, text="底模 …", bg=COLORS["bg"],
                                              fg=COLORS["muted"], font=("Microsoft YaHei UI", 9))
        self.beginner_model_status.pack(side="left", padx=(0, 10))
        self.beginner_prepare_btn = tk.Button(
            status_row, text="一键准备", command=self._beginner_prepare_all,
            bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
            padx=9, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2")
        self.beginner_prepare_btn.pack(side="right")
        self._decorate_button(self.beginner_prepare_btn, "download")
        self.beginner_recommend_btn = tk.Button(
            status_row, text="推荐包", command=self.open_recommended_pack,
            bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
            padx=7, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2")
        self.beginner_recommend_btn.pack(side="right", padx=(0, 5))
        self._decorate_button(self.beginner_recommend_btn, "model")
        self._env_check_running = False


        simple_card = tk.Frame(self.beginner_frame, bg=COLORS["panel"],
                               highlightbackground=COLORS["line"], highlightthickness=1)
        simple_card.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        mode_row = tk.Frame(simple_card, bg=COLORS["panel"])
        mode_row.pack(fill="x", padx=18, pady=(16, 6))
        tk.Label(mode_row, text="画面尺度", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left")
        self.beginner_mode_btn = tk.Button(mode_row, text="SFW", command=self.toggle_mode,
                                           bg=COLORS["green"], fg="#fff", relief="flat", bd=0,
                                           activebackground=COLORS["green"], activeforeground="#fff",
                                           font=("Microsoft YaHei UI", 11, "bold"), padx=22, pady=7,
                                           cursor="hand2")
        self.beginner_mode_btn.pack(side="left", padx=(10, 14))
        self.beginner_base_label = tk.Label(mode_row, text="", bg=COLORS["panel"],
                                            fg=COLORS["accent2"], font=("Microsoft YaHei UI", 9, "bold"))
        self.beginner_base_label.pack(side="left")
        tk.Button(mode_row, text="环境设置", command=self.open_settings_dialog,
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2").pack(side="right")

        base_row = tk.Frame(simple_card, bg=COLORS["panel"])
        base_row.pack(fill="x", padx=18, pady=(4, 4))
        tk.Label(base_row, text="底模", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left", padx=(0, 8))
        self.beginner_base_summary = tk.Label(
            base_row, text="", bg=COLORS["panel"], fg=COLORS["accent2"],
            font=("Microsoft YaHei UI", 9, "bold"))
        self.beginner_base_summary.pack(side="left")
        self.beginner_base_toggle_btn = tk.Button(
            base_row, text="换底模", command=self._toggle_beginner_base_cards,
            bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
            padx=6, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2")
        self.beginner_base_toggle_btn.pack(side="left", padx=(8, 0))
        self.beginner_base_cards = tk.Frame(base_row, bg=COLORS["panel"])
        self.beginner_base_buttons = []
        for base in BEGINNER_BASES:
            btn = tk.Button(self.beginner_base_cards, text=f"{base['icon']} {base['label']}",
                            command=lambda k=base["key"]: self._select_beginner_base(k),
                            bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                            padx=8, pady=4, font=("Microsoft YaHei UI", 9), cursor="hand2")
            btn.pack(side="left", padx=(0, 5))
            self.beginner_base_buttons.append((base["key"], btn))
            if base["key"] == self.beginner_base_key:
                btn.configure(bg=COLORS["accent"], fg="#fff", activebackground=COLORS["accent2"])
        tk.Button(self.beginner_base_cards, text="下载/管理", command=self._open_center_for_beginner_base,
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=6, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(side="left")
        self.beginner_base_cards.pack_forget()
        self._update_beginner_base_summary()

        reco_row = tk.Frame(simple_card, bg=COLORS["panel"])
        reco_row.pack(fill="x", padx=18, pady=(0, 2))
        self.beginner_base_reco_label = tk.Label(
            reco_row, text="", bg=COLORS["panel"], fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9), anchor="w")
        self.beginner_base_reco_label.pack(side="left")
        self.beginner_base_adopt_btn = tk.Button(
            reco_row, text="采用推荐", command=self._adopt_recommended_base,
            bg=COLORS["panel"], fg=COLORS["accent2"], relief="flat", bd=0,
            font=("Microsoft YaHei UI", 9, "bold"), cursor="hand2")
        self.beginner_base_adopt_btn.pack(side="left", padx=(8, 0))
        self.beginner_base_adopt_btn.pack_forget()

        self.beginner_missing_frame = tk.Frame(
            simple_card, bg="#fff1f0", highlightbackground=COLORS["red"], highlightthickness=1)
        self.beginner_missing_label = tk.Label(
            self.beginner_missing_frame, text="", bg="#fff1f0", fg=COLORS["red"],
            font=("Microsoft YaHei UI", 9, "bold"), anchor="w", justify="left", wraplength=900)
        self.beginner_missing_label.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=7)
        tk.Button(self.beginner_missing_frame, text="去下载/管理",
                  command=self._open_center_for_beginner_base,
                  bg=COLORS["red"], fg="#fff", relief="flat", bd=0,
                  padx=9, pady=4, cursor="hand2").pack(side="right", padx=(0, 8), pady=6)
        tk.Button(self.beginner_missing_frame, text="生成 DSH",
                  command=self._show_missing_dsh_prompt,
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=7, pady=4, cursor="hand2").pack(side="right", padx=(0, 4), pady=6)
        tk.Button(self.beginner_missing_frame, text="复制",
                  command=self._copy_missing_dsh_prompt,
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=7, pady=4, cursor="hand2").pack(side="right", padx=(0, 4), pady=6)
        self.beginner_missing_files = []
        self.beginner_missing_frame.pack_forget()

        tk.Label(simple_card, text="你想要什么画面？", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", padx=18, pady=(8, 4))
        character_row = tk.Frame(simple_card, bg=COLORS["panel"])
        character_row.pack(fill="x", padx=18, pady=(0, 4))
        self.beginner_character_label = tk.Label(
            character_row, text="角色：未选择", bg=COLORS["panel"], fg=COLORS["muted"],
            font=("Microsoft YaHei UI", 9))
        self.beginner_character_label.pack(side="left")
        char_btn = tk.Button(character_row, text="画角色 · 搜索并接入",
                             command=self.open_character_search,
                             bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                             padx=9, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2")
        char_btn.pack(side="right")
        self._decorate_button(char_btn, "character")
        tk.Button(character_row, text="清除",
                  command=self.clear_beginner_character,
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=5, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(
                      side="right", padx=(0, 4))
        self.beginner_brief = ScrolledText(simple_card, wrap="word", height=7,
                                           bg=COLORS["input"], fg=COLORS["text"],
                                           insertbackground=COLORS["text"], relief="flat", bd=0,
                                           font=("Microsoft YaHei UI", 11), padx=12, pady=10)
        self.beginner_brief.pack(fill="x", padx=18, pady=(0, 8))
        self.beginner_brief.insert("1.0", "例如：银发成年女性，雨夜霓虹街头，黑色风衣，温柔地看着镜头，电影感人像")

        inspire_row = tk.Frame(simple_card, bg=COLORS["panel"])
        inspire_row.pack(fill="x", padx=18, pady=(0, 6))
        tk.Label(inspire_row, text="灵感", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left", padx=(0, 8))
        for label in ("随机", "人物", "服装", "场景", "光线"):
            tk.Button(inspire_row, text=label,
                      command=lambda k=label: self._beginner_inspire(k),
                      bg=COLORS["panel"], fg=COLORS["accent2"], relief="flat", bd=0,
                      padx=6, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(
                          side="left", padx=(0, 3))
        tk.Label(inspire_row, text="点一下补进描述，可继续改",
                 bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Microsoft YaHei UI", 9)).pack(side="right")

        style_row = tk.Frame(simple_card, bg=COLORS["panel"])
        style_row.pack(fill="x", padx=18, pady=(0, 8))
        tk.Label(style_row, text="风格", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(anchor="w", pady=(0, 4))
        cards = tk.Frame(style_row, bg=COLORS["panel"])
        cards.pack(fill="x")
        self.beginner_style_buttons = []
        styles = [
            ("✦", "二次元", "anime"),
            ("▣", "电影感", "cinematic"),
            ("◐", "插画", "illustration"),
            ("◉", "写实", "photoreal"),
            ("⌁", "赛博朋克", "cyberpunk"),
            ("≋", "水彩", "watercolor"),
        ]
        for idx, (icon, label, value) in enumerate(styles):
            btn = tk.Button(cards, text=f"{icon} {label}", command=lambda l=label: self._select_beginner_style(l),
                            bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                            padx=10, pady=4, font=("Microsoft YaHei UI", 9), cursor="hand2")
            btn.grid(row=idx // 3, column=idx % 3, sticky="w", padx=(0, 5), pady=3)
            self.beginner_style_buttons.append((label, btn))
            if label == self.beginner_style.get():
                btn.configure(bg=COLORS["accent"], fg="#fff", activebackground=COLORS["accent2"])
        tk.Button(cards, text="× 无风格", command=lambda: self._select_beginner_style("无风格"),
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=6, pady=4, font=("Microsoft YaHei UI", 9), cursor="hand2").grid(
                      row=0, column=3, sticky="w", padx=(4, 0))

        ratio_row = tk.Frame(simple_card, bg=COLORS["panel"])
        ratio_row.pack(fill="x", padx=18, pady=(0, 6))
        tk.Label(ratio_row, text="画幅", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left", padx=(0, 8))
        self.beginner_ratio_buttons = []
        for label, icon in (("竖图", "▯"), ("方图", "□"), ("横图", "▭")):
            btn = tk.Button(ratio_row, text=f"{icon} {label}",
                            command=lambda l=label: self._select_beginner_ratio(l),
                            bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                            padx=8, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2")
            btn.pack(side="left", padx=(0, 5))
            self.beginner_ratio_buttons.append((label, btn))
            if label == self.beginner_ratio.get():
                btn.configure(bg=COLORS["accent"], fg="#fff", activebackground=COLORS["accent2"])

        bottom_row = tk.Frame(simple_card, bg=COLORS["panel"])
        bottom_row.pack(fill="x", padx=18, pady=(0, 8))
        tk.Label(bottom_row, text="张数", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left")
        for value in (1, 2, 4):
            tk.Radiobutton(bottom_row, text=str(value), variable=self.beginner_count_var,
                           value=value, bg=COLORS["panel"], fg=COLORS["text"],
                           activebackground=COLORS["panel"], selectcolor=COLORS["input"],
                           font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(4, 8))
        tk.Button(bottom_row, text="▣  打开输出", command=self.open_output_dir,
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=6, pady=4, cursor="hand2").pack(side="left", padx=(8, 0))
        self.beginner_generate_btn = tk.Button(
            bottom_row, text="开始生成", command=self.beginner_generate,
            bg=COLORS["accent"], fg="#fff", activebackground=COLORS["accent2"],
            activeforeground="#fff", relief="flat", bd=0, padx=22, pady=8,
            font=("Microsoft YaHei UI", 11, "bold"), cursor="hand2")
        self._decorate_button(self.beginner_generate_btn, "sparkles", "white")
        self.beginner_generate_btn.pack(side="right")

        self.beginner_progress = tk.Label(simple_card, text="准备就绪", bg=COLORS["panel"],
                                          fg=COLORS["accent2"], anchor="w",
                                          font=("Microsoft YaHei UI", 9, "bold"))
        self.beginner_progress.pack(fill="x", padx=18)
        progress_line = tk.Frame(simple_card, bg=COLORS["panel"])
        progress_line.pack(fill="x", padx=18, pady=(4, 8))
        self.beginner_progressbar = ttk.Progressbar(progress_line, orient="horizontal",
                                                     mode="determinate", maximum=4, value=0)
        self.beginner_progressbar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.beginner_stop_btn = tk.Button(progress_line, text="停止", state="disabled",
                                           command=self.stop_beginner_generation,
                                           bg=COLORS["card2"], fg=COLORS["text"],
                                           relief="flat", bd=0, padx=9, pady=2,
                                           font=("Microsoft YaHei UI", 9), cursor="hand2")
        self._decorate_button(self.beginner_stop_btn, "stop")
        self.beginner_stop_btn.pack(side="right")
        result_actions = tk.Frame(simple_card, bg=COLORS["panel"])
        result_actions.pack(fill="x", padx=18, pady=(0, 4))
        self.beginner_repeat_btn = tk.Button(
            result_actions, text="↻ 再来一张", state="disabled",
            command=self.repeat_beginner_generate,
            bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
            padx=10, pady=4, font=("Microsoft YaHei UI", 9), cursor="hand2")
        self.beginner_repeat_btn.pack(side="left")
        tk.Button(result_actions, text="▣ 打开输出", command=self.open_output_dir,
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=8, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(
                      side="left", padx=(6, 0))
        self.beginner_result_hint = tk.Label(
            result_actions, text="生成完成后可在这里继续操作",
            bg=COLORS["panel"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9))
        self.beginner_result_hint.pack(side="left", padx=(8, 0))
        self.beginner_results_inner = tk.Frame(simple_card, bg=COLORS["panel"])
        self.beginner_results_inner.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.beginner_result_photos = []
        self.beginner_result_paths = []
        self.beginner_mode_var.set(bool(self.settings.get("beginner_mode", True)))
        self._apply_beginner_mode(save=False)

        self._refresh_history()
        self.root.after(200, self._load_loras)
        self.root.after(650, self._refresh_beginner_env)

    # ---------- LoRA ----------
    def _load_loras(self):
        self.all_lora_files = scan_lora_files()
        self._filter_loras()

    def _filter_loras(self):
        base = self.lora_filter.get()
        if base == "全部":
            self.lora_files = list(self.all_lora_files)
        else:
            self.lora_files = [x for x in self.all_lora_files if x.get("base") == base]
        labels = [x["label"] for x in self.lora_files]
        self.lora_combo["values"] = labels
        if labels:
            self.lora_combo.current(0)
            self._on_lora_select()
            self.lora_status.configure(text=f"{base} · {len(labels)} 个 LoRA")
        else:
            self.lora_combo.set("")
            self.lora_trigger.delete(0, "end")
            self.lora_status.configure(text=f"{base} · 没有匹配的 LoRA")

    def _current_lora(self):
        label = self.lora_combo.get()
        return next((x for x in self.lora_files if x["label"] == label), None)

    def _on_lora_select(self):
        item = self._current_lora()
        if not item:
            return
        triggers, source = detect_triggers(item["path"], self.known_triggers)
        self.lora_trigger.delete(0, "end")
        self.lora_trigger.insert(0, " / ".join(triggers))
        self.lora_status.configure(text=source)

    def _add_lora(self):
        item = self._current_lora()
        if not item:
            return
        trigger = self.lora_trigger.get().strip()
        for old in list(self.selected_loras):
            if old["path"] == item["path"]:
                self.selected_loras.remove(old)
        self.selected_loras.append({
            "name": item["name"],
            "label": item["label"],
            "path": str(item["path"]),
            "base": item.get("base", ""),
            "trigger": trigger,
            "strength": round(float(self.lora_strength.get()), 2),
            "enabled": True,
        })
        self._refresh_lora_selected()
        self.lora_status.configure(text="已加入当前生成上下文")

    def _remove_lora(self):
        sel = self.lora_selected_list.curselection()
        if sel:
            idx = sel[0]
            if idx < len(self.selected_loras):
                self.selected_loras.pop(idx)
                self._refresh_lora_selected()

    def _toggle_lora_enabled(self):
        sel = self.lora_selected_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self.selected_loras):
            item = self.selected_loras[idx]
            item["enabled"] = not bool(item.get("enabled", True))
            self._refresh_lora_selected()

    def _refresh_lora_selected(self):
        self.lora_selected_list.delete(0, "end")
        for item in self.selected_loras:
            trig = item.get("trigger") or "无明确触发词"
            state = "开" if item.get("enabled", True) else "旁"
            strength = item.get("strength", 0.7)
            self.lora_selected_list.insert("end", f"[{state}] {item['name']}｜{strength}｜{trig}")

    def _lora_context(self):
        active = [x for x in self.selected_loras if x.get("enabled", True)]
        if not active:
            return ""
        lines = ["当前加载的 LoRA（用户已选择，必须围绕它们写提示词）："]
        for item in active:
            trig = item.get("trigger") or "未提供，按完整描述"
            lines.append(f"- {item['name']}；强度：{item.get('strength', 0.7)}；触发词：{trig}")
        lines.append("规则：触发词自然融入 Positive，不要只堆触发词；没有明确触发词时不要编造。")
        return "\n".join(lines)

    def _recommend_lora_inline(self):
        prompt = self.positive_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning(APP_NAME, "先在 Positive 里写提示词。")
            return
        key = self._current_generation_key()
        wf = self._current_workflow_info()
        base = wf["base"]
        self.lora_recommend_frame.pack(fill="x", padx=8, pady=(2, 2), before=self.lora_status)
        for w in self.lora_recommend_frame.winfo_children():
            w.destroy()
        self.lora_rec_rows = []
        tk.Label(self.lora_recommend_frame, text=f"推荐中 · {base}…", bg=COLORS["panel"],
                 fg=COLORS["accent2"], font=("Microsoft YaHei UI", 9), anchor="w").pack(fill="x", padx=8, pady=5)
        self.lora_status.configure(text="本地 9B 正在分析提示词与 LoRA…")
        self.lora_recommend_btn.configure(state="disabled", text="分析中…")
        q = queue.Queue()

        def worker():
            try:
                cands = []
                for item in self.all_lora_files:
                    if item.get("base") != base:
                        continue
                    trig, _ = detect_triggers(item["path"], self.known_triggers)
                    cands.append({"name": item["name"], "label": item["label"],
                                  "path": str(item["path"]), "base": item.get("base", ""),
                                  "trigger": " / ".join(trig)})
                chosen, raw = lora_match.auto_match(prompt, base, cands, model=self.model_map.get(self.model_var.get()))
                q.put(("ok", chosen))
            except Exception as e:
                q.put(("err", str(e)))

        def poll():
            try:
                kind, payload = q.get_nowait()
            except queue.Empty:
                self.root.after(400, poll)
                return
            self.lora_recommend_btn.configure(state="normal", text="推荐 LoRA")
            if kind == "err":
                self.lora_status.configure(text="推荐失败：" + payload[:160])
                for w in self.lora_recommend_frame.winfo_children():
                    w.destroy()
                self.lora_recommend_frame.pack_forget()
                return
            self.used_models.add(lora_match.MODEL)
            for w in self.lora_recommend_frame.winfo_children():
                w.destroy()
            self.lora_rec_rows = []
            for item in payload:
                row = tk.Frame(self.lora_recommend_frame, bg=COLORS["panel"])
                row.pack(fill="x", padx=8, pady=(4, 2))
                enabled = tk.BooleanVar(value=True)
                strength = tk.DoubleVar(value=item.get("strength", 0.7))
                tk.Checkbutton(row, variable=enabled, bg=COLORS["panel"],
                               activebackground=COLORS["panel"], selectcolor=COLORS["panel"]).pack(side="left")
                tk.Label(row, text=item["name"][:44], bg=COLORS["panel"], fg=COLORS["text"],
                         font=("Microsoft YaHei UI", 9), anchor="w").pack(side="left", fill="x", expand=True)
                tk.Label(row, text="强度", bg=COLORS["panel"], fg=COLORS["muted"],
                         font=("Microsoft YaHei UI", 9)).pack(side="left")
                tk.Spinbox(row, from_=0.1, to=1.2, increment=0.05, textvariable=strength,
                           width=4, bg=COLORS["input"], fg=COLORS["text"], relief="flat", bd=0).pack(side="left", padx=(3, 0))
                reason = item.get("reason", "")
                if reason:
                    tk.Label(self.lora_recommend_frame, text="  " + reason[:100], bg=COLORS["panel"],
                             fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), anchor="w",
                             justify="left", wraplength=470).pack(fill="x", padx=10)
                self.lora_rec_rows.append((item, enabled, strength))
            apply_row = tk.Frame(self.lora_recommend_frame, bg=COLORS["panel"])
            apply_row.pack(fill="x", padx=8, pady=(3, 6))

            def apply():
                selected = []
                for item, enabled, strength in self.lora_rec_rows:
                    if not enabled.get():
                        continue
                    selected.append({
                        "name": item["name"], "label": item.get("label", item["name"]),
                        "path": item["path"], "base": item.get("base", base),
                        "trigger": item.get("trigger", ""),
                        "strength": round(float(strength.get()), 2), "enabled": True,
                    })
                if not selected:
                    messagebox.showwarning(APP_NAME, "至少勾选一个推荐项。")
                    return
                self.selected_loras = selected
                self._refresh_lora_selected()
                self.lora_status.configure(text=f"已应用 {len(selected)} 个推荐")
                self.lora_recommend_frame.pack_forget()

            def clear():
                self.lora_recommend_frame.pack_forget()

            tk.Button(apply_row, text="应用推荐", bg=COLORS["accent"], fg="#fff",
                      activebackground=COLORS["accent2"], relief="flat", bd=0, padx=10, pady=3,
                      font=("Microsoft YaHei UI", 9), cursor="hand2", command=apply).pack(side="left")
            tk.Button(apply_row, text="收起", bg=COLORS["card2"], fg=COLORS["text"],
                      activebackground=COLORS["accent2"], relief="flat", bd=0, padx=8, pady=3,
                      font=("Microsoft YaHei UI", 9), cursor="hand2", command=clear).pack(side="right")
            self.lora_status.configure(text=f"推荐 {len(payload)} 个，可勾选/改强度后应用")
            self.root.after(80, lambda: self.left_canvas.yview_moveto(1.0))
            self.root.after(120, self._bind_left_mousewheel)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(300, poll)

    def open_lora_recommend_dialog(self):
        if getattr(self, "recommend_dialog", None) is not None:
            try:
                self.recommend_dialog.lift()
                return
            except Exception:
                self.recommend_dialog = None

        top = tk.Toplevel(self.root)
        self.recommend_dialog = top
        top.title("推荐 LoRA")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 700, 520)
        top.transient(self.root)
        top.resizable(False, False)
        try:
            top.iconbitmap(str(APP_ICON))
        except Exception:
            pass

        tk.Label(top, text="推荐 LoRA", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        prompt = self.positive_text.get("1.0", "end").strip()
        preview = (prompt[:150] + "…") if len(prompt) > 150 else prompt
        tk.Label(top, text="提示词：" + (preview or "（Positive 为空）"), bg=COLORS["bg"],
                 fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), anchor="w",
                 justify="left", wraplength=650).pack(fill="x", padx=20)
        base = wbgen.WORKFLOWS[wbgen.workflow_for_target(self.target_var.get())]["base"]
        tk.Label(top, text=f"目标底模：{base}", bg=COLORS["bg"], fg=COLORS["accent2"],
                 font=("Microsoft YaHei UI", 9, "bold"), anchor="w").pack(fill="x", padx=20, pady=(4, 8))

        status = tk.Label(top, text="点“开始分析”，9B 只从该底模的已安装 LoRA 中推荐。",
                          bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL, anchor="w")
        status.pack(fill="x", padx=20)
        result_box = tk.Frame(top, bg=COLORS["panel"], highlightbackground=COLORS["line"],
                              highlightthickness=1)
        result_box.pack(fill="both", expand=True, padx=20, pady=(8, 8))
        result_inner = tk.Frame(result_box, bg=COLORS["panel"])
        result_inner.pack(fill="both", expand=True, padx=10, pady=8)
        rows = []
        q = queue.Queue()

        def clear_rows():
            nonlocal rows
            for w in result_inner.winfo_children():
                w.destroy()
            rows = []

        def render(chosen):
            clear_rows()
            for i, item in enumerate(chosen, 1):
                frame = tk.Frame(result_inner, bg=COLORS["card2"])
                frame.pack(fill="x", pady=3)
                enabled = tk.BooleanVar(value=True)
                strength = tk.DoubleVar(value=item.get("strength", 0.7))
                tk.Checkbutton(frame, variable=enabled, bg=COLORS["card2"],
                               activebackground=COLORS["card2"], selectcolor=COLORS["card2"]).pack(side="left", padx=(8, 2))
                tk.Label(frame, text=item["name"][:62], bg=COLORS["card2"], fg=COLORS["text"],
                         font=("Microsoft YaHei UI", 9), anchor="w").pack(side="left", fill="x", expand=True)
                tk.Label(frame, text="强度", bg=COLORS["card2"], fg=COLORS["muted"],
                         font=("Microsoft YaHei UI", 9)).pack(side="left")
                tk.Spinbox(frame, from_=0.1, to=1.2, increment=0.05, textvariable=strength,
                           width=4, bg=COLORS["input"], fg=COLORS["text"], relief="flat", bd=0).pack(side="left", padx=(3, 8))
                reason = tk.Label(result_inner, text="  理由：" + item.get("reason", ""),
                                  bg=COLORS["panel"], fg=COLORS["muted"], font=("Microsoft YaHei UI", 9),
                                  anchor="w", justify="left", wraplength=620)
                reason.pack(fill="x", padx=10, pady=(0, 3))
                rows.append((item, enabled, strength))
            status.configure(text=f"推荐 {len(chosen)} 个；可取消勾选或调整强度后再应用。",
                             fg=COLORS["green"])

        def analysis_worker():
            try:
                cands = []
                for item in self.all_lora_files:
                    if item.get("base") != base:
                        continue
                    trig, _ = detect_triggers(item["path"], self.known_triggers)
                    cands.append({"name": item["name"], "label": item["label"],
                                  "path": str(item["path"]), "base": item.get("base", ""),
                                  "trigger": " / ".join(trig)})
                chosen, raw = lora_match.auto_match(prompt, base, cands, model=self.model_map.get(self.model_var.get()))
                q.put(("ok", chosen))
            except Exception as e:
                q.put(("err", str(e)))

        def poll():
            if not top.winfo_exists():
                return
            try:
                kind, payload = q.get_nowait()
            except queue.Empty:
                top.after(400, poll)
                return
            analyze_btn.configure(state="normal", text="开始分析")
            if kind == "ok":
                self.used_models.add(lora_match.MODEL)
                render(payload)
            else:
                status.configure(text="分析失败：" + payload[:180], fg=COLORS["red"])
                messagebox.showerror(APP_NAME, payload, parent=top)

        def analyze():
            if not prompt:
                messagebox.showwarning(APP_NAME, "Positive 提示词为空。", parent=top)
                return
            analyze_btn.configure(state="disabled", text="分析中…")
            status.configure(text="本地 9B 正在分析提示词与 LoRA…", fg=COLORS["accent2"])
            threading.Thread(target=analysis_worker, daemon=True).start()
            top.after(300, poll)

        def apply():
            selected = []
            for item, enabled, strength in rows:
                if not enabled.get():
                    continue
                selected.append({
                    "name": item["name"], "label": item.get("label", item["name"]),
                    "path": item["path"], "base": item.get("base", base),
                    "trigger": item.get("trigger", ""),
                    "strength": round(float(strength.get()), 2), "enabled": True,
                })
            if not selected:
                messagebox.showwarning(APP_NAME, "至少勾选一个推荐项。", parent=top)
                return
            self.selected_loras = selected
            self._refresh_lora_selected()
            status.configure(text="已应用推荐，回到工作台后可继续开/旁和调强度。", fg=COLORS["green"])
            top.after(300, top.destroy)

        buttons = tk.Frame(top, bg=COLORS["bg"])
        buttons.pack(fill="x", padx=20, pady=(0, 12))
        analyze_btn = tk.Button(buttons, text="开始分析", bg=COLORS["accent"], fg="#fff",
                                activebackground=COLORS["accent2"], relief="flat", bd=0,
                                padx=16, pady=6, font=("Microsoft YaHei UI", 9, "bold"), cursor="hand2")
        analyze_btn.pack(side="left")
        tk.Button(buttons, text="应用推荐", bg=COLORS["card2"], fg=COLORS["text"],
                  activebackground=COLORS["accent2"], relief="flat", bd=0, padx=14, pady=6,
                  font=FONT_SMALL, cursor="hand2", command=apply).pack(side="right")
        analyze_btn.configure(command=analyze)

        def on_close():
            self.recommend_dialog = None
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", on_close)

    def _load_settings(self):
        saved_label = self.settings.get("model")
        self.desired_model_id = self.settings.get("model_id")
        model_label = saved_label if saved_label else MODEL_OPTIONS[0][0]
        target = self.settings.get("target", list(TARGETS.keys())[0])
        if target not in TARGETS:
            target = list(TARGETS.keys())[0]
        self.model_var.set(model_label)
        self.target_var.set(target)
        mode = self.settings.get("mode")
        if mode not in ("SFW", "NSFW"):
            mode = "SFW" if not self.settings.get("nsfw", False) else "NSFW"
        self.mode.set(mode)
        self._update_mode_button()
        self._link_done = False
        self._on_target_change(False)
        self._refresh_top_workflows()
        saved_wf = self.settings.get("generation_workflow")
        saved_key = next((k for k, spec in wbgen.WORKFLOWS.items() if spec["name"] == saved_wf), None)
        saved_imp = self._find_imported(saved_wf)
        target_base = wbgen.WORKFLOWS[wbgen.workflow_for_target(target)]["base"]
        if saved_wf == EMPTY_WORKFLOW_LABEL:
            self.generation_workflow_var.set(saved_wf)
        elif saved_imp:
            imp_base = saved_imp.get("base", "Unknown")
            if imp_base in BASE_TARGET:
                self.target_var.set(BASE_TARGET[imp_base])
                self._update_target_desc()
            if imp_base in BASE_FILTERS:
                self.lora_filter.set(imp_base)
                if getattr(self, "all_lora_files", None):
                    self._filter_loras()
            self.generation_workflow_var.set(saved_wf)
        elif saved_key and wbgen.WORKFLOWS[saved_key]["base"] == target_base:
            self.generation_workflow_var.set(saved_wf)
        self._refresh_top_workflows()
        self._on_model_change()

    def _save_settings(self):
        save_json(SETTINGS_FILE, {
            "model": self.model_var.get(),
            "model_id": self.model_map.get(self.model_var.get(), ""),
            "target": self.target_var.get(),
            "generation_workflow": self.generation_workflow_var.get(),
            "mode": self.mode.get(),
            "nsfw": self.mode.get() != "SFW",
            "output_dir": str(self.output_dir),
            "auto_pick": bool(self.auto_pick_var.get()),
            "beginner_mode": bool(self.beginner_mode_var.get()),
            "beginner_base": self.beginner_base_key,
            "beginner_style": self.beginner_style.get(),
            "beginner_ratio": self.beginner_ratio.get(),
            "beginner_count": int(self.beginner_count_var.get() or 1),
            "civitai_guide_seen": bool(getattr(self, "civitai_guide_seen", False)),
        })

    def _sync_generation_workflow(self):
        key = wbgen.workflow_for_target(self.target_var.get())
        self.generation_workflow_var.set(wbgen.WORKFLOWS[key]["name"])

    def _on_generation_workflow_change(self):
        should_sync = not self._link_done
        self._link_done = True
        wf = self._current_workflow_info()
        base = wf.get("base", "Unknown")
        if should_sync and base in BASE_TARGET:
            self.target_var.set(BASE_TARGET[base])
            self._update_target_desc()
        if should_sync and base in BASE_FILTERS:
            self.lora_filter.set(base)
            if getattr(self, "all_lora_files", None):
                self._filter_loras()
        self._save_settings()

    def _update_target_desc(self):
        cfg = TARGETS.get(self.target_var.get(), {})
        status, note = model_guide.hint_for_target(self.target_var.get())
        text = f"  {cfg.get('desc', '')}    NSFW：{status} · {note}"
        self.target_desc.configure(text=text)

    def _on_lora_filter_change(self):
        should_sync = not self._link_done
        self._link_done = True
        base = self.lora_filter.get()
        if should_sync and base in BASE_TARGET:
            self.target_var.set(BASE_TARGET[base])
            self._update_target_desc()
        if should_sync and base in BASE_WORKFLOW:
            self.generation_workflow_var.set(wbgen.WORKFLOWS[BASE_WORKFLOW[base]]["name"])
        if getattr(self, "all_lora_files", None):
            self._filter_loras()
        self._save_settings()

    def _current_generation_key(self):
        label = self.generation_workflow_var.get()
        for key, spec in wbgen.WORKFLOWS.items():
            if spec["name"] == label:
                return key
        return wbgen.workflow_for_target(self.target_var.get())

    def _workflow_labels(self):
        labels = [EMPTY_WORKFLOW_LABEL]
        labels += [spec["name"] for spec in wbgen.WORKFLOWS.values()]
        labels += [x.get("label") or ("导入 · " + x.get("name", "")) for x in self.imported_workflows]
        return labels

    def _refresh_top_workflows(self):
        self._apply_workflow_filter()
        if self.generation_workflow_var.get() not in self._workflow_labels():
            self._sync_generation_workflow()

    def _apply_workflow_filter(self):
        labels = self._workflow_labels()
        query = self.workflow_search_var.get().strip().casefold()
        filtered = [x for x in labels if query in x.casefold()] if query else labels
        self.generation_workflow_combo.configure(values=filtered)
        if query and not filtered:
            self.status_var.set("没有匹配的工作流，点“清”恢复全部")
        elif query:
            self.status_var.set(f"工作流匹配 {len(filtered)} / {len(labels)} 个")
        else:
            self.status_var.set(f"工作流共 {len(labels)} 个")

    def clear_workflow_search(self):
        self.workflow_search_var.set("")
        self._apply_workflow_filter()
        self.workflow_search_entry.focus_set()

    def _find_imported(self, label):
        return next((x for x in self.imported_workflows if (x.get("label") or ("导入 · " + x.get("name", ""))) == label), None)

    def _current_workflow_info(self):
        label = self.generation_workflow_var.get()
        if label == EMPTY_WORKFLOW_LABEL:
            key = wbgen.workflow_for_target(self.target_var.get())
            return {"kind": "builtin", "key": key,
                    "base": wbgen.WORKFLOWS[key]["base"],
                    "label": label, "empty": True}
        imported = self._find_imported(label)
        if imported:
            return {"kind": "imported", "path": imported["path"], "base": imported.get("base", "Unknown"),
                    "label": label, "loras": imported.get("loras", 0), "name": imported.get("name", label)}
        for key, spec in wbgen.WORKFLOWS.items():
            if spec["name"] == label:
                return {"kind": "builtin", "key": key, "base": spec["base"], "label": label}
        key = wbgen.workflow_for_target(self.target_var.get())
        return {"kind": "builtin", "key": key, "base": wbgen.WORKFLOWS[key]["base"],
                "label": wbgen.WORKFLOWS[key]["name"]}

    def _workflow_initial_dir(self):
        configured = CFG.get("comfy_workflows_dir")
        if configured and Path(configured).exists():
            return str(configured)
        for root in CFG.paths("lora_roots"):
            candidate = root.parent.parent / "user" / "default" / "workflows"
            if candidate.exists():
                return str(candidate)
        return str(Path.home())

    def _import_workflow(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="导入 ComfyUI 工作流",
            initialdir=self._workflow_initial_dir(),
            filetypes=[("ComfyUI JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            imp = wfimport.load_workflow(path)
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e), parent=self.root)
            return
        name = Path(path).stem
        label = "导入 · " + name
        entry = {"name": name, "label": label, "path": str(path), "base": imp["base"],
                 "format": imp["format"], "loras": len(imp["loras"]), "node_count": imp["node_count"]}
        self.imported_workflows = [x for x in self.imported_workflows if str(x.get("path", "")).casefold() != str(path).casefold()]
        self.imported_workflows.append(entry)
        save_json(IMPORTED_WORKFLOWS_FILE, self.imported_workflows)
        self._refresh_top_workflows()
        self.generation_workflow_var.set(label)
        self._on_generation_workflow_change()
        self._save_settings()
        self.status_var.set(f"已导入工作流：{name}（{imp['base']}，LoRA {len(imp['loras'])}）")

    def _on_model_change(self):
        self._save_settings()
        if "27B" in self.model_var.get():
            self.status_var.set("27B 需要约 16GB 显存")
        else:
            self.status_var.set("LLM 模型已选择")

    def _on_target_change(self, manual=True):
        if manual:
            should_sync = not self._link_done
            self._link_done = True
        else:
            should_sync = True
        target = self.target_var.get()
        base = TARGET_LORA_FILTER.get(target, "")
        if should_sync and base in BASE_WORKFLOW:
            self.generation_workflow_var.set(wbgen.WORKFLOWS[BASE_WORKFLOW[base]]["name"])
        if should_sync and base in BASE_FILTERS:
            self.lora_filter.set(base)
            if getattr(self, "all_lora_files", None):
                self._filter_loras()
        self._update_target_desc()
        self._save_settings()

    def toggle_mode(self):
        order = ["SFW", "NSFW"]
        mode = self.mode.get()
        idx = order.index(mode) if mode in order else 0
        self.mode.set(order[(idx + 1) % len(order)])
        self._update_mode_button()
        self._save_settings()

    def _update_mode_button(self):
        mode = self.mode.get()
        if mode == "NSFW":
            self.mode_btn.configure(text="NSFW", bg=COLORS["red"], activebackground=COLORS["red"])
            self.mode_hint.configure(text="成人虚构 · 保留硬限制")
            if hasattr(self, "beginner_mode_btn"):
                self.beginner_mode_btn.configure(text="NSFW", bg=COLORS["red"], activebackground=COLORS["red"])
        else:
            self.mode_btn.configure(text="SFW", bg=COLORS["green"], activebackground=COLORS["green"])
            self.mode_hint.configure(text="默认 SFW")
            if hasattr(self, "beginner_mode_btn"):
                self.beginner_mode_btn.configure(text="SFW", bg=COLORS["green"], activebackground=COLORS["green"])
        self._update_beginner_base_label()
        self._update_base_recommendation()
        self._beginner_style_select_highlight()

    def _beginner_base(self):
        return next((x for x in BEGINNER_BASES if x["key"] == self.beginner_base_key), BEGINNER_BASES[0])

    def _beginner_target(self):
        base = self._beginner_base()
        return base["target"], f"{base['icon']} {base['label']}"

    def _update_beginner_base_label(self):
        if not hasattr(self, "beginner_base_label"):
            return
        base = self._beginner_base()
        suffix = " · NSFW 需匹配 LoRA" if self.mode.get() == "NSFW" and base["key"] != "moss" else ""
        vram = int(getattr(self, "gpu_vram_mb", 0) or 0)
        need = BASE_VRAM_REQUIREMENTS.get(base["key"], 0)
        shortage = bool(vram and need and need > vram)
        if shortage:
            suffix += f" · ⚠ 显存偏低（约需 {need / 1024:.0f}GB）"
        self.beginner_base_label.configure(
            text=f"{base['note']}{suffix}",
            fg=COLORS["red"] if shortage else COLORS["accent2"])

    def _recommended_beginner_base(self):
        style = self.beginner_style.get()
        mapping = (NSFW_STYLE_BASE_RECOMMENDATIONS if self.mode.get() == "NSFW"
                   else STYLE_BASE_RECOMMENDATIONS)
        ideal_key, reason = mapping.get(style, ("illustrious", "通用默认"))
        ideal = next((x for x in BEGINNER_BASES if x["key"] == ideal_key), BEGINNER_BASES[0])
        vram = int(getattr(self, "gpu_vram_mb", 0) or 0)
        vram_text = f"显存 {vram / 1024:.0f}GB" if vram else "显存未检测"
        if not vram:
            return ideal, f"{reason}；{vram_text}", vram_text
        need = BASE_VRAM_REQUIREMENTS.get(ideal_key, 0)
        if need <= vram:
            return ideal, f"{reason}；显存足够", vram_text
        fallback = None
        for key in ("illustrious", "anima"):
            candidate = next((x for x in BEGINNER_BASES if x["key"] == key), None)
            if candidate and BASE_VRAM_REQUIREMENTS.get(key, 0) <= vram:
                fallback = candidate
                break
        if fallback is None:
            fallback = next((x for x in BEGINNER_BASES if x["key"] == "anima"), BEGINNER_BASES[0])
        return fallback, f"风格首选 {ideal['label']} 显存不够；建议 {fallback['label']}", vram_text

    def _update_base_recommendation(self):
        if not hasattr(self, "beginner_base_reco_label"):
            return
        base, reason, vram_text = self._recommended_beginner_base()
        self.beginner_base_reco_key = base["key"]
        prefix = f"{vram_text} · "
        if self.beginner_base_key == base["key"]:
            self.beginner_base_reco_label.configure(
                text=f"{prefix}推荐：{base['label']} · 已采用")
            self.beginner_base_adopt_btn.pack_forget()
        else:
            self.beginner_base_reco_label.configure(
                text=f"{prefix}{base['label']} · {reason}（不强制）")
            self.beginner_base_adopt_btn.pack(side="left", padx=(8, 0))

    def _adopt_recommended_base(self):
        if self.beginner_base_reco_key:
            self._select_beginner_base(self.beginner_base_reco_key)

    def _update_beginner_base_summary(self):
        if not hasattr(self, "beginner_base_summary"):
            return
        base = self._beginner_base()
        self.beginner_base_summary.configure(text=f"{base['icon']} {base['label']}")

    def _toggle_beginner_base_cards(self):
        if not hasattr(self, "beginner_base_cards"):
            return
        if self.beginner_base_cards.winfo_manager():
            self.beginner_base_cards.pack_forget()
            self.beginner_base_toggle_btn.configure(text="换底模")
        else:
            self.beginner_base_cards.pack(side="left", padx=(8, 0))
            self.beginner_base_toggle_btn.configure(text="收起")

    def _select_beginner_base(self, key):
        base = next((x for x in BEGINNER_BASES if x["key"] == key), None)
        if not base:
            return
        self.beginner_base_key = key
        for name, btn in getattr(self, "beginner_base_buttons", []):
            if name == key:
                btn.configure(bg=COLORS["accent"], fg="#fff", activebackground=COLORS["accent2"])
            else:
                btn.configure(bg=COLORS["card2"], fg=COLORS["text"], activebackground=COLORS["card2"])
        self.beginner_base_cards.pack_forget()
        self.beginner_base_toggle_btn.configure(text="换底模")
        self._update_beginner_base_summary()
        self.target_var.set(base["target"])
        self._on_target_change(manual=False)
        self.generation_workflow_var.set(wbgen.WORKFLOWS[base["workflow"]]["name"])
        self._update_beginner_base_label()
        self._update_base_recommendation()
        self._refresh_beginner_missing()
        self._save_settings()

    def _beginner_missing(self):
        base = self._beginner_base()
        return model_center.missing_profile_files(CFG, base["workflow"], wbgen.MODEL_FILES)

    def _refresh_beginner_missing(self):
        if not hasattr(self, "beginner_missing_frame"):
            return
        missing = self._beginner_missing()
        self.beginner_missing_files = missing
        if not missing:
            self.beginner_missing_frame.pack_forget()
            self._refresh_beginner_model_status()
            return
        role_names = {"checkpoint": "checkpoint", "unet": "UNET", "clip": "文本编码器", "vae": "VAE"}
        detail = "；".join(
            f"{role_names.get(x['role'], x['role'])}：{x['filename']}" for x in missing)
        self.beginner_missing_label.configure(
            text=f"⚠ 当前底模缺少 {len(missing)} 个模型文件：{detail}。"
                 "请点右侧补齐，否则出图会失败。")
        if not self.beginner_missing_frame.winfo_manager():
            self.beginner_missing_frame.pack(
                fill="x", padx=18, pady=(0, 8), before=self.beginner_brief)
        self._refresh_beginner_model_status()

    def _missing_dsh_prompt_text(self):
        base = self._beginner_base()
        missing = self._beginner_missing()
        if not missing:
            return ""
        role_names = {"checkpoint": "checkpoint", "unet": "UNET", "clip": "文本编码器", "vae": "VAE"}
        missing_text = "\n".join(
            f"- {role_names.get(x['role'], x['role'])}：{x['filename']}" for x in missing)
        return f"""你是 DSH，请修复“提示词工作台”发布版的缺模型问题。

程序目录：{APP_DIR}
配置目录：{CFG.path}
当前简洁底模：{base['label']}
对应工作流：{base['workflow']}
不要修改归档版 D:\\prompt-workbench，不要覆盖历史记录。

检测到缺少：
{missing_text}

当前配置：
- ComfyUI：{CFG.get('comfy_url')}
- LoRA 根目录：{'; '.join(str(x) for x in CFG.paths('lora_roots')) or '未配置'}
- 底模目录：{CFG.get('checkpoint_dir') or '未配置'}
- 工作流目录：{CFG.get('comfy_workflows_dir') or '未配置'}
- skills：{CFG.get('skills_dir') or '未配置'}

请直接部署并接入：
1. 先盘点现有模型，不重复下载；能复用就复用。
2. 缺什么补什么；超过 1GB 的下载先报告大小、磁盘空间和通道，等我确认。
3. 优先直连 Civitai/Hugging Face；失败可测试 Ikuuu 或同类网络工具，它们不是模型来源。
4. 下载后校验 SHA256（有哈希时），放入正确模型目录。
5. 更新 config.json 的 model_files 和工作流配置。
6. 不要输出或提交 API Key。
7. 完成后运行 tools/selfcheck.py，并做 832×1216 的 SFW/NSFW 最小测试。
8. 报告真实加载的模型文件、测试图片路径、耗时和失败原因。
"""

    def _show_missing_dsh_prompt(self):
        text = self._missing_dsh_prompt_text()
        if not text:
            return
        prompt_top = tk.Toplevel(self.root)
        prompt_top.title("缺模型 · DSH 部署提示词")
        prompt_top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, prompt_top, 820, 620)
        prompt_top.transient(self.root)
        tk.Label(prompt_top, text="缺模型 · DSH 部署提示词", bg=COLORS["bg"],
                 fg=COLORS["text"], font=("Microsoft YaHei UI", 14, "bold")).pack(
                     anchor="w", padx=18, pady=(14, 2))
        tk.Label(prompt_top, text="复制给 DSH，让它补齐当前底模；不包含 API Key。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=18)
        box = ScrolledText(prompt_top, wrap="word", bg=COLORS["panel"], fg=COLORS["text"],
                           relief="flat", bd=0, font=("Consolas", 9), padx=12, pady=10)
        box.pack(fill="both", expand=True, padx=18, pady=(8, 6))
        box.insert("1.0", text)
        box.configure(state="disabled")

        def copy():
            prompt_top.clipboard_clear()
            prompt_top.clipboard_append(text)
            prompt_top.update_idletasks()
            messagebox.showinfo(APP_NAME, "DSH 提示词已复制。", parent=prompt_top)

        bar = tk.Frame(prompt_top, bg=COLORS["bg"])
        bar.pack(fill="x", padx=18, pady=(0, 12))
        tk.Button(bar, text="复制", command=copy, bg=COLORS["accent"], fg="#fff",
                  relief="flat", bd=0, padx=14, pady=5, cursor="hand2").pack(side="left")
        tk.Button(bar, text="关闭", command=prompt_top.destroy, bg=COLORS["panel"],
                  fg=COLORS["muted"], relief="flat", bd=0, padx=10, pady=5,
                  cursor="hand2").pack(side="right")

    def _copy_missing_dsh_prompt(self):
        text = self._missing_dsh_prompt_text()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()
        self.status_var.set("缺模型 DSH 提示词已复制")

    def _refresh_beginner_model_status(self):
        if not hasattr(self, "beginner_model_status"):
            return
        missing = self._beginner_missing()
        if missing:
            self.beginner_model_status.configure(text=f"底模 缺 {len(missing)} 个文件",
                                                 fg=COLORS["red"])
        else:
            self.beginner_model_status.configure(text="底模 ✓", fg=COLORS["green"])

    def _refresh_beginner_env(self):
        if self._env_check_running or not hasattr(self, "beginner_llm_status"):
            return
        self._env_check_running = True
        self.beginner_prepare_btn.configure(state="disabled", text="检查中…")
        self.beginner_llm_status.configure(text="LLM 检查中…", fg=COLORS["muted"])
        self.beginner_comfy_status.configure(text="ComfyUI 检查中…", fg=COLORS["muted"])
        self._refresh_beginner_model_status()

        def worker():
            llm_text, llm_ok = "LLM ✕", False
            try:
                models = llm_client.list_models(CFG)
                llm_text, llm_ok = f"LLM ✓ {len(models)} 个模型", True
            except Exception:
                llm_text = "LLM ✕ 未连接"
            comfy_text, comfy_ok = "ComfyUI ✕", False
            try:
                with urllib.request.urlopen(str(CFG.get("comfy_url")).rstrip("/") + "/system_stats",
                                            timeout=4) as r:
                    comfy_ok = r.status < 500
                    comfy_text = "ComfyUI ✓" if comfy_ok else f"ComfyUI HTTP {r.status}"
            except Exception:
                comfy_text = "ComfyUI ✕ 未启动"
            self.env_queue.put((llm_text, llm_ok, comfy_text, comfy_ok))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(250, self._poll_beginner_env)

    def _poll_beginner_env(self):
        try:
            llm_text, llm_ok, comfy_text, comfy_ok = self.env_queue.get_nowait()
        except queue.Empty:
            self.root.after(300, self._poll_beginner_env)
            return
        self._env_check_running = False
        self.beginner_llm_status.configure(text=llm_text,
                                           fg=COLORS["green"] if llm_ok else COLORS["red"])
        self.beginner_comfy_status.configure(text=comfy_text,
                                             fg=COLORS["green"] if comfy_ok else COLORS["red"])
        self.beginner_prepare_btn.configure(state="normal", text="一键准备")
        self._refresh_beginner_model_status()
        APP_LOG.info("环境状态: %s / %s", llm_text, comfy_text)

    def _beginner_prepare_all(self):
        if self._env_check_running:
            return
        self._env_check_running = True
        self.beginner_prepare_btn.configure(state="disabled", text="准备中…")
        self.beginner_comfy_status.configure(text="ComfyUI 准备中…", fg=COLORS["muted"])
        self.beginner_llm_status.configure(text="LLM 检查中…", fg=COLORS["muted"])

        def worker():
            comfy_error = ""
            try:
                if not wbgen.comfy_is_up():
                    wbgen.ensure_comfy()
            except Exception as e:
                comfy_error = str(e)
            llm_text, llm_ok = "LLM ✕ 未连接", False
            try:
                models = llm_client.list_models(CFG)
                llm_text, llm_ok = f"LLM ✓ {len(models)} 个模型", True
            except Exception:
                pass
            comfy_text, comfy_ok = "ComfyUI ✕", False
            try:
                with urllib.request.urlopen(str(CFG.get("comfy_url")).rstrip("/") + "/system_stats",
                                            timeout=5) as r:
                    comfy_ok = r.status < 500
                    comfy_text = "ComfyUI ✓" if comfy_ok else f"ComfyUI HTTP {r.status}"
            except Exception:
                comfy_text = "ComfyUI ✕ " + (comfy_error[:50] if comfy_error else "未启动")
            self.env_queue.put((llm_text, llm_ok, comfy_text, comfy_ok))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(300, self._poll_beginner_env)

    def clear_beginner_character(self):
        pinned = getattr(self, "beginner_pinned_lora", None)
        if pinned:
            target = str(Path(pinned.get("path", "")).resolve())
            self.selected_loras = [
                x for x in self.selected_loras
                if str(Path(x.get("path", "")).resolve()) != target
            ]
        self.beginner_pinned_lora = None
        self.beginner_character_trigger = ""
        if hasattr(self, "beginner_character_label"):
            self.beginner_character_label.configure(text="角色：未选择")
        self._refresh_lora_selected()
        self.status_var.set("已清除角色")

    def _character_aliases(self, query, model_id=""):
        prompt = (
            "把下面的角色中文名/别名转换成适合 Civitai 搜索的英文名、罗马音和常见拼写。"
            "输出 JSON 字符串数组，最多 6 个，不要解释。"
            "优先官方英文名和通行罗马音；不要只给中文。\n"
            f"角色：{query}"
        )
        raw = llm_client.chat(CFG, [{"role": "user", "content": prompt}],
                              model=model_id, temperature=0.2, num_predict=220)
        text = re.sub(r"^```(?:json)?\s*", "", (raw or "").strip())
        text = re.sub(r"\s*```$", "", text)
        items = []
        try:
            match = re.search(r"\[.*\]", text, re.S)
            if match:
                items = json.loads(match.group(0))
        except Exception:
            items = []
        if not isinstance(items, list):
            items = []
        if not items:
            items = [x.strip(" -•\t") for x in text.splitlines() if x.strip()]
        out = []
        for value in [query] + [str(x) for x in items]:
            value = value.strip()
            if value and value.lower() not in {x.lower() for x in out}:
                out.append(value)
        return out[:6]

    def open_character_search(self):
        if self._dialog_already_open("character_dialog"):
            return
        top = tk.Toplevel(self.root)
        self.character_dialog = top
        top.title("画角色 · 搜索并接入")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 920, 640)
        top.transient(self.root)
        base = self._beginner_base()
        expected_base = wbgen.WORKFLOWS[base["workflow"]]["base"]
        tk.Label(top, text="画角色 · 搜索并接入", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text=f"当前底模：{base['label']}（{expected_base}）。默认联网搜索 Civitai，也可切到本地已安装。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20)
        query_var = tk.StringVar()
        hint = tk.Frame(top, bg="#fff8e8")
        hint.pack(fill="x", padx=20, pady=(6, 0))
        tk.Label(hint, text="新角色/冷门角色：本地 LLM 可能不认识。请先用 DeepSeek Harness 等联网 AI 查出官方英文名/罗马音，再粘贴搜索。",
                 bg="#fff8e8", fg="#9a6500", font=("Microsoft YaHei UI", 9),
                 anchor="w", justify="left", wraplength=710).pack(
                     side="left", fill="x", expand=True, padx=(8, 4), pady=5)

        def copy_translation_hint():
            q = query_var.get().strip() or "（请填写角色中文名）"
            text = (
                f"请用联网搜索确认角色《{q}》的官方英文名、通行罗马音和常见拼写。"
                "只输出 JSON 字符串数组，最多 6 个别名，不要解释；"
                "优先官方英文名和 Civitai 常用写法。"
            )
            top.clipboard_clear()
            top.clipboard_append(text)
            top.update_idletasks()
            status.configure(text="已复制翻译提示词，可粘贴给 DeepSeek Harness 等联网 AI。")

        tk.Button(hint, text="复制翻译提示词", command=lambda: copy_translation_hint(),
                  bg="#fff8e8", fg="#9a6500", relief="flat", bd=0,
                  padx=7, pady=3, font=("Microsoft YaHei UI", 9), cursor="hand2").pack(
                      side="right", padx=(0, 6))
        query_row = tk.Frame(top, bg=COLORS["panel"])
        query_row.pack(fill="x", padx=20, pady=8)
        source_var = tk.StringVar(value="在线 Civitai")
        ent = tk.Entry(query_row, textvariable=query_var, bg=COLORS["input"], fg=COLORS["text"],
                       insertbackground=COLORS["text"], relief="flat", bd=0,
                       highlightbackground=COLORS["line"], highlightthickness=1,
                       font=("Microsoft YaHei UI", 10))
        ent.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        ent.bind("<Return>", lambda e: do_search())
        ttk.Combobox(query_row, textvariable=source_var, state="readonly",
                     values=["在线 Civitai", "本地已安装"], width=11).pack(side="left", padx=(0, 6))
        tk.Button(query_row, text="搜索角色 LoRA", command=lambda: do_search(),
                  bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                  padx=12, pady=5, cursor="hand2").pack(side="left")
        status = tk.Label(top, text="输入角色名，优先英文/罗马音，例如 2B、Raiden Shogun、Frieren。",
                          bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL, anchor="w")
        status.pack(fill="x", padx=20, pady=(0, 4))
        tree_frame = tk.Frame(top, bg=COLORS["panel"])
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        tree = ttk.Treeview(tree_frame, columns=("name", "base", "size", "downloads"),
                            show="headings", height=10)
        for col, title, width in (("name", "角色 / LoRA", 380), ("base", "底模", 150),
                                  ("size", "大小", 90), ("downloads", "下载量", 90)):
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        detail = tk.Text(top, height=5, wrap="word", bg=COLORS["panel"], fg=COLORS["text"],
                         relief="flat", bd=0, font=("Microsoft YaHei UI", 9), padx=10, pady=8)
        detail.pack(fill="x", padx=20, pady=(0, 6))
        detail.configure(state="disabled")
        bar = tk.Frame(top, bg=COLORS["bg"])
        bar.pack(fill="x", padx=20, pady=(0, 12))
        progress = ttk.Progressbar(bar, orient="horizontal", mode="determinate", maximum=100)
        progress.pack(side="left", fill="x", expand=True, padx=(0, 8))
        install_btn = tk.Button(bar, text="下载并接入", state="disabled",
                                bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                                padx=12, pady=5, cursor="hand2")
        install_btn.pack(side="right")
        tk.Button(bar, text="浏览器挑选", command=lambda: self.open_civitai_browser(query_var.get()),
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=10, pady=5, cursor="hand2").pack(side="right", padx=(0, 6))
        cancel_event = threading.Event()
        cancel_btn = tk.Button(bar, text="取消", state="disabled",
                               bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                               padx=8, pady=5, cursor="hand2")
        cancel_btn.pack(side="right", padx=(0, 6))
        records = []
        busy = {"search": False, "download": False}
        q = queue.Queue()

        def render(rows):
            records.clear()
            records.extend(rows)
            for iid in tree.get_children():
                tree.delete(iid)
            for i, rec in enumerate(records):
                tree.insert("", "end", iid=str(i), values=(
                    rec.get("name", ""), rec.get("base", ""),
                    f"{rec.get('size_kb', 0) / 1024:.1f} MB" if rec.get("size_kb") else "未知",
                    rec.get("downloads", 0)))
            status.configure(text=f"{source_var.get()} · 找到 {len(records)} 个角色 LoRA；选中后接入")
            install_btn.configure(state="disabled")

        def show_detail(_event=None):
            sel = tree.selection()
            if not sel:
                return
            rec = records[int(sel[0])]
            words = "、".join(rec.get("trained_words") or []) or "无"
            detail.configure(state="normal")
            detail.delete("1.0", "end")
            detail.insert("1.0", f"{rec.get('name', '')}\n"
                                 f"版本：{rec.get('version_name', '')}  ·  底模：{rec.get('base', '')}\n"
                                 f"训练词：{words}\n"
                                 f"命中别名：{rec.get('matched_alias', '')}\n"
                                 f"页面：{rec.get('page_url', '')}")
            detail.configure(state="disabled")
            install_btn.configure(state="normal",
                                  text="本地直接接入" if rec.get("local_path") else "下载并接入")

        tree.bind("<<TreeviewSelect>>", show_detail)

        def do_search():
            if busy["search"]:
                return
            text = query_var.get().strip()
            if not text:
                return
            if source_var.get() == "本地已安装":
                needle = text.lower()
                exp_base = str(expected_base).lower()
                rows = []
                for item in getattr(self, "all_lora_files", []):
                    item_base = str(item.get("base", "")).lower()
                    if exp_base and item_base and item_base != exp_base:
                        continue
                    name = str(item.get("name", ""))
                    trig, _ = detect_triggers(item["path"], self.known_triggers)
                    blob = (name + " " + " ".join(trig) + " " + str(item.get("label", ""))).lower()
                    if needle not in blob:
                        continue
                    try:
                        size_kb = Path(item["path"]).stat().st_size / 1024
                    except Exception:
                        size_kb = 0
                    rows.append({
                        "name": Path(name).stem,
                        "type": "LORA",
                        "base": item.get("base", ""),
                        "version_name": "本地已安装",
                        "size_kb": size_kb,
                        "downloads": 0,
                        "page_url": "",
                        "trained_words": trig,
                        "local_path": str(item["path"]),
                        "file_name": name,
                    })
                busy["search"] = False
                render(rows)
                return
            busy["search"] = True
            status.configure(text="正在联网搜索 Civitai…")
            base_filter = "Illustrious" if base["key"] == "illustrious" else ""
            model_id = self.model_map.get(self.model_var.get(), "")

            def worker():
                try:
                    aliases = [text]
                    is_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
                    if is_chinese:
                        q.put(("status", "检测到中文角色名，优先生成英文/罗马音别名…"))
                        try:
                            aliases = self._character_aliases(text, model_id)
                        except Exception:
                            aliases = [text]
                    english_aliases = [a for a in aliases
                                       if not re.search(r"[\u4e00-\u9fff]", a)]
                    if is_chinese:
                        search_aliases = (english_aliases or aliases)[:3]
                    else:
                        search_aliases = [text]
                    used_aliases = list(search_aliases)
                    q.put(("status", "优先搜索：" + " / ".join(search_aliases)))
                    merged = {}
                    order = []
                    errors = []

                    def search_one(alias):
                        nonlocal errors
                        try:
                            rows = model_center.search_civitai(
                                alias, kind="lora", base=base_filter,
                                api_key=str(CFG.get("civitai_api_key", "") or ""), limit=12)
                        except Exception as e:
                            errors.append(str(e))
                            return
                        for rec in rows:
                            key = rec.get("id") or rec.get("name")
                            if key not in merged:
                                rec = dict(rec)
                                rec["matched_alias"] = alias
                                merged[key] = rec
                                order.append(key)
                            else:
                                merged[key].setdefault("matched_alias", alias)

                    for alias in search_aliases:
                        search_one(alias)
                    if is_chinese and not merged and text.lower() not in {
                            x.lower() for x in used_aliases}:
                        q.put(("status", "英文别名没有结果，补搜中文原文…"))
                        search_one(text)
                        used_aliases.append(text)
                    rows = [merged[k] for k in order]
                    if not rows and errors:
                        q.put(("error", errors[0]))
                    else:
                        q.put(("search", rows, used_aliases))
                except Exception as e:
                    q.put(("error", str(e)))
            threading.Thread(target=worker, daemon=True).start()
            poll_search()

        def poll_search():
            try:
                item = q.get_nowait()
            except queue.Empty:
                top.after(150, poll_search)
                return
            kind = item[0]
            if kind == "status":
                status.configure(text=item[1])
                top.after(150, poll_search)
                return
            busy["search"] = False
            if kind == "search":
                rows, aliases = item[1], item[2]
                render(rows)
                status.configure(text=f"搜索别名：{' / '.join(aliases)} · 找到 {len(rows)} 个")
            else:
                payload = item[1]
                status.configure(text="搜索失败")
                messagebox.showerror(APP_NAME, f"搜索失败：{payload}", parent=top)

        def do_install():
            if busy["download"]:
                return
            sel = tree.selection()
            if not sel:
                return
            rec = records[int(sel[0])]
            if rec.get("local_path"):
                self._attach_character(rec["local_path"], rec, expected_base)
                messagebox.showinfo(APP_NAME, f"已接入本地角色：\n{Path(rec['local_path']).name}",
                                    parent=top)
                top.destroy()
                return
            rec_base = str(rec.get("base", "")).lower()
            exp_base = str(expected_base).lower()
            compatible = (not rec_base or not exp_base or rec_base in exp_base or exp_base in rec_base
                          or ("illustrious" in rec_base and "illustrious" in exp_base)
                          or ("sdxl" in rec_base and "sdxl" in exp_base))
            if not compatible:
                messagebox.showwarning(
                    APP_NAME,
                    f"底模不匹配：\n当前底模：{expected_base}\n角色 LoRA：{rec.get('base') or '未知'}\n\n"
                    "请先在简洁模式切换到匹配的底模（角色 LoRA 通常用 Illustrious/SDXL）。",
                    parent=top)
                return
            try:
                dest = model_center.destination_dir(CFG, "lora")
                target = dest / model_center.safe_filename(rec.get("file_name", "character.safetensors"))
            except Exception as e:
                messagebox.showerror(APP_NAME, str(e), parent=top)
                return
            if target.exists() and not messagebox.askyesno(
                    APP_NAME, f"文件已存在：\n{target}\n覆盖？", parent=top):
                return
            size_mb = rec.get("size_kb", 0) / 1024
            if not messagebox.askyesno(
                    APP_NAME,
                    f"接入角色：{rec.get('name', '')}\n"
                    f"大小约 {size_mb:.1f} MB\n保存到：\n{target}\n\n"
                    "请确认模型许可和角色适配。继续？", parent=top):
                return
            busy["download"] = True
            cancel_event.clear()
            install_btn.configure(state="disabled", text="下载中…")
            cancel_btn.configure(state="normal")
            progress["value"] = 0

            def cb(done, total):
                q.put(("progress", done, total))

            def worker():
                try:
                    path = model_center.download_model(rec, CFG, progress=cb,
                                                       cancel=cancel_event)
                    q.put(("installed", str(path), rec))
                except Exception as e:
                    q.put(("download_error", str(e)))
            threading.Thread(target=worker, daemon=True).start()
            poll_download()

        def poll_download():
            try:
                item = q.get_nowait()
            except queue.Empty:
                top.after(150, poll_download)
                return
            kind = item[0]
            if kind == "progress":
                _, done, total = item
                progress.configure(maximum=max(1, total), value=done)
                status.configure(text=f"下载中 {done / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB")
                top.after(150, poll_download)
                return
            busy["download"] = False
            cancel_btn.configure(state="disabled", text="取消")
            install_btn.configure(state="normal", text="下载并接入")
            if kind == "installed":
                path, rec = item[1], item[2]
                self._attach_character(path, rec, expected_base)
                messagebox.showinfo(APP_NAME, f"角色 LoRA 已接入：\n{Path(path).name}", parent=top)
                top.destroy()
            else:
                status.configure(text="下载失败或已取消；再次下载会尝试续传")
                messagebox.showerror(APP_NAME, f"下载失败：{item[1]}", parent=top)

        def cancel_download():
            if busy["download"]:
                cancel_event.set()
                cancel_btn.configure(state="disabled", text="取消中…")
                status.configure(text="正在取消；.part 文件会保留。")

        cancel_btn.configure(command=cancel_download)
        install_btn.configure(command=do_install)
        top.protocol("WM_DELETE_WINDOW", top.destroy)

    def open_civitai_browser(self, initial_query=""):
        if self._dialog_already_open("civitai_browser_dialog"):
            return
        top = tk.Toplevel(self.root)
        self.civitai_browser_dialog = top
        top.title("浏览器挑选 · Civitai")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 780, 620)
        top.transient(self.root)
        tk.Label(top, text="浏览器挑选 · Civitai", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text="绿色 civitai.com 只显示 SFW；红色 civitai.red 可看 NSFW。筛选会带底模和关键词。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20)
        query_row = tk.Frame(top, bg=COLORS["panel"])
        query_row.pack(fill="x", padx=20, pady=8)
        query_var = tk.StringVar(value=initial_query)
        ent = tk.Entry(query_row, textvariable=query_var, bg=COLORS["input"], fg=COLORS["text"],
                       insertbackground=COLORS["text"], relief="flat", bd=0,
                       highlightbackground=COLORS["line"], highlightthickness=1,
                       font=("Microsoft YaHei UI", 10))
        ent.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        tk.Button(query_row, text="生成容错别名", command=lambda: gen_aliases(),
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=10, pady=5, cursor="hand2").pack(side="left")
        base_row = tk.Frame(top, bg=COLORS["panel"])
        base_row.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(base_row, text="底模筛选", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left", padx=(0, 8))
        current = self._beginner_base()
        installed = []
        for base in BEGINNER_BASES:
            missing = model_center.missing_profile_files(CFG, base["workflow"], wbgen.MODEL_FILES)
            if not missing or base["key"] == current["key"]:
                installed.append(base)
        base_map = {f"{x['icon']} {x['label']}": x for x in installed}
        base_var = tk.StringVar(value=f"{current['icon']} {current['label']}")
        ttk.Combobox(base_row, textvariable=base_var, state="readonly",
                     values=list(base_map.keys()), width=22).pack(side="left")
        tk.Label(base_row, text="只列已安装/当前底模", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(8, 0))
        mode_row = tk.Frame(top, bg=COLORS["panel"])
        mode_row.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(mode_row, text="内容范围", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left", padx=(0, 8))
        mode_var = tk.StringVar(value=self.mode.get())
        tk.Radiobutton(mode_row, text="SFW · 绿色 C 站", variable=mode_var, value="SFW",
                       bg=COLORS["panel"], fg=COLORS["green"], selectcolor=COLORS["input"],
                       font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(0, 10))
        tk.Radiobutton(mode_row, text="NSFW · 红色 C 站", variable=mode_var, value="NSFW",
                       bg=COLORS["panel"], fg=COLORS["red"], selectcolor=COLORS["input"],
                       font=("Microsoft YaHei UI", 9)).pack(side="left")
        tk.Button(mode_row, text="如何显示成人内容", command=self.open_civitai_content_help,
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=5, pady=2, font=("Microsoft YaHei UI", 9),
                  cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Label(top, text="别名（双击选用；中文名、英文名、罗马音、同音/拼写变体都可试）",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20)
        alias_frame = tk.Frame(top, bg=COLORS["panel"])
        alias_frame.pack(fill="both", expand=True, padx=20, pady=(4, 6))
        alias_list = tk.Listbox(alias_frame, height=5, bg=COLORS["input"], fg=COLORS["text"],
                                selectbackground=COLORS["accent2"], selectforeground="#fff",
                                relief="flat", bd=0, font=("Microsoft YaHei UI", 9))
        alias_list.pack(fill="both", expand=True, padx=4, pady=4)
        alias_row = tk.Frame(top, bg=COLORS["bg"])
        alias_row.pack(fill="x", padx=20, pady=(0, 6))
        tk.Label(alias_row, text="当前搜索词", bg=COLORS["bg"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(side="left")
        alias_var = tk.StringVar(value=initial_query)
        tk.Entry(alias_row, textvariable=alias_var, bg=COLORS["input"], fg=COLORS["text"],
                 insertbackground=COLORS["text"], relief="flat", bd=0,
                 highlightbackground=COLORS["line"], highlightthickness=1,
                 font=("Microsoft YaHei UI", 9)).pack(side="left", fill="x", expand=True,
                                                       ipady=3, padx=(6, 0))
        status = tk.Label(top, text="可以直接打开，也可以先生成容错别名。",
                          bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL, anchor="w")
        status.pack(fill="x", padx=20)
        bar = tk.Frame(top, bg=COLORS["bg"])
        bar.pack(fill="x", padx=20, pady=(4, 12))
        tk.Button(bar, text="在 Civitai 打开", command=lambda: open_browser(),
                  bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                  padx=12, pady=6, font=("Microsoft YaHei UI", 9, "bold"),
                  cursor="hand2").pack(side="left")
        tk.Button(bar, text="下载好了 · 交给 DSH",
                  command=lambda: self.open_browser_download_dsh(
                      alias_var.get().strip() or query_var.get().strip(),
                      base_map.get(base_var.get()) or current),
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=10, pady=6, cursor="hand2").pack(side="left", padx=(6, 0))
        tk.Button(bar, text="关闭", command=top.destroy, bg=COLORS["panel"],
                  fg=COLORS["muted"], relief="flat", bd=0, padx=10, pady=6,
                  cursor="hand2").pack(side="right")

        def add_aliases(rows):
            alias_list.delete(0, "end")
            seen = set()
            for value in rows:
                value = str(value).strip()
                if value and value.lower() not in seen:
                    seen.add(value.lower())
                    alias_list.insert("end", value)
            if alias_list.size():
                alias_list.selection_set(0)
                alias_var.set(alias_list.get(0))

        def gen_aliases():
            query = query_var.get().strip()
            if not query:
                return
            status.configure(text="正在让 LLM 生成中文/英文/罗马音/同音变体…")
            q = queue.Queue()
            model_id = self.model_map.get(self.model_var.get(), "")
            prompt = (
                "把下面的角色关键词扩展成用于 Civitai 搜索的别名。"
                "输出 JSON 字符串数组，最多 6 个，不要解释。"
                "包含中文名、英文名、罗马音、常见同音字或拼写变体；不确定的也可以给候选。\n"
                f"角色：{query}"
            )

            def worker():
                try:
                    raw = llm_client.chat(CFG, [{"role": "user", "content": prompt}],
                                          model=model_id, temperature=0.2, num_predict=220)
                    q.put(("ok", raw))
                except Exception as e:
                    q.put(("error", str(e)))

            threading.Thread(target=worker, daemon=True).start()

            def poll():
                try:
                    kind, payload = q.get_nowait()
                except queue.Empty:
                    top.after(200, poll)
                    return
                if kind == "error":
                    status.configure(text="别名生成失败；直接用原始关键词打开。")
                    add_aliases([query])
                    return
                text = re.sub(r"^```(?:json)?\s*", "", payload.strip())
                text = re.sub(r"\s*```$", "", text)
                items = []
                try:
                    match = re.search(r"\[.*\]", text, re.S)
                    if match:
                        items = json.loads(match.group(0))
                    if not isinstance(items, list):
                        items = []
                except Exception:
                    items = []
                if not items:
                    items = [x.strip(" -•\t") for x in payload.splitlines() if x.strip()]
                items = [str(x) for x in items[:6]]
                english = [x for x in items if not re.search(r"[\u4e00-\u9fff]", x)]
                add_aliases(english + [query] + [x for x in items if x not in english])
                status.configure(text="已生成别名，优先显示英文/罗马音；双击选用后打开。")

            poll()

        def open_browser():
            alias = alias_var.get().strip() or query_var.get().strip()
            if not alias:
                return
            if mode_var.get() == "NSFW":
                if not messagebox.askyesno(
                        APP_NAME,
                        "即将进入红色 Civitai（civitai.red）。\n\n"
                        "该站包含不同分级内容，可能包含成人内容，并非全部都是成人内容。\n"
                        "如果你浏览成人内容，仅限 18 岁以上。\n"
                        "请勿下载或生成涉及未成年、幼态、年龄不明或真实人物性化的内容。\n\n"
                        "确认继续？", parent=top):
                    return
            base = base_map.get(base_var.get()) or current
            domain = "https://civitai.red" if mode_var.get() == "NSFW" else "https://civitai.com"
            params = {
                "query": alias,
                "types": "LORA",
                "baseModels": CIVITAI_BASE_LABELS.get(base["key"], base["label"]),
                "sort": "Most Downloaded",
                "period": "AllTime",
            }
            url = domain + "/search/models?" + urllib.parse.urlencode(params)
            if mode_var.get() == "NSFW" and not self.civitai_guide_seen:
                self.civitai_guide_seen = True
                self._save_settings()
                self.open_civitai_content_help(on_continue=lambda: webbrowser.open(url))
                status.configure(text="先按图解开启成人内容显示，再点“我已设置好，继续”。")
                return
            webbrowser.open(url)
            status.configure(text=f"已在浏览器打开：{alias} · {base['label']}")

        alias_list.bind("<Double-Button-1>",
                        lambda e: alias_var.set(alias_list.get(alias_list.nearest(e.y))))
        top.protocol("WM_DELETE_WINDOW", top.destroy)

    def open_civitai_content_help(self, on_continue=None):
        if self._dialog_already_open("guide_dialog"):
            return
        top = tk.Toplevel(self.root)
        self.guide_dialog = top
        top.title("Civitai 成人内容显示 · 原站图解")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 820, 800)
        top.transient(self.root)
        tk.Label(top, text="Civitai.red 显示成人内容 · 看图 3 步",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(top, text="原站截图来自 Civitai 官方内容分级指南；红框就是点击/打开的位置。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=18)
        img_holder = tk.Frame(top, bg=COLORS["panel"])
        img_holder.pack(fill="both", expand=True, padx=18, pady=6)
        img_label = tk.Label(img_holder, bg=COLORS["panel"])
        img_label.pack()
        caption = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["text"], justify="left",
                           wraplength=760, font=("Microsoft YaHei UI", 10))
        caption.pack(fill="x", padx=18, pady=(2, 0))
        detail = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["muted"], justify="left",
                          wraplength=760, font=FONT_SMALL)
        detail.pack(fill="x", padx=18, pady=(2, 4))
        step_label = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["accent2"],
                              font=("Microsoft YaHei UI", 9, "bold"))
        step_label.pack(anchor="w", padx=18)
        photos = []
        page = {"idx": 0}

        def show_page(idx):
            page["idx"] = max(0, min(len(CIVITAI_GUIDE_STEPS) - 1, idx))
            path, title, note = CIVITAI_GUIDE_STEPS[page["idx"]]
            caption.configure(text=title)
            detail.configure(text=note)
            step_label.configure(text=f"第 {page['idx'] + 1} / {len(CIVITAI_GUIDE_STEPS)} 步")
            if path.exists():
                try:
                    photo = tk.PhotoImage(file=str(path))
                    photos.append(photo)
                    img_label.configure(image=photo)
                    img_label.image = photo
                except Exception as e:
                    img_label.configure(image="", text=f"原图加载失败：{e}", fg=COLORS["red"])
            else:
                img_label.configure(image="", text="原图缺失", fg=COLORS["red"])
            prev_btn.configure(state="normal" if page["idx"] > 0 else "disabled")
            next_btn.configure(state="normal" if page["idx"] < len(CIVITAI_GUIDE_STEPS) - 1 else "disabled")

        bar = tk.Frame(top, bg=COLORS["bg"])
        bar.pack(fill="x", padx=18, pady=(4, 12))
        prev_btn = tk.Button(bar, text="上一步", command=lambda: show_page(page["idx"] - 1),
                             bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                             padx=10, pady=5, cursor="hand2")
        prev_btn.pack(side="left")
        next_btn = tk.Button(bar, text="下一步", command=lambda: show_page(page["idx"] + 1),
                             bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                             padx=10, pady=5, cursor="hand2")
        next_btn.pack(side="left", padx=(5, 0))
        tk.Button(bar, text="打开 civitai.red", command=lambda: webbrowser.open("https://civitai.red"),
                  bg=COLORS["panel"], fg=COLORS["accent2"], relief="flat", bd=0,
                  padx=8, pady=5, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(bar, text="官方原文",
                  command=lambda: webbrowser.open("https://education.civitai.com/civitais-guide-to-content-levels/"),
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=8, pady=5, cursor="hand2").pack(side="left", padx=(4, 0))
        if on_continue is not None:
            def continue_open():
                top.destroy()
                on_continue()
            tk.Button(bar, text="我已设置好，继续", command=continue_open,
                      bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                      padx=12, pady=5, font=("Microsoft YaHei UI", 9, "bold"),
                      cursor="hand2").pack(side="right")
        tk.Button(bar, text="关闭", command=top.destroy, bg=COLORS["panel"],
                  fg=COLORS["muted"], relief="flat", bd=0, padx=8, pady=5,
                  cursor="hand2").pack(side="right", padx=(0, 5))
        show_page(0)

    def open_browser_download_dsh(self, query, base):
        if self._dialog_already_open("browser_dsh_dialog"):
            return
        top = tk.Toplevel(self.root)
        self.browser_dsh_dialog = top
        top.title("下载后 · 交给 DSH 接入")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 820, 640)
        top.transient(self.root)
        tk.Label(top, text="下载后 · 交给 DSH 接入", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 16, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text="不需要 Civitai API Key。把 C 站截图和这段提示词一起发给 DSH 即可。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20)
        form = tk.Frame(top, bg=COLORS["panel"])
        form.pack(fill="x", padx=20, pady=8)
        download_dir = str(Path.home() / "Downloads")
        dir_var = tk.StringVar(value=download_dir)
        file_var = tk.StringVar()

        def choose_file():
            path = filedialog.askopenfilename(
                parent=top, title="选择刚下载的 LoRA",
                initialdir=dir_var.get() or str(Path.home() / "Downloads"),
                filetypes=[("Safetensors", "*.safetensors"), ("All files", "*.*")])
            if path:
                file_var.set(path)
                dir_var.set(str(Path(path).parent))

        for label, var, browse_file in (("下载目录", dir_var, False), ("已下载文件（可选）", file_var, True)):
            row = tk.Frame(form, bg=COLORS["panel"])
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text=label, width=14, anchor="w", bg=COLORS["panel"],
                     fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(side="left")
            tk.Entry(row, textvariable=var, bg=COLORS["input"], fg=COLORS["text"],
                     insertbackground=COLORS["text"], relief="flat", bd=0,
                     highlightbackground=COLORS["line"], highlightthickness=1,
                     font=("Microsoft YaHei UI", 9)).pack(side="left", fill="x", expand=True,
                                                           ipady=3, padx=(0, 5))
            tk.Button(row, text="选择文件" if browse_file else "选择目录",
                      command=(choose_file if browse_file else
                               lambda v=var: self._browse_setting(v, "dir")),
                      bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                      padx=7, pady=3, cursor="hand2").pack(side="left")
        lora_root = (CFG.paths("lora_roots")[0] if CFG.paths("lora_roots") else "未配置")
        prompt = f"""你是 DSH。用户通过浏览器从 Civitai 下载了一个角色 LoRA，但不会创建 Civitai API Key。
请不要要求 API Key，也不需要调用 Civitai 下载接口。

角色关键词：{query or '未填写'}
底模：{base['label']}（{base.get('target', '')}）
下载目录：{dir_var.get()}
用户指定的文件：{file_var.get() or '未指定'}
LoRA 目标目录：{lora_root}

用户可能会附上一张 Civitai 模型页/下载完成的截图。请结合截图确认模型名称和版本，但不要仅凭截图猜文件。

请执行：
1. 在下载目录找最近修改的 .safetensors；若有多个，列出文件名、大小、修改时间让我确认。
2. 检查文件大小和 SHA256，并报告；不要移动其他下载文件。
3. 读取 safetensors 元数据/文件名，确认底模是否与当前底模兼容。角色 LoRA 通常匹配 Illustrious/SDXL；不匹配就停止并说明。
4. 通过后移动到 LoRA 目标目录；已存在则先备份，不要覆盖用户已有文件。
5. 更新提示词工作台的角色接入状态或告诉我如何在“画角色 → 本地已安装”里选择它。
6. 用一张 832×1216 测试图验证 LoRA 真的加载；报告路径、耗时和失败原因。
7. 不要要求 Civitai API Key，不要静默下载，不要删除原文件，除非我确认。
8. 如果截图和实际文件不一致，停止并询问我。
"""
        box = ScrolledText(top, wrap="word", bg=COLORS["panel"], fg=COLORS["text"],
                           relief="flat", bd=0, font=("Consolas", 9), padx=10, pady=8)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        box.insert("1.0", prompt)
        box.configure(state="disabled")
        status = tk.Label(top, text="提示：先截图 C 站模型页，再复制这段提示词给 DSH。",
                          bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL, anchor="w")
        status.pack(fill="x", padx=20)
        bar = tk.Frame(top, bg=COLORS["bg"])
        bar.pack(fill="x", padx=20, pady=(4, 12))

        def current_prompt():
            text = prompt.replace(f"下载目录：{download_dir}", f"下载目录：{dir_var.get()}")
            return text.replace("用户指定的文件：未指定",
                                f"用户指定的文件：{file_var.get() or '未指定'}")

        def copy_prompt():
            top.clipboard_clear()
            top.clipboard_append(current_prompt())
            top.update_idletasks()
            status.configure(text="已复制；把 C 站截图和提示词一起发给 DSH。")

        tk.Button(bar, text="复制给 DSH", command=copy_prompt, bg=COLORS["accent"],
                  fg="#fff", relief="flat", bd=0, padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Button(bar, text="保存为 md", command=lambda: (
                      (DATA_DIR / "dsh-browser-download.md").write_text(current_prompt(), encoding="utf-8"),
                      status.configure(text=f"已保存：{DATA_DIR / 'dsh-browser-download.md'}")),
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=10, pady=6, cursor="hand2").pack(side="left", padx=(6, 0))
        tk.Button(bar, text="关闭", command=top.destroy, bg=COLORS["panel"],
                  fg=COLORS["muted"], relief="flat", bd=0, padx=10, pady=6,
                  cursor="hand2").pack(side="right")

    def _attach_character(self, path, rec, expected_base):
        path = str(path)
        item = {
            "label": f"角色/{Path(path).name}",
            "path": path,
            "name": Path(path).name,
            "base": expected_base,
            "strength": 0.8,
        }
        self.beginner_pinned_lora = item
        self.beginner_character_trigger = " ".join(rec.get("trained_words") or [])
        if all(str(Path(x.get("path", "")).resolve()) != str(Path(path).resolve())
               for x in self.selected_loras):
            self.selected_loras.append(item)
        self._load_loras()
        self._refresh_lora_selected()
        words = self.beginner_character_trigger[:60] or "无触发词"
        self.beginner_character_label.configure(
            text=f"角色：{rec.get('name', Path(path).stem)} · {words}")
        self.status_var.set(f"角色已接入：{Path(path).name}")

    def _dialog_already_open(self, attr):
        dialog = getattr(self, attr, None)
        if dialog is None:
            return False
        try:
            if dialog.winfo_exists():
                dialog.lift()
                return True
        except Exception:
            pass
        setattr(self, attr, None)
        return False

    def _schedule_env_refresh(self, delay=1800):
        def later():
            if self._env_check_running:
                self.root.after(1500, self._refresh_beginner_env)
            else:
                self._refresh_beginner_env()
        self.root.after(delay, later)

    def _beginner_style_select_highlight(self):
        for name, btn in getattr(self, "beginner_style_buttons", []):
            if name == self.beginner_style.get():
                btn.configure(bg=COLORS["accent"], fg="#fff", activebackground=COLORS["accent2"])
            else:
                btn.configure(bg=COLORS["card2"], fg=COLORS["text"], activebackground=COLORS["card2"])

    def toggle_beginner_mode(self):
        self.beginner_mode_var.set(not self.beginner_mode_var.get())
        self._apply_beginner_mode(save=True)

    def _apply_beginner_mode(self, save=False):
        beginner = bool(self.beginner_mode_var.get())
        if not hasattr(self, "beginner_frame"):
            return
        if beginner:
            for widget in self.advanced_surfaces:
                widget.pack_forget()
            for widget in self.advanced_nav_widgets:
                widget.pack_forget()
            self.beginner_outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))
            self._update_beginner_base_label()
        else:
            self.beginner_outer.pack_forget()
            self.advanced_surfaces[0].pack(fill="x", padx=24, pady=(4, 12))
            self.advanced_surfaces[1].pack(fill="both", expand=True, padx=24, pady=(0, 8))
            self.advanced_surfaces[2].pack(fill="x", padx=24, pady=(0, 12))
            for widget in self.advanced_nav_widgets:
                widget.pack(fill="x", pady=3)
        self._draw_mode_switch(animate=True)
        self._update_mode_button()
        self._refresh_beginner_missing()
        if save:
            self._save_settings()

    def _draw_mode_switch(self, pos=None, animate=False):
        if not hasattr(self, "mode_switch_canvas"):
            return
        canvas = self.mode_switch_canvas
        if pos is None:
            pos = self._switch_pos
        target = 1.0 if not self.beginner_mode_var.get() else 0.0
        if animate and pos != target:
            if self._switch_anim_job:
                try:
                    canvas.after_cancel(self._switch_anim_job)
                except Exception:
                    pass
            steps = 8
            start = float(pos)

            def step(i=1):
                t = i / steps
                eased = t * (2 - t)
                value = start + (target - start) * eased
                self._switch_pos = value
                self._draw_mode_switch(value, animate=False)
                if i < steps:
                    self._switch_anim_job = canvas.after(18, lambda: step(i + 1))
                else:
                    self._switch_anim_job = None
                    self._switch_pos = target
                    self._draw_mode_switch(target, animate=False)
            step()
            return
        self._switch_pos = target if not animate and pos is None else pos
        canvas.delete("all")
        width = max(180, canvas.winfo_width())
        height = 38
        # 左右标签 + 中间滑块
        canvas.create_text(4, height / 2, text="简洁", anchor="w",
                           fill=COLORS["accent"] if self.beginner_mode_var.get() else COLORS["muted"],
                           font=("Microsoft YaHei UI", 9, "bold"))
        canvas.create_text(width - 4, height / 2, text="高级", anchor="e",
                           fill=COLORS["accent"] if not self.beginner_mode_var.get() else COLORS["muted"],
                           font=("Microsoft YaHei UI", 9, "bold"))
        track_x = 46
        track_w = max(68, width - 92)
        track_y = 5
        track_h = 28
        r = track_h / 2
        x1, y1, x2, y2 = track_x, track_y, track_x + track_w, track_y + track_h
        if self.beginner_mode_var.get():
            fill = COLORS["card2"]
        else:
            fill = COLORS["accent"]
        canvas.create_oval(x1, y1, x1 + track_h, y2, fill=fill, outline="")
        canvas.create_oval(x2 - track_h, y1, x2, y2, fill=fill, outline="")
        canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
        knob_r = 11
        knob_x = track_x + knob_r + 3 + (track_w - 2 * knob_r - 6) * max(0.0, min(1.0, pos))
        knob_y = height / 2
        canvas.create_oval(knob_x - knob_r, knob_y - knob_r, knob_x + knob_r, knob_y + knob_r,
                           fill="#ffffff", outline=COLORS["line"])
        canvas.create_oval(knob_x - 3, knob_y - 3, knob_x + 3, knob_y + 3,
                           fill=COLORS["accent"], outline="")


    def beginner_generate(self):
        if self.generating:
            return
        self._refresh_beginner_missing()
        if self.beginner_missing_files:
            detail = "、".join(x["filename"] for x in self.beginner_missing_files)
            if not messagebox.askyesno(
                    APP_NAME,
                    f"当前底模缺少以下模型文件：\n{detail}\n\n"
                    "现在直接生成很可能失败。\n仍要尝试吗？"):
                return
        brief = self.beginner_brief.get("1.0", "end").strip()
        if not brief or brief.startswith("例如："):
            messagebox.showwarning(APP_NAME, "先写一句你想要的画面。")
            return
        style = self.beginner_style.get()
        if style and style != "无风格":
            brief += f"\n画面风格：{style}"
        self._beginner_prepare_base()
        self.brief_text.delete("1.0", "end")
        self.brief_text.insert("1.0", brief)
        self.beginner_pending = True
        self.gen_cancel.clear()
        if hasattr(self, "beginner_stop_btn"):
            self.beginner_stop_btn.configure(state="normal", text="停止")
        if hasattr(self, "beginner_repeat_btn"):
            self.beginner_repeat_btn.configure(state="disabled")
            self.beginner_result_hint.configure(text="生成完成后可在这里继续操作")
        self.beginner_progress.configure(text="第 1 步 / 2：正在写提示词…")
        self.beginner_progressbar.configure(maximum=2, value=0)
        self.beginner_generate_btn.configure(state="disabled", text="正在写提示词…")
        self.generate()

    def _beginner_inspire(self, kind):
        values = BEGINNER_INSPIRATION.get(kind) or []
        if not values:
            return
        text = random.choice(values)
        current = self.beginner_brief.get("1.0", "end").strip()
        if not current or current.startswith("例如："):
            current = ""
        if kind == "随机":
            new_text = text
        else:
            new_text = (current + ("，" if current else "") + text)
        self.beginner_brief.delete("1.0", "end")
        self.beginner_brief.insert("1.0", new_text)
        self.beginner_brief.focus_set()

    def _select_beginner_style(self, label):
        self.beginner_style.set(label)
        self._beginner_style_select_highlight()
        self._update_base_recommendation()
        self._save_settings()

    def _select_beginner_ratio(self, label):
        if label not in BEGINNER_RATIOS:
            return
        self.beginner_ratio.set(label)
        for name, btn in getattr(self, "beginner_ratio_buttons", []):
            if name == label:
                btn.configure(bg=COLORS["accent"], fg="#fff", activebackground=COLORS["accent2"])
            else:
                btn.configure(bg=COLORS["card2"], fg=COLORS["text"], activebackground=COLORS["card2"])
        self._save_settings()

    def stop_beginner_generation(self):
        if not self.generating:
            return
        self.gen_cancel.set()
        self.beginner_pending = False
        if hasattr(self, "beginner_stop_btn"):
            self.beginner_stop_btn.configure(state="disabled", text="停止中…")
        self._beginner_set_progress("正在中断当前任务…")
        self.status_var.set("正在停止生成…")
        threading.Thread(target=wbgen.interrupt, daemon=True).start()

    def repeat_beginner_generate(self):
        if self.generating:
            return
        if not self.positive_text.get("1.0", "end").strip():
            return
        self._beginner_prepare_base()
        self.beginner_repeat_btn.configure(state="disabled")
        self.beginner_generate_btn.configure(state="disabled", text="出图中…")
        self._beginner_set_progress("再来一张：正在出图…", 0, 1)
        self.generate_images()

    def _beginner_prepare_base(self):
        base = self._beginner_base()
        self.target_var.set(base["target"])
        self._on_target_change(manual=False)
        self.generation_workflow_var.set(wbgen.WORKFLOWS[base["workflow"]]["name"])
        self.gen_count_var.set(max(1, min(4, int(self.beginner_count_var.get() or 1))))
        self.auto_pick_var.set(True)
        self._save_settings()

    def _beginner_set_progress(self, text, value=None, maximum=None):
        if not hasattr(self, "beginner_progress"):
            return
        self.beginner_progress.configure(text=text)
        if maximum is not None:
            self.beginner_progressbar.configure(maximum=max(1, maximum))
        if value is not None:
            self.beginner_progressbar.configure(value=value)

    def _show_beginner_results(self, paths):
        if not hasattr(self, "beginner_results_inner"):
            return
        for w in self.beginner_results_inner.winfo_children():
            w.destroy()
        self.beginner_result_photos = []
        self.beginner_result_paths = list(paths)
        for i, path in enumerate(paths[:4]):
            try:
                img = tk.PhotoImage(file=path)
                factor = max(1, img.width() // 260, img.height() // 260)
                if factor > 1:
                    img = img.subsample(factor, factor)
                self.beginner_result_photos.append(img)
                cell = tk.Frame(self.beginner_results_inner, bg=COLORS["panel"])
                cell.grid(row=i // 2, column=i % 2, padx=8, pady=4, sticky="n")
                lbl = tk.Label(cell, image=img, bg=COLORS["panel"], cursor="hand2")
                lbl.pack()
                lbl.bind("<Button-1>", lambda e, p=path: os.startfile(p))
                tk.Label(cell, text=Path(path).name, bg=COLORS["panel"], fg=COLORS["muted"],
                         font=("Microsoft YaHei UI", 7)).pack()
            except Exception:
                pass
        if paths and not self.beginner_result_photos:
            tk.Label(self.beginner_results_inner, text=f"已生成 {len(paths)} 张，打开输出目录查看。",
                     bg=COLORS["panel"], fg=COLORS["muted"], font=FONT_SMALL).grid(
                         row=0, column=0, padx=8, pady=8)

    def _check_health(self):
        try:
            models = fetch_llm_models()
            self.queue.put(("models", models))
        except Exception:
            self.queue.put(("health", "LLM 未连接"))

    def _apply_models(self, models):
        known = {model_id: label for label, model_id in MODEL_OPTIONS}
        order = {model_id: i for i, (_, model_id) in enumerate(MODEL_OPTIONS)}
        models = sorted(models, key=lambda x: (order.get(x["name"], 99), x["name"].lower()))
        labels = []
        mapping = {}
        seen = set()
        for item in models:
            name = item["name"]
            size_gb = item.get("size", 0) / (1024 ** 3)
            label = known.get(name, f"{name} · {size_gb:.1f}GB")
            if label in seen:
                label = f"{label}（{name}）"
            seen.add(label)
            labels.append(label)
            mapping[label] = name
        if not labels:
            self.status_var.set("LLM 在线 · 没有可选模型")
            return
        self.model_map = mapping
        self.model_combo["values"] = labels
        current = self.model_var.get()
        chosen = None
        if self.desired_model_id and self.desired_model_id in mapping.values():
            chosen = next((label for label, mid in mapping.items() if mid == self.desired_model_id), None)
        if not chosen and current in labels:
            chosen = current
        if not chosen:
            for _, model_id in MODEL_OPTIONS:
                if model_id in mapping.values():
                    chosen = next(label for label, mid in mapping.items() if mid == model_id)
                    break
        if not chosen:
            chosen = labels[0]
        self.model_var.set(chosen)
        self.status_var.set(f"LLM 就绪 · {len(labels)} 个模型")
        self._save_settings()

    # ---------- 生成 ----------
    def _focus_generate(self):
        self.brief_text.focus_set()

    def _on_left_mousewheel(self, event):
        if self.left_canvas.winfo_exists():
            delta = -1 if event.delta > 0 else 1
            self.left_canvas.yview_scroll(delta, "units")

    def _bind_left_mousewheel(self, widget=None):
        if widget is None:
            widget = self.left_canvas
        if not widget.winfo_exists():
            return
        if not isinstance(widget, (tk.Text, tk.Listbox, ttk.Combobox)):
            widget.bind("<MouseWheel>", self._on_left_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_left_mousewheel(child)

    def _show_history_tab(self):
        self.tab.select(1)

    def _build_system_prompt(self) -> str:
        target_name = self.target_var.get()
        cfg = TARGETS.get(target_name, {})
        skill_path = SKILLS / cfg.get("skill", "")
        skill = read_text(skill_path, limit=18000)
        extra_path = cfg.get("extra")
        extra = read_text(SKILLS / extra_path, limit=6000) if extra_path else ""

        mode = self.mode.get()
        safety = f"""当前模式：{mode}。
硬性限制（任何模式都适用）：
- 仅限 18 岁以上的虚构角色。
- 禁止未成年、幼态、儿童化、年龄不明或看起来未成年的角色。
- 禁止真实人物性化、真实人物换脸/身份盗用。
- 如果用户需求触犯以上限制，只输出简短拒绝，不生成提示词。
- SFW 模式不要输出露骨性行为、裸露或成人内容。
"""
        if mode == "NSFW":
            safety += """- NSFW 模式允许成人向描写；仍然只限成年虚构角色。
"""
        fmt = f"""目标底模：{target_name}
{cfg.get('desc', '')}
输出格式要求：{cfg.get('format', '')}

只输出以下三段，不要解释、不要复述规则：
【Positive】
...
【Negative】
...
【Notes】
...
"""
        lora_ctx = self._lora_context()
        return f"""你是本地提示词工作台的专业提示词编辑。你会根据用户的中文需求，为目标底模生成可直接使用的 Positive 和 Negative 提示词。

{safety}

{fmt}

--- 目标底模的专用规则 ---
{skill}

--- 补充规则 ---
{extra}

--- 当前 LoRA ---
{lora_ctx}
"""

    def _build_refine_system(self):
        target = self.target_var.get()
        cfg = TARGETS.get(target, {})
        skill = read_text(SKILLS / cfg.get("skill", ""), limit=9000)
        mode = self.mode.get()
        lora_ctx = self._lora_context()
        return f"""你是提示词工作台的修改编辑。用户已经有 Positive/Negative，并会给出修改要求。
请保留当前提示词中未被要求改变的主体、服装、场景和风格，只修改用户要求的细节。
目标底模：{target}
当前模式：{mode}
硬性限制：仅限 18+ 虚构角色；禁止未成年/幼态/年龄不明；禁止真实人物性化。

当前 LoRA：
{lora_ctx or '（无）'}

只输出三段，不要解释：
【Positive】
...
【Negative】
...
【Notes】
...

目标底模规则参考：
{skill}
"""

    def refine_prompt(self):
        if self.generating:
            return
        instruction = self.refine_entry.get().strip()
        if not instruction:
            messagebox.showwarning(APP_NAME, "先写修改要求，例如：把外套改成白色、镜头更近。")
            return
        pos = self.positive_text.get("1.0", "end").strip()
        neg = self.negative_text.get("1.0", "end").strip()
        if not pos and not neg:
            messagebox.showwarning(APP_NAME, "当前没有可微调的提示词。")
            return
        self.generating = True
        self.generate_btn.configure(state="disabled", text="生成中…")
        self.refine_btn.configure(state="disabled", text="调整中…")
        self.status_var.set("正在基于当前提示词微调…")
        model = self.model_map.get(self.model_var.get(), MODEL_OPTIONS[0][1])
        target = self.target_var.get()
        mode = self.mode.get()
        brief = self.brief_text.get("1.0", "end").strip()
        system = self._build_refine_system()
        threading.Thread(target=self._worker_refine,
                         args=(model, system, pos, neg, instruction, brief, target, mode),
                         daemon=True).start()

    def _worker_refine(self, model, system, pos, neg, instruction, brief, target, mode):
        user = f"""当前 Positive：
{pos}

当前 Negative：
{neg}

修改要求：
{instruction}"""
        try:
            text = llm_client.chat(
                CFG,
                [{"role": "system", "content": system},
                 {"role": "user", "content": user}],
                model=model, temperature=0.5, num_ctx=32768, num_predict=2048)
            self.used_models.add(model)
            self.queue.put(("refined", text, instruction, brief, target, mode, pos, neg))
        except Exception as e:
            self.queue.put(("refine_error", str(e), instruction))

    def _refresh_refine_log(self):
        self.refine_log_list.delete(0, "end")
        for i, rec in enumerate(self.refine_history, 1):
            text = rec.get("instruction", "").replace("\n", " ")
            self.refine_log_list.insert("end", f"第{i}次 · {text[:54]}")
        if self.refine_history:
            self.refine_log_list.see("end")

    def _undo_refine(self):
        sel = self.refine_log_list.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.refine_history):
            return
        if not messagebox.askyesno(
                APP_NAME,
                f"撤销第 {idx + 1} 次及之后的所有调整，并恢复到该次之前？"):
            return
        rec = self.refine_history[idx]
        self.positive_text.delete("1.0", "end")
        self.positive_text.insert("1.0", rec.get("before_pos", ""))
        self.negative_text.delete("1.0", "end")
        self.negative_text.insert("1.0", rec.get("before_neg", ""))
        del self.refine_history[idx:]
        self.refine_entry.delete(0, "end")
        self._refresh_refine_log()
        self.status_var.set(f"已撤销第 {idx + 1} 次及之后的调整")

    def generate(self):
        if self.generating:
            return
        brief = self.brief_text.get("1.0", "end").strip()
        if not brief:
            messagebox.showwarning(APP_NAME, "先写一点中文需求。")
            return
        self.generating = True
        self.generate_btn.configure(state="disabled", text="生成中…")
        self.status_var.set("正在调用 LLM…")
        model = self.model_map.get(self.model_var.get(), MODEL_OPTIONS[0][1])
        system = self._build_system_prompt()
        target = self.target_var.get()
        mode = self.mode.get()
        threading.Thread(target=self._worker_generate, args=(model, system, brief, target, mode), daemon=True).start()

    def _worker_generate(self, model, system, brief, target, mode):
        try:
            text = llm_client.chat(
                CFG,
                [{"role": "system", "content": system},
                 {"role": "user", "content": brief}],
                model=model, temperature=0.6, num_ctx=32768, num_predict=2048)
            self.used_models.add(model)
            self.queue.put(("done", text, brief, target, mode))
        except Exception as e:
            self.queue.put(("error", str(e), brief, target, mode))

    def _poll_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                if item[0] == "health":
                    self.status_var.set(item[1])
                elif item[0] == "models":
                    self._apply_models(item[1])
                elif item[0] == "refined":
                    _, raw, instruction, brief, target, mode, before_pos, before_neg = item
                    pos, neg, notes = parse_sections(raw)
                    self.positive_text.delete("1.0", "end")
                    self.positive_text.insert("1.0", pos)
                    self.negative_text.delete("1.0", "end")
                    self.negative_text.insert("1.0", neg)
                    self.refine_history.append({
                        "instruction": instruction,
                        "before_pos": before_pos,
                        "before_neg": before_neg,
                        "after_pos": pos,
                        "after_neg": neg,
                    })
                    self._refresh_refine_log()
                    self.refine_entry.delete(0, "end")
                    self._add_record(brief + f"\n[微调] {instruction}", target, mode, pos, neg, notes, raw)
                    self.generating = False
                    self.generate_btn.configure(state="normal", text="新开一个")
                    self.refine_btn.configure(state="normal", text="继续调整")
                    self.status_var.set("调整已合并到上方提示词 · 输入框已清空")
                elif item[0] == "refine_error":
                    _, err, instruction = item
                    self.generating = False
                    self.generate_btn.configure(state="normal", text="新开一个")
                    self.refine_btn.configure(state="normal", text="继续调整")
                    self.status_var.set("调整失败")
                    messagebox.showerror(APP_NAME, err)
                elif item[0] == "done":
                    _, raw, brief, target, mode = item
                    pos, neg, notes = parse_sections(raw)
                    self.positive_text.delete("1.0", "end")
                    self.positive_text.insert("1.0", pos)
                    self.negative_text.delete("1.0", "end")
                    self.negative_text.insert("1.0", neg)
                    if self.beginner_pinned_lora and self.beginner_character_trigger:
                        if self.beginner_character_trigger not in pos:
                            pos = pos.rstrip(" ,，") + ", " + self.beginner_character_trigger
                            self.positive_text.delete("1.0", "end")
                            self.positive_text.insert("1.0", pos)
                    self._add_record(brief, target, mode, pos, neg, notes, raw)
                    self.refine_history = []
                    self._refresh_refine_log()
                    self.generating = False
                    self.generate_btn.configure(state="normal", text="新开一个")
                    self.status_var.set("生成完成 · 已保存版本")
                    if self.gen_cancel.is_set():
                        self.beginner_pending = False
                        self.gen_cancel.clear()
                        if hasattr(self, "beginner_stop_btn"):
                            self.beginner_stop_btn.configure(state="disabled", text="停止")
                        self._beginner_set_progress("已停止；提示词已生成，但没有出图", 0, 1)
                        self.status_var.set("已停止生成")
                        return
                    if self.beginner_pending:
                        self.beginner_pending = False
                        self._beginner_set_progress("第 2 步 / 2：提示词完成，正在出图…", 1, 2)
                        self.beginner_generate_btn.configure(state="disabled", text="出图中…")
                        self.generate_images()
                        self.root.after(200, self._poll_queue)
                        return
                elif item[0] == "error":
                    _, err, brief, target, mode = item
                    self.generating = False
                    self.beginner_pending = False
                    self.gen_cancel.clear()
                    if hasattr(self, "beginner_stop_btn"):
                        self.beginner_stop_btn.configure(state="disabled", text="停止")
                    self.generate_btn.configure(state="normal", text="新开一个")
                    if hasattr(self, "beginner_generate_btn"):
                        self.beginner_generate_btn.configure(state="normal", text="开始生成")
                        self.beginner_progress.configure(text="生成失败")
                    self.status_var.set("生成失败")
                    APP_LOG.error("提示词生成失败: %s", err)
                    messagebox.showerror(APP_NAME, humanize_error(err))
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    # ---------- 版本 / 历史 ----------
    def _add_record(self, brief, target, mode, pos, neg, notes, raw):
        rec = {
            "id": int(time.time() * 1000),
            "time": now_text(),
            "target": target,
            "model": self.model_var.get(),
            "mode": mode,
            "nsfw": mode != "SFW",
            "brief": brief,
            "positive": pos,
            "negative": neg,
            "notes": notes,
            "raw": raw,
            "loras": list(self.selected_loras),
        }
        self.records.insert(0, rec)
        self.records = self.records[:80]
        save_json(HISTORY_FILE, self.records)
        self._write_markdown(rec)
        self._refresh_history()

    def _write_markdown(self, rec):
        safe = re.sub(r"[\\/:*?\"<>|]", "-", rec.get("brief", "未命名"))[:24].strip() or "未命名"
        path = WORKBENCH_LIBRARY / f"{rec['time'].replace(':', '').replace(' ', '-')}-{safe}.md"
        text = f"""# {safe}

- 时间：{rec['time']}
- 目标：{rec['target']}
- 模型：{rec['model']}
- 模式：{rec.get('mode', 'NSFW' if rec.get('nsfw') else 'SFW')}
- LoRA：{'; '.join(x.get('name','') + ' [' + (x.get('trigger') or '无触发词') + ']' for x in rec.get('loras', [])) or '未选择'}

## 原始需求

{rec['brief']}

## Positive

{rec['positive']}

## Negative

{rec['negative']}

## Notes

{rec['notes']}
"""
        path.write_text(text, encoding="utf-8")

    def _refresh_history(self):
        self.history_list.delete(0, "end")
        for rec in self.records[:80]:
            label = f"{rec.get('time', '')[-8:]}  {rec.get('target', '')}  {rec.get('brief', '')[:40]}"
            self.history_list.insert("end", label)
        if hasattr(self, "history_delete_btn"):
            self.history_delete_btn.configure(state="disabled", text="删除选中")

    def _on_history_select(self, event=None):
        sel = self.history_list.curselection()
        if hasattr(self, "history_delete_btn"):
            self.history_delete_btn.configure(
                state="normal" if sel else "disabled",
                text=f"删除选中 ({len(sel)})" if sel else "删除选中")
        if sel:
            self.status_var.set(f"历史已选中 {len(sel)} 条 · 双击打开到左侧 · Delete 删除")
        else:
            self.status_var.set("历史：单击选中，双击打开")

    def _active_history_index(self):
        try:
            idx = self.history_list.index("active")
        except tk.TclError:
            idx = -1
        if 0 <= idx < len(self.records):
            return idx
        sel = self.history_list.curselection()
        return sel[0] if sel else -1

    def _select_all_history(self, event=None):
        if self.history_list.size():
            self.history_list.selection_set(0, "end")
            self._on_history_select()
        return "break"

    def open_active_history(self):
        idx = self._active_history_index()
        if idx >= 0:
            self._load_history_record(idx)

    def _open_history_record(self, event=None):
        if event is not None:
            idx = self.history_list.nearest(event.y)
            if idx < 0 or idx >= self.history_list.size():
                return
            self.history_list.selection_clear(0, "end")
            self.history_list.selection_set(idx)
            self.history_list.activate(idx)
            self._on_history_select()
        else:
            idx = self._active_history_index()
        if idx >= 0:
            self._load_history_record(idx)

    def _history_context_menu(self, event):
        idx = self.history_list.nearest(event.y)
        if idx < 0 or idx >= self.history_list.size():
            return
        if idx not in self.history_list.curselection():
            self.history_list.selection_clear(0, "end")
            self.history_list.selection_set(idx)
        self.history_list.activate(idx)
        self._on_history_select()
        try:
            self.history_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.history_menu.grab_release()

    def delete_active_history(self):
        idx = self._active_history_index()
        if idx < 0:
            self.status_var.set("先选中一条历史")
            return
        self._delete_history_indices([idx])

    def delete_selected_history(self):
        indices = list(self.history_list.curselection())
        if not indices:
            self.status_var.set("先选中要删除的历史")
            return
        self._delete_history_indices(indices)

    def _delete_history_indices(self, indices):
        indices = sorted({int(i) for i in indices if 0 <= int(i) < len(self.records)}, reverse=True)
        if not indices:
            return
        if not messagebox.askyesno(
                APP_NAME,
                f"删除 {len(indices)} 条历史记录？\n\n只删除历史记录，不删除图片、提示词库文件或已保存的版本文件。"):
            return
        for idx in indices:
            self.records.pop(idx)
        save_json(HISTORY_FILE, self.records)
        self._refresh_history()
        self._on_history_select()
        self.status_var.set(f"已删除 {len(indices)} 条历史记录")

    def _load_history_record(self, idx):
        if idx < 0 or idx >= len(self.records):
            return
        rec = self.records[idx]
        self.brief_text.delete("1.0", "end")
        self.brief_text.insert("1.0", rec.get("brief", ""))
        self.positive_text.delete("1.0", "end")
        self.positive_text.insert("1.0", rec.get("positive", ""))
        self.negative_text.delete("1.0", "end")
        self.negative_text.insert("1.0", rec.get("negative", ""))
        if rec.get("target") in TARGETS:
            self.target_var.set(rec["target"])
            self.target_var.set(rec.get("target", list(TARGETS.keys())[0]))
            self._link_done = False
            self._on_target_change(False)
        if rec.get("model") in self.model_combo["values"] or rec.get("model") in [x[0] for x in MODEL_OPTIONS]:
            self.model_var.set(rec["model"])
        mode = rec.get("mode")
        if mode not in ("SFW", "NSFW"):
            mode = "NSFW" if rec.get("nsfw", False) else "SFW"
        self.mode.set(mode)
        self._update_mode_button()
        self.selected_loras = [
            dict(x) for x in rec.get("loras", [])
            if isinstance(x, dict) and Path(x.get("path", "")).exists()
        ]
        self._refresh_lora_selected()
        self.refine_history = []
        self._refresh_refine_log()
        self.refine_entry.delete(0, "end")
        self.tab.select(0)
        self.status_var.set("已打开历史版本到左侧")

    def adjust_gen_count(self, delta):
        value = max(1, min(8, int(self.gen_count_var.get() or 1) + delta))
        self.gen_count_var.set(value)

    def auto_match_loras(self):
        if self.generating:
            return
        wf = self._current_workflow_info()
        if wf["kind"] != "builtin":
            messagebox.showinfo(APP_NAME, "导入工作流使用自带 LoRA；自动匹配只用于内置工作流。")
            return
        positive = self.positive_text.get("1.0", "end").strip()
        if not positive:
            messagebox.showwarning(APP_NAME, "先有 Positive 提示词。")
            return
        self.auto_match_btn.configure(state="disabled", text="匹配中…")
        self.status_var.set("本地 9B 正在匹配 LoRA…")
        threading.Thread(target=self._auto_match_worker, args=(wf["base"], positive), daemon=True).start()
        self.root.after(300, self._poll_auto_match)

    def _auto_match_worker(self, base, positive):
        try:
            cands = []
            for item in self.all_lora_files:
                if item.get("base") != base:
                    continue
                trig, _ = detect_triggers(item["path"], self.known_triggers)
                cands.append({"name": item["name"], "label": item["label"],
                              "path": str(item["path"]), "base": item.get("base", ""),
                              "trigger": " / ".join(trig)})
            chosen, _ = lora_match.auto_match(positive, base, cands, model=self.model_map.get(self.model_var.get()))
            self.match_queue.put(("ok", chosen))
        except Exception as e:
            self.match_queue.put(("err", str(e)))

    def _poll_auto_match(self):
        try:
            kind, payload = self.match_queue.get_nowait()
        except queue.Empty:
            self.root.after(400, self._poll_auto_match)
            return
        self.auto_match_btn.configure(state="normal", text="自动匹配")
        if kind == "ok":
            self.selected_loras = list(payload)
            self.used_models.add(lora_match.MODEL)
            self._refresh_lora_selected()
            self.status_var.set("自动匹配完成：" + "、".join(x["name"] for x in payload))
        else:
            self.status_var.set("自动匹配失败")
            messagebox.showerror(APP_NAME, payload)

    def generate_images(self):
        if self.generating:
            return
        positive = self.positive_text.get("1.0", "end").strip()
        negative = self.negative_text.get("1.0", "end").strip()
        if not positive:
            messagebox.showwarning(APP_NAME, "Positive 提示词为空。")
            return
        wf = self._current_workflow_info()
        count = max(1, min(8, int(self.gen_count_var.get() or 1)))
        close_after = bool(self.gen_close_var.get())
        self.generating = True
        self.gen_cancel.clear()
        APP_LOG.info("开始出图 workflow=%s count=%s ratio=%s auto_lora=%s",
                     wf.get("label"), count, self.beginner_ratio.get() if self.beginner_mode_var.get() else "advanced",
                     bool(self.auto_pick_var.get()))
        if hasattr(self, "beginner_stop_btn"):
            self.beginner_stop_btn.configure(state="normal", text="停止")
        if hasattr(self, "beginner_repeat_btn"):
            self.beginner_repeat_btn.configure(state="disabled")
            self.beginner_result_hint.configure(text="正在生成…")
        self.gen_btn.configure(state="disabled", text=f"出图中 · 已出 0/{count}")
        self.status_var.set(f"准备出图：已出 0/{count}")
        self.tab.select(self.results_tab)
        self._show_results([])
        self.result_note.configure(text="")
        self.result_progress.configure(text=f"已出 0/{count}")
        self.result_progressbar.configure(maximum=count, value=0)
        selected_snapshot = [dict(x) for x in self.selected_loras]
        model_id = self.model_map.get(self.model_var.get(), "")
        width = height = None
        if self.beginner_mode_var.get():
            width, height = BEGINNER_RATIOS.get(self.beginner_ratio.get(), BEGINNER_RATIOS["竖图"])
        threading.Thread(target=self._gen_worker,
                         args=(wf, positive, negative, count, close_after, str(self.output_dir),
                               bool(self.auto_pick_var.get()), selected_snapshot, model_id,
                               width, height),
                         daemon=True).start()
        self.root.after(300, self._poll_gen_queue)

    def _gen_worker(self, wf, positive, negative, count, close_after, out_dir,
                    auto_pick=False, selected_loras=None, model_id=None,
                    width=None, height=None):
        all_images = []
        summary = None
        plan = None
        was_up = wbgen.comfy_is_up()
        active_loras = list(selected_loras or [])
        try:
            if auto_pick and wf["kind"] == "builtin":
                self.gen_queue.put(("matching",))
                cands = []
                for item in self.all_lora_files:
                    if item.get("base") != wf["base"]:
                        continue
                    trig, _ = detect_triggers(item["path"], self.known_triggers)
                    cands.append({"name": item["name"], "label": item["label"],
                                  "path": str(item["path"]), "base": item.get("base", ""),
                                  "trigger": " / ".join(trig)})
                try:
                    active_loras, _ = lora_match.auto_match(
                        positive, wf["base"], cands,
                        model=model_id or "")
                    self.gen_queue.put(("auto", active_loras))
                except Exception as e:
                    active_loras = list(selected_loras or [])
                    self.gen_queue.put((
                        "notice",
                        f"当前底模没有匹配到 LoRA，已直接底模出图。"
                        f"可安装 {wf['base']} LoRA，或到高级模式切换底模。"
                        f"（{str(e)[:80]}）"
                    ))
            pinned = getattr(self, "beginner_pinned_lora", None)
            if pinned and pinned.get("base") == wf.get("base"):
                if all(Path(x.get("path", "")).resolve() != Path(pinned.get("path", "")).resolve()
                       for x in active_loras):
                    active_loras.append(dict(pinned))
            for i in range(count):
                if self.gen_cancel.is_set():
                    break
                self.gen_queue.put(("working", i + 1, count, len(all_images)))
                if wf["kind"] == "imported":
                    result = wbgen.generate_imported(wf["path"], positive, negative, 1, False, out_dir)
                else:
                    comp, _ = wbgen.compatible_loras(wf["key"], active_loras)
                    result = wbgen.generate(wf["key"], positive, negative, comp, 1, False, out_dir,
                                            width=width, height=height)
                summary = result.get("lora_plan_summary") or summary
                plan = result.get("lora_plan") or plan
                all_images.extend(result.get("images", []))
                self.gen_queue.put(("progress", i + 1, count, list(all_images), summary, plan))
            self.gen_queue.put(("done", all_images, summary, plan))
        except Exception as e:
            if self.gen_cancel.is_set():
                self.gen_queue.put(("done", all_images, summary, plan))
            else:
                self.gen_queue.put(("err", str(e)))
        finally:
            if close_after and not was_up:
                try:
                    wbgen.close_comfy()
                except Exception:
                    pass

    def _poll_gen_queue(self):
        try:
            msg = self.gen_queue.get_nowait()
        except queue.Empty:
            self.root.after(400, self._poll_gen_queue)
            return
        kind = msg[0]
        if kind == "matching":
            self.gen_btn.configure(text="自动挑选 LoRA…")
            self.result_progress.configure(text="正在根据提示词和底模挑选 LoRA…")
            self.status_var.set("正在自动挑选 LoRA…")
            self._beginner_set_progress("正在自动挑选 LoRA…", 1, 2)
            self.root.after(250, self._poll_gen_queue)
            return
        if kind == "auto":
            chosen = list(msg[1])
            self.selected_loras = chosen
            self.used_models.add(lora_match.MODEL)
            self._refresh_lora_selected()
            names = "、".join(x["name"] for x in chosen)
            self.result_progress.configure(text="已自动选 LoRA：" + names[:80])
            self.status_var.set("自动选 LoRA：" + names)
            self._beginner_set_progress("已自动选 LoRA，开始出图…", 1, 2)
            self.root.after(250, self._poll_gen_queue)
            return
        if kind == "notice":
            text = str(msg[1])
            self.result_progress.configure(text=text)
            self.status_var.set(text)
            if hasattr(self, "beginner_progress"):
                self.beginner_progress.configure(text=text)
            self.root.after(250, self._poll_gen_queue)
            return
        if kind == "working":
            _, idx, count, done = msg
            self.gen_btn.configure(text=f"出图中 · 已出 {done}/{count}")
            self.result_progress.configure(text=f"第 {idx} 张生成中 · 已出 {done}/{count}")
            self.result_progressbar.configure(maximum=count, value=done)
            self.status_var.set(f"第 {idx} 张生成中 · 已出 {done}/{count}")
            self._beginner_set_progress(f"第 {idx} 张生成中 · 已出 {done}/{count}", done, count)
            self.beginner_generate_btn.configure(text=f"出图中 · 已出 {done}/{count}")
            self.root.after(250, self._poll_gen_queue)
            return
        if kind == "progress":
            _, idx, count, images, summary, plan = msg
            self._show_results(images)
            self._show_beginner_results(images)
            done = len(images)
            self.gen_btn.configure(text=f"出图中 · 已出 {done}/{count}")
            self.result_progress.configure(text=f"已出 {done}/{count}")
            self.result_progressbar.configure(maximum=count, value=done)
            self.status_var.set(f"已出 {done}/{count}")
            self._beginner_set_progress(f"已出 {done}/{count}", done, count)
            self.beginner_generate_btn.configure(text=f"出图中 · 已出 {done}/{count}")
            self.root.after(250, self._poll_gen_queue)
            return
        self.generating = False
        self.gen_btn.configure(state="normal", text="生成并出图")
        if hasattr(self, "beginner_stop_btn"):
            self.beginner_stop_btn.configure(state="disabled", text="停止")
        if hasattr(self, "beginner_generate_btn"):
            self.beginner_generate_btn.configure(state="normal", text="开始生成")
        stopped = self.gen_cancel.is_set()
        self.gen_cancel.clear()
        if kind == "done":
            _, images, summary, plan = msg
            self._show_results(images)
            self._show_beginner_results(images)
            if stopped and not images:
                self._beginner_set_progress("已停止，没有生成图片", 0, 1)
                self.result_progress.configure(text="已停止")
                self.status_var.set("已停止生成")
                self.beginner_result_hint.configure(text="已停止；可修改描述后重新生成")
                return
            if hasattr(self, "beginner_repeat_btn"):
                self.beginner_repeat_btn.configure(state="normal")
                self.beginner_result_hint.configure(
                    text=f"{'已停止，' if stopped else ''}已出 {len(images)} 张 · 可再来一张或打开输出")
            self._beginner_set_progress(
                f"{'已停止，' if stopped else ''}完成 {len(images)}/{len(images)}",
                len(images), max(1, len(images)))
            self.result_progressbar.configure(maximum=max(1, len(images)), value=len(images))
            self.result_progress.configure(text=f"完成 {len(images)}/{len(images)}")
            if summary:
                names = [Path(x["name"]).name for x in (plan or []) if x.get("enabled")]
                self.result_note.configure(
                    text=f"导入工作流 LoRA 自动整理：开 {summary.get('enabled', 0)} / 旁 {summary.get('bypassed', 0)}；启用：{'、'.join(names[:6])}")
                self.status_var.set(
                    f"出图完成：{len(images)} 张 · LoRA 开 {summary.get('enabled', 0)} / 旁 {summary.get('bypassed', 0)}")
            else:
                self.result_note.configure(text="")
                self.status_var.set(f"出图完成：{len(images)} 张")
            self.tab.select(self.results_tab)
        else:
            self.result_progress.configure(text="出图失败")
            self._beginner_set_progress("出图失败，请查看提示", 0, 1)
            self.beginner_result_hint.configure(text="出图失败")
            self.status_var.set("出图失败")
            APP_LOG.error("出图失败: %s", msg[1])
            messagebox.showerror(APP_NAME, humanize_error(msg[1]))
        self._schedule_env_refresh()

    def _show_results(self, paths):
        paths = sorted(paths, key=lambda p: Path(p).name)
        for w in self.results_inner.winfo_children():
            w.destroy()
        self._result_photos = []
        self.result_paths = list(paths)
        for i, path in enumerate(paths[:8]):
            cell = tk.Frame(self.results_inner, bg=COLORS["panel"])
            cell.grid(row=i // 2, column=i % 2, padx=6, pady=4, sticky="n")
            try:
                img = tk.PhotoImage(file=path)
                factor = max(1, img.width() // 155, img.height() // 215)
                thumb = img.subsample(factor, factor)
                btn = tk.Button(cell, image=thumb, bd=0, relief="flat", bg=COLORS["panel"],
                                activebackground=COLORS["panel"], cursor="hand2",
                                command=lambda p=path: os.startfile(p))
                btn.image = thumb
                btn.pack()
                self._result_photos.append(thumb)
            except Exception as e:
                tk.Label(cell, text="预览失败\n" + Path(path).name, bg=COLORS["panel"],
                         fg=COLORS["red"], font=("Microsoft YaHei UI", 9)).pack()
            tk.Label(cell, text=Path(path).name[-28:], bg=COLORS["panel"], fg=COLORS["muted"],
                     font=("Microsoft YaHei UI", 7), wraplength=170).pack()

    def open_generate_dialog(self):
        if getattr(self, "gen_dialog", None) is not None:
            try:
                self.gen_dialog.lift()
                return
            except Exception:
                self.gen_dialog = None

        top = tk.Toplevel(self.root)
        self.gen_dialog = top
        top.title("工作台出图")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 660, 440)
        top.transient(self.root)
        top.resizable(False, False)
        try:
            top.iconbitmap(str(APP_ICON))
        except Exception:
            pass

        tk.Label(top, text="工作台出图", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text="使用当前正/负提示词和已加入的 LoRA；可自动启动/关闭 ComfyUI。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20, pady=(0, 12))

        labels = self._workflow_labels()
        current_info = self._current_workflow_info()
        workflow_var = tk.StringVar(value=current_info["label"])
        count_var = tk.IntVar(value=1)
        close_var = tk.BooleanVar(value=True)

        form = tk.Frame(top, bg=COLORS["panel"], highlightbackground=COLORS["line"], highlightthickness=1)
        form.pack(fill="x", padx=20)
        row = tk.Frame(form, bg=COLORS["panel"])
        row.pack(fill="x", padx=12, pady=10)
        tk.Label(row, text="工作流", bg=COLORS["panel"], fg=COLORS["muted"], font=FONT_SMALL).pack(side="left")
        combo = ttk.Combobox(row, textvariable=workflow_var, state="readonly",
                             values=labels, width=32)
        combo.pack(side="left", padx=(8, 16))
        self._disable_combo_wheel(combo)
        tk.Label(row, text="张数", bg=COLORS["panel"], fg=COLORS["muted"], font=FONT_SMALL).pack(side="left")
        tk.Spinbox(row, from_=1, to=4, textvariable=count_var, width=4,
                   bg=COLORS["input"], fg=COLORS["text"], relief="flat", bd=0).pack(side="left", padx=(6, 0))

        info = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["muted"],
                        font=("Microsoft YaHei UI", 9), anchor="w", justify="left")
        info.pack(fill="x", padx=20, pady=(10, 4))
        status = tk.Label(top, text="准备就绪", bg=COLORS["bg"], fg=COLORS["accent2"],
                          font=FONT_SMALL, anchor="w")
        status.pack(fill="x", padx=20)

        def selected_info():
            imp = self._find_imported(workflow_var.get())
            if imp:
                return {"kind": "imported", "path": imp["path"], "base": imp.get("base", "Unknown"),
                        "label": imp.get("label", workflow_var.get()), "loras": imp.get("loras", 0)}
            for key, spec in wbgen.WORKFLOWS.items():
                if spec["name"] == workflow_var.get():
                    return {"kind": "builtin", "key": key, "base": spec["base"], "label": spec["name"]}
            key = self._current_generation_key()
            return {"kind": "builtin", "key": key, "base": wbgen.WORKFLOWS[key]["base"],
                    "label": wbgen.WORKFLOWS[key]["name"]}

        def refresh_info():
            wf = selected_info()
            if wf["kind"] == "imported":
                info.configure(text=f"导入：{Path(wf['path']).name}  |  底模：{wf['base']}  |  LoRA {wf.get('loras', 0)} 个")
                status.configure(text="导入工作流使用自带 LoRA；自动匹配只用于内置工作流", fg=COLORS["accent2"])
                return
            key = wf["key"]
            spec = wbgen.WORKFLOWS[key]
            comp, skipped = wbgen.compatible_loras(key, self.selected_loras)
            info.configure(text=f"底模：{spec['base']}    兼容 LoRA：{len(comp)} 个    跳过不匹配：{len(skipped)} 个")

        def on_workflow_change():
            self.generation_workflow_var.set(workflow_var.get())
            self._save_settings()
            refresh_info()

        combo.bind("<<ComboboxSelected>>", lambda e: on_workflow_change())
        refresh_info()

        bottom = tk.Frame(top, bg=COLORS["bg"])
        bottom.pack(fill="x", padx=20, pady=(12, 8))
        ttk.Checkbutton(bottom, text="本次启动的 ComfyUI 在完成后关闭", variable=close_var).pack(side="left")
        auto_btn = tk.Button(bottom, text="自动匹配 LoRA", bg=COLORS["card2"], fg=COLORS["text"],
                             activebackground=COLORS["accent2"], activeforeground="#fff",
                             relief="flat", bd=0, padx=10, pady=6, font=FONT_SMALL, cursor="hand2")
        auto_btn.pack(side="left", padx=(10, 0))
        q = queue.Queue()
        run_btn = tk.Button(bottom, text="生成并出图", bg=COLORS["accent"], fg="#fff",
                            activebackground=COLORS["accent2"], relief="flat", bd=0,
                            padx=16, pady=7, font=("Microsoft YaHei UI", 9, "bold"), cursor="hand2")
        run_btn.pack(side="right")

        auto_q = queue.Queue()

        def candidates_for(base):
            out = []
            for item in self.all_lora_files:
                if item.get("base") != base:
                    continue
                triggers, _ = detect_triggers(item["path"], self.known_triggers)
                out.append({
                    "name": item["name"], "label": item["label"], "path": str(item["path"]),
                    "base": item.get("base", ""), "trigger": " / ".join(triggers),
                })
            return out

        def auto_worker(base, positive):
            try:
                cands = candidates_for(base)
                chosen, raw = lora_match.auto_match(positive, base, cands, model=self.model_map.get(self.model_var.get()))
                auto_q.put(("ok", chosen, raw))
            except Exception as e:
                auto_q.put(("err", str(e), ""))

        def auto_poll():
            if not top.winfo_exists():
                return
            try:
                kind, payload, raw = auto_q.get_nowait()
            except queue.Empty:
                top.after(400, auto_poll)
                return
            auto_btn.configure(state="normal", text="自动匹配 LoRA")
            if kind == "ok":
                self.selected_loras = list(payload)
                self.used_models.add(lora_match.MODEL)
                self._refresh_lora_selected()
                refresh_info()
                names = "、".join(x["name"] for x in payload)
                status.configure(text="自动匹配：" + names, fg=COLORS["green"])
            else:
                status.configure(text="自动匹配失败：" + payload[:160], fg=COLORS["red"])

        def auto_run():
            wf = selected_info()
            if wf["kind"] != "builtin":
                messagebox.showinfo(APP_NAME, "导入工作流使用自带 LoRA；自动匹配只用于内置工作流。", parent=top)
                return
            positive = self.positive_text.get("1.0", "end").strip()
            if not positive:
                messagebox.showwarning(APP_NAME, "先有 Positive 提示词。", parent=top)
                return
            auto_btn.configure(state="disabled", text="匹配中…")
            status.configure(text="本地 9B 正在分析提示词与 LoRA…", fg=COLORS["accent2"])
            threading.Thread(target=auto_worker, args=(wf["base"], positive), daemon=True).start()
            top.after(300, auto_poll)

        auto_btn.configure(command=auto_run)

        def worker(key, imported, positive, negative, comp, count, close_after):
            try:
                if imported:
                    q.put(("ok", wbgen.generate_imported(imported, positive, negative, count, close_after)))
                else:
                    q.put(("ok", wbgen.generate(key, positive, negative, comp, count, close_after)))
            except Exception as e:
                q.put(("err", str(e)))

        def poll():
            if not top.winfo_exists():
                return
            try:
                kind, payload = q.get_nowait()
            except queue.Empty:
                top.after(400, poll)
                return
            run_btn.configure(state="normal", text="生成并出图")
            if kind == "ok":
                status.configure(text="完成：" + payload["images"][-1], fg=COLORS["green"])
                try:
                    os.startfile(payload["images"][-1])
                except Exception:
                    pass
            else:
                status.configure(text="失败：" + payload[:160], fg=COLORS["red"])
                messagebox.showerror(APP_NAME, payload, parent=top)

        def run():
            wf = selected_info()
            positive = self.positive_text.get("1.0", "end").strip()
            negative = self.negative_text.get("1.0", "end").strip()
            if not positive:
                messagebox.showwarning(APP_NAME, "Positive 提示词为空。", parent=top)
                return
            if wf["kind"] == "imported":
                key, comp = None, []
                imported = wf["path"]
            else:
                key = wf["key"]
                comp, skipped = wbgen.compatible_loras(key, self.selected_loras)
                imported = None
            count = max(1, min(4, int(count_var.get() or 1)))
            run_btn.configure(state="disabled", text="生成中…")
            status.configure(text="准备 ComfyUI / 出图中…", fg=COLORS["accent2"])
            threading.Thread(target=worker, args=(key, imported, positive, negative, comp, count, bool(close_var.get())), daemon=True).start()
            top.after(300, poll)

        run_btn.configure(command=run)
        tk.Label(bottom, text="细节调节 / 自定义工作流请进 ComfyUI",
                 bg=COLORS["bg"], fg="#8a93a6", font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(12, 0))

        def on_close():
            self.gen_dialog = None
            top.destroy()

        top.protocol("WM_DELETE_WINDOW", on_close)

    def save_version(self):
        brief = self.brief_text.get("1.0", "end").strip()
        pos = self.positive_text.get("1.0", "end").strip()
        neg = self.negative_text.get("1.0", "end").strip()
        if not pos and not neg:
            messagebox.showwarning(APP_NAME, "当前没有提示词可保存。")
            return
        self._add_record(brief, self.target_var.get(), self.mode.get(), pos, neg, "", "")
        self.status_var.set("版本已保存")

    # ---------- 外部动作 ----------
    def _all_prompt(self):
        pos = self.positive_text.get("1.0", "end").strip()
        neg = self.negative_text.get("1.0", "end").strip()
        return f"【Positive】\n{pos}\n\n【Negative】\n{neg}".strip()

    def _copy_to_clipboard(self, text, label):
        if not text.strip():
            self.status_var.set(f"{label}为空")
            return False
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set(f"已复制{label}")
        return True

    def copy_positive(self):
        text = self.positive_text.get("1.0", "end").strip()
        self._copy_to_clipboard(text, "正向提示词")

    def copy_negative(self):
        text = self.negative_text.get("1.0", "end").strip()
        self._copy_to_clipboard(text, "负向提示词")

    def copy_all(self):
        text = self._all_prompt()
        self._copy_to_clipboard(text, " Positive + Negative")

    def open_tool80(self):
        self.copy_all()
        if not TOOL80 or not TOOL80.exists():
            messagebox.showerror(APP_NAME, "尚未配置 8.0 精修工具路径。\n请到“环境设置”中填写。")
            return
        try:
            os.startfile(str(TOOL80))
            self.status_var.set("已复制，8.0 已打开，直接粘贴")
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))

    def _output_dir_text(self):
        text = str(self.output_dir)
        return text if len(text) <= 72 else text[:34] + "…" + text[-34:]

    def choose_output_dir(self):
        path = filedialog.askdirectory(parent=self.root, title="选择生成图片输出目录",
                                       initialdir=str(self.output_dir), mustexist=False)
        if not path:
            return
        try:
            new_dir = Path(path)
            new_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror(APP_NAME, f"无法使用该目录：{e}")
            return
        self.output_dir = new_dir
        self.outdir_label.configure(text=self._output_dir_text())
        self._save_settings()
        self.status_var.set(f"输出目录已更改：{new_dir}")

    def open_output_dir(self):
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.output_dir))
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))

    def _open_center_for_beginner_base(self):
        base = self._beginner_base()
        self.open_model_center(initial_query=base["label"], initial_kind="底模")

    def open_model_center(self, initial_query="", initial_kind="LoRA"):
        if getattr(self, "model_center_dialog", None) is not None:
            try:
                self.model_center_dialog.lift()
                return
            except Exception:
                self.model_center_dialog = None
        top = tk.Toplevel(self.root)
        self.model_center_dialog = top
        top.title("模型中心 · Civitai")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 980, 690)
        top.transient(self.root)

        tk.Label(top, text="模型中心", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 18, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text="Civitai 搜索；下载前会显示大小并要求确认。不会静默下载。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20)
        tk.Label(top, text="网络提示：直连 CDN 优先；直连超时可测试 Ikuuu（VPN/梯子），也可自行使用同类工具。它们只是网络工具，不是模型来源。",
                 bg=COLORS["bg"], fg=COLORS["accent2"], font=("Microsoft YaHei UI", 9)).pack(
                     anchor="w", padx=20, pady=(2, 8))

        search_row = tk.Frame(top, bg=COLORS["panel"])
        search_row.pack(fill="x", padx=20, pady=(0, 8))
        query_var = tk.StringVar(value=initial_query)
        kind_var = tk.StringVar(value=initial_kind)
        base_var = tk.StringVar(value="全部")
        ent = tk.Entry(search_row, textvariable=query_var, bg=COLORS["input"], fg=COLORS["text"],
                       insertbackground=COLORS["text"], relief="flat", bd=0,
                       highlightbackground=COLORS["line"], highlightthickness=1,
                       font=("Microsoft YaHei UI", 10))
        ent.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
        ent.bind("<Return>", lambda e: do_search())
        ttk.Combobox(search_row, textvariable=kind_var, values=["LoRA", "底模"],
                     state="readonly", width=7).pack(side="left", padx=(0, 6))
        ttk.Combobox(search_row, textvariable=base_var,
                     values=["全部", "Illustrious", "Pony", "SDXL 1.0", "SD 1.5", "MOSS", "Anima", "Krea 2", "Qwen"],
                     state="readonly", width=14).pack(side="left", padx=(0, 6))
        tk.Button(search_row, text="搜索", command=lambda: do_search(),
                  bg=COLORS["accent"], fg="#fff", relief="flat", bd=0, padx=14, pady=5,
                  cursor="hand2").pack(side="left")

        status = tk.Label(top, text="输入关键词开始搜索", bg=COLORS["bg"], fg=COLORS["muted"],
                          font=FONT_SMALL, anchor="w")
        status.pack(fill="x", padx=20, pady=(0, 4))

        tree_frame = tk.Frame(top, bg=COLORS["panel"])
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 6))
        cols = ("name", "base", "size", "downloads")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for col, title, width in (("name", "名称", 360), ("base", "底模", 150),
                                  ("size", "大小", 90), ("downloads", "下载量", 90)):
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)

        detail = tk.Text(top, height=5, wrap="word", bg=COLORS["panel"], fg=COLORS["text"],
                         relief="flat", bd=0, font=("Microsoft YaHei UI", 9), padx=10, pady=8)
        detail.pack(fill="x", padx=20, pady=(0, 6))
        detail.configure(state="disabled")

        bottom = tk.Frame(top, bg=COLORS["bg"])
        bottom.pack(fill="x", padx=20, pady=(0, 12))
        progress = ttk.Progressbar(bottom, orient="horizontal", mode="determinate", maximum=100)
        progress.pack(side="left", fill="x", expand=True, padx=(0, 10))
        download_btn = tk.Button(bottom, text="下载选中版本", state="disabled",
                                 bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                                 padx=14, pady=5, cursor="hand2")
        download_btn.pack(side="right")
        cancel_event = threading.Event()
        cancel_btn = tk.Button(bottom, text="取消", state="disabled",
                               bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                               padx=10, pady=5, cursor="hand2")
        cancel_btn.pack(side="right", padx=(0, 6))
        records = []
        busy = {"search": False, "download": False}
        q = queue.Queue()

        def render(rows):
            records.clear()
            records.extend(rows)
            for iid in tree.get_children():
                tree.delete(iid)
            for i, rec in enumerate(records):
                size = f"{rec['size_kb'] / 1024:.1f} MB" if rec.get("size_kb") else "未知"
                tree.insert("", "end", iid=str(i), values=(
                    rec.get("name", ""), rec.get("base", ""), size, rec.get("downloads", 0)))
            detail.configure(state="normal")
            detail.delete("1.0", "end")
            detail.insert("1.0", f"找到 {len(records)} 个结果；选中一行查看详情。")
            detail.configure(state="disabled")
            status.configure(text=f"找到 {len(records)} 个结果")
            download_btn.configure(state="disabled")

        def show_detail(_event=None):
            sel = tree.selection()
            if not sel:
                return
            rec = records[int(sel[0])]
            detail.configure(state="normal")
            detail.delete("1.0", "end")
            detail.insert("1.0", (
                f"{rec.get('name', '')}\n"
                f"底模：{rec.get('base', '')}  ·  版本：{rec.get('version_name', '')}  ·  "
                f"文件：{rec.get('file_name', '')}\n"
                f"作者：{rec.get('creator', '')}  ·  页面：{rec.get('page_url', '')}\n"
                f"训练词：{'、'.join(rec.get('trained_words') or [])[:180] or '无'}"
            ))
            detail.configure(state="disabled")
            download_btn.configure(state="normal")

        tree.bind("<<TreeviewSelect>>", show_detail)

        def do_search():
            if busy["search"]:
                return
            qtext = query_var.get().strip()
            if not qtext:
                messagebox.showwarning(APP_NAME, "先输入模型名称或关键词。", parent=top)
                return
            busy["search"] = True
            status.configure(text="正在搜索 Civitai…")
            search_btn_state(False)
            kind = "lora" if kind_var.get() == "LoRA" else "checkpoint"

            def worker():
                try:
                    rows = model_center.search_civitai(
                        qtext, kind=kind, base=base_var.get(),
                        api_key=str(CFG.get("civitai_api_key", "") or ""))
                    q.put(("ok", rows))
                except Exception as e:
                    q.put(("err", str(e)))

            threading.Thread(target=worker, daemon=True).start()
            poll_search()

        def poll_search():
            try:
                kind, payload = q.get_nowait()
            except queue.Empty:
                top.after(120, poll_search)
                return
            busy["search"] = False
            search_btn_state(True)
            if kind == "ok":
                render(payload)
            else:
                status.configure(text="搜索失败")
                messagebox.showerror(APP_NAME, f"搜索失败：{payload}\n\n直连失败时可测试 Ikuuu。", parent=top)

        def search_btn_state(enabled):
            for child in search_row.winfo_children():
                if isinstance(child, tk.Button):
                    child.configure(state="normal" if enabled else "disabled")

        def do_download():
            if busy["download"]:
                return
            sel = tree.selection()
            if not sel:
                return
            rec = records[int(sel[0])]
            size_mb = rec.get("size_kb", 0) / 1024
            try:
                dest_dir = model_center.destination_dir(
                    CFG, "lora" if kind_var.get() == "LoRA" else "checkpoint")
            except Exception as e:
                messagebox.showerror(APP_NAME, str(e), parent=top)
                return
            target = dest_dir / model_center.safe_filename(rec.get("file_name", "model.safetensors"))
            if target.exists() and not messagebox.askyesno(
                    APP_NAME, f"文件已存在：\n{target}\n覆盖？", parent=top):
                return
            if not messagebox.askyesno(
                    APP_NAME,
                    f"下载 {rec.get('name', '')}\n大小约 {size_mb:.1f} MB\n保存到：\n{target}\n\n"
                    "请确认模型许可和内容边界。继续？", parent=top):
                return
            busy["download"] = True
            cancel_event.clear()
            download_btn.configure(state="disabled", text="下载中…")
            cancel_btn.configure(state="normal")
            progress["value"] = 0

            def progress_cb(done, total):
                q.put(("progress", done, total))

            def worker():
                try:
                    path = model_center.download_model(rec, CFG, progress=progress_cb,
                                                       cancel=cancel_event)
                    q.put(("downloaded", str(path)))
                except Exception as e:
                    q.put(("download_err", str(e)))

            threading.Thread(target=worker, daemon=True).start()
            poll_download()

        def poll_download():
            try:
                item = q.get_nowait()
            except queue.Empty:
                top.after(150, poll_download)
                return
            kind = item[0]
            if kind == "progress":
                _, done, total = item
                progress.configure(maximum=max(1, total), value=done)
                if total:
                    status.configure(text=f"下载中 {done / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB")
                top.after(150, poll_download)
                return
            busy["download"] = False
            cancel_btn.configure(state="disabled", text="取消")
            download_btn.configure(state="normal", text="下载选中版本")
            if kind == "downloaded":
                status.configure(text="下载完成")
                messagebox.showinfo(APP_NAME, f"下载完成：\n{item[1]}", parent=top)
                if kind_var.get() == "LoRA":
                    self._load_loras()
                self._refresh_beginner_missing()
            else:
                status.configure(text="下载失败或已取消；再次下载会尝试续传")
                messagebox.showerror(APP_NAME, f"下载失败：{item[1]}", parent=top)

        def cancel_download():
            if busy["download"]:
                cancel_event.set()
                cancel_btn.configure(state="disabled", text="取消中…")
                status.configure(text="正在取消下载；.part 文件会保留，下次续传。")

        cancel_btn.configure(command=cancel_download)
        download_btn.configure(command=do_download)
        top.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "model_center_dialog", None), top.destroy()))

    def open_model_guide(self):
        top = tk.Toplevel(self.root)
        top.title("模型指南")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 780, 640)
        top.transient(self.root)
        tk.Label(top, text="模型指南", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text="建议用于选型；NSFW 开关不等于画图模型解锁。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20, pady=(0, 8))
        box = ScrolledText(top, wrap="word", bg=COLORS["panel"], fg=COLORS["text"],
                           relief="flat", bd=0, font=("Microsoft YaHei UI", 9), padx=12, pady=10)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        box.insert("1.0", model_guide.guide_text())
        box.configure(state="disabled")
        tk.Button(top, text="关闭", command=top.destroy, bg=COLORS["card2"], fg=COLORS["text"],
                  relief="flat", bd=0, padx=16, pady=5, cursor="hand2").pack(
                      anchor="e", padx=20, pady=(0, 12))

    def open_first_run_wizard(self):
        if getattr(self, "first_run_dialog", None) is not None:
            try:
                self.first_run_dialog.lift()
                return
            except Exception:
                self.first_run_dialog = None
        top = tk.Toplevel(self.root)
        self.first_run_dialog = top
        top.title("首次使用 · 三步准备")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 760, 620)
        top.transient(self.root)
        top.grab_set()
        page_var = tk.IntVar(value=0)
        pages = []
        state = {"lora": "", "output": "", "comfy": str(CFG.get("comfy_url")),
                 "llm": str(CFG.get("llm_base_url"))}
        detected = detect_comfy_installations()
        det = detected[0] if detected else None
        if det:
            if not CFG.get("checkpoint_dir") and Path(det["checkpoints"]).exists():
                CFG.set("checkpoint_dir", det["checkpoints"])
            if not CFG.get("comfy_workflows_dir") and Path(det["workflows"]).exists():
                CFG.set("comfy_workflows_dir", det["workflows"])
            if not CFG.get("comfy_start_script") and det.get("start"):
                CFG.set("comfy_start_script", det["start"])
        header = tk.Frame(top, bg=COLORS["bg"])
        header.pack(fill="x", padx=22, pady=(18, 6))
        tk.Label(header, text="首次使用 · 三步准备", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 17, "bold")).pack(anchor="w")
        step_label = tk.Label(header, text="", bg=COLORS["bg"], fg=COLORS["muted"],
                              font=FONT_SMALL)
        step_label.pack(anchor="w", pady=(4, 0))
        body = tk.Frame(top, bg=COLORS["panel"], highlightbackground=COLORS["line"],
                        highlightthickness=1)
        body.pack(fill="both", expand=True, padx=22, pady=8)
        bar = tk.Frame(top, bg=COLORS["bg"])
        bar.pack(fill="x", padx=22, pady=(0, 14))

        def show_page(index):
            page_var.set(index)
            for p in pages:
                p.pack_forget()
            pages[index].pack(fill="both", expand=True, padx=18, pady=16)
            step_label.configure(text=f"第 {index + 1} / 3 步")

        # page 0: detect
        p0 = tk.Frame(body, bg=COLORS["panel"])
        pages.append(p0)
        tk.Label(p0, text="先看看这台电脑准备好了没有", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        tk.Label(p0, text="只检测，不会自动下载大模型。", bg=COLORS["panel"], fg=COLORS["muted"],
                 font=FONT_SMALL).pack(anchor="w", pady=(4, 12))
        gpu_label = tk.Label(p0, text="", bg=COLORS["panel"], fg=COLORS["text"],
                             font=("Microsoft YaHei UI", 10), anchor="w", justify="left")
        gpu_label.pack(fill="x", pady=(0, 8))
        gpu_label.configure(text=(
            f"显卡：{self.gpu_name}\n显存：{self.gpu_vram_mb / 1024:.0f} GB"
            if self.gpu_vram_mb else
            (f"显卡：{self.gpu_name}\n显存：未检测（非 NVIDIA 或驱动不提供）"
             if self.gpu_name else "显卡：未检测到；仍可手动配置")))
        llm_label = tk.Label(p0, text="LLM：未检查", bg=COLORS["panel"], fg=COLORS["muted"],
                             font=FONT_SMALL, anchor="w")
        llm_label.pack(fill="x", pady=2)
        comfy_label = tk.Label(p0, text="ComfyUI：未检查", bg=COLORS["panel"], fg=COLORS["muted"],
                               font=FONT_SMALL, anchor="w")
        comfy_label.pack(fill="x", pady=2)

        def check_env():
            llm_label.configure(text="LLM：检查中…", fg=COLORS["muted"])
            comfy_label.configure(text="ComfyUI：检查中…", fg=COLORS["muted"])

            def worker():
                llm_ok = False
                try:
                    llm_ok = bool(llm_client.list_models(CFG))
                except Exception:
                    pass
                comfy_ok = False
                try:
                    with urllib.request.urlopen(str(CFG.get("comfy_url")).rstrip("/") + "/system_stats",
                                                timeout=4) as r:
                        comfy_ok = r.status < 500
                except Exception:
                    pass
                self.root.after(0, lambda: (
                    llm_label.configure(text="LLM：✓ 已连接" if llm_ok else "LLM：✕ 未连接，需手动启动",
                                        fg=COLORS["green"] if llm_ok else COLORS["red"]),
                    comfy_label.configure(text="ComfyUI：✓ 已连接" if comfy_ok else "ComfyUI：✕ 未连接",
                                          fg=COLORS["green"] if comfy_ok else COLORS["red"]),
                ))
            threading.Thread(target=worker, daemon=True).start()

        tk.Button(p0, text="开始检查", command=check_env, bg=COLORS["card2"], fg=COLORS["text"],
                  relief="flat", bd=0, padx=12, pady=5, cursor="hand2").pack(anchor="w", pady=(12, 0))

        # page 1: paths
        p1 = tk.Frame(body, bg=COLORS["panel"])
        pages.append(p1)
        tk.Label(p1, text="告诉工作台模型在哪里", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        tk.Label(p1, text="只填最关键的几项，其余可用默认值。", bg=COLORS["panel"],
                 fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", pady=(4, 10))
        fields = {}

        def wizard_row(key, label, browse=False, default=None):
            row = tk.Frame(p1, bg=COLORS["panel"])
            row.pack(fill="x", pady=4)
            tk.Label(row, text=label, width=13, anchor="w", bg=COLORS["panel"],
                     fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(side="left")
            var = tk.StringVar(value=str(default if default is not None else (CFG.get(key, "") or "")))
            fields[key] = var
            ent = tk.Entry(row, textvariable=var, bg=COLORS["input"], fg=COLORS["text"],
                           insertbackground=COLORS["text"], relief="flat", bd=0,
                           highlightbackground=COLORS["line"], highlightthickness=1,
                           font=("Microsoft YaHei UI", 9))
            ent.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 5))
            if browse:
                tk.Button(row, text="浏览…",
                          command=lambda v=var: self._browse_setting(v, "dir"),
                          bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                          padx=8, pady=3, cursor="hand2").pack(side="left")
            return var

        wizard_row("lora_roots", "LoRA 根目录",
                   browse=True,
                   default=("; ".join(str(x) for x in CFG.paths("lora_roots"))
                            or (det["loras"] if det else "")))
        wizard_row("output_dir", "输出目录", browse=True)
        wizard_row("comfy_url", "ComfyUI 地址")
        wizard_row("llm_base_url", "LLM 地址")
        if det:
            tk.Label(p1, text=f"已自动找到 ComfyUI：{det['root']}",
                     bg=COLORS["panel"], fg=COLORS["green"],
                     font=("Microsoft YaHei UI", 9)).pack(anchor="w", pady=(6, 0))

        # page 2: finish
        p2 = tk.Frame(body, bg=COLORS["panel"])
        pages.append(p2)
        tk.Label(p2, text="可以开始了", bg=COLORS["panel"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w")
        finish_hint = tk.Label(p2, text="推荐：9B + Illustrious/WAI。\n"
                                        "底模齐全后，简洁模式可以直接出图。\n"
                                        "缺失的配置可以在主界面继续补齐。",
                               bg=COLORS["panel"], fg=COLORS["muted"], justify="left",
                               font=("Microsoft YaHei UI", 10))
        finish_hint.pack(anchor="w", pady=(10, 12))
        tk.Button(p2, text="打开完整环境设置",
                  command=lambda: (self._finish_first_run(top, fields), top.destroy(),
                                   self.open_settings_dialog()),
                  bg=COLORS["panel"], fg=COLORS["accent2"], relief="flat", bd=0,
                  padx=4, pady=3, cursor="hand2").pack(anchor="w")
        test_status = tk.Label(p2, text="", bg=COLORS["panel"], fg=COLORS["muted"],
                               font=FONT_SMALL, wraplength=620, justify="left")
        test_status.pack(anchor="w", pady=(10, 2))
        test_btn = tk.Button(p2, text="测试一张", bg=COLORS["card2"], fg=COLORS["text"],
                             relief="flat", bd=0, padx=12, pady=5, cursor="hand2")
        test_btn.pack(anchor="w")

        def test_image():
            for key, var in fields.items():
                CFG.set(key, [x.strip() for x in var.get().split(";") if x.strip()]
                        if key == "lora_roots" else var.get().strip())
            out_dir = DATA_DIR / "first-run-test"
            out_dir.mkdir(parents=True, exist_ok=True)
            test_btn.configure(state="disabled", text="测试中…")
            test_status.configure(text="正在启动/连接 ComfyUI 并生成一张测试图；首次可能要等 1–3 分钟。")

            def worker():
                try:
                    paths = wbgen.generate(
                        "illustrious", "1girl, adult, portrait, simple background",
                        "low quality, worst quality", [], 1, True, str(out_dir), 832, 1216)
                    self.root.after(0, lambda: (
                        test_btn.configure(state="normal", text="再测一张"),
                        test_status.configure(
                            text=f"测试成功：{paths[0] if paths else '已生成'}",
                            fg=COLORS["green"]),
                        messagebox.showinfo(APP_NAME,
                                            f"测试出图成功：\n{paths[0] if paths else out_dir}",
                                            parent=top)))
                except Exception as e:
                    msg = humanize_error(str(e))
                    APP_LOG.error("首次向导测试出图失败: %s", e)
                    self.root.after(0, lambda: (
                        test_btn.configure(state="normal", text="重试测试"),
                        test_status.configure(text="测试失败：" + msg, fg=COLORS["red"]),
                        messagebox.showerror(APP_NAME, "测试失败：\n" + msg, parent=top)))
            threading.Thread(target=worker, daemon=True).start()

        test_btn.configure(command=test_image)

        def next_page():
            idx = page_var.get()
            if idx == 1:
                for key, var in fields.items():
                    CFG.set(key, [x.strip() for x in var.get().split(";") if x.strip()]
                            if key == "lora_roots" else var.get().strip())
            if idx < 2:
                show_page(idx + 1)

        def prev_page():
            if page_var.get() > 0:
                show_page(page_var.get() - 1)

        def finish():
            self._finish_first_run(top, fields)
            try:
                CFG.save()
            except Exception as e:
                messagebox.showerror(APP_NAME, f"保存失败：{e}", parent=top)
                return
            top.destroy()
            self.first_run_dialog = None
            messagebox.showinfo(APP_NAME, "首次配置已保存。\n建议关闭并重新启动工作台，让模型路径生效。")

        tk.Button(bar, text="上一步", command=prev_page, bg=COLORS["panel"],
                  fg=COLORS["muted"], relief="flat", bd=0, padx=12, pady=6,
                  cursor="hand2").pack(side="left")
        tk.Button(bar, text="下一步", command=next_page, bg=COLORS["card2"],
                  fg=COLORS["text"], relief="flat", bd=0, padx=14, pady=6,
                  cursor="hand2").pack(side="right")
        tk.Button(bar, text="保存并进入", command=finish, bg=COLORS["accent"],
                  fg="#fff", relief="flat", bd=0, padx=14, pady=6,
                  cursor="hand2").pack(side="right", padx=(0, 6))
        show_page(0)
        top.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "first_run_dialog", None), top.destroy()))

    def _finish_first_run(self, top, fields):
        for key, var in fields.items():
            value = var.get().strip()
            CFG.set(key, [x.strip() for x in value.split(";") if x.strip()]
                    if key == "lora_roots" else value)
        CFG.save()
        self.first_run_dialog = None

    def open_recommended_pack(self):
        if self._dialog_already_open("recommended_pack_dialog"):
            return
        top = tk.Toplevel(self.root)
        self.recommended_pack_dialog = top
        top.title("推荐模型包")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 720, 470)
        top.transient(self.root)
        tk.Label(top, text="推荐模型包", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text="最小组合：9B + Illustrious/WAI + 一个匹配的 NSFW LoRA。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20)
        card = tk.Frame(top, bg=COLORS["panel"], highlightbackground=COLORS["line"],
                        highlightthickness=1)
        card.pack(fill="both", expand=True, padx=20, pady=10)
        missing = self._beginner_missing() if self._beginner_base()["key"] == "illustrious" else []
        illustrated = next((x for x in BEGINNER_BASES if x["key"] == "illustrious"), BEGINNER_BASES[0])
        check_base = model_center.missing_profile_files(CFG, "illustrious", wbgen.MODEL_FILES)
        loras = [x for x in self.all_lora_files if x.get("base") == "Illustrious/SDXL"]
        llm_ok = bool(self.model_var.get())
        rows = [
            ("LLM", f"{self.model_var.get() or '未选择'} · 连接状态见顶部", llm_ok),
            ("底模", "Illustrious/WAI 文件齐全" if not check_base else
             f"缺 {len(check_base)} 个文件", not check_base),
            ("LoRA", f"检测到 {len(loras)} 个 Illustrious LoRA；NSFW 效果需实测" if loras
             else "没有检测到 Illustrious LoRA；NSFW 可能只能底模直出", bool(loras)),
        ]
        for name, text, ok in rows:
            row = tk.Frame(card, bg=COLORS["panel"])
            row.pack(fill="x", padx=14, pady=8)
            tk.Label(row, text=("✓" if ok else "⚠"), width=2, bg=COLORS["panel"],
                     fg=COLORS["green"] if ok else COLORS["red"],
                     font=("Microsoft YaHei UI", 12, "bold")).pack(side="left")
            tk.Label(row, text=name, width=7, anchor="w", bg=COLORS["panel"],
                     fg=COLORS["text"], font=("Microsoft YaHei UI", 9, "bold")).pack(side="left")
            tk.Label(row, text=text, anchor="w", bg=COLORS["panel"],
                     fg=COLORS["muted"], font=FONT_SMALL).pack(side="left", fill="x", expand=True)
        tk.Label(card, text="模型中心下载前会显示大小并二次确认；不会静默下载。\n"
                            "MOSS/Krea2/Qwen/Anima 属于可选底模，不是最小包必需。",
                 bg=COLORS["panel"], fg=COLORS["muted"], justify="left",
                 font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=14, pady=(4, 10))
        pack_status = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["muted"],
                               font=FONT_SMALL, anchor="w")
        pack_status.pack(fill="x", padx=20)
        pack_bar = ttk.Progressbar(top, orient="horizontal", mode="determinate", maximum=100)
        pack_bar.pack(fill="x", padx=20, pady=(3, 6))
        pack_bar.pack_forget()
        btns = tk.Frame(top, bg=COLORS["bg"])
        btns.pack(fill="x", padx=20, pady=(0, 12))
        fill_btn = None

        def do_fill():
            if fill_btn is None or str(fill_btn.cget("state")) == "disabled":
                return
            fill_btn.configure(state="disabled", text="搜索中…")
            pack_status.configure(text="正在 Civitai 搜索 WAI-illustrious…")
            q = queue.Queue()

            def search():
                try:
                    rows = model_center.search_civitai(
                        "WAI-illustrious-SDXL", kind="checkpoint", base="Illustrious",
                        api_key=str(CFG.get("civitai_api_key", "") or ""), limit=5)
                    q.put(("search", rows))
                except Exception as e:
                    q.put(("error", str(e)))

            threading.Thread(target=search, daemon=True).start()

            def poll():
                try:
                    kind, payload = q.get_nowait()
                except queue.Empty:
                    top.after(200, poll)
                    return
                if kind == "search":
                    rows = payload or []
                    if not rows:
                        pack_status.configure(text="没有搜到推荐底模；请打开模型中心手动选择。")
                        fill_btn.configure(state="normal", text="一键补齐")
                        return
                    rec = next((x for x in rows if "wai" in x.get("name", "").lower()), rows[0])
                    size_gb = rec.get("size_kb", 0) / 1024 / 1024
                    if not messagebox.askyesno(
                            APP_NAME,
                            f"找到推荐底模：\n{rec.get('name', '')}\n"
                            f"版本：{rec.get('version_name', '')}\n"
                            f"大小约 {size_gb:.1f} GB\n\n"
                            "确认下载并设为 Illustrious 底模？\n"
                            "请确认模型许可和磁盘空间。", parent=top):
                        pack_status.configure(text="已取消下载。")
                        fill_btn.configure(state="normal", text="一键补齐")
                        return
                    pack_status.configure(text="开始下载…")
                    pack_bar.pack(fill="x", padx=20, pady=(3, 6))
                    pack_bar.configure(maximum=max(1, int(rec.get("size_kb", 0) * 1024)),
                                       value=0)
                    fill_btn.configure(text="下载中…")

                    def progress(done, total):
                        q.put(("progress", done, total))

                    def download():
                        try:
                            path = model_center.download_model(rec, CFG, progress=progress)
                            q.put(("downloaded", str(path), rec))
                        except Exception as e:
                            q.put(("download_error", str(e)))

                    threading.Thread(target=download, daemon=True).start()
                    top.after(200, poll)
                    return
                if kind == "progress":
                    _, done, total = payload
                    pack_bar.configure(maximum=max(1, total), value=done)
                    if total:
                        pack_status.configure(
                            text=f"下载中 {done / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB")
                    top.after(200, poll)
                    return
                if kind == "downloaded":
                    path, rec = payload[1], payload[2]
                    try:
                        wbgen.MODEL_FILES.setdefault("illustrious", {})["ckpt_name"] = Path(path).name
                        CFG.set("model_files", wbgen.MODEL_FILES)
                        CFG.save()
                    except Exception:
                        pass
                    pack_status.configure(text=f"已下载并设为 Illustrious 底模：{Path(path).name}",
                                          fg=COLORS["green"])
                    fill_btn.configure(state="normal", text="已补齐")
                    self._refresh_beginner_missing()
                    messagebox.showinfo(APP_NAME, f"推荐底模已下载：\n{path}", parent=top)
                    return
                if kind == "error":
                    pack_status.configure(text=f"搜索失败：{payload}", fg=COLORS["red"])
                    fill_btn.configure(state="normal", text="一键补齐")
                    return
                pack_status.configure(text=f"下载失败：{payload}", fg=COLORS["red"])
                fill_btn.configure(state="normal", text="一键补齐")

            poll()

        if check_base:
            fill_btn = tk.Button(btns, text="一键补齐", command=do_fill,
                                 bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                                 padx=12, pady=5, cursor="hand2")
            fill_btn.pack(side="left")
            pack_status.configure(text="推荐底模未齐全；可一键补齐，或手动打开模型中心。")
        else:
            pack_status.configure(text="推荐底模已齐全。", fg=COLORS["green"])
        tk.Button(btns, text="打开模型中心",
                  command=lambda: (top.destroy(),
                                   self.open_model_center("WAI-illustrious", "底模")),
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=12, pady=5, cursor="hand2").pack(side="left", padx=(6, 0))
        tk.Button(btns, text="关闭", command=top.destroy, bg=COLORS["panel"],
                  fg=COLORS["muted"], relief="flat", bd=0, padx=10, pady=5,
                  cursor="hand2").pack(side="right")

    def _update_dsh_prompt_text(self, error="", remote="", requirements=None):
        llm_state = ""
        comfy_state = ""
        for attr, target in (("beginner_llm_status", "llm"), ("beginner_comfy_status", "comfy")):
            widget = getattr(self, attr, None)
            if widget is not None:
                try:
                    if target == "llm":
                        llm_state = widget.cget("text")
                    else:
                        comfy_state = widget.cget("text")
                except Exception:
                    pass
        req = ""
        if isinstance(requirements, dict) and requirements:
            req = "\n".join(f"- {k}: {v}" for k, v in requirements.items())
        else:
            req = "更新清单未提供显式环境要求。"
        return f"""你是 DSH，请诊断并修复“本地出图工作台”（Prompt Workbench）的更新/环境适配问题。

程序版本：{APP_VERSION}
程序目录：{APP_DIR}
配置目录：{CFG.path}
数据目录：{DATA_DIR}
目标版本：{remote or '未知'}
更新错误：{error or '无具体错误；用户报告环境不适配'}
操作系统：{platform.platform()}
Python：{sys.version.split()[0]}
ComfyUI 地址：{CFG.get('comfy_url')}
LLM 地址：{CFG.get('llm_base_url')}
LoRA 根目录：{'; '.join(str(x) for x in CFG.paths('lora_roots')) or '未配置'}
底模目录：{CFG.get('checkpoint_dir') or '未配置'}
工作流目录：{CFG.get('comfy_workflows_dir') or '未配置'}
当前状态：LLM={llm_state or '未知'}；ComfyUI={comfy_state or '未知'}

目标版本环境要求：
{req}

请按下面顺序处理：
1. 先备份 config.json、settings.json、history.json，不删除用户模型、LoRA、历史图片或已保存版本。
2. 检查更新包是否完整、程序目录是否可写、路径是否有中文/空格权限问题；核对 SHA256。
3. 检查 Python、ComfyUI、Ollama、CUDA/驱动、端口和模型路径是否与目标版本匹配。
4. 不要自动升级 Python、CUDA、ComfyUI 或 Ollama；先说明风险和兼容性，得到我确认后再动。
5. 如果是便携版替换问题，保留 AppData 配置，只替换程序目录；如果是源码版，先确认依赖和启动脚本。
6. 修复后重新运行“检查更新”，再做一次 832×1216 最小出图测试。
7. 报告根因、实际改动、测试图片路径、耗时和仍存在的限制。
8. 不要输出或提交 API Key、token 或用户隐私数据。
"""

    def _show_update_dsh_prompt(self, error="", remote="", requirements=None):
        text = self._update_dsh_prompt_text(error, remote, requirements)
        top = tk.Toplevel(self.root)
        top.title("更新修复 · DSH 提示词")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 860, 660)
        top.transient(self.root)
        tk.Label(top, text="更新修复 · DSH 提示词", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(top, text="复制给 DSH，让它先诊断再修；不包含 API Key。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=18)
        box = ScrolledText(top, wrap="word", bg=COLORS["panel"], fg=COLORS["text"],
                           relief="flat", bd=0, font=("Consolas", 9), padx=12, pady=10)
        box.pack(fill="both", expand=True, padx=18, pady=(8, 6))
        box.insert("1.0", text)
        box.configure(state="disabled")

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
            messagebox.showinfo(APP_NAME, "DSH 更新修复提示词已复制。", parent=top)

        def save():
            path = DATA_DIR / "dsh-update-prompt.md"
            path.write_text(text, encoding="utf-8")
            messagebox.showinfo(APP_NAME, f"已保存：\n{path}", parent=top)

        bar = tk.Frame(top, bg=COLORS["bg"])
        bar.pack(fill="x", padx=18, pady=(0, 12))
        tk.Button(bar, text="复制", command=copy, bg=COLORS["accent"], fg="#fff",
                  relief="flat", bd=0, padx=14, pady=5, cursor="hand2").pack(side="left")
        tk.Button(bar, text="保存", command=save, bg=COLORS["card2"], fg=COLORS["text"],
                  relief="flat", bd=0, padx=10, pady=5, cursor="hand2").pack(side="left", padx=(6, 0))
        tk.Button(bar, text="关闭", command=top.destroy, bg=COLORS["panel"],
                  fg=COLORS["muted"], relief="flat", bd=0, padx=10, pady=5,
                  cursor="hand2").pack(side="right")

    def check_updates(self):
        if getattr(self, "_update_checking", False):
            return
        self._update_checking = True
        manifest = str(CFG.get("update_manifest_url") or DEFAULT_UPDATE_MANIFEST).strip()
        self.status_var.set("正在检查更新…")
        update_q = queue.Queue()
        started = time.time()

        def version_key(value):
            m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(value or ""))
            return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)

        def worker():
            try:
                req = urllib.request.Request(manifest, headers={"User-Agent": f"PromptWorkbench/{APP_VERSION}"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    data = json.loads(r.read().decode("utf-8"))
                remote = str(data.get("version") or "").strip()
                url = str(data.get("url") or "").strip()
                notes = str(data.get("notes") or "").strip()
                requirements = data.get("requires") or {}
                if not remote or not url.startswith(("http://", "https://")):
                    raise ValueError("更新清单缺少 version 或 url")
                update_q.put(("ok", remote, url, notes, requirements))
            except Exception as e:
                update_q.put(("err", str(e)))

        def poll():
            try:
                item = update_q.get_nowait()
            except queue.Empty:
                if time.time() - started > 20:
                    failed_update("检查更新超时")
                else:
                    self.root.after(100, poll)
                return
            if item[0] == "ok":
                done_update(item[1], item[2], item[3], item[4])
            else:
                failed_update(item[1])

        def done_update(remote, url, notes, requirements):
            self._update_checking = False
            self.status_var.set(f"当前版本 v{APP_VERSION}")
            req_text = ""
            if isinstance(requirements, dict) and requirements:
                req_text = "\n\n环境要求：\n" + "\n".join(
                    f"- {k}: {v}" for k, v in requirements.items())
            if version_key(remote) > version_key(APP_VERSION):
                extra = f"\n\n更新说明：\n{notes[:800]}" if notes else ""
                if messagebox.askyesno(APP_NAME,
                                       f"发现新版本 v{remote}\n当前 v{APP_VERSION}{extra}{req_text}\n\n"
                                       "打开 GitHub Release 下载新版便携包？\n"
                                       "设置和历史保存在 AppData，不会丢。",
                                       parent=self.root):
                    webbrowser.open(url)
            else:
                messagebox.showinfo(APP_NAME, f"已是最新版本 v{APP_VERSION}。",
                                    parent=self.root)

        def failed_update(err):
            self._update_checking = False
            self.status_var.set(f"更新检查失败 · 当前 v{APP_VERSION}")
            APP_LOG.warning("检查更新失败: %s", err)
            if messagebox.askyesno(APP_NAME,
                                   "更新检查失败。\n\n请确认网络可访问 GitHub，"
                                   "或稍后再试。\n\n"
                                   "是否生成一份 DSH 环境修复提示词？\n"
                                   "（会带上版本、错误和本机环境，不含 API Key）\n\n"
                                   + err[:300],
                                   parent=self.root):
                self._show_update_dsh_prompt(error=err)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, poll)

    def open_settings_dialog(self, first_run=False):
        if getattr(self, "settings_dialog", None) is not None:
            try:
                self.settings_dialog.lift()
                return
            except Exception:
                self.settings_dialog = None
        top = tk.Toplevel(self.root)
        self.settings_dialog = top
        top.title("首次环境设置" if first_run else "环境设置")
        top.configure(bg=COLORS["bg"])
        center_dialog_over(self.root, top, 780, 700)
        top.transient(self.root)
        top.resizable(False, False)
        try:
            top.iconbitmap(str(APP_ICON))
        except Exception:
            pass

        tk.Label(top, text="首次环境设置" if first_run else "环境设置",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Microsoft YaHei UI", 15, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        tk.Label(top, text="配置只保存在用户目录，不写入程序目录；保存后请重启工作台。",
                 bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=20, pady=(0, 10))
        data_lbl = tk.Label(top, text=f"配置目录：{CFG.path}", bg=COLORS["bg"],
                            fg=COLORS["muted"], font=("Microsoft YaHei UI", 9), anchor="w")
        data_lbl.pack(fill="x", padx=20, pady=(0, 8))

        form_holder = tk.Frame(top, bg=COLORS["panel"])
        form_holder.pack(fill="both", expand=True, padx=20)
        form_canvas = tk.Canvas(form_holder, bg=COLORS["panel"], highlightthickness=0)
        form_scroll = ttk.Scrollbar(form_holder, orient="vertical", command=form_canvas.yview)
        form_canvas.configure(yscrollcommand=form_scroll.set)
        form_scroll.pack(side="right", fill="y")
        form_canvas.pack(side="left", fill="both", expand=True)
        form = tk.Frame(form_canvas, bg=COLORS["panel"], highlightbackground=COLORS["line"],
                        highlightthickness=1)
        form_window = form_canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.bind("<Configure>", lambda e: form_canvas.itemconfigure(form_window, width=e.width))
        vars_ = {}

        def row(key, label, browse=None, width=44, secret=False):
            r = tk.Frame(form, bg=COLORS["panel"])
            r.pack(fill="x", padx=12, pady=4)
            tk.Label(r, text=label, width=13, anchor="w", bg=COLORS["panel"],
                     fg=COLORS["muted"], font=("Microsoft YaHei UI", 9)).pack(side="left")
            var = tk.StringVar(value=str(CFG.get(key, "") or ""))
            vars_[key] = var
            ent = tk.Entry(r, textvariable=var, width=width, bg=COLORS["input"], fg=COLORS["text"],
                           insertbackground=COLORS["text"], relief="flat", bd=0,
                           highlightbackground=COLORS["line"], highlightthickness=1,
                           font=("Microsoft YaHei UI", 9),
                           show="•" if secret else "")
            ent.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 5))
            if secret:
                def toggle_secret(e=ent):
                    e.configure(show="" if e.cget("show") else "•")
                tk.Button(r, text="显示/隐藏", command=toggle_secret,
                          bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                          padx=6, pady=3, cursor="hand2").pack(side="left")
            if browse:
                tk.Button(r, text="浏览…", command=lambda v=var, k=browse: self._browse_setting(v, k),
                          bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                          padx=8, pady=3, cursor="hand2").pack(side="left")

        row("llm_type", "LLM 类型", width=44)
        row("llm_base_url", "LLM 地址")
        row("llm_api_key", "API Key", secret=True)
        row("llm_model", "默认模型 ID")
        row("comfy_url", "ComfyUI 地址")
        row("lora_roots", "LoRA 根目录（; 分隔）", "dir")
        row("checkpoint_dir", "底模下载目录", "dir")
        row("civitai_api_key", "Civitai API Key", secret=True)
        row("update_manifest_url", "更新清单地址")
        row("output_dir", "输出目录", "dir")
        row("skills_dir", "提示词 skills 目录", "dir")
        row("prompt_library_dir", "提示词库目录", "dir")
        row("comfy_start_script", "ComfyUI 启动脚本", "file")
        row("comfy_close_script", "ComfyUI 关闭脚本", "file")
        row("comfy_workflows_dir", "工作流目录", "dir")
        row("tool80_path", "8.0 精修 HTML（可选）", "file")

        status = tk.Label(top, text="", bg=COLORS["bg"], fg=COLORS["muted"],
                          font=FONT_SMALL, anchor="w")
        status.pack(fill="x", padx=20, pady=(8, 4))

        buttons = tk.Frame(top, bg=COLORS["bg"])
        buttons.pack(fill="x", padx=20, pady=(0, 12))

        def test_connections():
            import urllib.request
            msgs = []
            llm_type = vars_["llm_type"].get().strip().lower()
            llm_base = vars_["llm_base_url"].get().rstrip("/")
            llm_path = "/api/tags" if llm_type == "ollama" else (
                "/models" if llm_base.endswith("/v1") else "/v1/models")
            headers = {}
            key = vars_["llm_api_key"].get().strip()
            if key:
                headers["Authorization"] = "Bearer " + key
            try:
                req = urllib.request.Request(llm_base + llm_path, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=4) as r:
                    msgs.append(f"LLM: {'OK' if r.status < 500 else 'HTTP '+str(r.status)}")
            except Exception as e:
                msgs.append(f"LLM: 失败 {str(e)[:50]}")
            comfy = vars_["comfy_url"].get().rstrip("/")
            try:
                with urllib.request.urlopen(comfy + "/system_stats", timeout=4) as r:
                    msgs.append(f"ComfyUI: {'OK' if r.status < 500 else 'HTTP '+str(r.status)}")
            except Exception as e:
                msgs.append(f"ComfyUI: 失败 {str(e)[:50]}")
            status.configure(text="  |  ".join(msgs))

        def save_settings():
            for key, var in vars_.items():
                value = var.get().strip()
                if key == "lora_roots":
                    CFG.set(key, [x.strip() for x in value.split(";") if x.strip()])
                else:
                    CFG.set(key, value)
            try:
                Path(CFG.get("output_dir")).mkdir(parents=True, exist_ok=True)
                Path(CFG.get("prompt_library_dir")).mkdir(parents=True, exist_ok=True)
                CFG.save()
            except Exception as e:
                messagebox.showerror(APP_NAME, f"保存配置失败：{e}", parent=top)
                return
            status.configure(text="已保存，请重启工作台使路径生效。", fg=COLORS["green"])
            messagebox.showinfo(APP_NAME, "环境设置已保存。\n请关闭并重新启动工作台。", parent=top)
            self.settings_dialog = None
            top.destroy()

        def generate_dsh_prompt():
            tmp = appconfig.Config(data_dir=CFG.data_dir)
            for key, var in vars_.items():
                value = var.get().strip()
                if key == "lora_roots":
                    tmp.set(key, [x.strip() for x in value.split(";") if x.strip()])
                else:
                    tmp.set(key, value)
            issues = []
            for root in tmp.paths("lora_roots"):
                if not root.exists():
                    issues.append(f"LoRA 根目录不存在：{root}")
            for key, label in (
                    ("checkpoint_dir", "底模目录"),
                    ("skills_dir", "skills 目录"),
                    ("prompt_library_dir", "提示词库目录"),
                    ("output_dir", "输出目录"),
                    ("comfy_workflows_dir", "工作流目录")):
                value = str(tmp.get(key, "") or "").strip()
                if value and not Path(value).expanduser().exists():
                    issues.append(f"{label}不存在：{value}")
            for key, label in (
                    ("comfy_start_script", "ComfyUI 启动脚本"),
                    ("comfy_close_script", "ComfyUI 关闭脚本"),
                    ("tool80_path", "8.0 HTML")):
                value = str(tmp.get(key, "") or "").strip()
                if value and not Path(value).expanduser().exists():
                    issues.append(f"{label}不存在：{value}")
            for profile in ("illustrious", "moss", "krea2", "qwen", "anima"):
                for miss in model_center.missing_profile_files(tmp, profile, wbgen.MODEL_FILES):
                    issues.append(
                        f"{profile} 缺少 {miss['role']} 文件（{miss['filename']}）")
            if not issues:
                issues.append("暂未发现路径/模型文件缺失；仍需检查 LLM 和 ComfyUI 服务连接。")
            lines = [
                "你是 DSH，请修复“提示词工作台”发布版环境。",
                "",
                f"程序目录：{APP_DIR}",
                f"配置目录：{tmp.path}",
                "不要修改归档版 D:\\prompt-workbench；不要覆盖已有历史记录。",
                "",
                "当前配置：",
                f"- LLM 类型：{tmp.get('llm_type')}",
                f"- LLM 地址：{tmp.get('llm_base_url')}",
                f"- 默认模型：{tmp.get('llm_model')}",
                f"- ComfyUI：{tmp.get('comfy_url')}",
                f"- LoRA 根目录：{'; '.join(str(x) for x in tmp.paths('lora_roots')) or '未配置'}",
                f"- 底模目录：{tmp.get('checkpoint_dir') or '未配置'}",
                f"- 工作流目录：{tmp.get('comfy_workflows_dir') or '未配置'}",
                f"- 输出目录：{tmp.get('output_dir') or '未配置'}",
                f"- skills：{tmp.get('skills_dir') or '未配置'}",
                f"- 提示词库：{tmp.get('prompt_library_dir') or '未配置'}",
                f"- API Key：{'已配置（不输出）' if tmp.get('llm_api_key') else '未配置'}",
                f"- Civitai API Key：{'已配置（不输出）' if tmp.get('civitai_api_key') else '未配置'}",
                "",
                "检测到的问题：",
            ]
            lines += [f"- {x}" for x in issues]
            lines += [
                "",
                "请按以下顺序处理：",
                "1. 先检查 Ollama/LLM 和 ComfyUI 端口是否可连接，不要猜。",
                "2. 只修复上面列出的缺失项；能复用现有模型就复用，不重复下载。",
                "3. 任何超过 1GB 的下载，先向我报告文件、大小、磁盘空间和直连/代理通道。",
                "4. 优先直连 Civitai/Hugging Face CDN；失败时可测试 Ikuuu 或同类网络工具。",
                "5. 下载后校验 SHA256（有哈希时），更新 config.json 的对应路径。",
                "6. 不要输出或提交 API Key。",
                "7. 修复后运行 tools/selfcheck.py，并启动发布版确认简洁模式能看到底模。",
                "8. 用 SFW/NSFW 各一张 832×1216 做最小测试，报告真实加载的模型文件和失败原因。",
                "9. 不要停掉正在服务用户的聊天后端。",
                "10. 完成后只汇报：改了哪些字段、哪些文件存在、哪些仍然缺失、下一步需要我提供什么。",
            ]
            text = "\n".join(lines)
            prompt_top = tk.Toplevel(top)
            prompt_top.title("DSH 环境配置提示词")
            prompt_top.configure(bg=COLORS["bg"])
            center_dialog_over(top, prompt_top, 820, 620)
            prompt_top.transient(top)
            tk.Label(prompt_top, text="DSH 环境配置提示词", bg=COLORS["bg"], fg=COLORS["text"],
                     font=("Microsoft YaHei UI", 14, "bold")).pack(anchor="w", padx=18, pady=(14, 2))
            tk.Label(prompt_top, text="可复制给 DSH；包含当前配置和缺失项，不包含 API Key。",
                     bg=COLORS["bg"], fg=COLORS["muted"], font=FONT_SMALL).pack(anchor="w", padx=18)
            box = ScrolledText(prompt_top, wrap="word", bg=COLORS["panel"], fg=COLORS["text"],
                               relief="flat", bd=0, font=("Consolas", 9), padx=12, pady=10)
            box.pack(fill="both", expand=True, padx=18, pady=(8, 6))
            box.insert("1.0", text)
            box.configure(state="disabled")

            def copy_prompt():
                prompt_top.clipboard_clear()
                prompt_top.clipboard_append(text)
                prompt_top.update_idletasks()
                messagebox.showinfo(APP_NAME, "DSH 提示词已复制。", parent=prompt_top)

            def save_prompt():
                path = DATA_DIR / "dsh-setup-prompt.md"
                path.write_text(text, encoding="utf-8")
                messagebox.showinfo(APP_NAME, f"已保存：\n{path}", parent=prompt_top)

            bar = tk.Frame(prompt_top, bg=COLORS["bg"])
            bar.pack(fill="x", padx=18, pady=(0, 12))
            tk.Button(bar, text="复制到剪贴板", command=copy_prompt,
                      bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                      padx=14, pady=5, cursor="hand2").pack(side="left")
            tk.Button(bar, text="保存为 md", command=save_prompt,
                      bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                      padx=12, pady=5, cursor="hand2").pack(side="left", padx=(6, 0))
            tk.Button(bar, text="关闭", command=prompt_top.destroy,
                      bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                      padx=10, pady=5, cursor="hand2").pack(side="right")

        tk.Button(buttons, text="检测连接", command=test_connections,
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=12, pady=6, cursor="hand2").pack(side="left")
        tk.Button(buttons, text="生成 DSH 提示词", command=generate_dsh_prompt,
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="更新修复提示词",
                  command=lambda: self._show_update_dsh_prompt(),
                  bg=COLORS["card2"], fg=COLORS["text"], relief="flat", bd=0,
                  padx=12, pady=6, cursor="hand2").pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="保存并关闭", command=save_settings,
                  bg=COLORS["accent"], fg="#fff", relief="flat", bd=0,
                  padx=16, pady=6, font=("Microsoft YaHei UI", 9, "bold"),
                  cursor="hand2").pack(side="right")
        tk.Button(buttons, text="取消", command=lambda: (setattr(self, "settings_dialog", None), top.destroy()),
                  bg=COLORS["panel"], fg=COLORS["muted"], relief="flat", bd=0,
                  padx=10, pady=6, cursor="hand2").pack(side="right", padx=(0, 6))
        if first_run:
            top.grab_set()
        top.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "settings_dialog", None), top.destroy()))

    def _browse_setting(self, var, kind):
        path = filedialog.askdirectory() if kind == "dir" else filedialog.askopenfilename(
            filetypes=[("HTML/脚本", "*.html *.ps1 *.bat *.cmd"), ("All files", "*.*")])
        if path:
            var.set(path)

    def open_library(self):
        try:
            os.startfile(str(PROMPT_LIBRARY))
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))

    def clear(self):
        self.brief_text.delete("1.0", "end")
        self.positive_text.delete("1.0", "end")
        self.negative_text.delete("1.0", "end")
        self.refine_history = []
        self._refresh_refine_log()
        self.refine_entry.delete(0, "end")
        self.status_var.set("已清空")

    def _unload_used_models(self):
        """关闭工作台时只卸载本次调用过的 Ollama 模型；云端不处理。"""
        for model in list(self.used_models):
            try:
                llm_client.unload(CFG, model)
            except Exception:
                pass
        self.used_models.clear()

    def on_close(self):
        self._save_settings()
        save_json(HISTORY_FILE, self.records)
        self._unload_used_models()
        self.root.destroy()


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    APP_LOG.info("启动工作台 config=%s", CFG.path)
    app = PromptWorkbench(root)
    if "--smoke" in sys.argv:
        root.after(1200, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
