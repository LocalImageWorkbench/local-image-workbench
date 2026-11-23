# -*- coding: utf-8 -*-
"""0.4 core primitives: task/service state, request object, error taxonomy."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional


class TaskStatus:
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    CANCELING = "canceling"
    DONE = "done"
    ERROR = "error"


@dataclass
class TaskSnapshot:
    status: str = TaskStatus.IDLE
    message: str = ""
    done: int = 0
    total: int = 0
    seed: Optional[int] = None
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    stop_after: bool = False
    cancel_requested: bool = False


class TaskController:
    """Single source of truth for generation state."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = TaskSnapshot()

    def begin(self, total: int = 1) -> None:
        with self._lock:
            self._state = TaskSnapshot(
                status=TaskStatus.RUNNING, total=max(1, int(total)),
                started_at=time.time(), message="准备出图",
            )

    def update(self, done: int, total: Optional[int] = None, seed=None,
               message: str = "") -> None:
        with self._lock:
            self._state.done = max(0, int(done))
            if total is not None:
                self._state.total = max(1, int(total))
            if seed not in (None, ""):
                try:
                    self._state.seed = int(seed)
                except (TypeError, ValueError):
                    pass
            if message:
                self._state.message = message

    def finish(self) -> None:
        with self._lock:
            self._state.status = TaskStatus.DONE
            self._state.finished_at = time.time()
            self._state.message = "完成"

    def fail(self, error: str) -> None:
        with self._lock:
            self._state.status = TaskStatus.ERROR
            self._state.error = str(error)
            self._state.finished_at = time.time()
            self._state.message = "失败"

    def cancel(self) -> None:
        with self._lock:
            self._state.cancel_requested = True
            if self._state.status in (TaskStatus.QUEUED, TaskStatus.RUNNING):
                self._state.status = TaskStatus.CANCELING

    def request_stop_after(self) -> None:
        with self._lock:
            self._state.stop_after = True

    def can_start(self) -> bool:
        with self._lock:
            return self._state.status in (TaskStatus.IDLE, TaskStatus.DONE, TaskStatus.ERROR)

    def snapshot(self) -> TaskSnapshot:
        with self._lock:
            return TaskSnapshot(**asdict(self._state))


class ServiceStatus:
    UNKNOWN = "unknown"
    STOPPED = "stopped"
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceInfo:
    name: str
    status: str = ServiceStatus.UNKNOWN
    detail: str = ""
    updated_at: float = 0.0


class ServiceRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._services: Dict[str, ServiceInfo] = {}

    def set(self, name: str, status: str, detail: str = "") -> None:
        with self._lock:
            self._services[name] = ServiceInfo(name, status, detail, time.time())

    def get(self, name: str) -> ServiceInfo:
        with self._lock:
            return self._services.get(name, ServiceInfo(name))

    def snapshot(self) -> Dict[str, ServiceInfo]:
        with self._lock:
            return dict(self._services)


@dataclass
class GenerationRequest:
    workflow_key: str = ""
    workflow_label: str = ""
    positive: str = ""
    negative: str = ""
    loras: list = field(default_factory=list)
    count: int = 1
    width: Optional[int] = None
    height: Optional[int] = None
    seed: int = 0
    steps: Optional[int] = None
    cfg: Optional[float] = None
    sampler: str = ""
    scheduler: str = ""
    out_dir: str = ""
    close_after: bool = True

    def params(self) -> dict:
        out = {"seed": max(0, int(self.seed or 0))}
        for key in ("steps", "cfg", "width", "height", "sampler", "scheduler"):
            value = getattr(self, key)
            if value not in (None, ""):
                out[key] = value
        return out


@dataclass
class ErrorInfo:
    code: str
    title: str
    hint: str
    actions: list = field(default_factory=list)


_ERROR_RULES = (
    ("cancel", ("cancel", "取消", "中断"), "已取消", "生成被用户取消。", ["重试"]),
    ("comfy_down", ("10061", "connection refused", "积极拒绝", "18188"), "ComfyUI 未连接",
     "ComfyUI 没有启动，或端口不对。", ["启动 ComfyUI", "打开设置", "重试"]),
    ("timeout", ("timeout", "超时", "timed out"), "请求超时", "服务响应太慢，检查模型加载或端口。",
     ["打开日志", "重试"]),
    ("model_missing", ("no such file", "缺", "not found", "找不到"), "文件缺失",
     "底模、VAE、文本编码器或 LoRA 文件不完整。", ["检查模型", "复制 DSH 提示词"]),
    ("node_missing", ("node", "节点", "class_type"), "节点缺失",
     "工作流引用了未安装的自定义节点。", ["校验工作流", "复制 DSH 提示词"]),
    ("vram", ("out of memory", "显存", "oom"), "显存不足",
     "降低分辨率、减少张数或关闭其他占显存的程序。", ["降低分辨率", "重试"]),
)


def classify_error(message: str) -> ErrorInfo:
    text = str(message or "").lower()
    for code, needles, title, hint, actions in _ERROR_RULES:
        if any(n.lower() in text for n in needles):
            return ErrorInfo(code, title, hint, list(actions))
    return ErrorInfo("unknown", "出图失败", "查看原始错误和日志后再试。",
                     ["复制 DSH 提示词", "打开日志", "重试"])


def atomic_write_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


class JsonlDiagnostics:
    """Append-only JSONL diagnostics; never contains API keys unless caller adds them."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()

    def write(self, event: str, **fields) -> None:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event}
        rec.update(fields)
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
