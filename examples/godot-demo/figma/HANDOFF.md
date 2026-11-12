# Handoff: Game UI example

For the coding agent (or person) who makes these screens work. The screens were drawn in Figma and converted by figma2godot. This file says what each control is for, which signal to listen to, how focus moves, and what the design could not show. `handoff.json` holds the same facts as data.

## Read this first

1. **Do not edit anything under this folder.** Scenes, themes and scripts here are generated and will be overwritten. To change how a screen looks, change the Figma file (a layer name, a tag, a variable) and convert again. To change what it does, write code outside this folder.
2. **Listen to the screen, not to its buttons.** Each screen's root has two signals: `action(id, source)` and `value_changed(id, value, source)`. Connect to those. Do not reach into the generated node tree by path: paths change when the design changes; action ids do not.
3. **If you must reach a control, use its unique name.** Tagged controls have `unique_name_in_owner` set, so `%PlayButton` (GDScript) or `GetNode<Button>("%PlayButton")` (C#) keeps working when the layout moves.
4. **Put game code where the game keeps it.** A screen's behavior lives beside the feature it belongs to (for example `ui/menus/main_menu.gd`), not in this folder. Files and folders are snake_case; a scene's root node is PascalCase. Keep generation inputs and references outside the Godot project.
5. **Use the project's language.** The generated helpers are GDScript and run in every Godot 4 build, including .NET. In a C# project write your own code in C#: every Godot class is `partial`, signal delegates end in `EventHandler`, and you connect to a GDScript signal with `Connect("action", Callable.From<StringName, Control>(OnAction))`. Check C# enum names against the installed Godot; do not guess them.
6. **Do not hardcode version-sensitive values.** Run `godot --version` (and `dotnet --version` in a C# project) and match `config_version`, the SDK version and the target framework to what is installed. On an existing project, keep what is there.
7. **Commit the sidecars.** Commit every `.uid` and `.import` file next to its source; ignore `.godot/`. Move or rename files inside the Godot editor, or with the editor closed and the sidecar moved with the file. A copied file is a new resource with a new UID.
8. **Do not reuse the `ui_*` input actions for gameplay.** Godot keeps them for focus and menus. Give gameplay its own actions.
9. **Prove it in Godot, not by reading the files.** After any change run the build gate below. A scene that loads without error can still have lost a node or a neighbor; the check counts them.

## The build gate

Run these after every change. All three must pass.

```bash
godot --headless --path . --import
godot --headless --path . --script tests/godot_check.gd      # every scene loads; theme modes swap
godot --headless --path . --script tests/godot_ux_check.gd   # focus, text size, safe area, tap targets
```

Copy the two scripts from figma-to-godot's `tests/` folder if the project does not have them. In a C# project run `dotnet build` first.

## Screens

### MainMenu

- Scene: `res://figma/scenes/MainMenu.tscn` (root node `MainMenu`, script `res://figma/scripts/figma_screen.gd`)
- Platform: pc. Kind: screen. Design size: 1280 by 720.
- Safe area: none applied.
- Focus when it opens: `Content/Play`.

| Control | Type | Action id | Listen for | Label | String key | Focus moves to | Notes |
|---|---|---|---|---|---|---|---|
| %Play | Button | `start_game` | `action(id, source)` | Play | menu.play | down: Settings* |  |
| %Settings | Button | `open_settings` | `action(id, source)` | Settings | menu.settings | up: Play*, down: Quit* |  |
| %Quit | Button | `quit_game` | `action(id, source)` | Quit | menu.quit | up: Settings* | confirm with QuitDialog |

A `*` marks a focus neighbor the converter worked out from the layout. The designer did not set it; check it with a controller.

Example (GDScript, in your own script, not in this folder):

```gdscript
@onready var screen: Control = $MainMenu

func _ready() -> void:
	screen.action.connect(_on_action)
	screen.value_changed.connect(_on_value_changed)

func _on_action(id: StringName, _source: Control) -> void:
	match id:
		&"start_game":
			pass  # Play
		&"open_settings":
			pass  # Settings
		&"quit_game":
			pass  # Quit

func _on_value_changed(id: StringName, value: Variant, _source: Control) -> void:
	pass
```

### Settings

- Scene: `res://figma/scenes/Settings.tscn` (root node `Settings`, script `res://figma/scripts/figma_screen.gd`)
- Platform: pc. Kind: screen. Design size: 1280 by 720.
- Safe area: none applied.
- Focus when it opens: `Content/Settings Panel/Margin/Box/Fullscreen`.

| Control | Type | Action id | Listen for | Label | String key | Focus moves to | Notes |
|---|---|---|---|---|---|---|---|
| %Fullscreen | CheckButton | `set_fullscreen` | `value_changed(id, on: bool, source)` | Fullscreen | settings.fullscreen | down: Music volume*, right: Apply* |  |
| %Music volume | HSlider | `set_music_volume` | `value_changed(id, value: float, source)` |  |  | up: Fullscreen*, down: Player name*, right: Apply* |  |
| %Player name | LineEdit | `set_player_name` | `value_changed(id, text: String, source)` |  |  | up: Music volume*, down: Quality*, right: Apply* |  |
| %Quality | OptionButton | `set_quality` | `value_changed(id, index: int, source)` |  |  | up: Player name*, down: Back*, left: Back*, right: Apply* |  |
| %Back | Button | `close_settings` | `action(id, source)` | Back | common.back | up: Quality*, right: Apply* |  |
| %Apply | Button | `apply_settings` | `action(id, source)` | Apply | common.apply | up: Quality*, left: Back* |  |

A `*` marks a focus neighbor the converter worked out from the layout. The designer did not set it; check it with a controller.

Example (GDScript, in your own script, not in this folder):

```gdscript
@onready var screen: Control = $Settings

func _ready() -> void:
	screen.action.connect(_on_action)
	screen.value_changed.connect(_on_value_changed)

func _on_action(id: StringName, _source: Control) -> void:
	match id:
		&"close_settings":
			pass  # Back
		&"apply_settings":
			pass  # Apply

func _on_value_changed(id: StringName, value: Variant, _source: Control) -> void:
	pass
```

### HUD

- Scene: `res://figma/scenes/HUD.tscn` (root node `HUD`, script `res://figma/scripts/figma_screen.gd`)
- Platform: pc. Kind: hud. Design size: 1280 by 720.
- Safe area: none applied.
- Nothing on this screen takes focus.

Button prompts to swap when the input device changes (register `scripts/figma_input_mode.gd` as the autoload `InputMode`):

- `%Hint`: interact

Example (GDScript, in your own script, not in this folder):

```gdscript
@onready var screen: Control = $HUD

func _ready() -> void:
	screen.action.connect(_on_action)
	screen.value_changed.connect(_on_value_changed)

func _on_action(id: StringName, _source: Control) -> void:
	match id:
		_:
			pass

func _on_value_changed(id: StringName, value: Variant, _source: Control) -> void:
	pass
```

## Strings

`strings.csv` lists every visible text with a key, in Godot's CSV translation layout (`keys,en`). The scenes still hold the English text so they read correctly before translation is set up. To localise: import the CSV, then set each control's text to its key (it is in the control's `figma_key` meta).

## What the check found in the design

Nothing.

Notes:

- `Game UI example`: not checked: the export lists no component states. Export with exporter/export.js, or check by eye that every control has a focus state.

## What the design cannot show: you build these

- **Players can resize text up to 200% without losing content** (GUX-TEXT-SCALE). Drive every size from one Theme and build layouts from containers so larger text reflows instead of clipping.
- **All settings are saved** (GUX-SETTINGS-SAVED). 
- **Controls can be remapped** (GUX-REMAP). 
- **All important speech is subtitled, with size and background options** (GUX-SUBTITLES). No more than 38 characters per line.
- **Screen shake, flashes and motion blur can be turned down or off** (GUX-JUICE-OPTIONS). Juice reliably improves appeal; whether it helps understanding depends on context. If an effect carries information, test it as information.
- **Button prompts match the device in the player's hands** (GUX-PROMPT-SWAP). Tag a prompt [prompt=accept] instead of writing a button's name into the text. The implementer swaps the glyph when the input device changes.
- **On a phone, ask the device for its safe area at run time** (GUX-SAFE-DEVICE). Notches, rounded corners and home indicators differ by device. Never hard-code insets.
- **No flickering images or repetitive patterns** (GUX-NO-FLICKER). 

## What only a person can decide

Ask; do not assume.

- **Each system is marked as intended challenge or as interface** (GUX-CHALLENGE-MARKED). The usability rules apply to the interface. They do not apply to what is meant to be hard.
- **No information is conveyed by color alone** (GUX-NO-COLOR-ALONE). 
- **Every interaction shows what can be done and what just happened** (GUX-SIGNS-FEEDBACK). 
- **Each piece of HUD information has a chosen register** (GUX-REGISTER). Diegetic, meta, spatial or plain HUD. Tag it [register=hud]. Diegesis is a tool, not a goal.
- **Teach one new thing at a time, by doing, and let experts skip** (GUX-ONBOARD). 
- **Reference libraries keep their owners' terms** (GUX-REFERENCE-TERMS). The Game UI Database's creator has said its content may not be used for anything related to machine learning. Keep it as a human reference and out of any agent's inputs.

## What the import dropped or approximated

- info `fonts`: font 'Recursive' is not imported; Godot uses its default font. Drop the .ttf into the project and set it on the theme.
- warn `HUD/Minimap ring`: node type ELLIPSE is not supported and was skipped
