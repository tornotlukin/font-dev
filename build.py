# build.py — SVG -> UFO -> OTF
# Usage: python build.py
import os, re, sys, subprocess
from pathlib import Path
from ufoLib2 import Font
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Identity
from svgpathtools import svg2paths2, Path as SvgPath, Line, QuadraticBezier, CubicBezier, Arc

PROJECT = Path(__file__).resolve().parent
SVG_DIR = PROJECT / "svgs"
OUT_DIR = PROJECT / "out"
FAMILY = "DilloHand"
STYLE = "Regular"

# ==== Metrics (1000 UPM grid) ====
UPM = 1000
BASELINE_SVG_Y = 200  # baseline measured from top of the 1000x1000 SVG
ASCENDER = 800
DESCENDER = -200
XHEIGHT = 500
CAPHEIGHT = 750

# If your SVGs appear upside-down in the test OTF, set this to False.
# True means: y_font = (1000 - y_svg) - 800 == 200 - y_svg  (flip + offset)
# False means: y_font = y_svg - 200                         (no flip, just shift)
SVG_Y_IS_DOWN = True

# Default advance width (can be adjusted per glyph if you like)
DEFAULT_ADV = 1000

HEX_RE = re.compile(r"^[0-9A-Fa-f]{4,6}$")

def ensure_dirs():
    OUT_DIR.mkdir(exist_ok=True)
    SVG_DIR.mkdir(exist_ok=True)

def svg_point_to_font(pt):
    """pt is complex (x + y*i) from svgpathtools."""
    x = pt.real
    y = pt.imag
    if SVG_Y_IS_DOWN:
        y_new = (UPM - y) - BASELINE_SVG_Y  # flip + shift so baseline lands at y=0
    else:
        y_new = y - BASELINE_SVG_Y  # just shift
    return (float(x), float(y_new))


# --- helpers for robust SVG path drawing ---
def approx_equal(pt1, pt2, eps=1e-6):
    return abs(pt1[0] - pt2[0]) <= eps and abs(pt1[1] - pt2[1]) <= eps

def _draw_segment(seg, pen):
    from svgpathtools import Line, QuadraticBezier, CubicBezier, Arc
    if isinstance(seg, Line):
        p1 = svg_point_to_font(seg.end)
        pen.lineTo(p1)
    elif isinstance(seg, QuadraticBezier):
        p0 = svg_point_to_font(seg.start)
        q1 = svg_point_to_font(seg.control)
        p2 = svg_point_to_font(seg.end)
        c1 = (p0[0] + 2.0/3.0*(q1[0]-p0[0]), p0[1] + 2.0/3.0*(q1[1]-p0[1]))
        c2 = (p2[0] + 2.0/3.0*(q1[0]-p2[0]), p2[1] + 2.0/3.0*(q1[1]-p2[1]))
        pen.curveTo(c1, c2, p2)
    elif isinstance(seg, CubicBezier):
        c1 = svg_point_to_font(seg.control1)
        c2 = svg_point_to_font(seg.control2)
        p1 = svg_point_to_font(seg.end)
        pen.curveTo(c1, c2, p1)
    elif isinstance(seg, Arc):
        for cubic in seg.as_cubic_curves():
            c1 = svg_point_to_font(cubic.control1)
            c2 = svg_point_to_font(cubic.control2)
            p1 = svg_point_to_font(cubic.end)
            pen.curveTo(c1, c2, p1)
    else:
        p1 = svg_point_to_font(seg.end)
        pen.lineTo(p1)

def _split_into_contours(svg_path):
    contours = []
    if len(svg_path) == 0:
        return contours
    current = []
    prev_end = None
    for seg in svg_path:
        start = svg_point_to_font(seg.start)
        end   = svg_point_to_font(seg.end)
        if prev_end is not None and not approx_equal(start, prev_end):
            if current:
                contours.append(current)
                current = []
        current.append(seg)
        prev_end = end
    if current:
        contours.append(current)
    return contours

def draw_svg_path_into_pen(svg_path, pen):
    """Draw an SvgPath that may contain multiple discontinuous contours."""
    contours = _split_into_contours(svg_path)
    for segs in contours:
        if not segs:
            continue
        start = svg_point_to_font(segs[0].start)
        pen.moveTo(start)
        for seg in segs:
            _draw_segment(seg, pen)
        end_pt = svg_point_to_font(segs[-1].end)
        if approx_equal(start, end_pt):
            pen.closePath()
        else:
            pen.endPath()

def load_svg_to_glyph(svg_pathfile, glyph):
    """Parse an SVG and draw all <path> elements into the UFO glyph."""
    paths, attrs, svg_attrs = svg2paths2(str(svg_pathfile))
    pen = glyph.getPen()
    for p in paths:
        if len(p) == 0:
            continue
        draw_svg_path_into_pen(p, pen)

def codepoint_from_name(name: str):
    base = name.split('.')[0]
    if HEX_RE.match(base):
        return int(base, 16)
    # Allow simple ASCII names like A, a, zero, etc., if desired:
    if len(base) == 1:
        return ord(base)
    return None

def production_name_from_cp(cp: int):
    # Use 'uniXXXX' / 'uXXXXX' naming convention
    if cp <= 0xFFFF:
        return f"uni{cp:04X}"
    return f"u{cp:05X}"

def build_ufo():
    u = Font()
    u.info.familyName = FAMILY
    u.info.styleName = STYLE
    u.info.unitsPerEm = UPM
    u.info.ascender = ASCENDER
    u.info.descender = DESCENDER
    u.info.xHeight = XHEIGHT
    u.info.capHeight = CAPHEIGHT

    # .notdef (required)
    g = u.newGlyph(".notdef")
    g.width = DEFAULT_ADV

    # Space (U+0020) if an SVG named 0020.svg is not provided
    # We still set width so spacing is OK.
    if not (SVG_DIR / "0020.svg").exists():
        sp = u.newGlyph("space")
        sp.unicodes = [0x0020]
        sp.width = DEFAULT_ADV

    glyph_order = [".notdef", "space"]

    # Import SVG glyphs
    for svg_file in sorted(SVG_DIR.glob("*.svg")):
        stem = svg_file.stem
        cp = codepoint_from_name(stem)
        if cp is None:
            print(f"Skipping {svg_file.name}: cannot infer Unicode from filename")
            continue
        gname = production_name_from_cp(cp)
        g = u.newGlyph(gname) if gname not in u else u[gname]
        g.width = DEFAULT_ADV
        g.unicodes = [cp]
        load_svg_to_glyph(svg_file, g)
        if gname not in glyph_order:
            glyph_order.append(gname)

    # Persist preferred order
    u.lib["public.glyphOrder"] = glyph_order

    ufo_path = PROJECT / f"{FAMILY}-{STYLE}.ufo"
    u.save(ufo_path, overwrite=True)
    return ufo_path

def compile_otf(ufo_path: Path):
    cmd = ["fontmake", "-u", str(ufo_path), "-o", "otf", "--output-dir", str(OUT_DIR)]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)

def main():
    ensure_dirs()
    ufo_path = build_ufo()
    compile_otf(ufo_path)
    print("Done. Check 'out' folder.")

if __name__ == "__main__":
    main()
