# Run: godot --path examples/godot-demo --script ../../tests/godot_shots.gd -- <outdir>
# Needs a window (not --headless). Saves <Scene>-<mode>.png for each scene and mode.
extends SceneTree

func _initialize() -> void:
	var out := "res://../../docs/img"
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	DirAccess.make_dir_recursive_absolute(out)
	get_root().size = Vector2i(1280, 720)
	var FT = load("res://figma/theme/figma_theme.gd")
	for scene in ["MainMenu", "Settings", "HUD"]:
		for mode in ["Dark", "Light"]:
			var root: Control = load("res://figma/scenes/%s.tscn" % scene).instantiate()
			get_root().add_child(root)
			FT.apply(root, mode)
			for i in 4:
				await process_frame
			var img := get_root().get_texture().get_image()
			img.save_png("%s/%s-%s.png" % [out, scene, mode.to_lower()])
			root.queue_free()
			await process_frame
	quit(0)
