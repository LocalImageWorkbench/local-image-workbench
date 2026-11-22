import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import workflow_import as wi


def _api_with_loras(names):
    api = {"1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "base.safetensors"}}}
    prev = ["1", 0]
    for i, name in enumerate(names, 2):
        nid = str(i)
        api[nid] = {"class_type": "LoraLoaderModelOnly", "inputs": {
            "model": prev, "lora_name": name + ".safetensors", "strength_model": 0.8}}
        prev = [nid, 0]
    api["99"] = {"class_type": "KSampler", "inputs": {
        "model": prev, "positive": ["1", 0], "negative": ["1", 0],
        "latent_image": ["1", 0], "seed": 1, "steps": 20, "cfg": 6,
        "sampler_name": "euler", "scheduler": "normal", "denoise": 1}}
    return api


class ReleaseTests(unittest.TestCase):
    def test_interchangeable_groups_are_bypassed(self):
        api = _api_with_loras([
            "Pussy_Peach_Rear_v2_XL",
            "Pussy_Spreading_v5i_XL",
            "Sextoy_Dildo_Pussy_v2i_XL",
            "Clothing_PearlBeads_v3_XL",
        ])
        plan, summary = wi.plan_loras(api, "1girl, pussy, spreading, portrait", "bad anatomy")
        enabled = [x for x in plan if x["enabled"]]
        self.assertLessEqual(summary["enabled"], 3)
        self.assertTrue(all(
            x["group"] != "pussy_variant"
            or x["name"].endswith("Pussy_Spreading_v5i_XL.safetensors")
            for x in enabled
        ))

    def test_different_groups_can_stack(self):
        api = _api_with_loras([
            "cool style XL",
            "dynamic pose v2",
            "skin detail boost",
            "dildo toy pack",
            "pearl clothing",
        ])
        plan, summary = wi.plan_loras(
            api, "1girl, cool style, dynamic pose, detailed skin, toy, clothing portrait", "bad anatomy")
        enabled = [x for x in plan if x["enabled"]]
        self.assertGreater(summary["enabled"], 3)
        self.assertLessEqual(sum(x["strength"] for x in enabled), 2.4)

    def test_bypassed_model_chain_is_rewired(self):
        api = _api_with_loras([
            "Pussy_Peach_Rear_v2_XL",
            "Sextoy_Dildo_Pussy_v2i_XL",
            "cool style XL",
            "skin detail boost",
        ])
        plan, _ = wi.plan_loras(api, "1girl, spreading pussy, cool style, detailed skin", "")
        out = wi.apply_lora_plan(api, plan)
        self.assertIn(out["99"]["inputs"]["model"][0], out)
        self.assertTrue(all(
            n.get("class_type") != "LoraLoaderModelOnly"
            or n["inputs"]["lora_name"] not in (
                "Pussy_Peach_Rear_v2_XL.safetensors",
                "Sextoy_Dildo_Pussy_v2i_XL.safetensors",
            )
            for n in out.values()
        ))

    def test_config_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            c = config.Config(data_dir=tmp)
            c.set("output_dir", str(tmp / "out"))
            c.set("lora_roots", [str(tmp / "loras")])
            c.save()
            c2 = config.Config(data_dir=tmp)
            self.assertEqual(c2.get("output_dir"), str(tmp / "out"))
            self.assertEqual(c2.paths("lora_roots"), [tmp / "loras"])
            self.assertFalse(c2.is_new)


if __name__ == "__main__":
    unittest.main()
