# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from pathlib import Path

import random_library as rl


CATS = {"人物": ["成年女性，窗边，柔光", "成年男性，街角，侧逆光"],
        "场景": ["雪山湖泊，清晨薄雾", "雨夜街道，霓虹"]}
STYLES = {"人物": "电影感", "场景": "电影感"}
TEMPLATES = {
    "人物": {"style": "电影感", "format": "{subject}，{setting}，{light}",
             "parts": {"subject": ["成年女性"], "setting": ["窗边"], "light": ["柔光"]}},
}


class RandomLibraryTests(unittest.TestCase):
    def test_default_and_pick_curated(self):
        data = rl.default_library(CATS, STYLES, TEMPLATES)
        self.assertEqual(set(data["categories"]), {"人物", "场景"})
        for _ in range(10):
            got = rl.pick(data, "人物", "精选")
            self.assertEqual(got["mode"], "精选")
            self.assertIn(got["text"], CATS["人物"])
            self.assertEqual(got["style"], "电影感")

    def test_template_pick(self):
        data = rl.default_library(CATS, STYLES, TEMPLATES)
        got = rl.pick(data, "人物", "模板")
        self.assertEqual(got["mode"], "模板")
        self.assertIn("成年女性", got["text"])
        self.assertIn("窗边", got["text"])

    def test_mixed_and_fallback(self):
        data = rl.default_library(CATS, STYLES, TEMPLATES)
        got = rl.pick(data, "混合", "混合")
        self.assertIn(got["mode"], ("精选", "模板"))
        got = rl.pick(data, "场景", "模板")
        self.assertEqual(got["mode"], "精选")  # no template for scene

    def test_import_export_roundtrip(self):
        data = rl.default_library(CATS, STYLES, TEMPLATES)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "random-library.json"
            rl.save_user(p, data)
            loaded = rl.load_user(p)
            self.assertEqual(len(loaded["categories"]["人物"]["prompts"]), 2)
            self.assertIn("人物", loaded["templates"])

    def test_simple_list_schema(self):
        data = rl.normalize({"categories": {"人物": ["成年女性，窗边"]}})
        self.assertEqual(data["categories"]["人物"]["style"], "写实")
        self.assertEqual(len(data["categories"]["人物"]["prompts"]), 1)

    def test_invalid(self):
        with self.assertRaises(rl.LibraryError):
            rl.normalize({"categories": {}})
        with self.assertRaises(rl.LibraryError):
            rl.normalize({"categories": {"人物": []}})
        with self.assertRaises(rl.LibraryError):
            rl.normalize({"categories": {"人物": ["x"] * 6000}})


if __name__ == "__main__":
    unittest.main()
