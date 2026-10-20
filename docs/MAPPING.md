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
| button, btn, cta | `Button` (text from the `label` property or its text child) |
| anything else | Plain frame; **reported** so you can tag it |

Component properties are lower-cased by name: `label`, `checked`, `placeholder`, `value`, `max`, `step`, `options`, `selected`.

## Text

| Figma | Godot |
|---|---|
| Text node | `Label` |
| Alignment left / center / right | `horizontal_alignment` 0 / 1 / 2 |
| Auto-resize height or fixed | `autowrap_mode` = word (smart) |
| Font size different from `font-size/body` | `theme_override_font_sizes/font_size` |
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

A missing variable uses a built-in default and adds a **warn** row to the report.

Swap at runtime with the generated helper: `FigmaTheme.apply($MainMenu, "Light")`.

## Not imported (and reported)

Effects (shadows, blurs), rotation, blend modes, masks, ellipses and vectors, grid layout (treated as no auto-layout), image fills without an exported asset, children of widgets other than a Button's text.

## Known limitations

- **Toggle and slider icons.** Godot's default toggle switch and slider grabber are light-colored. They are faint on a light theme. Supply icons from Figma to fix that; not automated yet.
- **Edits do not return.** One direction only.
- **Fonts, shadows and vector art** need manual work.
- **Exporter** (`exporter/export.js`) has not yet been run on a live Figma file.
