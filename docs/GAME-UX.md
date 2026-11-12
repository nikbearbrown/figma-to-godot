# Game UX rules

The rules this tool applies to game UI, and where each one is checked. The machine-readable copy is [rules/game-ux.json](../rules/game-ux.json); a test keeps the code and the rulebook in step.

## The two tensions

App design removes obstacles between a person and a goal. A game is a set of obstacles placed on purpose. So the first job is telling **intended challenge** from **unintended friction**, and removing the second without touching the first. The second tension is **information against immersion**: players need state (health, objectives, what can be used), and every piece of interface reminds them they are operating a machine.

Neither tension has a number. That is why some rules below are checked by code and others are handed to a person.

## How a rule is checked

- **The design (`lint`)**: worked out from the Figma export before anything is built.
- **The running scene**: measured in Godot by `tests/godot_ux_check.gd`, where layout is real.
- **Handed to the implementer**: the design cannot show it (remapping, saved settings), so `HANDOFF.md` lists it as work to do.
- **A person decides**: a judgment. It is listed for review and never auto-decided.

Labels follow the kind of rule: breaking a published accessibility standard is a **failure**; going against platform or expert guidance is a **concern**; breaking this tool's own conventions is a **deviation**.

## Legibility

Game UI is read from a couch, a desk and a hand, so the numbers change with the platform.

| Rule | What | How it is checked | Source |
|---|---|---|---|
| `GUX-TEXT-MIN` | Text is at least the platform minimum, measured as rendered body height. Console 26 px at 1080p (52 at 4K). PC 18 px at 1080p (36 at 4K). Handheld 17 pt body text. Body height is the pixel distance from the lowest descender to the highest ascender, not the font size. | the design (`lint`), the running scene | Xbox Accessibility Guideline 101 (re-read 2026-11-11); Apple, Designing for games |
| `GUX-TEXT-SCALE` | Players can resize text up to 200% without losing content. Drive every size from one Theme and build layouts from containers so larger text reflows instead of clipping. | handed to the implementer | Xbox Accessibility Guideline 101 (re-read 2026-11-11) |
| `GUX-CONTRAST` | Text contrast is at least 4.5:1, or 3:1 for large text. Worked out per theme mode from the text color and the fill behind it. | the design (`lint`) | WCAG 2.x 1.4.3, as cited in Unity's accessibility guidance |
| `GUX-NO-COLOR-ALONE` | No information is conveyed by color alone | a person decides | Game Accessibility Guidelines, Basic |

## Screen real estate

Televisions still overscan; phones have notches.

| Rule | What | How it is checked | Source |
|---|---|---|---|
| `GUX-SAFE-TITLE` | On a TV, text and controls stay inside the title-safe area. The inner 90% of the screen. Xbox's page gives 3456 x 1944 at 4K (exactly 90%) but 1720 x 1000 with 96 px and 40 px margins at 1080p, which do not agree with each other; this tool uses 5% on every side, which satisfies both. | the design (`lint`), the running scene | Xbox, Screen areas (re-read 2026-11-11); Amazon Fire TV design guidelines |
| `GUX-SAFE-DEVICE` | On a phone, ask the device for its safe area at run time. Notches, rounded corners and home indicators differ by device. Never hard-code insets. | handed to the implementer | Research brief, Part 7 |
| `GUX-TARGET-MIN` | On touch screens, anything tappable is at least 44 by 44 points. 48 by 48 dp when the frame is tagged for Android. | the design (`lint`), the running scene | Apple, Designing for games; Material Design 3 (Android figure, from the figma-appdesigner rulebook) |

## Input: focus, navigation and glyphs

A mouse can point at a pixel. A controller can only move focus between controls, and a design drawn with a mouse has no focus graph unless someone writes one.

| Rule | What | How it is checked | Source |
|---|---|---|---|
| `GUX-FOCUS-FIRST` | Something has focus when a screen opens. Without initial focus, controller input does nothing. Tag one control [focus=first]. | the design (`lint`), the running scene | Godot docs, Keyboard/Controller Navigation and Focus; research brief, Part 8 |
| `GUX-FOCUS-REACH` | Every control can be reached with directional input. The focus graph is explicit: neighbors come from [up=] [down=] [left=] [right=] tags, or are generated from layout and flagged for review. | the design (`lint`), the running scene | Godot docs, Keyboard/Controller Navigation and Focus; research brief, Part 8 |
| `GUX-FOCUS-STATE` | Every interactive component has a visible focus state. A focus state is not a hover state: hover does not exist on a gamepad. Checked when the export lists the component's states. | the design (`lint`) | Research brief, Parts 8 and 12 |
| `GUX-PROMPT-SWAP` | Button prompts match the device in the player's hands. Tag a prompt [prompt=accept] instead of writing a button's name into the text. The implementer swaps the glyph when the input device changes. | the design (`lint`), handed to the implementer | Research brief, Part 8 |
| `GUX-REMAP` | Controls can be remapped | handed to the implementer | Research brief, Part 8 |

## Usability outside the challenge

Hodent's pillars apply to the interface, not to what is meant to be hard. Dying to a boss is design. Losing a save to a mis-press is a defect.

| Rule | What | How it is checked | Source |
|---|---|---|---|
| `GUX-CHALLENGE-MARKED` | Each system is marked as intended challenge or as interface. The usability rules apply to the interface. They do not apply to what is meant to be hard. | a person decides | Research brief, Part 1 |
| `GUX-CONFIRM-DESTRUCTIVE` | A destructive action is confirmed or can be undone. Error prevention belongs in menus, saves and shops, never in the designed challenge. Tag the control [confirm=<screen or dialog>] or [undo=yes]. | the design (`lint`) | Hodent, The Gamer's Brain (error prevention and recovery) |
| `GUX-CONSISTENCY` | The same action has the same label everywhere. Checked across screens by action id. | the design (`lint`) | Hodent, The Gamer's Brain (consistency) |
| `GUX-SIGNS-FEEDBACK` | Every interaction shows what can be done and what just happened | a person decides | Hodent, The Gamer's Brain (signs and feedback) |
| `GUX-ONBOARD` | Teach one new thing at a time, by doing, and let experts skip | a person decides | Research brief, Part 4 |

## Information versus immersion

| Rule | What | How it is checked | Source |
|---|---|---|---|
| `GUX-REGISTER` | Each piece of HUD information has a chosen register. Diegetic, meta, spatial or plain HUD. Tag it [register=hud]. Diegesis is a tool, not a goal. | a person decides | Fagerholt and Lorentzon, Beyond the HUD (2009) |
| `GUX-JUICE-OPTIONS` | Screen shake, flashes and motion blur can be turned down or off. Juice reliably improves appeal; whether it helps understanding depends on context. If an effect carries information, test it as information. | handed to the implementer | Research brief, Part 5 |
| `GUX-NO-FLICKER` | No flickering images or repetitive patterns | a person decides, handed to the implementer | Game Accessibility Guidelines, Basic |

## Accessibility baseline

The Basic tier of the Game Accessibility Guidelines prevents most complaints. Ship these before anything advanced.

| Rule | What | How it is checked | Source |
|---|---|---|---|
| `GUX-SUBTITLES` | All important speech is subtitled, with size and background options. No more than 38 characters per line. | handed to the implementer | Game Accessibility Guidelines, Basic; IGDA Game Accessibility SIG top ten |
| `GUX-SETTINGS-SAVED` | All settings are saved | handed to the implementer | Game Accessibility Guidelines, Basic |

## So a coding agent can read the design

This tool's own rules. See [AGENT-CONTRACT.md](AGENT-CONTRACT.md).

| Rule | What | How it is checked | Source |
|---|---|---|---|
| `GUX-ACTION-NAMED` | Every interactive control names the action it triggers. [action=start_game]. Without it a coding agent has a button and no verb. | the design (`lint`) | figma-to-godot |
| `GUX-LAYER-NAMED` | Layers are named for what they are. A layer still called Frame 12 or Rectangle 3 tells an implementer nothing and becomes a node with that name. | the design (`lint`) | figma-to-godot |
| `GUX-STRING-KEY` | Visible text has a string key. [key=menu.play]. Keys go to figma/strings.csv for translation; text with no key gets a generated one, flagged. | the design (`lint`) | Research brief, Part 12 |
| `GUX-COLOR-VAR` | Colors are variables, not loose hex values. A bound color becomes a theme entry and changes with the mode. A loose one is frozen. | the design (`lint`) | figma-to-godot |
| `GUX-AUTOLAYOUT` | Menus use auto layout; only a HUD is positioned by hand. Hand-placed controls become brittle pixel offsets. Tag an overlay frame [kind=hud] to say the placement is deliberate. | the design (`lint`) | Research brief, Part 12 |
| `GUX-REFERENCE-TERMS` | Reference libraries keep their owners' terms. The Game UI Database's creator has said its content may not be used for anything related to machine learning. Keep it as a human reference and out of any agent's inputs. | a person decides | Research brief, Part 12 |

## Numbers by platform

| Platform | Smallest text | Safe area | Smallest tap target |
|---|---|---|---|
| Console (TV) | 26 px at 1080p, scaled to the frame | title-safe: inner 90% | not applicable |
| PC | 18 px at 1080p, scaled to the frame | none | not applicable |
| Phone (iOS figures) | 17 pt | the device's, asked for at run time | 44 by 44 |
| Phone (Android) | 17 pt | the device's, asked for at run time | 48 by 48 |

Tag a frame `[platform=console]` (or `pc`, `mobile`, `android`) to choose.

## Cautions

- **Font size is not body height.** Xbox measures text as body height: the pixel distance from the lowest descender to the highest ascender. A Godot `font_size` of 26 does not draw text 26 px tall. `lint` treats a font size under the minimum as a concern, and the Godot check treats a line box under the minimum as a certain failure. Passing both still needs a measured screenshot.
- **Xbox's title-safe numbers do not agree with each other.** The page gives the inner 90% and 3456 by 1944 at 4K (exactly 90%), but 1720 by 1000 with margins of 96 and 40 px at 1080p. This tool uses 5% on every side (96 and 54 px at 1080p), which satisfies both readings.
- **No Android text minimum is in the sources.** Android frames use Apple's 17 pt.
- **Juice is not proven to aid understanding.** Studies find it improves appeal reliably; effects on competence and performance depend on context (Juul and Begy 2016; Hicks et al. 2019). If an effect carries information, test it as information.
- **Heuristics are a lens; playtests are evidence.** A problem a rule predicts and no player hits is a hypothesis. About five target players surface most usability problems; recruit six.
- **Readability is an art-direction constraint from day one.** Interactable things must be tellable from set dressing by shape, light and placement. A marking toggle is an accessibility option, so the version with marking off has to be playable.
- **The usability framework is heuristics informed by psychology, not neuroscience findings.** Treat it as a well-organized checklist.

## Sources

From the project's November 2026 research brief on game UX and UI. The two Xbox pages were re-read on 2026-11-11; the rest are cited as the brief gives them.

- Xbox Accessibility Guideline 101, Text display: https://devdocs.xbox.com/gaming/accessibility/xbox-accessibility-guidelines/101
- Xbox, Screen areas: https://devdocs.xbox.com/build/core-features/graphics/overviews/screen-areas
- Game Accessibility Guidelines: https://gameaccessibilityguidelines.com/
- Apple Human Interface Guidelines, Designing for games: https://developer.apple.com/design/human-interface-guidelines/designing-for-games
- Amazon Fire TV design and UX guidelines: https://developer.amazon.com/docs/fire-tv/design-and-user-experience-guidelines.html
- IGDA Game Accessibility SIG, Top Ten: https://igda-gasig.org/how/game-accessibility-top-ten-se/
- Godot docs, Keyboard/Controller Navigation and Focus: https://docs.godotengine.org/en/stable/tutorials/ui/gui_navigation.html
- Hodent, C. (2017). *The Gamer's Brain*. CRC Press.
- Fagerholt, E., and Lorentzon, M. (2009). *Beyond the HUD*. Master's thesis, Chalmers University of Technology.
- Pinelle, D., Wong, N., and Stach, T. (2008). Heuristic evaluation for games. CHI '08.
- Juul, J., and Begy, J. S. (2016). Good feedback for bad players? FDG/DiGRA.
- Hicks, K., et al. (2019). Juicy game design. CHI PLAY '19.
- Bromley, S. Games User Research: https://gamesuserresearch.com/
- Walker (the Godot rules for implementers): `engines/godot.md` and the asset-organization report in the Walker repository.
