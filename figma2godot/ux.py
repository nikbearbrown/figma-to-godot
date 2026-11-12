"""Game UX: read the tags in layer names, work out the focus graph, lint the design.

A Figma file says what a screen looks like. A game also needs to know what each
control does, where controller focus starts and how it moves, which text is a
translatable string, and which platform the screen is for. That intent is written
in the layer name as tags, so every tool that can read a layer name can read it:

    Play [action=start_game] [focus=first] [key=menu.play]

`prepare()` strips the tags (the converter never sees them), `lint()` checks the
design against rules/game-ux.json, and `focus_graph()` gives every control its
neighbors: from tags where the designer set them, from layout where not (flagged).
"""
import json
import os
import re

from .util import parse_color

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rules", "game-ux.json")

TAG = re.compile(r"\s*\[([A-Za-z_]+)(?:\s*=\s*([^\]]*))?\]")
KNOWN_TAGS = {
    "action", "focus", "up", "down", "left", "right", "key", "platform", "safe", "kind",
    "prompt", "confirm", "undo", "register", "challenge",
}
# Godot classes a player can move focus to.
FOCUSABLE = {"Button", "LinkButton", "CheckButton", "CheckBox", "OptionButton", "HSlider", "LineEdit"}
# What the screen's root script emits for each class (see figma_screen.gd).
SIGNALS = {
    "Button": ("pressed", "action(id, source)"),
    "LinkButton": ("pressed", "action(id, source)"),
    "CheckButton": ("toggled", "value_changed(id, on: bool, source)"),
    "CheckBox": ("toggled", "value_changed(id, on: bool, source)"),
    "OptionButton": ("item_selected", "value_changed(id, index: int, source)"),
    "HSlider": ("value_changed", "value_changed(id, value: float, source)"),
    "LineEdit": ("text_submitted", "value_changed(id, text: String, source)"),
}
LABEL = {"normative": "failure", "platform": "concern", "heuristic": "concern", "house": "deviation"}
DEFAULT_NAME = re.compile(r"^(Frame|Group|Rectangle|Ellipse|Vector|Line|Text|Component|Instance|Section|Polygon|Star|Image|Slice)\s*\d*$")
DESTRUCTIVE = re.compile(r"\b(delete|erase|reset|wipe|overwrite|discard|abandon|quit|exit|buy|purchase|spend|sell)\b", re.I)
BUTTON_IN_TEXT = re.compile(r"\b(press|hold|tap|push)\s+(the\s+)?(A|B|X|Y|LB|RB|LT|RT|L1|R1|L2|R2|Start|Select|Enter|Space|Esc|Escape|[EFQR])\b|\((A|B|X|Y)\)", re.I)
SIDES = ("up", "down", "left", "right")


def load_rules(path=RULES_PATH):
    with open(path) as f:
        data = json.load(f)
    data["by_id"] = {r["id"]: r for r in data["rules"]}
    return data


def parse_name(name):
    """'Play [action=start_game] [focus=first]' -> ('Play', {'action': 'start_game', 'focus': 'first'})"""
    tags = {}
    for m in TAG.finditer(name or ""):
        tags[m.group(1).lower()] = (m.group(2) or "yes").strip()
    clean = TAG.sub("", name or "").strip()
    return (clean or "Node"), tags


def snake(text):
    s = re.sub(r"[^0-9A-Za-z]+", "_", text or "").strip("_").lower()
    return s or "x"


def classify(n):
    """The Godot class a node becomes, without the converter's reporting side effects."""
    from .scene import WIDGETS  # late import: scene.py does not depend on this module
    if n.get("godotType"):
        return n["godotType"]
    t = n.get("type")
    if t == "TEXT":
        return "Label"
    if t in ("INSTANCE", "COMPONENT"):
        label = ((n.get("component") or "") + " " + n.get("name", "")).lower().replace("=", " ")
        for pat, cls in WIDGETS:
            if re.search(pat, label):
                return cls
    return None


# ------------------------------------------------------------------ geometry

def _measure(n):
    """Width and height of a node; estimated where the export gives none. Returns (w, h, exact)."""
    w, h = n.get("width"), n.get("height")
    lay = n.get("layout") or {}
    kids = [(_measure(c), c) for c in n.get("children") or []]
    exact = w is not None and h is not None
    if w is None or h is None:
        if n.get("type") == "TEXT" or (n.get("text") and not kids):
            t = n.get("text") or {}
            size = t.get("size") or 16
            ew, eh = len(t.get("characters", "")) * size * 0.55, size * 1.3
        elif kids and lay.get("mode") in ("VERTICAL", "HORIZONTAL"):
            pad = lay.get("padding") or [0, 0, 0, 0]
            gap = lay.get("spacing", 0) * max(0, len(kids) - 1)
            ws, hs = [k[0][0] for k in kids], [k[0][1] for k in kids]
            if lay["mode"] == "VERTICAL":
                ew, eh = max(ws) + pad[0] + pad[2], sum(hs) + gap + pad[1] + pad[3]
            else:
                ew, eh = sum(ws) + gap + pad[0] + pad[2], max(hs) + pad[1] + pad[3]
        else:
            ew, eh = 200, 44
        w = ew if w is None else w
        h = eh if h is None else h
    n["_size"] = (w, h, exact)
    return w, h, exact


def _place(n, ox, oy, exact):
    """Give every node an absolute rectangle in frame coordinates: n['_abs'] = (x, y, w, h, exact)."""
    w, h, size_exact = n["_size"]
    n["_abs"] = (ox, oy, w, h, exact and size_exact)
    lay = n.get("layout") or {}
    kids = n.get("children") or []
    auto = lay.get("mode") in ("VERTICAL", "HORIZONTAL")
    have_xy = all(c.get("x") is not None and c.get("y") is not None for c in kids)
    if kids and auto and not have_xy:
        pad = lay.get("padding") or [0, 0, 0, 0]
        cx, cy = ox + pad[0], oy + pad[1]
        for c in kids:
            cw, ch, _ = c["_size"]
            _place(c, cx, cy, False)
            if lay["mode"] == "VERTICAL":
                cy += ch + lay.get("spacing", 0)
            else:
                cx += cw + lay.get("spacing", 0)
    else:
        for c in kids:
            _place(c, ox + (c.get("x") or 0), oy + (c.get("y") or 0), exact and c.get("x") is not None)


# -------------------------------------------------------------------- prepare

def prepare(design, default_platform="pc", rules=None):
    """Strip tags from every layer name and annotate the design in place.

    Returns one dict per frame: platform, kind, safe mode, the focusable controls in
    reading order, the strings, and the tags that were not understood."""
    rules = rules or load_rules()
    out = []
    for frame in design.get("frames", []):
        name, tags = parse_name(frame.get("name", ""))
        frame["name"], frame["_tags"] = name, tags
        platform = tags.get("platform", default_platform).lower()
        if platform not in rules["platforms"]:
            platform_note = "platform %r is not one of %s; %s used" % (platform, ", ".join(rules["platforms"]), default_platform)
            platform = default_platform
        else:
            platform_note = None
        profile = rules["platforms"][platform]
        fx = {"frame": frame, "name": name, "platform": platform, "profile": profile,
              "kind": tags.get("kind", "screen").lower(), "safe": tags.get("safe", profile["safe"]).lower(),
              "controls": [], "texts": [], "prompts": [], "registers": [], "unknown_tags": [], "nodes": [],
              "notes": [platform_note] if platform_note else []}
        _measure(frame)
        _place(frame, 0, 0, True)

        def walk(n, parent, bleed):
            if n is not frame:
                n["name"], n["_tags"] = parse_name(n.get("name", ""))
            t = n["_tags"]
            for k in t:
                if k not in KNOWN_TAGS:
                    fx["unknown_tags"].append((n["name"], k))
            n["_parent_auto"] = bool(parent is not None and (parent.get("layout") or {}).get("mode") in ("VERTICAL", "HORIZONTAL"))
            n["_bleed"] = bleed or t.get("safe") == "bleed"
            cls = classify(n)
            n["_cls"] = cls
            fx["nodes"].append(n)
            if t.get("focus") != "none" and cls in FOCUSABLE:
                fx["controls"].append(n)
            if cls == "Label" or (cls in ("Button", "LinkButton", "CheckButton", "CheckBox") and _label(n)):
                fx["texts"].append(n)
            if t.get("prompt"):
                fx["prompts"].append(n)
            if t.get("register"):
                fx["registers"].append((n["name"], t["register"]))
            if cls in FOCUSABLE and n.get("properties"):
                return  # a widget's internals are not separate nodes
            for c in n.get("children") or []:
                walk(c, n, n["_bleed"])

        walk(frame, None, False)
        fx["controls"].sort(key=lambda c: (round(c["_abs"][1] / 8), c["_abs"][0]))  # reading order
        out.append(fx)
    return out


def _label(n):
    p = n.get("properties") or {}
    return p.get("label") or (n.get("text") or {}).get("characters") or ""


def text_of(n):
    return (n.get("text") or {}).get("characters", "") if n.get("_cls") == "Label" else _label(n)


def action_id(n):
    """(id, generated?) for a control: its [action=] tag, or one made from its name."""
    a = (n.get("_tags") or {}).get("action")
    return (snake(a), False) if a else (snake(n["name"]), True)


def string_key(fx, n):
    """(key, generated?) for a visible text. [key=none] means it is not a translatable string."""
    k = (n.get("_tags") or {}).get("key")
    if k:
        return (None, False) if k.lower() == "none" else (k, False)
    return "%s.%s" % (snake(fx["name"]), snake(n["name"])), True


# ----------------------------------------------------------------- focus graph

def focus_graph(fx):
    """Neighbors for every control. Explicit tags win; the rest come from layout and are flagged.

    Returns {"first": index or None, "first_generated": bool,
             "edges": [{side: (index, "tag"|"generated")}], "problems": [text]}"""
    cs = fx["controls"]
    problems = []
    by_name = {}
    for i, c in enumerate(cs):
        by_name.setdefault(c["name"].lower(), i)
    firsts = [i for i, c in enumerate(cs) if c["_tags"].get("focus") == "first"]
    if len(firsts) > 1:
        problems.append("%d controls are tagged [focus=first]; %r is used" % (len(firsts), cs[firsts[0]]["name"]))
    first = firsts[0] if firsts else (0 if cs else None)

    def center(c):
        x, y, w, h, _ = c["_abs"]
        return x + w / 2, y + h / 2

    def nearest(i, side):
        cx, cy = center(cs[i])
        best, best_score = None, None
        for j, o in enumerate(cs):
            if j == i:
                continue
            ox, oy = center(o)
            dx, dy = ox - cx, oy - cy
            along, across = {"up": (-dy, dx), "down": (dy, dx), "left": (-dx, dy), "right": (dx, dy)}[side]
            if along <= 1 or abs(across) > along * 2 + 1:
                continue  # not in that direction, or far more sideways than forward
            score = along + 2 * abs(across)
            if best_score is None or score < best_score:
                best, best_score = j, score
        return best

    edges = []
    for i, c in enumerate(cs):
        e = {}
        for side in SIDES:
            want = c["_tags"].get(side)
            if want:
                j = by_name.get(want.lower())
                if j is None:
                    problems.append("%r says [%s=%s] but no control on this screen is called %r" % (c["name"], side, want, want))
                else:
                    e[side] = (j, "tag")
                    continue
            j = nearest(i, side)
            if j is not None:
                e[side] = (j, "generated")
        edges.append(e)
    return {"first": first, "first_generated": bool(cs) and not firsts, "edges": edges, "problems": problems}


def unreachable(graph, count):
    if graph["first"] is None:
        return []
    seen, todo = {graph["first"]}, [graph["first"]]
    while todo:
        i = todo.pop()
        for j, _ in graph["edges"][i].values():
            if j not in seen:
                seen.add(j)
                todo.append(j)
    return [i for i in range(count) if i not in seen]


# ------------------------------------------------------------------------ lint

def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def contrast(a, b):
    la, lb = (0.2126 * _lin(c[0]) + 0.7152 * _lin(c[1]) + 0.0722 * _lin(c[2]) for c in (a, b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _resolve(ref, tokens, mode, fallback_role):
    if ref and ref.get("var") and tokens.has(ref["var"]):
        return tokens.color(ref["var"], mode)
    if ref and ref.get("color"):
        return parse_color(ref["color"])
    return tokens.color(fallback_role, mode)


def lint(design, frames, tokens, rules=None):
    """Findings for a prepared design. Each: {rule, label, where, msg}. Also fills fx['graph'] and fx['strings']."""
    rules = rules or load_rules()
    found = []

    def add(rule, where, msg):
        r = rules["by_id"][rule]
        found.append({"rule": rule, "label": LABEL[r["tier"]], "title": r["title"], "where": where, "msg": msg})

    labels_by_action = {}
    any_states = False
    for fx in frames:
        frame, prof = fx["frame"], fx["profile"]
        fw, fh = frame["_abs"][2], frame["_abs"][3]
        scale = (min(fw, fh) / prof["text_min_at"]) if prof["text_min_at"] else 1.0
        text_min = prof["text_min"] * scale
        fx["text_min"] = round(text_min, 1)
        for note in fx["notes"]:
            found.append({"rule": "", "label": "note", "title": "", "where": fx["name"], "msg": note})
        for nm, tag in fx["unknown_tags"]:
            found.append({"rule": "", "label": "note", "title": "", "where": "%s/%s" % (fx["name"], nm),
                          "msg": "tag [%s] is not one this tool reads (%s); ignored" % (tag, ", ".join(sorted(KNOWN_TAGS)))})

        # parents, for the fill behind a text
        parent_of = {}
        for n in fx["nodes"]:
            for c in n.get("children") or []:
                parent_of[id(c)] = n

        def fill_behind(n):
            p = parent_of.get(id(n))
            while p is not None:
                if p.get("fill"):
                    return p["fill"]
                p = parent_of.get(id(p))
            return None

        # An auto-layout screen gets a safe-area container in Godot, so its content cannot leave the
        # safe area there. What can go wrong is the Figma frame no longer matching what ships.
        root_lay = frame.get("layout") or {}
        root_auto = root_lay.get("mode") in ("VERTICAL", "HORIZONTAL")
        if fx["safe"] == "title" and root_auto:
            pad = root_lay.get("padding") or [0, 0, 0, 0]
            ix, iy = fw * prof["safe_inset"], fh * prof["safe_inset"]
            short = [side for side, v, need in zip(("left", "top", "right", "bottom"), pad, (ix, iy, ix, iy)) if v < need - 0.5]
            if short:
                add("GUX-SAFE-TITLE", fx["name"], "padding on the %s is under the title-safe inset (%g px at the sides, %g px top and bottom). Godot will inset the content at run time, so the Figma frame will not match what ships: add the padding in Figma"
                    % (", ".join(short), round(ix), round(iy)))
        fx["strings"] = []
        text_ids = {id(x) for x in fx["texts"]}
        control_ids = {id(x) for x in fx["controls"]}
        for n in fx["nodes"]:
            where = "%s/%s" % (fx["name"], n["name"])
            cls, tags = n.get("_cls"), n["_tags"]
            if n is not frame and DEFAULT_NAME.match(n["name"]):
                add("GUX-LAYER-NAMED", where, "still has Figma's default name; say what it is")
            for kind in ("fill", "stroke"):
                ref = n.get(kind)
                if ref and ref.get("color") and not ref.get("var") and not ref.get("gradient"):
                    add("GUX-COLOR-VAR", where, "%s %s is a loose color; bind it to a variable" % (kind, ref["color"]))
            if id(n) in text_ids:
                t = n.get("text") or {}
                size = t.get("size")
                if size and size < text_min:
                    add("GUX-TEXT-MIN", where, "font size %g is under the %s minimum of %g for a %g-high frame; and font size is not body height, so measure the rendered text too"
                        % (size, fx["platform"], round(text_min, 1), min(fw, fh)))
                col = t.get("color")
                if col and col.get("color") and not col.get("var"):
                    add("GUX-COLOR-VAR", where, "text color %s is a loose color; bind it to a variable" % col["color"])
                if cls == "Label" and t.get("characters"):
                    bg_ref = fill_behind(n)
                    need = 3.0 if (size or 0) >= 24 else 4.5
                    for mode in tokens.modes:
                        fg = _resolve(col, tokens, mode, "text")
                        bg = _resolve(bg_ref, tokens, mode, "bg")
                        if fg[3] < 0.99 or bg[3] < 0.99:
                            continue  # translucent: the ratio depends on what is underneath
                        r = contrast(fg, bg)
                        if r < need:
                            add("GUX-CONTRAST", where, "%.2f:1 in mode %s; needs %g:1" % (r, mode, need))
                words = text_of(n)
                if words and BUTTON_IN_TEXT.search(words) and not tags.get("prompt"):
                    add("GUX-PROMPT-SWAP", where, "the text %r names a button; use a prompt layer tagged [prompt=...] so the glyph can follow the player's device" % words)
                key, generated = string_key(fx, n)
                if key and words:
                    fx["strings"].append({"key": key, "text": words, "node": n["name"], "generated": generated})
                    if generated:
                        add("GUX-STRING-KEY", where, "no [key=]; %r was generated" % key)
            if cls in FOCUSABLE:
                if id(n) in control_ids or tags.get("focus") == "none":
                    aid, generated = action_id(n)
                    if generated:
                        add("GUX-ACTION-NAMED", where, "no [action=]; %r was generated from the layer name" % aid)
                    lab = _label(n)
                    if lab:
                        labels_by_action.setdefault(aid, {}).setdefault(lab, []).append(where)
                    if (DESTRUCTIVE.search(aid.replace("_", " ")) or DESTRUCTIVE.search(lab)) and not (tags.get("confirm") or tags.get("undo")):
                        add("GUX-CONFIRM-DESTRUCTIVE", where, "looks destructive (%s); tag it [confirm=<dialog>] or [undo=yes], or say why neither is needed" % (lab or aid))
                if fx["kind"] != "hud" and n is not frame and not n["_parent_auto"]:
                    add("GUX-AUTOLAYOUT", where, "is placed by hand inside a frame with no auto layout; it becomes fixed pixel offsets in Godot")
                x, y, w, h, exact = n["_abs"]
                if prof["target_min"] and exact and (w < prof["target_min"] or h < prof["target_min"]):
                    add("GUX-TARGET-MIN", where, "%g by %g; needs %g by %g on %s" % (w, h, prof["target_min"], prof["target_min"], fx["platform"]))
                if "states" in n:
                    any_states = True
                    if not any(re.search(r"focus", s, re.I) for s in n["states"]):
                        add("GUX-FOCUS-STATE", where, "component states are %s; none is a focus state" % (", ".join(n["states"]) or "none"))
            if fx["safe"] == "title" and not root_auto and (cls == "Label" or cls in FOCUSABLE) and not n["_bleed"]:
                x, y, w, h, exact = n["_abs"]
                ix, iy = fw * prof["safe_inset"], fh * prof["safe_inset"]
                if exact and (x < ix - 0.5 or y < iy - 0.5 or x + w > fw - ix + 0.5 or y + h > fh - iy + 0.5):
                    add("GUX-SAFE-TITLE", where, "sits outside the title-safe area (%g px in from the sides, %g px from top and bottom of a %g by %g frame)" % (round(ix), round(iy), fw, fh))

        g = focus_graph(fx)
        fx["graph"] = g
        if fx["controls"]:
            if g["first_generated"]:
                add("GUX-FOCUS-FIRST", fx["name"], "no control is tagged [focus=first]; %r (first in reading order) was chosen" % fx["controls"][g["first"]]["name"])
            for p in g["problems"]:
                add("GUX-FOCUS-REACH", fx["name"], p)
            for i in unreachable(g, len(fx["controls"])):
                add("GUX-FOCUS-REACH", "%s/%s" % (fx["name"], fx["controls"][i]["name"]), "cannot be reached from the first control with directional input")
    for aid, labs in labels_by_action.items():
        if len(labs) > 1:
            add("GUX-CONSISTENCY", "action %s" % aid, "has %d different labels: %s" % (len(labs), "; ".join("%r in %s" % (k, v[0]) for k, v in sorted(labs.items()))))
    if not any_states and any(fx["controls"] for fx in frames):
        found.append({"rule": "GUX-FOCUS-STATE", "label": "note", "title": rules["by_id"]["GUX-FOCUS-STATE"]["title"], "where": design.get("file", "design"),
                      "msg": "not checked: the export lists no component states. Export with exporter/export.js, or check by eye that every control has a focus state."})
    return found
