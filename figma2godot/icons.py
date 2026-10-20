"""Theme icons that Godot draws from textures: toggle switch and slider knob.

Godot's default CheckButton and slider-grabber icons are light-colored and ignore
the theme, so a toggle drawn red in Figma would render as a pale default switch.
These are rasterised here (standard library only, 4x supersampled for smooth
edges) in the colors of each mode and written as PNGs next to the theme.
"""
import os
import struct
import zlib

SS = 4  # supersampling factor


def _png(path, w, h, rgba):
    raw = b"".join(b"\x00" + bytes(rgba[y * w * 4:(y + 1) * w * 4]) for y in range(h))
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _raster(w, h, shade):
    """shade(x, y) -> (r, g, b, a) floats or None, sampled at SSxSS per pixel."""
    out = bytearray()
    n = SS * SS
    for py in range(h):
        for px in range(w):
            ar = ag = ab = aa = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    c = shade(px + (sx + 0.5) / SS, py + (sy + 0.5) / SS)
                    if c:
                        ar += c[0] * c[3]; ag += c[1] * c[3]; ab += c[2] * c[3]; aa += c[3]
            if aa > 0:
                out += bytes([round(255 * ar / aa), round(255 * ag / aa),
                              round(255 * ab / aa), round(255 * aa / n)])
            else:
                out += b"\x00\x00\x00\x00"
    return out


def _in_pill(x, y, w, h, inset=0.0):
    r = h / 2 - inset
    cx0, cx1, cy = h / 2, w - h / 2, h / 2
    if cx0 <= x <= cx1:
        return abs(y - cy) <= r
    cx = cx0 if x < cx0 else cx1
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def toggle_icon(path, on, track_on, track_off, border, knob, alpha=1.0, w=56, h=32):
    """A switch: a pill track and a round knob (right when on, left when off)."""
    kr = h / 2 - 4
    kx = (w - h / 2) if on else (h / 2)
    def shade(x, y):
        if (x - kx) ** 2 + (y - h / 2) ** 2 <= kr * kr:
            return knob[:3] + (alpha,)
        if _in_pill(x, y, w, h):
            if not _in_pill(x, y, w, h, inset=1.0):
                return border[:3] + (alpha,)
            return (track_on if on else track_off)[:3] + (alpha,)
        return None
    _png(path, w, h, _raster(w, h, shade))


def knob_icon(path, color, alpha=1.0, d=28):
    r = d / 2
    def shade(x, y):
        return color[:3] + (alpha,) if (x - r) ** 2 + (y - r) ** 2 <= r * r else None
    _png(path, d, d, _raster(d, d, shade))


def write_mode_icons(icon_dir, mode_slug, colors):
    """Write this mode's icons; return {icon_key: filename}.

    colors: dict with button, quiet, border, text (rgba tuples)."""
    os.makedirs(icon_dir, exist_ok=True)
    files = {}
    def tog(key, on, alpha=1.0):
        name = "toggle_%s_%s.png" % (mode_slug, key)
        toggle_icon(os.path.join(icon_dir, name), on, colors["button"], colors["quiet"],
                    colors["border"], colors["text"], alpha)
        files[key] = name
    tog("on", True); tog("off", False)
    tog("on_disabled", True, 0.4); tog("off_disabled", False, 0.4)
    for key, alpha in (("knob", 1.0), ("knob_disabled", 0.4)):
        name = "slider_%s_%s.png" % (mode_slug, key)
        knob_icon(os.path.join(icon_dir, name), colors["text"], alpha)
        files[key] = name
    return files
