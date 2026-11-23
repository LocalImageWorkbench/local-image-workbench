# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from pathlib import Path

import core_state as core


class CoreStateTests(unittest.TestCase):
    def test_task_lifecycle(self):
        t = core.TaskController()
        self.assertTrue(t.can_start())
        t.begin(4)
        t.update(2, 4, seed=123, message="第二张")
        snap = t.snapshot()
        self.assertEqual(snap.status, core.TaskStatus.RUNNING)
        self.assertEqual(snap.done, 2)
        self.assertEqual(snap.seed, 123)
        t.finish()
        self.assertEqual(t.snapshot().status, core.TaskStatus.DONE)
        self.assertTrue(t.can_start())

    def test_task_cancel_and_stop_after(self):
        t = core.TaskController()
        t.begin(2)
        t.request_stop_after()
        t.cancel()
        snap = t.snapshot()
        self.assertTrue(snap.stop_after)
        self.assertTrue(snap.cancel_requested)
        self.assertEqual(snap.status, core.TaskStatus.CANCELING)
        self.assertFalse(t.can_start())

    def test_services(self):
        s = core.ServiceRegistry()
        s.set("comfyui", core.ServiceStatus.READY, "18188")
        s.set("llm", core.ServiceStatus.STOPPED)
        self.assertEqual(s.get("comfyui").status, core.ServiceStatus.READY)
        self.assertEqual(s.get("llm").status, core.ServiceStatus.STOPPED)
        self.assertEqual(s.get("missing").name, "missing")

    def test_generation_request(self):
        r = core.GenerationRequest(seed=42, steps=20, cfg=6.0, sampler="euler")
        p = r.params()
        self.assertEqual(p["seed"], 42)
        self.assertEqual(p["steps"], 20)
        self.assertEqual(p["sampler"], "euler")
        self.assertNotIn("width", p)

    def test_error_classification(self):
        self.assertEqual(core.classify_error("WinError 10061 积极拒绝").code, "comfy_down")
        self.assertEqual(core.classify_error("CUDA out of memory").code, "vram")
        self.assertEqual(core.classify_error("timed out").code, "timeout")
        self.assertEqual(core.classify_error("weird").code, "unknown")

    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "state.json"
            core.atomic_write_json(p, {"a": 1, "中文": "值"})
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["中文"], "值")
            self.assertFalse(p.with_name(p.name + ".tmp").exists())

    def test_jsonl_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "diag.jsonl"
            log = core.JsonlDiagnostics(p)
            log.write("gen_start", seed=1, workflow="illustrious")
            log.write("gen_done", seed=1, elapsed=2.5)
            lines = p.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["event"], "gen_start")


if __name__ == "__main__":
    unittest.main()
