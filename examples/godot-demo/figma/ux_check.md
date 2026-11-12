# UX check: Game UI example

Measured in Godot 4.7.2-stable (official) by tests/godot_ux_check.gd.

- **MainMenu** (pc, 1280 by 720): 3 of 3 tagged controls reachable; smallest text at most 26.0 px (minimum 12.0); safe area none.
- **Settings** (pc, 1280 by 720): 6 of 6 tagged controls reachable; smallest text at most 26.0 px (minimum 12.0); safe area none.
- **HUD** (pc, 1280 by 720): 0 of 0 tagged controls reachable; smallest text at most 26.0 px (minimum 12.0); safe area none.

No failures.

## Not proven

- MainMenu: the smallest text (Content/Play) is at most 26.0 px tall against a minimum of 12.0. That passes the screen but is an upper bound: measure a screenshot to be sure of body height.
- Settings: the smallest text (Content/Settings Panel/Margin/Box/Fullscreen) is at most 26.0 px tall against a minimum of 12.0. That passes the screen but is an upper bound: measure a screenshot to be sure of body height.
- HUD: the smallest text (Hint) is at most 26.0 px tall against a minimum of 12.0. That passes the screen but is an upper bound: measure a screenshot to be sure of body height.
