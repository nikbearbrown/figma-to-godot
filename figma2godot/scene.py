"""Normalized Figma frames -> Godot .tscn text.

Mapping in one table (full detail in docs/MAPPING.md):

  auto-layout VERTICAL / HORIZONTAL   VBoxContainer / HBoxContainer
  padding                             MarginContainer
  fill / stroke on a frame            Panel / PanelContainer + theme type variation
  no auto-layout                      Control with absolute offsets
  TEXT                                Label
  component "Button", "Toggle" ...    Button, CheckButton, LineEdit, HSlider ...
"""
import re
from .util import node_name, gd_string, num, parse_color, as_float, truthy, slug

# Godot size flags
SHRINK_BEGIN, FILL, EXPAND_FILL, SHRINK_CENTER, SHRINK_END = 0, 1, 3, 4, 8
ALIGN = {"MIN": SHRINK_BEGIN, "CENTER": SHRINK_CENTER, "MAX": SHRINK_END}

# component-name patterns -> Godot class. First match wins.
WIDGETS = [
    (r"progress|health ?bar|meter|loading ?bar", "ProgressBar"),
    (r"slider", "HSlider"),
    (r"toggle|switch", "CheckButton"),
    (r"check ?box|checkbox", "CheckBox"),
    (r"dropdown|select|option ?button|combo", "OptionButton"),
    (r"input|text ?field|textfield|text ?box", "LineEdit"),
    (r"divider|separator", "Separator"),
    (r"icon|image|avatar|thumbnail", "TextureRect"),
    (r"coffee|link", "LinkButton"),
    (r"button|btn|cta", "Button"),
]
# Properties each widget understands; anything else is reported, not silently dropped.
KNOWN_PROPS = {
    "Button": {"label", "style"}, "LinkButton": {"label", "url", "uri"},
    "CheckButton": {"label", "checked"}, "CheckBox": {"label", "checked"},
    "LineEdit": {"placeholder", "value"}, "HSlider": {"value", "max", "step"},
    "ProgressBar": {"value", "max"}, "OptionButton": {"options", "selected", "label"},
}
INTERACTIVE = {"Button", "LinkButton", "CheckButton", "CheckBox", "OptionButton"}


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, where, msg):
        self.items.append((level, where, msg))

    def markdown(self, title):
        out = ["# Import report: %s" % title, ""]
        if not self.items:
            out.append("Nothing was dropped or approximated.")
            return "\n".join(out) + "\n"
        out.append("What the import could not express exactly, and why.\n")
        for lvl in ("error", "warn", "info"):
            rows = [(w, m) for (l, w, m) in self.items if l == lvl]
            if rows:
                out.append("## %s (%d)\n" % (lvl, len(rows)))
                out += ["- `%s`: %s" % (w, m) for w, m in rows]
                out.append("")
        return "\n".join(out)


class GNode:
    def __init__(self, name, typ, parent, props=None, extra_header=""):
        self.name, self.type, self.parent = name, typ, parent
        self.props = props or []
        self.extra = extra_header

    def text(self):
        head = "[node name=%s type=\"%s\"" % (gd_string(self.name), self.type)
        if self.parent is not None:
            head += " parent=%s" % gd_string(self.parent)
        head += "]"
        return "\n".join([head] + self.props) + "\n"


class Converter:
    def __init__(self, tokens, report, res_theme_path, res_asset_root, asset_dir):
        self.tokens, self.report = tokens, report
        self.theme_path = res_theme_path
        self.res_asset_root = res_asset_root
        self.asset_dir = asset_dir
        self.variations = {}  # shared across every scene in the design
        self._fonts_seen = set()

    # ---------------------------------------------------------------- public
    def convert_frame(self, frame):
        self.nodes = []
        self.ext = []  # (type, path, id)
        self.names = {}
        self.where = frame["name"]
        self.ext.append(("Theme", self.theme_path, "1_theme"))
        root_name = node_name(frame["name"])
        root = GNode(root_name, "Control", None, [
            "layout_mode = 3", "anchors_preset = 15", "anchor_right = 1.0",
            "anchor_bottom = 1.0", "grow_horizontal = 2", "grow_vertical = 2",
            'theme = ExtResource("1_theme")'])
        self.nodes.append(root)
        self._used(None, root_name)
        if self._surface(frame):
            self._emit_surface(frame, ".", "Panel", "Background", fullrect=True)
        lay = frame.get("layout", {}) or {}
        if lay.get("mode") in ("VERTICAL", "HORIZONTAL"):
            self._emit_layout_chain(frame, ".", "root", "Content",
                                    surface=False, place=("full", None))
        else:
            for ch in frame.get("children", []):
                self._emit(ch, ".", ("control", None))
        return self._render()

    # --------------------------------------------------------------- helpers
    def _used(self, parent, name):
        s = self.names.setdefault(parent, set())
        base, i = name, 2
        while name in s:
            name = "%s%d" % (base, i)
            i += 1
        s.add(name)
        return name

    def _add(self, parent, name, typ, props):
        name = self._used(parent, node_name(name))
        n = GNode(name, typ, parent, props)
        self.nodes.append(n)
        return n

    def _child_path(self, parent, n):
        return n.name if parent == "." else "%s/%s" % (parent, n.name)

    def _render(self):
        steps = 1 + len(self.ext)
        out = ["[gd_scene load_steps=%d format=3]" % steps, ""]
        for typ, path, rid in self.ext:
            out.append('[ext_resource type="%s" path="%s" id="%s"]' % (typ, path, rid))
        out.append("")
        out += [n.text() for n in self.nodes]
        return "\n".join(out)

    # ----------------------------------------------------------- variations
    def _variation(self, base, kind, color, radius=0, border=None, bw=0):
        var = (color or {}).get("var")
        key = "%s_%s_%s" % (base, kind, (var or color["color"]).replace("/", "_").replace("#", ""))
        key = re.sub(r"[^0-9A-Za-z_]", "_", key)
        if radius:
            key += "_r%d" % round(radius)
        if bw:
            key += "_b%d" % round(bw)
        self.variations.setdefault(key, {
            "base": base, "kind": kind, "var": var, "color": color["color"],
            "radius": radius, "border": border, "border_width": bw})
        return key

    def _variations_for_button(self, style):
        key = "Button_%s" % slug(style).lower()
        self.variations.setdefault(key, {"base": "Button", "kind": "button", "style": style,
                                         "var": None, "color": "#000000"})
        return key

    # ------------------------------------------------------------ placement
    def _place(self, node, ctx, force_flags=None):
        """Lines that position the outermost Godot node for `node`.

        ctx = ("vbox"|"hbox", counter_align)  child of a box container
              ("control", None)               absolute child of a Control
              ("full", None)                  fills its parent
              ("inner", None)                 child of Margin/PanelContainer
        """
        kind, counter = ctx
        w, h = node.get("width"), node.get("height")
        sz = node.get("sizing", {}) or {}
        sh, sv = sz.get("h", "FIXED"), sz.get("v", "FIXED")
        L = []
        if kind == "full":
            return ["layout_mode = 1", "anchors_preset = 15", "anchor_right = 1.0",
                    "anchor_bottom = 1.0", "grow_horizontal = 2", "grow_vertical = 2"]
        if kind == "control":
            x, y = node.get("x", 0), node.get("y", 0)
            return ["layout_mode = 0", "offset_left = %s" % num(x),
                    "offset_top = %s" % num(y),
                    "offset_right = %s" % num(x + (w or 0)),
                    "offset_bottom = %s" % num(y + (h or 0))]
        L.append("layout_mode = 2")
        if kind == "inner":
            return L + ["size_flags_horizontal = 3", "size_flags_vertical = 3"]
        minx = w if (sh == "FIXED" and w) else 0
        miny = h if (sv == "FIXED" and h) else 0
        if minx or miny:
            L.append("custom_minimum_size = Vector2(%s, %s)" % (num(minx), num(miny)))
        horiz = kind == "hbox"
        prim_fill = (sh if horiz else sv) == "FILL"
        cnt_fill = (sv if horiz else sh) == "FILL"
        pflag = EXPAND_FILL if prim_fill else FILL
        cflag = FILL if cnt_fill else ALIGN.get(counter or "MIN", SHRINK_BEGIN)
        hf, vf = (pflag, cflag) if horiz else (cflag, pflag)
        if hf != FILL:
            L.append("size_flags_horizontal = %d" % hf)
        if vf != FILL:
            L.append("size_flags_vertical = %d" % vf)
        return L

    # ------------------------------------------------------------- dispatch
    def _surface(self, n):
        return bool(n.get("fill") or n.get("stroke"))

    def _classify(self, n):
        if n.get("godotType"):
            return n["godotType"]
        t = n["type"]
        if t == "TEXT":
            return "Label"
        if t in ("INSTANCE", "COMPONENT"):
            label = (n.get("component") or "") + " " + n.get("name", "")
            label = label.lower().replace("=", " ")
            for pat, cls in WIDGETS:
                if re.search(pat, label):
                    return cls
            self.report.add("info", "%s/%s" % (self.where, n["name"]),
                            "component %r has no widget mapping; imported as a plain frame "
                            "(tag it with godotType to map it)" % n.get("component"))
            return "Frame"
        if t in ("FRAME", "GROUP", "SECTION"):
            return "Frame"
        if t == "RECTANGLE":
            return "Rect"
        if t == "IMAGE":
            return "TextureRect"
        self.report.add("warn", "%s/%s" % (self.where, n.get("name", "?")),
                        "node type %s is not supported and was skipped" % t)
        return None

    def _emit(self, n, parent, ctx):
        cls = self._classify(n)
        if cls is None:
            return
        for k in ("effects", "rotation", "blend", "mask"):
            if n.get(k):
                self.report.add("warn", "%s/%s" % (self.where, n["name"]),
                                "%s is not imported (Godot Control has no equivalent here)" % k)
        fill = n.get("fill") or {}
        if fill.get("gradient"):
            self.report.add("warn", "%s/%s" % (self.where, n["name"]),
                            "gradient fill approximated by its first stop")
        if cls == "Frame":
            lay = n.get("layout", {}) or {}
            if lay.get("mode") in ("VERTICAL", "HORIZONTAL"):
                self._emit_layout_chain(n, parent, ctx[0], node_name(n["name"]),
                                        surface=self._surface(n), place=ctx)
            elif self._surface(n) or n.get("children"):
                typ = "Panel" if self._surface(n) else "Control"
                gn = self._emit_surface(n, parent, typ, n["name"], ctx=ctx) \
                    if self._surface(n) else self._add(parent, n["name"], "Control",
                                                       self._place(n, ctx))
                for ch in n.get("children", []):
                    self._emit(ch, self._child_path(parent, gn), ("control", None))
            else:
                # An empty frame is a spacer or a gap: keep it, it carries sizing.
                self._add(parent, n["name"], "Control", self._place(n, ctx))
            return
        if cls == "Rect":
            self._emit_surface(n, parent, "Panel", n["name"], ctx=ctx)
            return
        self._emit_widget(n, cls, parent, ctx)

    # --------------------------------------------------------------- frames
    def _emit_surface(self, n, parent, typ, name, ctx=None, fullrect=False):
        fill = n.get("fill") or {"color": "#00000000"}
        stroke = n.get("stroke") or {}
        props = self._place(n, ("full", None) if fullrect else ctx)
        var = self._variation(typ, "surface", fill, n.get("radius", 0),
                              border=stroke if stroke else None,
                              bw=stroke.get("width", 1) if stroke else 0)
        props.append("theme_type_variation = &\"%s\"" % var)
        return self._add(parent, name, typ, props)

    def _emit_layout_chain(self, n, parent, parent_kind, name, surface, place):
        lay = n["layout"]
        vertical = lay["mode"] == "VERTICAL"
        pad = lay.get("padding") or [0, 0, 0, 0]
        has_pad = any(pad)
        chain = []  # (type, name, props)
        if surface:
            chain.append(("PanelContainer", name, "surface"))
        if has_pad:
            chain.append(("MarginContainer", "Margin" if surface else name, "pad"))
        chain.append(("VBoxContainer" if vertical else "HBoxContainer",
                      "Box" if chain else name, "box"))
        cur_parent, ctx = parent, place
        box_path = None
        for i, (typ, nm, role) in enumerate(chain):
            props = self._place(n, ctx)
            if role == "surface":
                fill = n.get("fill") or {"color": "#00000000"}
                stroke = n.get("stroke") or {}
                var = self._variation("PanelContainer", "surface", fill,
                                      n.get("radius", 0),
                                      border=stroke if stroke else None,
                                      bw=stroke.get("width", 1) if stroke else 0)
                props.append("theme_type_variation = &\"%s\"" % var)
            if role == "pad":
                for side, v in zip(("left", "top", "right", "bottom"), pad):
                    props.append("theme_override_constants/margin_%s = %s" % (side, num(v)))
            if role == "box":
                al = lay.get("primaryAlign", "MIN")
                if al == "CENTER":
                    props.append("alignment = 1")
                elif al == "MAX":
                    props.append("alignment = 2")
                elif al in ("SPACE_BETWEEN", "SPACE_EVENLY", "SPACE_AROUND"):
                    self.report.add("warn", "%s/%s" % (self.where, n["name"]),
                                    "primary alignment %s approximated as MIN; add expanding "
                                    "spacers or set the children to FILL" % al)
                sp = lay.get("spacing", 0)
                if sp:
                    props.append("theme_override_constants/separation = %s" % num(sp))
            gn = self._add(cur_parent, nm, typ, props)
            cur_parent = self._child_path(cur_parent, gn)
            ctx = ("inner", None)
        box_path = cur_parent
        kind = "vbox" if vertical else "hbox"
        counter = lay.get("counterAlign", "MIN")
        for ch in n.get("children", []):
            self._emit(ch, box_path, (kind, counter))

    # -------------------------------------------------------------- widgets
    def _label_text(self, n):
        p = n.get("properties", {}) or {}
        if p.get("label"):
            return p["label"]
        if (n.get("text") or {}).get("characters"):
            return n["text"]["characters"]
        for ch in n.get("children", []) or []:
            if ch.get("type") == "TEXT":
                return ch["text"]["characters"]
        return n.get("name", "")

    def _emit_widget(self, n, cls, parent, ctx):
        props = self._place(n, ctx)
        p = n.get("properties", {}) or {}
        typ = cls
        if cls == "Label":
            t = n["text"]
            props.append("text = %s" % gd_string(t["characters"]))
            al = {"LEFT": 0, "CENTER": 1, "RIGHT": 2}.get(t.get("align", "LEFT"), 0)
            if al:
                props.append("horizontal_alignment = %d" % al)
            if t.get("autoResize", "WIDTH_AND_HEIGHT") != "WIDTH_AND_HEIGHT":
                props.append("autowrap_mode = 3")
            if t.get("size") and round(t["size"]) != self.tokens.body_size():
                props.append("theme_override_font_sizes/font_size = %d" % round(t["size"]))
            col = t.get("color")
            if col:
                default_var = "color/text"
                is_default = (col.get("var") == default_var) or (
                    not col.get("var") and
                    parse_color(col["color"]) == self.tokens.color("text", self.tokens.default_mode))
                if not is_default:
                    props.append("theme_type_variation = &\"%s\"" %
                                 self._variation("Label", "text", col))
            if t.get("family") and t["family"] not in self._fonts_seen:
                self._fonts_seen.add(t["family"])
                self.report.add("info", "fonts",
                                "font %r is not imported; Godot uses its default font. Drop the "
                                ".ttf into the project and set it on the theme." % t["family"])
        elif cls == "Button":
            props.append("text = %s" % gd_string(self._label_text(n)))
            style = str(p.get("style", "primary")).strip().lower()
            if style not in ("primary", "default", ""):
                v = self._variations_for_button(style)
                props.append("theme_type_variation = &\"%s\"" % v)
        elif cls == "LinkButton":
            props.append("text = %s" % gd_string(self._label_text(n)))
            # The link's own layout centers its text; a LinkButton has no alignment,
            # so center the control itself instead of stretching it left-aligned.
            if (n.get("layout") or {}).get("primaryAlign") == "CENTER":
                props = [x for x in props if not x.startswith("size_flags_horizontal")]
                props.append("size_flags_horizontal = 4")
            uri = p.get("url") or p.get("uri")
            if uri:
                props.append("uri = %s" % gd_string(str(uri)))
            else:
                self.report.add("warn", "%s/%s" % (self.where, n["name"]),
                                "link has no url property; it will not open anything")
            props.append("underline = 0")
        elif cls in ("CheckButton", "CheckBox"):
            props.append("text = %s" % gd_string(self._label_text(n)))
            if truthy(p.get("checked")):
                props.append("button_pressed = true")
        elif cls == "LineEdit":
            if p.get("placeholder"):
                props.append("placeholder_text = %s" % gd_string(p["placeholder"]))
            if p.get("value"):
                props.append("text = %s" % gd_string(str(p["value"])))
        elif cls == "HSlider":
            props += ["max_value = %s" % num(as_float(p.get("max"), 1)),
                      "step = %s" % num(as_float(p.get("step"), 0.01)),
                      "value = %s" % num(as_float(p.get("value"), 0.5))]
        elif cls == "ProgressBar":
            props += ["max_value = %s" % num(as_float(p.get("max"), 100)),
                      "value = %s" % num(as_float(p.get("value"), 50)),
                      "show_percentage = false"]
        elif cls == "OptionButton":
            opts = p.get("options") or [self._label_text(n)]
            props += ["selected = %d" % int(as_float(p.get("selected"), 0)),
                      "item_count = %d" % len(opts)]
            for i, o in enumerate(opts):
                props += ["popup/item_%d/text = %s" % (i, gd_string(o)),
                          "popup/item_%d/id = %d" % (i, i)]
        elif cls == "Separator":
            horiz_axis = (n.get("width") or 0) >= (n.get("height") or 0)
            typ = "HSeparator" if horiz_axis else "VSeparator"
        elif cls == "TextureRect":
            asset = n.get("asset")
            if asset:
                rid = "tex_%d" % (len(self.ext) + 1)
                self.ext.append(("Texture2D", "%s/%s" % (self.res_asset_root, asset), rid))
                props.append("texture = ExtResource(\"%s\")" % rid)
            else:
                self.report.add("warn", "%s/%s" % (self.where, n["name"]),
                                "image has no exported asset; TextureRect left empty")
            props += ["expand_mode = 1", "stretch_mode = 5"]
        else:
            self.report.add("warn", "%s/%s" % (self.where, n["name"]),
                            "unknown godotType %r; node skipped" % cls)
            return
        # Label size of a widget comes from its first text child (the exporter
        # keeps it as `text` on property-bearing instances).
        wt = n.get("text") or {}
        if cls in ("Button", "LinkButton", "CheckButton", "CheckBox") and wt.get("size") \
                and round(wt["size"]) != self.tokens.body_size():
            props.append("theme_override_font_sizes/font_size = %d" % round(wt["size"]))
        unknown = set(p) - KNOWN_PROPS.get(cls, set(p))
        if unknown:
            self.report.add("info", "%s/%s" % (self.where, n["name"]),
                            "component properties not used by a Godot %s: %s"
                            % (cls, ", ".join(sorted(unknown))))
        gn = self._add(parent, n["name"], typ, props)
        # Text children of widgets (a Button's label) are consumed above; other
        # children of a widget cannot be represented and are reported.
        if cls in INTERACTIVE:
            return
        if n.get("children") and cls not in ("Label",):
            self.report.add("info", "%s/%s" % (self.where, n["name"]),
                            "children of a %s are not imported" % cls)
