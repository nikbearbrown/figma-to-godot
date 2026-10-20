# Run: godot --path <project> --script <this file> -- <outdir> [mode ...]
# Needs a window (not --headless). Saves <Scene>-<mode>.png for every scene and
# for the given modes (default: all modes the project has).
extends SceneTree

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var out: String = args[0] if args.size() > 0 else "user://shots"
	DirAccess.make_dir_recursive_absolute(out)
	var FT = load("res://figma/theme/figma_theme.gd")
	var modes: Array = FT.MODES.keys()
	if args.size() > 1:
		modes = args.slice(1)
	get_root().size = Vector2i(ProjectSettings.get_setting("display/window/size/viewport_width"),
		ProjectSettings.get_setting("display/window/size/viewport_height"))
	var dir := DirAccess.open("res://figma/scenes")
	var scenes: Array[String] = []
	for f in dir.get_files():
		if f.ends_with(".tscn"):
			scenes.append(f.get_basename())
	scenes.sort()
	for scene in scenes:
		for mode in modes:
			var root: Control = load("res://figma/scenes/%s.tscn" % scene).instantiate()
			get_root().add_child(root)
			FT.apply(root, mode)
			for i in 4:
				await process_frame
			var img := get_root().get_texture().get_image()
			img.save_png("%s/%s-%s.png" % [out, scene, String(mode).replace(" ", "_").replace("&", "and")])
			root.queue_free()
			await process_frame
	quit(0)
