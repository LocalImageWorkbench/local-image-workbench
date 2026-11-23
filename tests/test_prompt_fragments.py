# -*- coding: utf-8 -*-
import unittest

import prompt_fragments as pf


class PromptFragmentTests(unittest.TestCase):
    def test_split(self):
        self.assertEqual(pf.split_fragments("雪山，清晨，薄雾, 远山\n湖面"),
                         ["雪山", "清晨", "薄雾", "远山", "湖面"])
        self.assertEqual(pf.split_fragments("，，\n"), [])

    def test_join(self):
        self.assertEqual(pf.join_fragments(["雪山", "清晨", ""]), "雪山，清晨")

    def test_edit(self):
        items = ["雪山", "清晨", "薄雾"]
        self.assertEqual(pf.replace_fragment(items, 1, "黄昏"), ["雪山", "黄昏", "薄雾"])
        self.assertEqual(pf.delete_fragment(items, 0), ["清晨", "薄雾"])
        self.assertEqual(pf.add_fragment(items, "湖面"), ["雪山", "清晨", "薄雾", "湖面"])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            pf.replace_fragment(["a"], 0, "a，b")
        with self.assertRaises(IndexError):
            pf.delete_fragment([], 0)


if __name__ == "__main__":
    unittest.main()
