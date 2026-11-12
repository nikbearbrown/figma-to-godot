---
name: figma-godot
description: "Figma → Godot UI. Use when the user mentions Godot, GDScript, .tscn, Control nodes, a Godot Theme, a game menu/HUD/settings screen, game UI or game UX, or wants a Figma frame turned into a Godot scene. Builds or reads game UI in Figma so a coding agent can implement it: layer-name tags carry each control's action, controller focus, string keys and platform. Exports the frames and variables with the Figma MCP, checks them against the game UX rules, converts them with figma2godot into .tscn scenes plus one Theme per variable mode and a HANDOFF.md for the implementer, and verifies the result by loading and measuring it in Godot."
disable-model-invocation: false
---

# Figma → Godot

Turns Figma frames into Godot scenes and Figma variables into Godot Themes. The
conversion is **deterministic code** (`figma2godot`), not the model improvising
`.tscn` text: Claude's job is to get the design out of Figma, run the tool,
read the report, and verify in Godot.

## When you build the UI in Figma

Whatever you draw has to be readable by the coding agent that implements it. A picture of a menu makes that agent guess; tags in the layer names tell it. Follow [docs/AGENT-CONTRACT.md](../../docs/AGENT-CONTRACT.md) while building, not afterwards:

- **Tag as you create.** Every interactive layer gets `[action=<verb_noun>]`. One control per screen gets `[focus=first]`. Every visible text gets `[key=<screen.name>]`, or `[key=none]` for a number the game fills in. Example: `Play [action=start_game] [focus=first] [key=menu.play]`.
- **Tag the frame with its platform** (`[platform=console]`, `pc`, `mobile`, `android`) and draw at that platform's size. It sets the text minimum, the safe area and the tap-target size. Tag a hand-placed overlay `[kind=hud]`.
- **Say where focus goes when layout would guess wrong** (grids, wrap-around, a button off to one side): `[down=Apply]`.
- **Never write a button's name into text** ("Press A"). Make the prompt its own layer tagged `[prompt=accept]` so it can follow the player's device.
- **A destructive control says how a mistake is stopped:** `[confirm=QuitDialog]` or `[undo=yes]`.
- **Give interactive components a `State` variant that includes `Focus`.** Hover does not exist on a gamepad.
- **Name every layer, use auto layout for menus, bind every color to a variable.** These are checked.
- **On a TV screen, pad the frame at least 5% on every side.** Godot keeps content title-safe regardless, so an unpadded frame will not match what ships.
- **Ask, do not decide,** which systems are meant to be hard, which register each HUD element uses (diegetic, meta, spatial, plain HUD), and anything else [docs/GAME-UX.md](../../docs/GAME-UX.md) marks "a person decides".
- **Reference libraries keep their owners' terms.** The Game UI Database's creator has said its content may not be used for anything related to machine learning: do not fetch it, read it or feed it to any tool. Point a person to it instead.

Run `python3 -m figma2godot lint <name>.design.json` after exporting and fix what it finds **in Figma**. A finding you leave goes into the handoff for the implementer to see.

## Workflow

1. **Get the file key and frames.** Parse the Figma URL (`figma.com/design/:fileKey/...?node-id=...`).
2. **Open a session**, then export. Load `figma-use` first (it is mandatory before
   any `use_figma` call), then run `exporter/export.js` through `use_figma`. It
   returns a `figma-to-godot/0.1` design JSON (frames + variable collections).
   Save it as `<name>.design.json`.
   - The exporter has run live on one real file. Pass `OPTS` (see docs/SCHEMA.md) to
     export frames across pages, and compare its JSON with the frames before trusting it.
   - `use_figma` forbids `setPluginData`; tag a component through its name (`Coffee Link`,
     `Toggle`) or its `Style` variant instead.
   - Fallback if `use_figma` is unavailable: `get_variable_defs` +
     `get_metadata` + `get_design_context` give the same facts; assemble the JSON
     by hand against [docs/SCHEMA.md](../../docs/SCHEMA.md).
3. **Lint.** `python3 -m figma2godot lint <name>.design.json --platform <console|pc|mobile|android>`.
   Each finding cites a rule in `rules/game-ux.json`. Fix them in Figma and export again.
   Report what is left by its label (failure, concern, deviation); never call a concern a failure.
4. **Convert.** `python3 -m figma2godot build <name>.design.json --project <godot project> --snake-files`
   (`--snake-files` names scenes `main_menu.tscn`, Godot's own convention; leave it off
   for a project that already uses the older `MainMenu.tscn` names).
5. **Read `figma/figma_import_report.md`.** Anything dropped or approximated is
   listed there. Tell the user; never claim a clean import when the report has rows.
6. **Verify in Godot, do not eyeball the text.** Run
   `godot --headless --path <project> --script tests/godot_check.gd` (loads every
   scene, swaps modes) and `tests/godot_ux_check.gd` (focus is set and every control is
   reachable, text is not under the platform minimum, TV content is title-safe, tap
   targets are big enough; writes `figma/ux_check.md`). For visual checks run
   `tests/godot_shots.gd` (needs a window) and look at the PNGs. The text check gives an
   upper bound on body height: under the minimum is a certain failure, over it still
   needs a measured screenshot. Say which.
7. **Hand off.** `figma/HANDOFF.md` is what the implementing agent reads first: every
   control's action id and signal, the focus graph, the string keys, the findings, what
   the design cannot show (remapping, saved settings, text scaling, subtitles) and the
   rules for working in the project. Point the implementer at it; do not paraphrase it.
8. **Never hand-edit generated files.** Fix the design (a layer name, a tag, a
   variable) or the converter, then re-run. Game code goes outside the `figma/` folder
   and listens to the screen's `action` and `value_changed` signals.

## Conventions that make the mapping work

- Variables named `color/<role>`: `bg, panel, text, text-muted, accent, button,
  button-text, input, input-text, border`; floats `radius/button`, `radius/panel`,
  `radius/input`, `font-size/body`, `spacing/button-x`, `spacing/button-y`.
  Missing roles use loud, reported fallbacks.
- Bind frame fills and text colors to variables, not literal hex: bound colors
  become theme type variations and re-color when the mode changes.
- Components are matched by name (`Button`, `Toggle`, `Text Field`, `Slider`,
  `Dropdown`, `Progress Bar`, `Divider`, `Icon`, and `Coffee Link` / any `Link` for a
  LinkButton with a `URL` property). A Button `Style` variant (Secondary, Tertiary,
  Quiet) needs `color/button-<style>` and `color/button-<style>-text` variables.
- Auto-layout is the contract. Frames without auto-layout become absolutely
  positioned Controls (right for HUD overlays, wrong for responsive menus).

## Reference

| Doc | When |
|---|---|
| [docs/AGENT-CONTRACT.md](../../docs/AGENT-CONTRACT.md) | The tags, what the converter writes, and what the implementer does with it |
| [docs/GAME-UX.md](../../docs/GAME-UX.md) | The game UX rules, how each is checked, and the cautions |
| [docs/MAPPING.md](../../docs/MAPPING.md) | What every Figma construct becomes, and what is not imported |
| [docs/SCHEMA.md](../../docs/SCHEMA.md) | The design JSON, if you must assemble it by hand |
| [docs/WHY.md](../../docs/WHY.md) | Why this exists |
