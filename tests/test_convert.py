"""Converter tests. Pure stdlib: python3 -m unittest discover -s tests

These check the generated text. Whether Godot accepts it is checked separately
by tests/godot_check.gd (see README, "Verify").
"""
import json
import os
import re
import tempfile
import unittest

from figma2godot.cli import build, load_design

HERE = os.path.dirname(__file__)
EXAMPLE = os.path.join(HERE, "..", "examples", "game-ui.design.json")


def read(path):
    with open(path) as f:
        return f.read()


class ConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.design = load_design(EXAMPLE)
        cls.written, cls.report = build(cls.design, cls.tmp.name)
        cls.fig = os.path.join(cls.tmp.name, "figma")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def scene(self, name):
        return read(os.path.join(self.fig, "scenes", name + ".tscn"))

    def test_one_scene_per_frame_and_one_theme_per_mode(self):
        for f in ("MainMenu", "Settings", "HUD"):
            self.assertTrue(os.path.exists(os.path.join(self.fig, "scenes", f + ".tscn")))
        for m in ("dark", "light"):
            self.assertTrue(os.path.exists(os.path.join(self.fig, "theme", "theme_%s.tres" % m)))

    def test_auto_layout_becomes_containers(self):
        s = self.scene("MainMenu")
        self.assertIn('type="VBoxContainer"', s)
        # primary + counter CENTER on the screen frame
        self.assertIn("alignment = 1", s)
        self.assertIn("size_flags_horizontal = 4", s)
        self.assertIn("theme_override_constants/separation = 18", s)

    def test_padding_becomes_margin_container(self):
        s = self.scene("Settings")
        self.assertIn('type="MarginContainer"', s)
        self.assertIn("margin_left = 24", s)

    def test_components_map_to_widgets(self):
        s = self.scene("Settings")
        for typ in ("CheckButton", "HSlider", "LineEdit", "OptionButton", "HSeparator", "Button"):
            self.assertIn('type="%s"' % typ, s)
        self.assertIn("button_pressed = true", s)
        self.assertIn('placeholder_text = "Player name"', s)
        self.assertIn("selected = 0", s)

    def test_fill_sizing(self):
        s = self.scene("Settings")
        # 'Apply' is FILL on the primary axis of an HBox -> expand+fill
        apply_block = s[s.index('[node name="Apply"'):]
        self.assertIn("size_flags_horizontal = 3", apply_block.split("[node")[1])

    def test_absolute_frames_use_offsets(self):
        s = self.scene("HUD")
        self.assertIn("offset_left = 1000", s)
        self.assertIn("horizontal_alignment = 2", s)  # right-aligned score
        self.assertIn("autowrap_mode = 3", s)

    def test_every_variation_used_is_defined_in_every_theme(self):
        used = set()
        for f in ("MainMenu", "Settings", "HUD"):
            used |= set(re.findall(r'theme_type_variation = &"([^"]+)"', self.scene(f)))
        self.assertTrue(used, "expected at least one type variation")
        for m in ("dark", "light"):
            theme = read(os.path.join(self.fig, "theme", "theme_%s.tres" % m))
            for v in used:
                self.assertIn('%s/base_type' % v, theme)

    def test_bound_variable_changes_between_modes(self):
        dark = read(os.path.join(self.fig, "theme", "theme_dark.tres"))
        light = read(os.path.join(self.fig, "theme", "theme_light.tres"))

        def bg(theme):
            sid = re.search(r'Panel_surface_color_bg/styles/panel = SubResource\("([^"]+)"\)', theme).group(1)
            block = theme[theme.index('id="%s"' % sid):]
            return re.search(r"bg_color = (Color\([^)]*\))", block).group(1)

        self.assertNotEqual(bg(dark), bg(light))

    def test_report_lists_unsupported_and_font(self):
        text = "\n".join(m for _, _, m in self.report.items)
        self.assertIn("ELLIPSE", text)
        self.assertIn("Recursive", text)

    def test_missing_tokens_fall_back_loudly(self):
        d = json.loads(json.dumps(self.design))
        d["collections"] = []
        with tempfile.TemporaryDirectory() as t:
            _, report = build(d, t)
        msgs = [m for lvl, _, m in report.items if lvl == "warn"]
        self.assertTrue(any("color/text" in m for m in msgs))

    def test_node_names_are_godot_safe(self):
        d = {"schema": "figma-to-godot/0.1", "file": "t", "frames": [{
            "type": "FRAME", "name": "Main/Menu: v1.0", "width": 100, "height": 100,
            "layout": {"mode": "VERTICAL"}, "children": [
                {"type": "TEXT", "name": "a.b", "text": {"characters": "x"}},
                {"type": "TEXT", "name": "a.b", "text": {"characters": "y"}}]}]}
        with tempfile.TemporaryDirectory() as t:
            build(d, t)
            s = read(os.path.join(t, "figma", "scenes", "Main_Menu_v1_0.tscn"))
        self.assertNotIn('name="Main/Menu', s)
        self.assertIn('name="a_b"', s)
        self.assertIn('name="a_b2"', s)  # duplicates are made unique

    def test_rejects_wrong_schema(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"schema": "nope"}, f)
        try:
            with self.assertRaises(SystemExit):
                load_design(f.name)
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
