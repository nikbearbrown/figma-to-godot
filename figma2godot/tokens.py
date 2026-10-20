"""Figma variables -> per-mode token lookup, and the Godot Theme writer."""
from .util import (parse_color, color_expr, lighten, darken, with_alpha, num,
                   slug)

# Theme types whose look comes straight from the roles below.

# Fallbacks used when a design has no variable for a role. Every use is
# reported, so a missing token never silently becomes a magic color.
DEFAULT_COLORS = {
    "bg": "#16161D", "panel": "#24242C", "text": "#E8E8EC",
    "text-muted": "#8A8A96", "button": "#3B5BDB", "button-text": "#FFFFFF",
    "input": "#1B1B22", "input-text": "#E8E8EC", "border": "#3A3A46",
    "accent": "#5C7CFA",
}
DEFAULT_NUMBERS = {"radius/button": 8, "radius/panel": 12, "radius/input": 6,
                   "font-size/body": 16, "spacing/button-x": 16,
                   "spacing/button-y": 8}


class Tokens:
    def __init__(self, design, report):
        self.report = report
        self.collections = design.get("collections", [])
        # A theme is a mode of a *multi-mode* collection. Single-mode collections
        # (metrics, a shared palette) have one mode, typically named "Value", and
        # must not become themes of their own.
        self.modes = []
        multi = [c for c in self.collections if len(c.get("modes", [])) > 1]
        for col in (multi or self.collections):
            for m in col.get("modes", []):
                if m not in self.modes:
                    self.modes.append(m)
        if not self.modes:
            self.modes = [design.get("defaultMode", "Default")]
        self.default_mode = design.get("defaultMode", self.modes[0])
        self._vars = {}
        for col in self.collections:
            first = col["modes"][0]
            for v in col.get("variables", []):
                self._vars[v["name"]] = (col["modes"], first, v)
        self._warned = set()

    def has(self, name):
        return name in self._vars

    def raw(self, name, mode):
        if name not in self._vars:
            return None
        modes, first, v = self._vars[name]
        vals = v["values"]
        return vals.get(mode, vals.get(first))

    def color(self, name, mode):
        """A color variable in a mode, as an rgba tuple.

        `name` is a full variable name ("brick/red", "color/panel") or a bare
        role ("panel", meaning "color/panel")."""
        full = name if name in self._vars else (name if name.startswith("color/") else "color/" + name)
        raw = self.raw(full, mode)
        if raw is not None:
            return parse_color(raw)
        return self._fallback_color(full[len("color/"):], mode)

    def _fallback_color(self, role, mode):
        derived = {
            "button-hover": lambda: lighten(self.color("button", mode), 0.12),
            "button-pressed": lambda: darken(self.color("button", mode), 0.15),
            "button-disabled": lambda: with_alpha(self.color("button", mode), 0.4),
        }
        if role in derived:
            return derived[role]()
        if role in DEFAULT_COLORS:
            key = ("color", role)
            if key not in self._warned:
                self._warned.add(key)
                self.report.add("warn", "theme",
                                "no variable 'color/%s'; using built-in default %s"
                                % (role, DEFAULT_COLORS[role]))
            return parse_color(DEFAULT_COLORS[role])
        raise KeyError("unknown color variable color/" + role)

    def button_colors(self, style, mode):
        """normal/hover/pressed/disabled/text colors for a Button style variant.

        Reads color/button-<style> and color/button-<style>-text; hover, pressed
        and disabled come from color/button-<style>-hover etc. when present,
        otherwise they are derived from the base color."""
        base_name = "color/button-%s" % style
        if not self.has(base_name):
            key = ("style", style)
            if key not in self._warned:
                self._warned.add(key)
                self.report.add("warn", "theme", "no variable '%s'; button style %r uses the "
                                "primary button colors" % (base_name, style))
            return None
        base = self.color(base_name, mode)

        def pick(suffix, derive):
            n = "%s-%s" % (base_name, suffix)
            return self.color(n, mode) if self.has(n) else derive(base)
        text_name = base_name + "-text"
        return {
            "normal": base,
            "hover": pick("hover", lambda c: lighten(c, 0.12)),
            "pressed": pick("pressed", lambda c: darken(c, 0.15)),
            "disabled": pick("disabled", lambda c: with_alpha(c, 0.4)),
            "text": self.color(text_name, mode) if self.has(text_name) else self.color("button-text", mode),
        }

    def number(self, name, mode):
        raw = self.raw(name, mode)
        if raw is not None:
            return float(raw)
        return float(DEFAULT_NUMBERS.get(name, 0))

    def body_size(self, mode=None):
        return int(self.number("font-size/body", mode or self.default_mode))


class StyleBox:
    """Accumulates StyleBoxFlat sub-resources for one theme file."""

    def __init__(self):
        self.items = []

    def flat(self, bg, radius, border=None, border_w=0, margins=None):
        sid = "StyleBoxFlat_%d" % (len(self.items) + 1)
        lines = ["bg_color = " + color_expr(bg)]
        if margins:
            l, t, r, b = margins
            lines += ["content_margin_left = %s" % num(l),
                      "content_margin_top = %s" % num(t),
                      "content_margin_right = %s" % num(r),
                      "content_margin_bottom = %s" % num(b)]
        if border is not None and border_w:
            lines += ["border_width_left = %s" % num(border_w),
                      "border_width_top = %s" % num(border_w),
                      "border_width_right = %s" % num(border_w),
                      "border_width_bottom = %s" % num(border_w),
                      "border_color = " + color_expr(border)]
        if radius:
            for c in ("top_left", "top_right", "bottom_right", "bottom_left"):
                lines.append("corner_radius_%s = %d" % (c, round(radius)))
        self.items.append((sid, lines))
        return sid


def build_theme(tokens, mode, variations, icons=None):
    """Return the text of theme_<mode>.tres.

    `variations` is the registry collected while converting scenes: each entry
    becomes a Godot theme type variation so a frame bound to `color/panel`
    re-colors itself when the theme (mode) is swapped.
    """
    sb = StyleBox()
    res = []
    icons = icons or {}  # key -> res:// path of a generated texture
    ext = []             # (id, path) for the .tres header
    def icon(theme_type, item, key):
        if key in icons:
            rid = "icon_%s" % len(ext)
            ext.append((rid, icons[key]))
            res.append('%s/icons/%s = ExtResource("%s")' % (theme_type, item, rid))
    c = lambda role: tokens.color(role, mode)  # noqa: E731
    n = lambda name: tokens.number(name, mode)  # noqa: E731

    bx, by = n("spacing/button-x"), n("spacing/button-y")
    rb, ri, rp = n("radius/button"), n("radius/input"), n("radius/panel")
    margins = (bx, by, bx, by)

    res.append("default_font_size = %d" % tokens.body_size(mode))

    # Labels
    res.append("Label/colors/font_color = " + color_expr(c("text")))

    # Buttons (Button, OptionButton share look)
    states = [("normal", "button"), ("hover", "button-hover"),
              ("pressed", "button-pressed"), ("disabled", "button-disabled")]
    for typ in ("Button", "OptionButton"):
        for st, role in states:
            sid = sb.flat(c(role), rb, margins=margins)
            res.append("%s/styles/%s = SubResource(\"%s\")" % (typ, st, sid))
        res.append("%s/colors/font_color = %s" % (typ, color_expr(c("button-text"))))
        res.append("%s/colors/font_hover_color = %s" % (typ, color_expr(c("button-text"))))
        res.append("%s/colors/font_pressed_color = %s" % (typ, color_expr(c("button-text"))))
        res.append("%s/colors/font_disabled_color = %s" % (typ, color_expr(c("text-muted"))))
    # CheckButton / CheckBox inherit Button's styles in Godot; without these
    # overrides a toggle renders as a filled blue button.
    clear = sb.flat((0, 0, 0, 0), 0, margins=(4, 4, 4, 4))
    for typ in ("CheckButton", "CheckBox"):
        for st in ("normal", "hover", "pressed", "hover_pressed", "disabled"):
            res.append("%s/styles/%s = SubResource(\"%s\")" % (typ, st, clear))
        res.append("%s/colors/font_color = %s" % (typ, color_expr(c("text"))))
        res.append("%s/colors/font_hover_color = %s" % (typ, color_expr(c("text"))))
        res.append("%s/colors/font_pressed_color = %s" % (typ, color_expr(c("text"))))
        res.append("%s/colors/font_hover_pressed_color = %s" % (typ, color_expr(c("text"))))
    for item, key in (("checked", "on"), ("unchecked", "off"), ("checked_disabled", "on_disabled"),
                      ("unchecked_disabled", "off_disabled")):
        icon("CheckButton", item, key)

    # Links (a LinkButton with a uri, e.g. a donate or support link)
    for st in ("font_color", "font_hover_color", "font_pressed_color", "font_focus_color"):
        res.append("LinkButton/colors/%s = %s" % (st, color_expr(c("accent"))))

    # Inputs
    sid = sb.flat(c("input"), ri, border=c("border"), border_w=1,
                  margins=(10, 6, 10, 6))
    res.append("LineEdit/styles/normal = SubResource(\"%s\")" % sid)
    res.append("LineEdit/colors/font_color = " + color_expr(c("input-text")))
    res.append("LineEdit/colors/font_placeholder_color = " + color_expr(c("text-muted")))

    # Panels
    sid = sb.flat(c("panel"), rp, border=c("border"), border_w=1)
    for typ in ("Panel", "PanelContainer"):
        res.append("%s/styles/panel = SubResource(\"%s\")" % (typ, sid))

    # Progress + slider
    track = sb.flat(c("input"), ri)
    fill = sb.flat(c("accent"), ri)
    res.append("ProgressBar/styles/background = SubResource(\"%s\")" % track)
    res.append("ProgressBar/styles/fill = SubResource(\"%s\")" % fill)
    res.append("ProgressBar/colors/font_color = " + color_expr(c("text")))
    # A flat stylebox has no intrinsic height; the slider needs margins to get a track.
    s_track = sb.flat(c("input"), 5, border=c("border"), border_w=1, margins=(0, 5, 0, 5))
    s_fill = sb.flat(c("accent"), 5, margins=(0, 5, 0, 5))
    for item, key in (("grabber", "knob"), ("grabber_highlight", "knob"), ("grabber_disabled", "knob_disabled")):
        icon("HSlider", item, key)
    res.append("HSlider/styles/slider = SubResource(\"%s\")" % s_track)
    res.append("HSlider/styles/grabber_area = SubResource(\"%s\")" % s_fill)
    res.append("HSlider/styles/grabber_area_highlight = SubResource(\"%s\")" % s_fill)

    # Variations discovered while converting frames / text
    for name, v in sorted(variations.items()):
        if v["kind"] == "surface":
            bg = _var_color(tokens, v, mode)
            border = None
            bw = v.get("border_width", 0)
            if v.get("border"):
                border = _color_of(tokens, v["border"], mode)
            sid = sb.flat(bg, v.get("radius", 0), border=border, border_w=bw)
            res.append("%s/base_type = &\"%s\"" % (name, v["base"]))
            res.append("%s/styles/panel = SubResource(\"%s\")" % (name, sid))
        elif v["kind"] == "button":
            cols = tokens.button_colors(v["style"], mode)
            if cols is None:
                cols = {"normal": c("button"), "hover": c("button-hover"),
                        "pressed": c("button-pressed"),
                        "disabled": c("button-disabled"), "text": c("button-text")}
            res.append("%s/base_type = &\"Button\"" % name)
            for st in ("normal", "hover", "pressed", "disabled"):
                sid = sb.flat(cols[st], rb, margins=margins)
                res.append("%s/styles/%s = SubResource(\"%s\")" % (name, st, sid))
            for fc in ("font_color", "font_hover_color", "font_pressed_color"):
                res.append("%s/colors/%s = %s" % (name, fc, color_expr(cols["text"])))
            res.append("%s/colors/font_disabled_color = %s" % (name, color_expr(c("text-muted"))))
        elif v["kind"] == "text":
            col = _var_color(tokens, v, mode)
            res.append("%s/base_type = &\"%s\"" % (name, v["base"]))
            res.append("%s/colors/font_color = %s" % (name, color_expr(col)))

    out = ["[gd_resource type=\"Theme\" load_steps=%d format=3]" % (len(sb.items) + len(ext) + 1), ""]
    for rid, path in ext:
        out.append('[ext_resource type="Texture2D" path="%s" id="%s"]' % (path, rid))
    if ext:
        out.append("")
    for sid, lines in sb.items:
        out.append("[sub_resource type=\"StyleBoxFlat\" id=\"%s\"]" % sid)
        out += lines
        out.append("")
    out.append("[resource]")
    out += res
    out.append("")
    return "\n".join(out)


def _color_of(tokens, ref, mode):
    if ref.get("var"):
        return tokens.color(ref["var"], mode) if tokens.has(ref["var"]) \
            else parse_color(ref["color"])
    return parse_color(ref["color"])


def _var_color(tokens, v, mode):
    return _color_of(tokens, {"var": v.get("var"), "color": v["color"]}, mode)


def mode_file(mode):
    return "theme_%s.tres" % slug(mode).lower()
