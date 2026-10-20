# Run: godot --headless --path <project> --script <this file>
# Loads every generated scene in real Godot, checks it instantiates and gets its
# theme, and that swapping the Figma mode really re-colors a bound frame.
# Works on any project built by figma2godot: scenes and modes are discovered.
extends SceneTree

var failures := 0

func fail(msg: String) -> void:
	failures += 1
	printerr("FAIL: ", msg)

func count(n: Node) -> int:
	var c := 1
	for ch in n.get_children():
		c += count(ch)
	return c

func find_background(root: Node) -> Panel:
	for ch in root.get_children():
		if ch is Panel and String(ch.name) == "Background":
			return ch
	return null

func _initialize() -> void:
	var dir := DirAccess.open("res://figma/scenes")
	if dir == null:
		fail("res://figma/scenes missing")
		quit(1)
		return
	var FT = load("res://figma/theme/figma_theme.gd")
	var modes: Array = FT.MODES.keys()
	print("modes: ", modes)
	if modes.size() < 2:
		print("note: only one mode, skipping the mode-swap check")
	var scenes: Array[String] = []
	for f in dir.get_files():
		if f.ends_with(".tscn"):
			scenes.append(f)
	scenes.sort()
	for f in scenes:
		var ps = load("res://figma/scenes/" + f)
		if ps == null:
			fail(f + " did not load")
			continue
		var root: Control = ps.instantiate()
		if root == null:
			fail(f + " did not instantiate")
			continue
		get_root().add_child(root)
		await process_frame
		print("OK  %s: %d nodes, theme=%s" % [f, count(root), root.theme != null])
		if root.theme == null:
			fail(f + " has no theme")
		var bg := find_background(root)
		if bg != null and modes.size() >= 2:
			FT.apply(root, modes[0])
			await process_frame
			var a: StyleBoxFlat = bg.get_theme_stylebox("panel")
			var ca := a.bg_color
			FT.apply(root, modes[1])
			await process_frame
			var b: StyleBoxFlat = bg.get_theme_stylebox("panel")
			print("    Background %s=%s  %s=%s" % [modes[0], ca, modes[1], b.bg_color])
			if ca == b.bg_color:
				fail(f + ": Background did not change between modes")
		root.queue_free()
	if failures > 0:
		quit(1)
	else:
		print("ALL GOOD")
		quit(0)
