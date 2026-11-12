# Design JSON (`figma-to-godot/0.1`)

The boundary between the Figma side (exporter) and the Godot side (converter).
Anything that can produce this JSON works: the bundled `exporter/export.js`, a
Figma plugin, or Claude assembling it from the Figma MCP's read tools.

```jsonc
{
  "schema": "figma-to-godot/0.1",
  "file": "Game UI",
  "defaultMode": "Dark",
  "collections": [{
    "name": "Theme",
    "modes": ["Dark", "Light"],
    "variables": [
      {"name": "color/bg", "type": "COLOR", "values": {"Dark": "#16161D", "Light": "#F4F1EA"}},
      {"name": "radius/button", "type": "FLOAT", "values": {"Dark": 10, "Light": 10}}
    ]
  }],
  "frames": [ /* one entry per top-level screen */ ]
}
```

## Node

```jsonc
{
  "type": "FRAME | TEXT | INSTANCE | COMPONENT | RECTANGLE | GROUP | IMAGE | ...",
  "name": "Settings Panel",
  "x": 0, "y": 0, "width": 480, "height": 420,   // relative to the parent
  "godotType": "Button",                         // optional override
  "component": "Button/Primary",                 // INSTANCE: main component (set/variant)
  "properties": {"label": "Play", "checked": true},
  "sizing": {"h": "FIXED | HUG | FILL", "v": "FIXED | HUG | FILL"},
  "layout": {
    "mode": "VERTICAL | HORIZONTAL | NONE",
    "spacing": 16, "padding": [left, top, right, bottom],
    "primaryAlign": "MIN | CENTER | MAX | SPACE_BETWEEN",
    "counterAlign": "MIN | CENTER | MAX"
  },
  "fill":   {"color": "#24242CFF", "var": "color/panel"},   // var optional: binds to a variable
  "stroke": {"color": "#3A3A46", "var": "color/border", "width": 1},
  "radius": 16,
  "text": {"characters": "Settings", "size": 32, "family": "Recursive",
           "align": "LEFT | CENTER | RIGHT", "autoResize": "WIDTH_AND_HEIGHT | HEIGHT | NONE",
           "color": {"color": "#E8E8EC", "var": "color/text"}},
  "text": {...},                                         // on an INSTANCE with properties: its first text child (label size/color)
  "asset": "icon_sword.png",                              // IMAGE: file under <subdir>/assets/
  "effects": ["DROP_SHADOW"], "rotation": 0,              // reported, not imported
  "children": [ /* nodes */ ]
}
```

Colors are `#RGB`, `#RRGGBB` or `#RRGGBBAA`. A `var` is the Figma variable's
name; `color` is its value in the default mode and is the fallback when the
variable is not in `collections`.

Component `properties` are the instance's Figma component properties with names lower-cased and the `#id` suffix removed. Variant booleans and numbers arrive as strings; the converter coerces them.

A layer `name` may end in tags, `Play [action=start_game] [focus=first] [key=menu.play]`. The converter strips them before naming nodes and uses them for the focus graph, the action ids and the handoff; see [AGENT-CONTRACT.md](AGENT-CONTRACT.md). An INSTANCE of a component set may carry `"states": ["Default", "Hover", "Pressed", "Focus"]`, the options of its `State` variant, so the lint can tell when a control has no focus state.

An INSTANCE that has properties is treated as a widget and exported **without children** (its label and state are in `properties` and `text`). An instance without properties keeps its children.

Exporter options, defined above the script as `const OPTS = {...}`: `skipCollections` (frames only), `frameIds` (explicit frames, across pages) and `file` (the design name; `figma.root.name` is just "Document" in plugin context).

A complete worked example is `examples/game-ui.design.json`.
