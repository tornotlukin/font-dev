# build.py — SVG -> UFO -> OTF
# Usage: python build.py [auto] [FAMILY] [STYLE]
# Use 'auto' as first argument to enable automatic sidebearing calculation
import os, re, sys, subprocess, json
from pathlib import Path
from ufoLib2 import Font
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Identity
from svgpathtools import svg2paths2, Path as SvgPath, Line, QuadraticBezier, CubicBezier, Arc
import xml.etree.ElementTree as ET

PROJECT = Path(__file__).resolve().parent
SVG_DIR = PROJECT / "svgs"
OUT_DIR = PROJECT / "out"

# Global configuration loaded from JSON
CONFIG = None

HEX_RE = re.compile(r"^[0-9A-Fa-f]{4,6}$")
UNICODE_RE = re.compile(r"^U\+([0-9A-Fa-f]{4,6})$")

def load_config():
    """Load the main configuration from font-config.json"""
    global CONFIG
    if CONFIG is None:
        config_file = PROJECT / "font-config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                CONFIG = json.load(f)
        else:
            # Fallback defaults if no config file
            CONFIG = {
                "font": {
                    "familyName": "DilloHand",
                    "styleName": "Regular",
                    "unitsPerEm": 1000,
                    "ascender": 800,
                    "descender": -200,
                    "xHeight": 500,
                    "capHeight": 750,
                    "defaultAdvanceWidth": 1000
                },
                "build": {
                    "svgYIsDown": True,
                    "baselineSvgY": 200,
                    "autoSidebearingMargin": 10,
                    "enableAutoSidebearings": True
                },
                "glyphMetrics": {},
                "kerning": {}
            }
    return CONFIG



def get_svg_bbox(svg_file):
    """Extract bounding box from SVG file to calculate sidebearings."""
    try:
        # First try with svgpathtools for path-based content
        paths, attrs, svg_attrs = svg2paths2(str(svg_file))
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        # Process paths from svgpathtools
        for path in paths:
            if path:
                bbox = path.bbox()
                if bbox and len(bbox) >= 4:
                    min_x = min(min_x, bbox[0])
                    max_x = max(max_x, bbox[1]) 
                    min_y = min(min_y, bbox[2])
                    max_y = max(max_y, bbox[3])
        
        # If no paths found, try parsing XML elements directly
        if min_x == float('inf'):
            tree = ET.parse(str(svg_file))
            root = tree.getroot()
            
            # Look for common SVG elements with position info
            for elem in root.iter():
                tag = elem.tag.split('}')[-1]  # Remove namespace
                
                if tag in ['rect', 'circle', 'ellipse', 'line']:
                    # Get bounding box from basic shapes
                    x = float(elem.get('x', 0))
                    y = float(elem.get('y', 0))
                    w = float(elem.get('width', 0))
                    h = float(elem.get('height', 0))
                    
                    if tag == 'circle':
                        cx = float(elem.get('cx', 0))
                        cy = float(elem.get('cy', 0))
                        r = float(elem.get('r', 0))
                        x, y, w, h = cx - r, cy - r, r * 2, r * 2
                    elif tag == 'ellipse':
                        cx = float(elem.get('cx', 0))
                        cy = float(elem.get('cy', 0))
                        rx = float(elem.get('rx', 0))
                        ry = float(elem.get('ry', 0))
                        x, y, w, h = cx - rx, cy - ry, rx * 2, ry * 2
                    
                    if w > 0 and h > 0:
                        min_x = min(min_x, x)
                        max_x = max(max_x, x + w)
                        min_y = min(min_y, y)
                        max_y = max(max_y, y + h)
        
        if min_x == float('inf'):
            return None
            
        return (min_x, min_y, max_x, max_y)
    except Exception as e:
        print(f"Warning: Could not parse SVG {svg_file.name}: {e}")
        return None

def calculate_auto_sidebearings(bbox, config, margin_units=5):
    """Calculate sidebearings with specified margin from glyph edges."""
    if not bbox:
        return None
        
    min_x, min_y, max_x, max_y = bbox
    
    # The actual glyph width (visual content)
    glyph_width = max_x - min_x
    
    # Add specified margins on each side
    left_margin = margin_units
    right_margin = margin_units
    
    # Total advance width = left margin + glyph width + right margin
    total_width = int(left_margin + glyph_width + right_margin)
    
    return {
        'width': total_width,
        'leftMargin': int(left_margin),
        'rightMargin': int(right_margin),
        'glyphWidth': int(glyph_width),
        'glyphBounds': (min_x, max_x),
        'svgMinX': min_x,  # Original SVG left edge
        'offsetX': left_margin - min_x  # How much to move glyph to achieve left margin
    }

def analyze_all_svgs_for_metrics(config, auto_sidebearing=False):
    """Pre-analyze all SVG files and calculate proper metrics before font creation."""
    calculated_metrics = {}
    margin = config["build"].get("autoSidebearingMargin", 5)
    
    print("Analyzing SVG files for automatic sidebearing calculation...")
    
    for svg_file in sorted(SVG_DIR.glob("*.svg")):
        stem = svg_file.stem
        cp = codepoint_from_name(stem)
        if cp is None:
            print(f"Skipping {svg_file.name}: cannot infer Unicode from filename")
            continue
            
        # Check if this is the space character
        if cp == 0x0020:
            gname = "space"
        else:
            gname = production_name_from_cp(cp)
            
        if auto_sidebearing:
            bbox = get_svg_bbox(svg_file)
            auto_metrics = calculate_auto_sidebearings(bbox, config, margin)
            
            if auto_metrics:
                calculated_metrics[gname] = {
                    'width': auto_metrics['width'],
                    'leftMargin': auto_metrics['leftMargin'],
                    'rightMargin': auto_metrics['rightMargin'],
                    'offsetX': auto_metrics['offsetX'],
                    'originalBounds': auto_metrics['glyphBounds']
                }
                print(f"Calculated metrics for {gname}: width={auto_metrics['width']}, "
                      f"left={auto_metrics['leftMargin']}, right={auto_metrics['rightMargin']}, "
                      f"offset={auto_metrics['offsetX']:.1f}")
            else:
                print(f"Warning: Could not calculate metrics for {gname}")
    
    return calculated_metrics

def generate_opentype_features(config, font_glyphs):
    """Generate OpenType feature code for alternates that actually exist in the font."""
    features = []
    alternates_config = config.get("alternates", {})
    
    # Generate Stylistic Sets (ss01, ss02, etc.)
    stylistic_sets = alternates_config.get("stylisticSets", {})
    for set_tag, set_info in stylistic_sets.items():
        # Only include substitutions where both base and alternate glyphs exist
        valid_substitutions = []
        for base_glyph, alt_glyph in set_info.get("substitutions", {}).items():
            if base_glyph in font_glyphs and alt_glyph in font_glyphs:
                valid_substitutions.append((base_glyph, alt_glyph))
        
        if valid_substitutions:  # Only create feature if we have valid substitutions
            feature_code = f"""
feature {set_tag} {{
    # {set_info.get('name', set_tag)}
    # {set_info.get('description', '')}
"""
            for base_glyph, alt_glyph in valid_substitutions:
                feature_code += f"    sub {base_glyph} by {alt_glyph};\n"
            
            feature_code += "} " + set_tag + ";\n"
            features.append(feature_code)
    
    # Generate Character Variants (cv01, cv02, etc.)
    char_variants = alternates_config.get("characterVariants", {})
    for cv_tag, cv_info in char_variants.items():
        # Only include substitutions where both base and alternate glyphs exist
        valid_substitutions = []
        for base_glyph, alt_glyph in cv_info.get("substitutions", {}).items():
            if base_glyph in font_glyphs and alt_glyph in font_glyphs:
                valid_substitutions.append((base_glyph, alt_glyph))
        
        if valid_substitutions:  # Only create feature if we have valid substitutions
            feature_code = f"""
feature {cv_tag} {{
    # {cv_info.get('name', cv_tag)}
    # {cv_info.get('description', '')}
"""
            for base_glyph, alt_glyph in valid_substitutions:
                feature_code += f"    sub {base_glyph} by {alt_glyph};\n"
            
            feature_code += "} " + cv_tag + ";\n"
            features.append(feature_code)
    
    return "\n".join(features)

def detect_alternate_glyphs(svg_dir):
    """Detect alternate glyph files like U+0061-ss01.svg or uni0061-ss01.svg."""
    alternates = {}
    
    for svg_file in svg_dir.glob("*.svg"):
        name = svg_file.stem
        
        # Check for stylistic set alternates (e.g., U+0061-ss01 or uni0061-ss01)
        if "-ss" in name:
            parts = name.split("-ss")
            if len(parts) == 2:
                base_name = parts[0]
                set_number = parts[1]
                if set_number.isdigit():
                    # Convert U+ format to uni format for glyph name
                    if base_name.startswith("U+"):
                        uni_base = f"uni{base_name[2:].upper().zfill(4)}"
                    else:
                        uni_base = base_name
                    
                    alt_glyph = f"{uni_base}.ss{set_number.zfill(2)}"
                    alternates[alt_glyph] = {
                        'file': svg_file,
                        'base': base_name,
                        'type': 'stylistic_set',
                        'number': set_number
                    }
        
        # Check for character variants (e.g., U+0061-cv01 or uni0061-cv01)
        elif "-cv" in name:
            parts = name.split("-cv")
            if len(parts) == 2:
                base_name = parts[0]
                cv_number = parts[1]
                if cv_number.isdigit():
                    # Convert U+ format to uni format for glyph name
                    if base_name.startswith("U+"):
                        uni_base = f"uni{base_name[2:].upper().zfill(4)}"
                    else:
                        uni_base = base_name
                        
                    alt_glyph = f"{uni_base}.cv{cv_number.zfill(2)}"
                    alternates[alt_glyph] = {
                        'file': svg_file,
                        'base': base_name,
                        'type': 'character_variant',
                        'number': cv_number
                    }
    
    return alternates

def ensure_dirs():
    OUT_DIR.mkdir(exist_ok=True)
    SVG_DIR.mkdir(exist_ok=True)

def svg_point_to_font(pt):
    """pt is complex (x + y*i) from svgpathtools."""
    config = load_config()
    x = pt.real
    y = pt.imag
    if config["build"]["svgYIsDown"]:
        y_new = (config["font"]["unitsPerEm"] - y) - config["build"]["baselineSvgY"]  # flip + shift so baseline lands at y=0
    else:
        y_new = y - config["build"]["baselineSvgY"]  # just shift
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

def load_svg_to_glyph(svg_pathfile, glyph, offset_x=0):
    """Parse an SVG and draw all <path> elements into the UFO glyph with optional horizontal offset."""
    paths, attrs, svg_attrs = svg2paths2(str(svg_pathfile))
    pen = glyph.getPen()
    
    # Apply transform if offset is needed
    if offset_x != 0:
        from fontTools.misc.transform import Transform
        transform_pen = TransformPen(pen, Transform(1, 0, 0, 1, offset_x, 0))
        pen = transform_pen
    
    for p in paths:
        if len(p) == 0:
            continue
        draw_svg_path_into_pen(p, pen)

def codepoint_from_name(name: str):
    base = name.split('.')[0]
    # Check for Unicode format: U+0043
    unicode_match = UNICODE_RE.match(base)
    if unicode_match:
        return int(unicode_match.group(1), 16)
    # Check for plain hex: 0043
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

def build_ufo(family_name, style_name, auto_sidebearing=False):
    config = load_config()
    
    # Pre-analyze all SVGs for metrics if auto-sidebearing is enabled
    calculated_metrics = {}
    if auto_sidebearing:
        calculated_metrics = analyze_all_svgs_for_metrics(config, auto_sidebearing)
    
    u = Font()
    u.info.familyName = family_name
    u.info.styleName = style_name
    u.info.unitsPerEm = config["font"]["unitsPerEm"]
    u.info.ascender = config["font"]["ascender"]
    u.info.descender = config["font"]["descender"]
    u.info.xHeight = config["font"]["xHeight"]
    u.info.capHeight = config["font"]["capHeight"]

    # Load configuration sections
    metrics_config = config.get("glyphMetrics", {})
    kerning_config = config.get("kerning", {})

    # .notdef (required)
    g = u.newGlyph(".notdef")
    g.width = config["font"]["defaultAdvanceWidth"]

    glyph_order = [".notdef"]

    # Detect alternate glyphs
    alternates = detect_alternate_glyphs(SVG_DIR)
    if alternates:
        print(f"Found {len(alternates)} alternate glyphs:")
        for alt_name, alt_info in alternates.items():
            print(f"  {alt_name} -> {alt_info['file'].name}")

    # Import SVG glyphs - separate regular glyphs from alternates
    has_space = False
    all_svg_files = list(SVG_DIR.glob("*.svg"))
    
    # Get list of alternate files to skip in regular processing
    alternate_files = set()
    for alt_info in alternates.values():
        alternate_files.add(alt_info['file'].stem)
    
    # Process regular glyphs first
    processed_regulars = set()
    for svg_file in sorted(all_svg_files):
        stem = svg_file.stem
        
        # Skip alternate glyph files - they'll be processed separately
        if stem in alternate_files:
            continue
            
        # Handle regular glyphs only
        cp = codepoint_from_name(stem)
        if cp is None:
            print(f"Skipping {svg_file.name}: cannot infer Unicode from filename")
            continue
        
        # Check if this is the space character
        if cp == 0x0020:
            has_space = True
            gname = "space"  # Use "space" instead of "uni0020" for better compatibility
        else:
            gname = production_name_from_cp(cp)
        
        print(f"Processing regular glyph: {gname} (U+{cp:04X})")
        
        # Check if we've already processed this glyph name
        if gname in processed_regulars:
            print(f"Warning: Regular glyph {gname} already processed, skipping {svg_file.name}")
            continue
            
        # Always create a new glyph (don't reuse existing ones)
        if gname in u:
            print(f"Warning: Glyph {gname} already exists in UFO, skipping {svg_file.name}")
            continue
            
        g = u.newGlyph(gname)
        processed_regulars.add(gname)
        if cp is not None:  # Regular glyphs get Unicode assignments
            g.unicodes = [cp]
        # Alternate glyphs don't get Unicode assignments
        
        # Determine metrics and offset for this glyph
        offset_x = 0
        final_width = config["font"]["defaultAdvanceWidth"]
        
        # Priority 1: Manual metrics from config
        if gname in metrics_config:
            metrics = metrics_config[gname]
            final_width = metrics.get("width", config["font"]["defaultAdvanceWidth"])
            
            # Calculate offset for manual metrics if needed
            if "leftMargin" in metrics:
                bbox = get_svg_bbox(svg_file)
                if bbox:
                    svg_left = bbox[0]
                    desired_left = metrics["leftMargin"]
                    offset_x = desired_left - svg_left
        
        # Priority 2: Auto-calculated metrics (if enabled and not manually configured)
        elif auto_sidebearing and gname in calculated_metrics:
            auto_metrics = calculated_metrics[gname]
            final_width = auto_metrics['width']
            offset_x = auto_metrics['offsetX']
        
        # Load SVG content with proper positioning
        load_svg_to_glyph(svg_file, g, offset_x)
        g.width = final_width
        
        if auto_sidebearing and gname in calculated_metrics:
            print(f"Applied auto-metrics for {gname}: width={final_width}, offset={offset_x:.1f}")
        elif gname in metrics_config:
            print(f"Applied manual metrics for {gname}: width={final_width}, offset={offset_x:.1f}")
        
        if gname not in glyph_order:
            glyph_order.append(gname)

    # Process alternate glyphs separately
    processed_alternates = set()
    for alt_name, alt_info in alternates.items():
        svg_file = alt_info['file']
        gname = alt_name  # e.g., uni0061.ss01
        
        print(f"Processing alternate glyph: {gname} (variant of {alt_info['base']})")
        
        # Check if we've already processed this alternate name
        if gname in processed_alternates:
            print(f"Warning: Alternate glyph {gname} already processed, skipping {svg_file.name}")
            continue
            
        # Always create a new glyph (don't reuse existing ones)
        if gname in u:
            print(f"Warning: Glyph {gname} already exists in UFO, skipping {svg_file.name}")
            continue
            
        g = u.newGlyph(gname)
        processed_alternates.add(gname)
        # Alternates don't get Unicode assignments
        
        # Determine metrics and offset for this alternate glyph
        offset_x = 0
        final_width = config["font"]["defaultAdvanceWidth"]
        
        # Priority 1: Manual metrics from config
        if gname in metrics_config:
            metrics = metrics_config[gname]
            final_width = metrics.get("width", config["font"]["defaultAdvanceWidth"])
            
            # Calculate offset for manual metrics if needed
            if "leftMargin" in metrics:
                bbox = get_svg_bbox(svg_file)
                if bbox:
                    svg_left = bbox[0]
                    desired_left = metrics["leftMargin"]
                    offset_x = desired_left - svg_left
        
        # Priority 2: Auto-calculated metrics (if enabled and not manually configured)
        elif auto_sidebearing and gname in calculated_metrics:
            auto_metrics = calculated_metrics[gname]
            final_width = auto_metrics['width']
            offset_x = auto_metrics['offsetX']
        
        # Load SVG content with proper positioning
        load_svg_to_glyph(svg_file, g, offset_x)
        g.width = final_width
        
        if auto_sidebearing and gname in calculated_metrics:
            print(f"Applied auto-metrics for {gname}: width={final_width}, offset={offset_x:.1f}")
        elif gname in metrics_config:
            print(f"Applied manual metrics for {gname}: width={final_width}, offset={offset_x:.1f}")
        
        if gname not in glyph_order:
            glyph_order.append(gname)

    # Only create fallback space if no 0020.svg exists
    if not has_space:
        sp = u.newGlyph("space")
        sp.unicodes = [0x0020]
        sp.width = config["font"]["defaultAdvanceWidth"]
        glyph_order.append("space")

    # Apply kerning pairs
    if kerning_config:
        for left_glyph, right_dict in kerning_config.items():
            if left_glyph in u:
                for right_glyph, kern_value in right_dict.items():
                    if right_glyph in u:
                        u.kerning[(left_glyph, right_glyph)] = kern_value
                        print(f"Applied kerning: {left_glyph} + {right_glyph} = {kern_value}")

    # Generate OpenType features for alternates (only for glyphs that exist)
    font_glyph_names = set(u.keys())
    feature_code = generate_opentype_features(config, font_glyph_names)
    if feature_code.strip():
        u.features.text = feature_code
        print("Generated OpenType features for alternates")
    else:
        print("No valid alternate glyphs found for OpenType features")

    # Persist preferred order
    u.lib["public.glyphOrder"] = glyph_order

    ufo_path = PROJECT / f"{family_name}-{style_name}.ufo"
    u.save(ufo_path, overwrite=True)
    return ufo_path

def compile_otf(ufo_path: Path):
    cmd = ["fontmake", "-u", str(ufo_path), "-o", "otf", "--output-dir", str(OUT_DIR)]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)

def main():
    config = load_config()
    
    # Check for help request
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("Usage: python build.py [auto] [FAMILY] [STYLE]")
        print("")
        print("Arguments:")
        print("  auto      Enable automatic sidebearing calculation from SVG bounds")
        print("  FAMILY    Font family name (default from config)")
        print("  STYLE     Font style name (default from config)")
        print("")
        print("Examples:")
        print("  python build.py")
        print("  python build.py auto")
        print("  python build.py DilloHand")
        print("  python build.py auto DilloHand Bold")
        return
    
    # Parse command-line arguments with auto-sidebearing control
    auto_sidebearing = False
    args = sys.argv[1:]  # Remove script name
    
    # Check if 'auto' is the first argument
    if len(args) > 0 and args[0].lower() == "auto":
        auto_sidebearing = True
        args = args[1:]  # Remove 'auto' from arguments
        print("Auto-sidebearing: ENABLED via command line")
    
    # Parse remaining arguments for family and style
    if len(args) >= 2:
        family_name = args[0]
        style_name = args[1]
    elif len(args) == 1:
        family_name = args[0]
        style_name = config["font"]["styleName"]  # Use config default for style
    else:
        family_name = config["font"]["familyName"]  # Use config defaults
        style_name = config["font"]["styleName"]
    
    print(f"Building font: {family_name} {style_name}")
    if auto_sidebearing:
        print("Auto-sidebearing: ENABLED")
    else:
        print("Auto-sidebearing: DISABLED")
    
    ensure_dirs()
    ufo_path = build_ufo(family_name, style_name, auto_sidebearing)
    compile_otf(ufo_path)
    print("Done. Check 'out' folder.")

if __name__ == "__main__":
    main()
