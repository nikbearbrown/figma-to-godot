# Run: godot --headless --path examples/godot-demo --script ../../tests/godot_check.gd
# Loads every generated scene in real Godot, checks it instantiates, the theme
# resolves, and that swapping the Figma mode actually re-colors a bound frame.
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

func _initialize() -> void:
	var dir := DirAccess.open("res://figma/scenes")
	if dir == null:
		fail("res://figma/scenes missing")
		quit(1)
		return
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
		# A frame bound to color/bg must re-color when the mode changes.
		var bg := root.get_node_or_null("Background")
		if bg is Panel:
			var dark: StyleBoxFlat = bg.get_theme_stylebox("panel")
			var dc := dark.bg_color
			var FT = load("res://figma/theme/figma_theme.gd")
			FT.apply(root, "Light")
			await process_frame
			var light: StyleBoxFlat = bg.get_theme_stylebox("panel")
			print("    Background dark=%s light=%s" % [dc, light.bg_color])
			if dc == light.bg_color:
				fail(f + ": Background did not change between Dark and Light")
			FT.apply(root, "Dark")
			await process_frame
		root.queue_free()
	if failures > 0:
		quit(1)
	else:
		print("ALL GOOD")
		quit(0)
