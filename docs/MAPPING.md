# Mapping reference

What every Figma construct becomes in Godot, and what is not imported. Anything
dropped is also written to `figma/figma_import_report.md` on each build.

## Layout

| Figma | Godot |
|---|---|
| Auto-layout vertical / horizontal | `VBoxContainer` / `HBoxContainer` |
| Item spacing | `theme_override_constants/separation` |
| Padding | `MarginContainer` (four margin constants) wrapping the box |
| Primary axis `CENTER` / `MAX` | Box `alignment` = 1 / 2 |
| Primary axis `SPACE_BETWEEN` and friends | Approximated as `MIN`; **reported** |
| Counter axis `MIN` / `CENTER` / `MAX` | Child `size_flags` = shrink-begin / shrink-center / shrink-end |
| Child sizing `FILL` on primary axis | `size_flags` = expand + fill |
| Child sizing `FILL` on counter axis | fill |
| Child sizing `FIXED` | `custom_minimum_size` |
| Child sizing `HUG` | no minimum size; the control sizes to content |
| No auto-layout | `Control` with absolute offsets from the frame's x / y / size |
| Top-level frame | Full-rect `Control` root with the theme attached |

## Surfaces

| Figma | Godot |
|---|---|
| Frame fill / stroke / radius, no auto-layout | `Panel` + theme type variation |
| Frame fill / stroke / radius, with auto-layout | `PanelContainer` > `MarginContainer` > box, + theme type variation |
| Screen background | `Background` `Panel` as the first child of the root |
| Rectangle | `Panel` + theme type variation |
| Fill bound to variable `color/x` | Theme type variation that reads `color/x`, so it changes with the mode |
| Fill with a literal color | A theme type variation with that literal (does not change with the mode) |
| Gradient fill | First stop only; **reported** |

## Components

Matched by lowercase name of the component (and node), first match wins. Set plugin data `godotType` on the node or component to override.

| Name contains | Godot |
|---|---|
| progress, health bar, meter, loading bar | `ProgressBar` |
| slider | `HSlider` |
| toggle, switch | `CheckButton` |
| checkbox | `CheckBox` |
| dropdown, select, option button, combo | `OptionButton` (items from the `options` property) |
| input, text field, text box | `LineEdit` (`placeholder`, `value`) |
| divider, separator | `HSeparator` / `VSeparator` (by shape) |
| icon, image, avatar, thumbnail | `TextureRect` |
| coffee, link | `LinkButton` (`label` text, `url` property becomes `uri`, so a tap opens it) |
| button, btn, cta | `Button` (text from the `label` property or its text child) |
| anything else | Plain frame; **reported** so you can tag it |

Component properties are lower-cased by name: `label`, `checked`, `placeholder`, `value`, `max`, `step`, `options`, `selected`, `style`, `url`. Figma sends them as strings (`"True"`, `"0.7"`); the converter coerces them. A property a widget does not use is listed in the import report.

**Button styles.** A Button instance with a `style` variant other than Primary becomes a theme type variation. `Style=Secondary` reads `color/button-secondary` and `color/button-secondary-text`; hover, pressed and disabled come from `color/button-secondary-hover` etc. if they exist, otherwise they are derived. A style with no matching variable falls back to the primary button and is reported.

**Spacers.** An empty frame is kept as a plain `Control` carrying its sizing, so a `FILL` spacer pushes the controls after it to the end of the box.

## Text

| Figma | Godot |
|---|---|
| Text node | `Label` |
| Alignment left / center / right | `horizontal_alignment` 0 / 1 / 2 |
| Auto-resize height or fixed | `autowrap_mode` = word (smart) |
| Font size different from `font-size/body` | `theme_override_font_sizes/font_size` (also read from a widget's label, so a 14px link stays 14px) |
| Fill bound to `color/text` | Theme default (no override) |
| Fill bound to another variable | `Label` type variation reading that variable |
| Font family | **Not imported**; reported. Add the `.ttf` to the project and set it on the theme. |

## Tokens (variables)

One `theme_<mode>.tres` per variable mode. Collections that lack a mode use their first mode.

| Variable | Used for |
|---|---|
| `color/text`, `color/text-muted` | Label, button disabled, input placeholder |
| `color/button`, `color/button-text` | Button, OptionButton (hover = lighter, pressed = darker, disabled = translucent, unless `color/button-hover` / `-pressed` / `-disabled` exist) |
| `color/input`, `color/input-text`, `color/border` | LineEdit, ProgressBar and slider tracks |
| `color/panel` | Panel, PanelContainer |
| `color/accent` | ProgressBar fill, slider fill |
| `radius/button`, `radius/input`, `radius/panel` | Corner radii |
| `font-size/body` | Theme default font size |
| `spacing/button-x`, `spacing/button-y` | Button padding |

A missing variable uses a built-in default and adds a **warn** row to the report. Any variable name can be bound (`brick/red`, `pop/cyan`), not only `color/...`. A collection with one mode (a shared palette, metrics) is read for values but never becomes a theme; themes are the modes of the multi-mode collections.

**Generated icons.** Godot's default toggle switch and slider knob are light-colored and ignore the theme, so for each mode the converter writes `theme/icons/toggle_<mode>_{on,off,on_disabled,off_disabled}.png` and `slider_<mode>_knob*.png` in that mode's colors (track = `color/button` when on, `color/button-quiet` or `color/input` when off; knob = `color/text`).

Swap at runtime with the generated helper: `FigmaTheme.apply($MainMenu, "Light")`.

## Not imported (and reported)

Effects (shadows, blurs), rotation, blend modes, masks, ellipses and vectors, grid layout (treated as no auto-layout), image fills without an exported asset, children of widgets other than a Button's text.

## Known limitations

- **Checkbox icons.** Square checkboxes still use Godot's default icon. Toggles (`CheckButton`) and slider knobs are generated.
- **Icon sharpness.** The generated toggle and knob icons are drawn at design size, so they look slightly soft on a very high-density screen.
- **Icons inside widgets** (the cup in a link, a glyph in a button) are not imported.
- **Edits do not return.** One direction only.
- **Fonts, shadows and vector art** need manual work.
- **Exporter** (`exporter/export.js`) has been run on one real Figma file. Gradients, images and plugin-data tagging are untested live; `use_figma` does not allow `setPluginData`, so tag a component through its name instead.

## Game UI intent (tags in layer names)

| In Figma | In Godot |
|---|---|
| `[action=start_game]` on a control | meta `figma_action`, a unique name (`%Play`), and the screen root emits `action` or `value_changed` with that id |
| `[focus=first]` | the root's `initial_focus`; `figma_screen.gd` grabs it when the screen opens |
| `[up=]` `[down=]` `[left=]` `[right=]`, or layout when absent | `focus_neighbor_top/bottom/left/right`; `focus_next` and `focus_previous` follow reading order |
| `[key=menu.play]` | meta `figma_key`, and a row in `strings.csv` |
| `[prompt=accept]` | meta `figma_prompt`; `figma_input_mode.gd` is written for the game to register |
| `[platform=console]` on an auto-layout frame | the content container runs `figma_safe_area.gd` in `title` mode (inner 90%) |
| `[platform=mobile]` or `android` on an auto-layout frame | the same container in `device` mode (asks the phone at run time) |
| a hand-placed frame (`[kind=hud]`) | no container; positions are kept and the checks report anything outside the safe area |

The full contract is in [AGENT-CONTRACT.md](AGENT-CONTRACT.md).
