# Free game UX and wireframe resources

[Machine-readable catalog](free-game-ux-resources.json), checked 2026-11-11.

This is source data for designing PC, iPhone and Android game interfaces. It contains links and original descriptions, **not downloaded asset bundles**. Free access does not automatically mean permission to redistribute. The repository MIT license does not relicense external content.

## Start here

| Source | What you get | Cost and rights | Suggested use |
| --- | --- | --- | --- |
| [Game UX Kit](https://www.figma.com/community/file/1460785931676185568/game-ux-kit) | Editable Figma wireframes and components | Creator says free use/modification; redistribution terms not verified | Start menus, buttons, character cards, quests and achievements |
| [Interface In Game](https://interfaceingame.com/screenshots) | Public screenshot and motion reference library | Free gallery access, not a reusable-art license | Compare PC/Mobile menus, inventories, settings and tutorials |
| [Kenney UI Pack](https://kenney-assets.itch.io/ui-pack) | Sprites and vector sources | Zero-price option, CC0 | Prototype original interfaces with reusable graphics |
| [Kenney Input Prompts Pixel 16×](https://kenney-assets.itch.io/input-prompts-pixel-16) | Keyboard, mouse, gamepad and touch prompts | Zero-price option, CC0 | Show the right controls for each input method |

The Game UX Kit's [creator article](https://medium.com/@alenaeres/game-ux-kit-5-reasons-that-make-it-an-essential-tool-7ce4ec072b8a) verifies its free availability. The Figma download/account flow was not tested. Read the file's current terms before copying assets into this repository.

### Not yet verified

[Game UI Database](https://www.gameuidatabase.com/) is recorded separately as a reference candidate, not counted among the four verified sources. Independent coverage describes free browsing, but direct access was blocked during this check. Verify current free access manually before relying on it. Its game screenshots are not licensed art assets for our games.

## No paid anything

- Use only free public browsing and zero-cost downloads. Do not pay, tip, start trials, subscribe or buy upgrades.
- Interface In Game's separate paid wireframe product is deliberately excluded. A free reference gallery is not the same thing as a free editable template.
- Do not bulk scrape screenshot libraries or commit their images. Keep links and create original designs based on general interaction patterns.
- Before any future asset import, record the source/version, download date and license. Keep included notices. If terms or cost are unclear, skip it.

## Using these with this converter

1. Choose the screen and input method: desktop mouse/keyboard or controller, phone portrait/landscape and touch.
2. Use references for layout research; use an editable kit or original Figma components for actual wireframes.
3. Follow [component naming and auto-layout conventions](../README.md#in-your-figma-file). Inspect [supported mappings](../docs/MAPPING.md) rather than assuming arbitrary Figma components will convert.
4. Export, convert, and read the dropped-feature report. **Images, vector art, fonts and shadows are not imported by the current converter.** Kenney graphics need a separate manual Godot asset step.
5. Check safe areas, small-screen wrapping, touch-target size, contrast, text scaling, keyboard/controller focus and back/cancel behavior. Test on actual iPhone/Android devices before claiming support; current project verification is Mac-only.

The platform labels in the JSON describe design applicability, not a claim that any kit or converted game was device-tested.

## Catalog maintenance

`resources` contains four source-verified zero-required-payment entries. `unverified_candidates` is excluded from that count and from automated selection. `cost.model` distinguishes public browsing from zero-price asset downloads. License restrictions, verification sources and converter limitations are recorded per entry. No downloading automation is included.

Validate JSON syntax with `python3 -m json.tool data/free-game-ux-resources.json >/dev/null` from the repository root. Recheck costs and terms before obtaining external files.
