# Run: godot --headless --path <project> --script <this file>
# Measures every generated screen in real Godot against the game UX rules:
#   - something has focus when the screen opens, and every tagged control can be
#     reached from it with directional input (Godot's own neighbor lookup)
#   - text is not smaller than the platform minimum
#   - on a TV screen, text and controls sit inside the title-safe area
#   - on a touch screen, anything tappable is big enough
# Reads res://figma/handoff.json (written by figma2godot) and writes res://figma/ux_check.md.
extends SceneTree

const SIDES := [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]

var failures: Array[String] = []
var notes: Array[String] = []
var lines: Array[String] = []

func fail(screen: String, rule: String, msg: String) -> void:
	failures.append("%s  %s: %s" % [rule, screen, msg])
	printerr("FAIL ", rule, " ", screen, ": ", msg)

func controls_in(n: Node, out: Array[Control]) -> void:
	for ch in n.get_children():
		if ch is Control:
			out.append(ch)
		controls_in(ch, out)

# The tallest a glyph can be at this size: ascent plus descent. Body height (lowest
# descender to highest ascender of the drawn text) is never more than this, so a value
# under the minimum is a certain failure; a value over it still needs a measured screenshot.
func line_box(c: Control) -> float:
	var font: Font = c.get_theme_font(&"font")
	var size: int = c.get_theme_font_size(&"font_size")
	if font == null:
		return 0.0
	return font.get_ascent(size) + font.get_descent(size)

func has_text(c: Control) -> bool:
	if c is Label:
		return (c as Label).text != ""
	if c is Button:
		return (c as Button).text != ""
	return c is LineEdit

func _initialize() -> void:
	var f := FileAccess.open("res://figma/handoff.json", FileAccess.READ)
	if f == null:
		printerr("res://figma/handoff.json is missing: convert with figma2godot first")
		quit(1)
		return
	var data: Dictionary = JSON.parse_string(f.get_as_text())
	for s: Dictionary in data["screens"]:
		await check_screen(s)
	var out := ["# UX check: %s" % data["design"], "",
		"Measured in Godot %s by tests/godot_ux_check.gd." % Engine.get_version_info()["string"], ""]
	out.append_array(lines)
	out.append("")
	if failures.is_empty():
		out.append("No failures.")
	else:
		out.append("## Failures (%d)" % failures.size())
		out.append("")
		for x in failures:
			out.append("- " + x)
	if not notes.is_empty():
		out.append("")
		out.append("## Not proven")
		out.append("")
		for x in notes:
			out.append("- " + x)
	var w := FileAccess.open("res://figma/ux_check.md", FileAccess.WRITE)
	w.store_string("\n".join(out) + "\n")
	w.close()
	print("ux check: %d failure(s), %d screen(s). Wrote res://figma/ux_check.md" % [failures.size(), data["screens"].size()])
	quit(1 if not failures.is_empty() else 0)

func check_screen(s: Dictionary) -> void:
	var name_: String = s["screen"]
	var packed: PackedScene = load(s["scene"])
	if packed == null:
		fail(name_, "LOAD", "scene %s did not load" % s["scene"])
		return
	var size := Vector2i(int(s["design_size"][0]), int(s["design_size"][1]))
	root.size = size
	root.content_scale_size = size
	var scene: Control = packed.instantiate()
	root.add_child(scene)
	await process_frame
	await process_frame
	var view := Vector2(size)
	var all: Array[Control] = []
	controls_in(scene, all)

	# --- focus
	var tagged: Array[Control] = []
	for c in all:
		if c.has_meta(&"figma_action") and c.is_visible_in_tree() and c.focus_mode != Control.FOCUS_NONE:
			tagged.append(c)
	var reached := 0
	if s["initial_focus"] == null:
		if not tagged.is_empty():
			fail(name_, "GUX-FOCUS-FIRST", "has %d control(s) and no initial focus" % tagged.size())
	else:
		var first := scene.get_node_or_null(NodePath(String(s["initial_focus"]))) as Control
		if first == null:
			fail(name_, "GUX-FOCUS-FIRST", "initial focus %s is not in the scene" % s["initial_focus"])
		else:
			var owner_ := root.gui_get_focus_owner()
			if owner_ != first:
				notes.append("%s: could not confirm the focus owner in this run (got %s). Headless Godot may not hand out focus; check with a window." % [name_, owner_])
			var seen := {first: true}
			var todo: Array[Control] = [first]
			while not todo.is_empty():
				var c: Control = todo.pop_back()
				for side in SIDES:
					var n := c.find_valid_focus_neighbor(side)
					if n != null and not seen.has(n):
						seen[n] = true
						todo.append(n)
			for c in tagged:
				if seen.has(c):
					reached += 1
				else:
					fail(name_, "GUX-FOCUS-REACH", "%s cannot be reached from %s with directional input" % [scene.get_path_to(c), first.name])

	# --- text size
	var text_min: float = float(s["text_min"]) if s["text_min"] != null else 0.0
	var smallest := INF
	var smallest_at := ""
	var texts := 0
	for c in all:
		if not c.is_visible_in_tree() or not has_text(c):
			continue
		texts += 1
		var h := line_box(c)
		if h < smallest:
			smallest = h
			smallest_at = String(scene.get_path_to(c))
		if text_min > 0.0 and h < text_min:
			fail(name_, "GUX-TEXT-MIN", "%s: at most %.1f px tall, minimum is %.1f on %s" % [scene.get_path_to(c), h, text_min, s["platform"]])
	if texts > 0 and text_min > 0.0 and smallest >= text_min:
		notes.append("%s: the smallest text (%s) is at most %.1f px tall against a minimum of %.1f. That passes the screen but is an upper bound: measure a screenshot to be sure of body height." % [name_, smallest_at, smallest, text_min])

	# --- title-safe area (TV)
	var outside := 0
	if s["safe_area"] == "title":
		var inset: float = float(s["safe_inset"])
		var safe := Rect2(view * inset, view * (1.0 - 2.0 * inset)).grow(0.5)
		for c in all:
			if not c.is_visible_in_tree():
				continue
			if not (has_text(c) or c.has_meta(&"figma_action")):
				continue
			if not safe.encloses(c.get_global_rect()):
				outside += 1
				fail(name_, "GUX-SAFE-TITLE", "%s at %s is outside the title-safe area %s" % [scene.get_path_to(c), c.get_global_rect(), safe])

	# --- tap targets (touch)
	var target_min: float = float(s["target_min"])
	if target_min > 0.0:
		for c in tagged:
			var r := c.get_global_rect().size
			if r.x < target_min - 0.5 or r.y < target_min - 0.5:
				fail(name_, "GUX-TARGET-MIN", "%s is %.0f by %.0f; needs %.0f by %.0f on %s" % [scene.get_path_to(c), r.x, r.y, target_min, target_min, s["platform"]])

	lines.append("- **%s** (%s, %d by %d): %d of %d tagged controls reachable; smallest text at most %s px (minimum %s); safe area %s%s." % [
		name_, s["platform"], size.x, size.y, reached, tagged.size(),
		("%.1f" % smallest) if texts > 0 else "n/a", ("%.1f" % text_min) if text_min > 0.0 else "none",
		s["safe_area"], (", %d outside" % outside) if outside > 0 else ""])
	root.remove_child(scene)
	scene.free()
