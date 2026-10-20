"""Small helpers: colors, names, Godot string escaping."""
import re


def parse_color(s):
    """'#RGB', '#RRGGBB' or '#RRGGBBAA' -> (r, g, b, a) floats 0..1."""
    h = s.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        raise ValueError("bad color %r" % s)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return (r, g, b, a)


def as_float(v, default=0.0):
    """Figma component properties arrive as strings ("0.7"); coerce safely."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def truthy(v):
    """Figma variant booleans arrive as "True"/"False" strings; "False" must be false."""
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "on", "1")
    return bool(v)


def num(x):
    x = as_float(x)
    t = ("%.4f" % x).rstrip("0").rstrip(".")
    return t if t not in ("", "-0") else "0"


def color_expr(c):
    return "Color(%s)" % ", ".join(num(v) for v in c)


def mix(c, other, t):
    """Blend rgb of c toward other by t, keep alpha."""
    return tuple(c[i] + (other[i] - c[i]) * t for i in range(3)) + (c[3],)


def lighten(c, t):
    return mix(c, (1, 1, 1, 1), t)


def darken(c, t):
    return mix(c, (0, 0, 0, 1), t)


def with_alpha(c, a):
    return c[:3] + (a,)


def slug(s):
    return re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_") or "x"


def node_name(s):
    """Godot node names may not contain . : @ / " % and must be non-empty."""
    out = re.sub(r'[.:@/"%\x00-\x1f]', "_", s).strip()
    return out or "Node"


def gd_string(s):
    return '"%s"' % (s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))
