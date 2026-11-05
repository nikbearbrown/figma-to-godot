# Theme swap signboard (Colorfigure for "Variables to Theme", the light/dark mode swap)

Files: `figure.html` (source, loads `core.js`, a copy of the engine), `theme-swap-signboard.html` (built with the skill's `build.py`, self-contained, keeps the
"Made with Colorfigures" credit), `stills/`, `shots/` (verification renders). Card: `figma-to-godot/pantry/variables-to-theme-mode-swap-colorfigure.md`.

## What the figure says (declared analogy)
A converted scene stores names, not colours. Each Figma variable mode became its own Godot Theme file that defines the same names; swapping the Theme on the
root re-colours the unchanged scene, but only fills that were bound to variables follow the mode; a fill typed as a literal hex does not. The signboard is the
scene, the cards are the theme files, the rack is the mode table, the hoist is `FigmaTheme.apply`. Nothing is asserted beyond the card's mapping table. Colours
on the bands are illustrative (they are not the README's Settings screenshot values). No on-figure text claims anything about how Godot reads the Theme.

## Parts -> one job -> card (the 10 parts)
| # | Part | Its one job | Card / source |
|---|---|---|---|
| 1 | SIGNBOARD: base, back plate, front plate with three holes | holds the three windows; never moves when a card is swapped | generated scene `Settings.tscn` |
| 2 | BACKGROUND WINDOW + printed tag `color/bg` | shows the band named `color/bg` of whichever card is seated | `Background` Panel, variation `Panel_surface_color_bg` |
| 3 | PANEL WINDOW + tag `color/panel` | same, for the panel | `PanelContainer_surface_color_panel_r16_b1` |
| 4 | LITERAL-COLOUR WINDOW + tag `#B39F7F` | shows a band that is the same tan on both cards, so it never changes | MAPPING "literal color ... does not change with the mode" |
| 5 | CARD SLOT (the middle bay behind the windows) | the one place a card sits; whatever is in it is what the windows read | root node's `theme` property |
| 6 | DARK CARD | one colour band per name; dark-brown family; name printed on its header | `theme_dark.tres` |
| 7 | LIGHT CARD | same names, different colours; cream family | `theme_light.tres` |
| 8 | BANDS (three per card, top to bottom: bg, panel, literal) | the colour a window shows | variation entries inside each theme file |
| 9 | CARD RACK: one low rack, a pocket for each mode name (DARK pocket, LIGHT pocket), printed with the mode name | holds a card for each mode, keyed by name | `FigmaTheme.MODES` |
| 10 | SWAP HOIST | clamps the seated card and slides it back into ITS pocket, then clamps the card of the named mode and slides it into the slot | `FigmaTheme.apply(root, mode)` |

Not parts (support only, no label, no claim): the ground board everything stands on (the skill's "board"); the two posts and the rail the hoist rides on (they
hold the hoist, nothing else); the rack's front/back walls and end stops (they keep cards standing and stop them sliding off).

## Layout decision (one change from the card's wording, flag for Bear)
The rack is one low rack with three bays in a row, `[LIGHT pocket | slot behind the board | DARK pocket]`, and the board stands in the middle bay. Reason: the
card says the lever (now the hoist) takes one card from the rack and seats it while the other goes back to the rack; with a single side rack the second card would have to be
carried over the first (a 150-unit-tall gantry that swamped the figure) or pass through it. With a pocket on each side each card only slides one bay. So "the
rack" has two wings, one each side of the board. The card file's word "lever" is now "hoist" in the figure (approved rename): the part is drawn as a carriage on a rail with a rod and a clamp, so the on-figure label is SWAP HOIST;
mapping: swap hoist = `FigmaTheme.apply(root, mode)`, the part that "picks the card for the named mode and seats it in the slot". The card file in pantry/ still says "lever" (not edited here).
When the slot is empty (mid-swap) the windows show the slot's plain back wall, which is drawn in the same constant tan #B39F7F as the literal band so the
literal window never visibly changes; the bg and panel windows show that tan for about a second. This is the analogy's one gap: in Godot the swap is
atomic, here a physical card has to leave before the other arrives.

## Buttons (the card's)
1. **Open scene**: the scene fades in (about 1 s) with the DARK card seated; the hoist hangs just above it, brown.
2. **Theme mode** (one picker, choices Dark / Light, both disabled with "Open the scene first" until opened):
   - Light: hoist (terracotta) clamps DARK, slides it left into the DARK pocket, lets go; goes to the LIGHT pocket, clamps LIGHT, slides it into the slot, lets go, parks.
     The card being carried has a terracotta header; its label pill and SWAP HOIST's pill light terracotta. Windows: bg and panel change to the light bands;
     literal stays; name tags and board do not move.
   - Dark: the reverse.
   Out-of-order: Light/Dark before Open flashes "Open the scene first"; a second swap while one runs flashes "One swap at a time"; choosing the mode already in the slot
   flashes "... is already in the slot". One swap takes about 5 s.

## URL params
`seek=open+light+dark:T` plays steps (`open`, `light`, `dark`, joined with `%2B`) on a fake 60 fps clock for T seconds and stops (open about 1 s; each swap about 5 s);
`open=1` starts opened; `mode=light` starts with LIGHT seated; `clean=1` hides page furniture and any notice; `fast=1` removes the hand-drawn filter (needed for
pixel reads); `probe=1` (or after a seek) writes `data-probe` on `<html>` (window centres, band colours, tag positions, leaders); `xr=1&labels=1`; `yaw= pitch= free=1`;
`press=Open%20scene@300,Theme%20mode%3ELight@2500` uses the real timers.
- `stills/theme-swap-signboard-closed.png`: `?clean=1&yaw=35&seek=open:4`, scale 5, auto-cropped (DARK seated, LIGHT in its pocket, hoist hanging over the seated card; no labels, no toast).
- `stills/theme-swap-signboard-see-through.png`: `?clean=1&xr=1&labels=1&yaw=-30&seek=open%2Blight:14`, scale 5, auto-cropped (after SWAP TO LIGHT: LIGHT seated, DARK in its pocket).

## Verification actually done
- End states by rendered pixels (fast=1, built page, sample at the three window centres) after Open / Light / Light then Dark / Light, Dark, Light:
  dark seated: bg `#3D3929`, panel `#73705F`, literal `#B39F7F`; light seated: bg `#E5E2D9`, panel `#FAF9F5`, literal `#B39F7F`. The literal band is the same
  in every state. The three name tags kept identical screen positions in all four states. `data-errors` empty in all runs.
- Mid-swap frames (T = 0.5 ... 12 s) read: window shows the tan back wall while the slot is empty, hoist and the carried card's header terracotta, hoist parked brown at rest.
- Leaders: an in-page check (segment intersections, leader-to-other-dot distance, leader-through-other-pill, pill overlap, pill outside the frame) passes for yaw -30/0/35/45
  in both modes and for 8 mid-swap frames (T = 2.0, 2.8, 3.6, 4.6 at yaw -30 and 35). The anchors were chosen by a small search over candidate anchors and sides, then confirmed in the stills.
- Angles yaw 110/170/230/300, closed and see-through, in `shots/angles_c.png`, `shots/angles_x.png`: no missing faces, backs make sense. At yaw about 300 the windows are seen
  at a steep angle and show the hole walls (physically correct parallax).
- No NaN in the scene (the only NaN/undefined grep hit is the base64 grain image). Palette grep: only browns, cream, ink, terracotta (`#f4b829` appears only as a CSS fallback that is overridden).

## Not verified / limits
- Real-timer `?press=` runs: headless virtual time advances the engine's frames slowly, so those runs stop mid-swap (one run showed LIGHT seated in the slot but the hoist still returning). End states were read through `seek` only.
- Phone width: headless Chrome will not go narrower than about 500 px, so `shots/phone.png` (390 CSS px requested) is cropped on the right; numbered badges and the legend list do render. Not checked on a real phone.
- The contact between the gripper jaws and the card top, and the slide clearances, were checked by coordinates and by eye, not by an automated test.
- Page layout: the see-through frame is padded for the label columns, so the figure sits smallish on the page (zoom chip available); the page sets `window.FIG_A` itself (taller frame) because build.py's head fixes .75 on desktop.
- [verify, from the card] The card says Godot reading the active Theme at draw time is supported by committed screenshots only; the figure does not assert it (no text about draw time). The literal-colour row is confirmed
  by code and MAPPING only (the example design has no literal fills). The film use and the beat sheet are not verified (none exists in the folder).
- SIGNBOARD's dot is on the bare plate beside the lowest tag; its leader runs left across the DARK pocket (in light mode over the DARK card). Chosen over crowding the right-hand column.
- Dropped / not drawn: radius and border (band is colour only, as the card says), per-widget themes, Figma-side collections, converter re-run, the `FigmaTheme` GDScript, unknown-mode error path. No other part was dropped; every card part is drawn.

## Rename round (SWAP LEVER -> SWAP HOIST)
Only the on-figure label text changed ("lever" appears nowhere else visible: buttons, toast and legend never used it). The pill has the same character count, so its width is unchanged. Rebuilt; leader/pill check re-run and passing at yaw -30/0/35/45 in both modes and at T = 2.0, 3.6, 4.6 at yaw -30 and 35; both stills re-shot. The closed still is pixel-identical (no label in it); the see-through still differs only in the pill region. Internal names (`st.lev`, `levTo`, `data-state` "lever:") are unchanged and not visible.
