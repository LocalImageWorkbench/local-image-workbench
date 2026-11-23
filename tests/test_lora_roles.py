# -*- coding: utf-8 -*-
import tempfile
import unittest
from pathlib import Path

import lora_roles as lr


def item(name, base="Illustrious/SDXL", trigger="", path=None):
    return {"name": name, "label": name, "path": path or name, "base": base, "trigger": trigger}


class LoraRoleTests(unittest.TestCase):
    def test_guess(self):
        self.assertEqual(lr.guess_role(item("xx_pose_v2")), "pose")
        self.assertEqual(lr.guess_role(item("watercolor_style")), "style")
        self.assertEqual(lr.guess_role(item("character_kafka")), "character")
        self.assertEqual(lr.guess_role(item("outfit_dress")), "other")

    def test_store_override(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "roles.json"
            s = lr.RoleStore(p)
            it = item("kafka")
            self.assertEqual(s.role_for(it), "character")
            s.set_role(it, "pose")
            s2 = lr.RoleStore(p)
            self.assertEqual(s2.role_for(it), "pose")

    def test_choose_same_base(self):
        with tempfile.TemporaryDirectory() as d:
            s = lr.RoleStore(Path(d) / "roles.json")
            items = [item("kafka"), item("pose_a"), item("style_a"),
                     item("other_char", base="MOSS"), item("pose_moss", base="MOSS")]
            for it in items:
                if "pose" in it["name"]:
                    s.set_role(it, "pose")
                elif "style" in it["name"]:
                    s.set_role(it, "style")
                elif "char" in it["name"]:
                    s.set_role(it, "character")
            # explicit character role for kafka
            s.set_role(items[0], "character")
            chosen = lr.choose_theme(items, s, base="Illustrious/SDXL")
            self.assertEqual(chosen["character"]["base"], "Illustrious/SDXL")
            self.assertEqual(chosen["pose"]["base"], "Illustrious/SDXL")
            self.assertEqual(chosen["style"]["base"], "Illustrious/SDXL")

    def test_no_character(self):
        with tempfile.TemporaryDirectory() as d:
            s = lr.RoleStore(Path(d) / "roles.json")
            self.assertIsNone(lr.choose_theme([item("style_a")], s, base="MOSS"))

    def test_character_outfits(self):
        with tempfile.TemporaryDirectory() as d:
            s = lr.RoleStore(Path(d) / "roles.json")
            it = item("kafka")
            s.set_role(it, "character")
            s.set_outfits(it, ["黑色长风衣", "白色礼服"])
            s2 = lr.RoleStore(Path(d) / "roles.json")
            self.assertEqual(s2.record_for(it)["outfits"], ["黑色长风衣", "白色礼服"])
            chosen = lr.choose_theme([it], s2)
            self.assertEqual(chosen["character"]["outfits"][0], "黑色长风衣")

    def test_rating_filter(self):
        with tempfile.TemporaryDirectory() as d:
            s = lr.RoleStore(Path(d) / "roles.json")
            a = item("kafka")
            b = item("moss_char", base="MOSS")
            s.set_role(a, "character")
            s.set_role(b, "character")
            s.set_rating(a, "sfw")
            s.set_rating(b, "nsfw")
            sfw = lr.choose_theme([a, b], s, sfw=True)
            nsfw = lr.choose_theme([a, b], s, sfw=False)
            self.assertEqual(sfw["character"]["path"], a["path"])
            self.assertEqual(nsfw["character"]["path"], b["path"])


if __name__ == "__main__":
    unittest.main()
