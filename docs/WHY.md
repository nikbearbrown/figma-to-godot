# Why Figma to Godot

## Executive summary

**What.** A tool that turns Figma frames into Godot scenes and Figma variables into Godot Themes.

**Why.** In most games, UI is a large share of the work, and Godot's editor makes it slow to build by hand. Figma already holds the design, the spacing, the colors and the light/dark variants. Converting that, instead of re-typing it, removes the repetitive part.

**What is true today.** Frames, auto-layout, padding, common widgets, and color/number variables convert. The result loads in Godot 4.7 and re-colors when you swap Figma modes. The Figma-side exporter is written but not yet run on a live file. See the [README](../README.md) for the full status.

---

## UI is a large share of game work

A game is not only the world the player moves through. Around it sits a lot of interface:

- the main menu, pause menu, settings, and save/load screens
- the HUD: health, ammo, score, minimap, prompts
- inventory, dialogue, shops, crafting, quest logs
- controller and keyboard navigation, focus order, accessibility options
- translations: every string changes length, and some languages read right to left
- several resolutions and aspect ratios

Almost none of that is the fun part, and all of it has to be built, tested and kept in sync with the design every time the design changes.

## Why that hurts in Godot specifically

Godot's UI is built from `Control` nodes: containers, margins, anchors, size flags, and a `Theme` resource that styles every widget. It is a good system, but assembling a screen means dozens of nodes, many small properties (`size_flags`, `custom_minimum_size`, separation constants), and a theme with a stylebox for every state of every widget. It is easy to get wrong and tedious to change.

## Why Figma helps

Figma is where the layout is already decided:

| In Figma | Becomes in Godot |
|---|---|
| Auto-layout (direction, spacing, padding, alignment) | `VBoxContainer` / `HBoxContainer` / `MarginContainer`, with size flags |
| Frame fill, stroke, corner radius | A `Panel` or `PanelContainer` styled through the theme |
| Components (Button, Toggle, Slider, ...) | Real Godot controls |
| Variables (colors, radii, sizes) | Theme values |
| Variable modes (Dark / Light) | One Theme per mode, swapped at runtime |

The last row is the useful one. A designer changes a color variable once; every screen and both themes update. Nobody re-hunts through scenes.

## Why now

Unity just released an experimental UI Toolkit connector for Figma, which imports frames as UXML/USS, maps variables to theme stylesheets and components to controls. The interesting question that release asks is not whether a conversion is possible but how people want to work between the two tools. Godot has the same ingredients: text-based scenes and themes, and a UI system that maps cleanly onto auto-layout. This project is the Godot version of that idea.

## Why it is part of Walker

[Walker](https://github.com/nikbearbrown/walker) is a framework for building games with AI agents: game brief, build, playtest, inspect, revise. A human decides what the game is and whether it feels right; the agent does the repeatable work and shows evidence. UI conversion is exactly repeatable work. A designer (or a student) draws the menu in Figma; the agent converts it, loads it in Godot, and reports what it could not express.

## What this does not claim

- It does not design your UI. Figma is where the design happens.
- It is one-directional. Structure goes Figma to Godot; edits made in Godot do not go back.
- It does not handle gameplay, animation, 2D/3D art, or level layout.
- It does not ship final-quality UI by itself. It removes the typing; judgment about feel is still yours.
