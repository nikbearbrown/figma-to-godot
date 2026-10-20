---
name: figma-godot
description: "Figma → Godot UI. Use when the user mentions Godot, GDScript, .tscn, Control nodes, a Godot Theme, a game menu/HUD/settings screen, or wants a Figma frame turned into a Godot scene. Exports the frames and variables with the Figma MCP, converts them with figma2godot into .tscn scenes plus one Theme per variable mode, and verifies the result by loading it in Godot."
disable-model-invocation: false
---

# Figma → Godot

Turns Figma frames into Godot scenes and Figma variables into Godot Themes. The
conversion is **deterministic code** (`figma2godot`), not the model improvising
`.tscn` text: Claude's job is to get the design out of Figma, run the tool,
read the report, and verify in Godot.

## Workflow

1. **Get the file key and frames.** Parse the Figma URL (`figma.com/design/:fileKey/...?node-id=...`).
2. **Open a session**, then export. Load `figma-use` first (it is mandatory before
   any `use_figma` call), then run `exporter/export.js` through `use_figma`. It
   returns a `figma-to-godot/0.1` design JSON (frames + variable collections).
   Save it as `<name>.design.json`.
   - The exporter is not yet verified on a live file. Compare its JSON with the
     frames before trusting it, and say so in your report.
   - Fallback if `use_figma` is unavailable: `get_variable_defs` +
     `get_metadata` + `get_design_context` give the same facts; assemble the JSON
     by hand against [docs/SCHEMA.md](../../docs/SCHEMA.md).
3. **Convert.** `python3 -m figma2godot build <name>.design.json --project <godot project>`
4. **Read `figma/figma_import_report.md`.** Anything dropped or approximated is
   listed there. Tell the user; never claim a clean import when the report has rows.
5. **Verify in Godot, do not eyeball the text.** Run
   `godot --headless --path <project> --script tests/godot_check.gd` (loads every
   scene, swaps modes). For visual checks run `tests/godot_shots.gd` (needs a window)
   and look at the PNGs.
6. **Never hand-edit generated files.** Fix the design (name a component, bind a
   variable, set a `godotType` plugin-data tag) or the converter, then re-run.

## Conventions that make the mapping work

- Variables named `color/<role>`: `bg, panel, text, text-muted, accent, button,
  button-text, input, input-text, border`; floats `radius/button`, `radius/panel`,
  `radius/input`, `font-size/body`, `spacing/button-x`, `spacing/button-y`.
  Missing roles use loud, reported fallbacks.
- Bind frame fills and text colors to variables, not literal hex: bound colors
  become theme type variations and re-color when the mode changes.
- Components are matched by name (`Button/Primary`, `Toggle`, `Text Field`,
  `Slider`, `Dropdown`, `Progress Bar`, `Divider`, `Icon`). Override with plugin
  data `godotType` on the node or component.
- Auto-layout is the contract. Frames without auto-layout become absolutely
  positioned Controls (right for HUD overlays, wrong for responsive menus).

## Reference

| Doc | When |
|---|---|
| [docs/MAPPING.md](../../docs/MAPPING.md) | What every Figma construct becomes, and what is not imported |
| [docs/SCHEMA.md](../../docs/SCHEMA.md) | The design JSON, if you must assemble it by hand |
| [docs/WHY.md](../../docs/WHY.md) | Why this exists |
