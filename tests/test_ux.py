"""Game UX tests: tags, focus graph, lint, and what the build hands to a coding agent.

Pure stdlib: python3 -m unittest discover -s tests
Whether Godot agrees is checked by tests/godot_ux_check.gd (see README, "Verify").
"""
import copy
import csv
import json
import os
import re
import tempfile
import unittest

from figma2godot import ux
from figma2godot.cli import build, lint_design, load_design, snake_file, main

HERE = os.path.dirname(__file__)
EXAMPLE = os.path.join(HERE, "..", "examples", "game-ui.design.json")

THEME = [{"name": "Theme", "modes": ["Dark", "Light"], "variables": [
    {"name": "color/bg", "type": "COLOR", "values": {"Dark": "#16161D", "Light": "#F4F1EA"}},
    {"name": "color/text", "type": "COLOR", "values": {"Dark": "#E8E8EC", "Light": "#1D1D22"}},
    {"name": "color/text-muted", "type": "COLOR", "values": {"Dark": "#55555E", "Light": "#6B6B76"}},
    {"name": "color/button", "type": "COLOR", "values": {"Dark": "#3B5BDB", "Light": "#2F4AC0"}},
    {"name": "color/button-text", "type": "COLOR", "values": {"Dark": "#FFFFFF", "Light": "#FFFFFF"}}]}]


def button(name, x, y, w=320, h=64, label="Go", **extra):
    n = {"type": "INSTANCE", "name": name, "component": "Button/Primary", "x": x, "y": y, "width": w, "height": h,
         "properties": {"label": label}}
    n.update(extra)
    return n


def text(name, chars, size, x=0, y=0, w=300, h=40, var="color/text", color="#E8E8EC"):
    return {"type": "TEXT", "name": name, "x": x, "y": y, "width": w, "height": h,
            "text": {"characters": chars, "size": size, "color": {"color": color, "var": var} if var else {"color": color}}}


def design(*frames):
    return {"schema": "figma-to-godot/0.1", "file": "Test", "defaultMode": "Dark", "collections": copy.deepcopy(THEME), "frames": list(frames)}


def frame(name, children, w=1920, h=1080, mode="VERTICAL", padding=(96, 54, 96, 54)):
    f = {"type": "FRAME", "name": name, "x": 0, "y": 0, "width": w, "height": h, "fill": {"color": "#16161D", "var": "color/bg"},
         "layout": {"mode": mode}, "children": children}
    if mode != "NONE":
        f["layout"].update({"spacing": 24, "padding": list(padding), "primaryAlign": "MIN", "counterAlign": "MIN"})
    return f


def rules_hit(findings):
    return sorted({f["rule"] for f in findings if f["label"] != "note"})


class Tags(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(ux.parse_name("Play [action=start_game] [focus=first]"), ("Play", {"action": "start_game", "focus": "first"}))
        self.assertEqual(ux.parse_name("HUD [kind = hud]"), ("HUD", {"kind": "hud"}))
        self.assertEqual(ux.parse_name("Plain name"), ("Plain name", {}))
        self.assertEqual(ux.parse_name("[safe=bleed]"), ("Node", {"safe": "bleed"}))
        self.assertEqual(ux.parse_name("Skip [undo]"), ("Skip", {"undo": "yes"}))

    def test_tags_never_reach_a_node_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(load_design(EXAMPLE), tmp)
            for name in os.listdir(os.path.join(tmp, "figma", "scenes")):
                body = open(os.path.join(tmp, "figma", "scenes", name)).read()
                self.assertNotRegex(body, r"name=\"[^\"]*\[")

    def test_unknown_tag_is_reported_not_swallowed(self):
        f = lint_design(design(frame("Menu", [button("Play [action=play] [focus=first] [key=a] [colour=red]", 96, 54)])))
        self.assertTrue(any("[colour]" in x["msg"] for x in f if x["label"] == "note"))


class FocusGraph(unittest.TestCase):
    def prepared(self, children, **kw):
        d = design(frame("Menu", children, **kw))
        return ux.prepare(d)[0]

    def test_neighbors_from_layout_are_flagged_generated(self):
        fx = self.prepared([button("A [focus=first]", 96, 54), button("B", 96, 142), button("C", 96, 230)])
        g = ux.focus_graph(fx)
        self.assertEqual(g["first"], 0)
        self.assertFalse(g["first_generated"])
        self.assertEqual(g["edges"][0], {"down": (1, "generated")})
        self.assertEqual(g["edges"][1], {"up": (0, "generated"), "down": (2, "generated")})
        self.assertEqual(ux.unreachable(g, 3), [])

    def test_a_tag_wins_over_layout(self):
        fx = self.prepared([button("A [focus=first] [down=C]", 96, 54), button("B", 96, 142), button("C", 96, 230)])
        self.assertEqual(ux.focus_graph(fx)["edges"][0]["down"], (2, "tag"))

    def test_a_tag_that_names_nothing_is_a_problem(self):
        fx = self.prepared([button("A [focus=first] [down=Zebra]", 96, 54), button("B", 96, 142)])
        self.assertTrue(any("Zebra" in p for p in ux.focus_graph(fx)["problems"]))

    def test_side_by_side_controls_move_left_and_right(self):
        fx = self.prepared([button("Back", 96, 54, w=200), button("Apply", 320, 54, w=200)], mode="NONE")
        g = ux.focus_graph(fx)
        self.assertEqual(g["edges"][0], {"right": (1, "generated")})
        self.assertEqual(g["edges"][1], {"left": (0, "generated")})

    def test_no_first_tag_means_the_first_in_reading_order_and_says_so(self):
        fx = self.prepared([button("Lower", 96, 400), button("Upper", 96, 54)], mode="NONE")
        g = ux.focus_graph(fx)
        self.assertTrue(g["first_generated"])
        self.assertEqual(fx["controls"][g["first"]]["name"], "Upper")

    def test_focus_none_takes_a_control_out(self):
        fx = self.prepared([button("A [focus=first]", 96, 54), button("Decor [focus=none]", 96, 142)])
        self.assertEqual([c["name"] for c in fx["controls"]], ["A"])


class Lint(unittest.TestCase):
    def test_a_fully_tagged_example_is_clean(self):
        self.assertEqual(rules_hit(lint_design(load_design(EXAMPLE))), [])

    def test_console_text_safe_area_contrast_and_destructive(self):
        d = design(
            frame("Pause [platform=console]", [
                text("Heading [key=p.h]", "Paused", 48, 0, 0),
                text("Tip [key=p.t]", "Tiny", 16, 0, 84, var="color/text-muted", color="#55555E"),
                button("Resume [action=resume] [focus=first] [key=p.r]", 0, 132, label="Resume"),
                button("Delete save [action=delete_save] [key=p.d]", 0, 220, label="Delete save"),
            ], padding=(0, 0, 0, 0)),
            frame("Corner HUD [platform=console] [kind=hud]", [text("Ammo [key=none]", "30 / 90", 30, 8, 8)], mode="NONE"))
        f = lint_design(d)
        self.assertEqual(rules_hit(f), ["GUX-CONFIRM-DESTRUCTIVE", "GUX-CONTRAST", "GUX-SAFE-TITLE", "GUX-TEXT-MIN"])
        safe = [x for x in f if x["rule"] == "GUX-SAFE-TITLE"]
        self.assertEqual(len(safe), 2)  # one for the auto-layout frame's padding, one for the hand-placed HUD text
        self.assertTrue(any("padding" in x["msg"] and x["where"] == "Pause" for x in safe))
        self.assertTrue(any(x["where"] == "Corner HUD/Ammo" for x in safe))
        contrast = next(x for x in f if x["rule"] == "GUX-CONTRAST")
        self.assertEqual(contrast["label"], "failure")
        self.assertIn("Dark", contrast["msg"])

    def test_text_minimum_scales_with_the_frame(self):
        small = lint_design(design(frame("Menu [platform=console]", [text("T [key=k]", "x", 20, 96, 54)], mode="NONE")))
        self.assertIn("GUX-TEXT-MIN", rules_hit(small))  # 20 is under 26 at 1080p
        d720 = design(frame("Menu [platform=console]", [text("T [key=k]", "x", 20, 64, 36)], w=1280, h=720, mode="NONE"))
        self.assertNotIn("GUX-TEXT-MIN", rules_hit(lint_design(d720)))  # at 720p the minimum is 17.3

    def test_phone_tap_target_states_and_default_names(self):
        d = design(frame("Phone [platform=mobile]", [
            button("Play [action=play] [focus=first] [key=m.p]", 20, 20, w=200, h=30, states=["Default", "Hover", "Pressed"]),
            button("Frame 12 [action=shop]", 20, 66, w=200, h=48, label="Shop", states=["Default", "Focus"]),
        ], w=390, h=844, padding=(20, 20, 20, 20)))
        f = lint_design(d)
        self.assertEqual(rules_hit(f), ["GUX-FOCUS-STATE", "GUX-LAYER-NAMED", "GUX-STRING-KEY", "GUX-TARGET-MIN"])
        self.assertEqual(len([x for x in f if x["rule"] == "GUX-FOCUS-STATE"]), 1)  # the second button has a focus state
        android = copy.deepcopy(d)
        android["frames"][0]["name"] = "Phone [platform=android]"
        self.assertEqual(len([x for x in lint_design(android) if x["rule"] == "GUX-TARGET-MIN"]), 1)
        android["frames"][0]["children"][1]["height"] = 46  # fine at 44, short of Android's 48
        self.assertEqual(len([x for x in lint_design(android) if x["rule"] == "GUX-TARGET-MIN"]), 2)

    def test_states_not_exported_is_said_not_assumed(self):
        notes = [x for x in lint_design(load_design(EXAMPLE)) if x["label"] == "note"]
        self.assertTrue(any(x["rule"] == "GUX-FOCUS-STATE" and "not checked" in x["msg"] for x in notes))

    def test_untagged_controls_get_generated_ids_that_are_flagged(self):
        f = lint_design(design(frame("Menu", [button("Start Game", 96, 54, label="Start")])))
        self.assertEqual(rules_hit(f), ["GUX-ACTION-NAMED", "GUX-FOCUS-FIRST", "GUX-STRING-KEY"])
        self.assertTrue(any("'start_game'" in x["msg"] for x in f))

    def test_hand_placed_controls_loose_colors_and_button_names_in_text(self):
        d = design(frame("Menu", [
            button("Go [action=go] [focus=first] [key=k.go]", 96, 54),
            text("Hint [key=k.hint]", "Press A to jump", 30, 96, 200, var=None, color="#E8E8EC"),
        ], mode="NONE"))
        f = lint_design(d)
        # The loose text color is light. It reads on the dark theme and vanishes on the light one,
        # which is exactly why a loose color is a finding: the contrast failure names the mode.
        self.assertEqual(rules_hit(f), ["GUX-AUTOLAYOUT", "GUX-COLOR-VAR", "GUX-CONTRAST", "GUX-PROMPT-SWAP"])
        self.assertEqual([x["msg"].split(" in mode ")[1].split(";")[0] for x in f if x["rule"] == "GUX-CONTRAST"], ["Light"])
        d["frames"][0]["name"] = "Menu [kind=hud]"
        d["frames"][0]["children"][1]["name"] = "Hint [key=k.hint] [prompt=jump]"
        self.assertEqual(rules_hit(lint_design(d)), ["GUX-COLOR-VAR", "GUX-CONTRAST"])

    def test_unreachable_control_and_inconsistent_label(self):
        d = design(
            frame("A", [button("Back [action=back] [focus=first] [key=a.b]", 96, 54, label="Back"),
                        button("Far [action=far] [key=a.f]", 1500, 60, label="Far")], mode="NONE"),
            frame("B", [button("Back [action=back] [focus=first] [key=b.b]", 96, 54, label="Return")]))
        d["frames"][0]["name"] = "A [kind=hud]"
        f = lint_design(d)
        self.assertIn("GUX-CONSISTENCY", rules_hit(f))
        self.assertNotIn("GUX-FOCUS-REACH", rules_hit(f))  # Far is to the right of Back, so it is reachable
        # A designer's tag can cut a control off: here "right" from Back goes nowhere new.
        d["frames"][0]["children"][0]["name"] = "Back [action=back] [focus=first] [key=a.b] [right=Back]"
        cut = lint_design(d)
        self.assertTrue(any(x["rule"] == "GUX-FOCUS-REACH" and x["where"] == "A/Far" for x in cut))

    def test_every_rule_the_code_cites_is_in_the_rulebook(self):
        rules = ux.load_rules()
        src = open(os.path.join(HERE, "..", "figma2godot", "ux.py")).read() + open(os.path.join(HERE, "..", "figma2godot", "handoff.py")).read()
        for rid in set(re.findall(r"GUX-[A-Z-]+[A-Z]", src)):
            self.assertIn(rid, rules["by_id"], rid)
        for r in rules["rules"]:
            self.assertIn(r["tier"], rules["tiers"])
            self.assertTrue(set(r["check"]) <= set(rules["checks"]), r["id"])
            self.assertTrue(r["source"], r["id"])


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.written, cls.report = build(load_design(EXAMPLE), cls.tmp.name)
        cls.fig = os.path.join(cls.tmp.name, "figma")
        cls.handoff = json.load(open(os.path.join(cls.fig, "handoff.json")))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def scene(self, name):
        return open(os.path.join(self.fig, "scenes", name + ".tscn")).read()

    def test_scene_carries_the_screen_script_focus_and_action_ids(self):
        s = self.scene("MainMenu")
        self.assertIn('path="res://figma/scripts/figma_screen.gd"', s)
        self.assertIn('initial_focus = NodePath("Content/Play")', s)
        self.assertIn('metadata/figma_action = &"start_game"', s)
        self.assertIn('metadata/figma_key = "menu.play"', s)
        self.assertIn('focus_neighbor_bottom = NodePath("../Settings")', s)
        self.assertIn("unique_name_in_owner = true", s)
        self.assertEqual(int(re.search(r"load_steps=(\d+)", s).group(1)), 1 + s.count("[ext_resource"))

    def test_helpers_are_written_and_only_the_ones_needed(self):
        scripts = sorted(os.listdir(os.path.join(self.fig, "scripts")))
        self.assertEqual(scripts, ["figma_input_mode.gd", "figma_safe_area.gd", "figma_screen.gd"])  # the HUD has a prompt
        with tempfile.TemporaryDirectory() as tmp:
            build(design(frame("Menu", [button("Go [action=go] [focus=first] [key=k]", 96, 54)])), tmp)
            self.assertNotIn("figma_input_mode.gd", os.listdir(os.path.join(tmp, "figma", "scripts")))

    def test_handoff_json_says_what_each_control_does(self):
        menu = next(s for s in self.handoff["screens"] if s["screen"] == "MainMenu")
        self.assertEqual(menu["initial_focus"], "Content/Play")
        self.assertFalse(menu["initial_focus_generated"])
        quit_ = next(c for c in menu["controls"] if c["action"] == "quit_game")
        self.assertEqual((quit_["type"], quit_["godot_signal"], quit_["unique_name"], quit_["confirm"]), ("Button", "pressed", "%Quit", "QuitDialog"))
        self.assertEqual(quit_["neighbors"], {"up": {"to": "Settings", "from": "generated"}})
        settings = next(s for s in self.handoff["screens"] if s["screen"] == "Settings")
        kinds = {c["action"]: c["screen_signal"].split("(")[0] for c in settings["controls"]}
        self.assertEqual(kinds, {"set_fullscreen": "value_changed", "set_music_volume": "value_changed", "set_player_name": "value_changed",
                                 "set_quality": "value_changed", "close_settings": "action", "apply_settings": "action"})
        hud = next(s for s in self.handoff["screens"] if s["screen"] == "HUD")
        self.assertEqual(hud["kind"], "hud")
        self.assertIsNone(hud["initial_focus"])
        self.assertEqual(hud["prompts"][0]["prompt"], "interact")
        for s in self.handoff["screens"]:
            for c in s["controls"]:
                self.assertIn('[node name="%s"' % c["path"].split("/")[-1], self.scene(s["screen"]))

    def test_handoff_markdown_is_written_for_an_implementer(self):
        md = open(os.path.join(self.fig, "HANDOFF.md")).read()
        for want in ("Do not edit anything under this folder", "`start_game`", "screen.action.connect", "godot_ux_check.gd",
                     "What the design cannot show: you build these", "What only a person can decide", "Controls can be remapped"):
            self.assertIn(want, md)

    def test_strings_csv_is_godots_layout_and_skips_key_none(self):
        rows = list(csv.reader(open(os.path.join(self.fig, "strings.csv"))))
        self.assertEqual(rows[0], ["keys", "en"])
        keys = [r[0] for r in rows[1:]]
        self.assertIn("menu.play", keys)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertFalse(any("score" in k for k in keys))  # Score is tagged [key=none]

    def test_tv_screen_gets_a_safe_area_container_that_keeps_the_design_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(design(frame("Pause [platform=console]", [button("Resume [action=resume] [focus=first] [key=k]", 120, 80)], padding=(120, 80, 120, 80))), tmp)
            s = open(os.path.join(tmp, "figma", "scenes", "Pause.tscn")).read()
            self.assertIn("figma_safe_area.gd", s)
            self.assertIn('mode = "title"', s)
            self.assertIn("inset = 0.05", s)
            self.assertIn("design_margins = Vector4i(120, 80, 120, 80)", s)
            self.assertIn('platform = &"console"', s)
            self.assertEqual(int(re.search(r"load_steps=(\d+)", s).group(1)), 1 + s.count("[ext_resource"))

    def test_pc_screen_gets_no_safe_area_container(self):
        self.assertNotIn("figma_safe_area.gd", self.scene("MainMenu"))

    def test_snake_case_file_names(self):
        self.assertEqual([snake_file(x) for x in ("MainMenu", "Main Menu", "HUD", "pauseScreen2")], ["main_menu", "main_menu", "hud", "pause_screen2"])
        with tempfile.TemporaryDirectory() as tmp:
            build(load_design(EXAMPLE), tmp, snake_files=True)
            self.assertEqual(sorted(os.listdir(os.path.join(tmp, "figma", "scenes"))), ["hud.tscn", "main_menu.tscn", "settings.tscn"])
            h = json.load(open(os.path.join(tmp, "figma", "handoff.json")))
            self.assertEqual(h["screens"][0]["scene"], "res://figma/scenes/main_menu.tscn")

    def test_the_callers_design_is_not_changed(self):
        d = load_design(EXAMPLE)
        before = json.dumps(d, sort_keys=True)
        with tempfile.TemporaryDirectory() as tmp:
            build(d, tmp)
        self.assertEqual(json.dumps(d, sort_keys=True), before)

    def test_cli(self):
        self.assertEqual(main(["lint", EXAMPLE]), 0)
        self.assertEqual(main(["lint", EXAMPLE, "--strict"]), 0)
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "d.json")
            json.dump(design(frame("Menu", [button("Start", 96, 54)])), open(p, "w"))
            self.assertEqual(main(["lint", p]), 0)
            self.assertEqual(main(["lint", p, "--strict"]), 1)


if __name__ == "__main__":
    unittest.main()
