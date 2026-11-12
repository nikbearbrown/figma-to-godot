# The contract: a Figma file a coding agent can build from

A Figma frame says what a screen looks like. A game also needs to know what each control does, where controller focus starts and how it moves, which words are translatable, and which platform the screen is for. A prototype link cannot say any of that, and a coding agent handed a picture of a menu has to guess.

So the intent goes in the one place every tool can read: the layer name. Whoever builds the screen in Figma (a person, or Claude through the Figma MCP) writes it there as tags. The converter strips the tags, carries the intent into the Godot scenes, and writes a handoff file that tells the implementer exactly what to wire.

## Tags

A tag is `[name=value]` after the layer's name. A layer can have several.

```
Play [action=start_game] [focus=first] [key=menu.play]
Quit [action=quit_game] [key=menu.quit] [confirm=QuitDialog]
HUD [kind=hud] [platform=console]
```

| Tag | Goes on | Means | Without it |
|---|---|---|---|
| `[action=start_game]` | a button, toggle, slider, dropdown or text field | the id the game listens for | an id is made from the layer name and flagged |
| `[focus=first]` | one control per screen | it has focus when the screen opens | the first control in reading order is chosen and flagged |
| `[focus=none]` | a control | it is never focused (decoration that looks like a button) | |
| `[up=Name]` `[down=Name]` `[left=Name]` `[right=Name]` | a control | where focus goes in that direction, by layer name | worked out from the layout and marked for review |
| `[key=menu.play]` | text, or a control with a label | its string key for translation | a key is made from screen and layer name and flagged |
| `[key=none]` | text | not a translatable string (a score, a timer) | |
| `[platform=console]` | a top-level frame | `console`, `pc`, `mobile` or `android`: sets the text minimum, the safe area and the tap-target size | the `--platform` given to the converter, `pc` by default |
| `[kind=hud]` | a top-level frame | an overlay placed by hand on purpose | hand-placed controls are reported |
| `[safe=bleed]` | a layer | full-bleed art, allowed outside the safe area | |
| `[prompt=accept]` | a glyph or a line of text | a button prompt that must change with the player's device | a button named in text is reported |
| `[confirm=QuitDialog]` or `[undo=yes]` | a destructive control | how a mistake is prevented or reversed | a destructive-looking action is reported |
| `[register=diegetic]` | a HUD element | the designer's chosen register: `diegetic`, `meta`, `spatial` or `hud` | |
| `[challenge=yes]` | a control or frame | part of the designed difficulty, so the usability rules do not apply to it | |

A tag this tool does not know is reported and ignored, never guessed at.

## What else the Figma file must do

These come from the mapping ([MAPPING.md](MAPPING.md)) and are checked by `figma2godot lint`:

1. **Name every layer for what it is.** `Frame 12` becomes a node called `Frame 12`.
2. **Use auto layout for menus.** It becomes Godot containers. Hand placement becomes fixed pixel offsets and is right only for a HUD.
3. **Bind colors to variables.** A bound color follows the theme mode; a loose one is frozen, and may be unreadable in the other mode.
4. **Use the component names the converter knows** (`Button`, `Toggle`, `Slider`, `Text Field`, `Dropdown`, `Progress Bar`, `Divider`, `Icon`, `Link`).
5. **Give interactive components a `State` variant that includes `Focus`.** A focus state is not a hover state: hover does not exist on a gamepad.
6. **Draw at the platform's size.** 1920 by 1080 for console and PC, the device's point size for a phone. The text minimum is scaled to the frame.
7. **On a TV screen, give the frame padding of at least 5% on every side.** Godot will keep content inside the title-safe area either way, so a frame without that padding will not match what ships.

## What the converter writes

```
figma/
  HANDOFF.md          read first: every screen, control, action id and signal
  handoff.json        the same facts as data
  strings.csv         keys and source text, in Godot's CSV translation layout
  scenes/*.tscn       one per frame
  scripts/
    figma_screen.gd       on every scene's root: two signals, and initial focus
    figma_safe_area.gd    on a TV or phone screen's content container
    figma_input_mode.gd   only when a screen has a prompt: which device is in use
  theme/…             one Theme per variable mode
  figma_import_report.md   what was dropped or approximated
```

In each scene:

- The root has the script `figma_screen.gd`, with `initial_focus` set. It emits `action(id, source)` for presses and `value_changed(id, value, source)` for toggles, sliders, dropdowns and text fields.
- Every tagged control has its action id in the meta `figma_action`, a unique name (`%Play`), and explicit `focus_neighbor_*`, `focus_next` and `focus_previous` paths.
- Every keyed text has its key in the meta `figma_key`. The scene keeps the English text so it reads correctly before translation is set up.
- A prompt has its id in the meta `figma_prompt`.
- On a console or phone screen laid out with auto layout, the content container keeps the larger of the design's padding and the safe-area inset, so nothing is inset twice.

## What the implementer does

`HANDOFF.md` says it in full for each project. In short:

```gdscript
@onready var screen: Control = $MainMenu

func _ready() -> void:
	screen.action.connect(_on_action)

func _on_action(id: StringName, _source: Control) -> void:
	match id:
		&"start_game":
			get_tree().change_scene_to_file("res://content/worlds/forest/forest.tscn")
```

The rules for the implementer are Walker's Godot rules, cut down to what applies to wiring generated UI: never edit the generated folder; listen to the screen's signals instead of reaching into its node tree; game code lives with the feature, in snake_case files; use the project's language (C# classes are `partial`, and check enum names against the installed Godot); do not hardcode version-sensitive values; commit `.uid` and `.import` sidecars; keep `ui_*` actions for the interface; and prove a change in Godot with the build gate, not by reading the files.

## The checks

```bash
python3 -m figma2godot lint design.json --platform console      # the design, before anything is built
python3 -m figma2godot build design.json --project game --snake-files
godot --headless --path game --import
godot --headless --path game --script tests/godot_check.gd      # scenes load, theme modes swap
godot --headless --path game --script tests/godot_ux_check.gd   # focus, text size, safe area, tap targets
```

`lint` works from the design. `godot_ux_check.gd` measures the running scene, where layout is real. They can disagree, and both are right: a 30-point-high button in Figma is a finding in the design even though Godot grows it to fit its label.

## What this does not do

- It does not write game logic. The handoff says what to wire, not what the game does.
- It does not measure body height exactly. Godot reports the tallest a glyph can be at a size (ascent plus descent); body height is never more than that. Under the minimum is a certain failure. Over it, measure a screenshot.
- The focus graph it generates is a starting point. Try it with a controller.
- The phone safe-area code has not been run on a phone.
- The exporter's list of component states has not been run on a live Figma file yet.
