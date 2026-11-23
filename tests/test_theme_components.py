# -*- coding: utf-8 -*-
import unittest

import theme_components as tc


class ThemeComponentTests(unittest.TestCase):
    def test_sfw_nsfw_separate(self):
        sfw = tc.pick(True, ["服装", "场景"])
        nsfw = tc.pick(False, ["服装", "场景"])
        self.assertIn(sfw["服装"], tc.COMPONENTS["SFW"]["服装"])
        self.assertIn(nsfw["服装"], tc.COMPONENTS["NSFW"]["服装"])
        self.assertNotEqual(tc.COMPONENTS["SFW"]["服装"], tc.COMPONENTS["NSFW"]["服装"])

    def test_selected_keys(self):
        out = tc.pick(True, ["服装", "场景", "光线"])
        self.assertEqual(set(out), {"服装", "场景", "光线"})

    def test_compose(self):
        text = tc.compose({"服装": "黑色长风衣", "场景": "雨夜街头", "光线": "侧逆光"})
        self.assertIn("服装：黑色长风衣", text)
        self.assertIn("场景：雨夜街头", text)

    def test_extended_components(self):
        out = tc.pick(True, ["道具", "天气", "季节", "配色", "构图"])
        self.assertEqual(set(out), {"道具", "天气", "季节", "配色", "构图"})
        self.assertIn("构图", tc.compose(out))


if __name__ == "__main__":
    unittest.main()
