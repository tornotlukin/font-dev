# Font Build Tool

A comprehensive Python-based font build system that converts individual SVG glyph files into professional OpenType fonts (OTF). The tool provides intelligent automatic sidebearing calculation, configurable kerning pairs, and flexible font metrics through a unified JSON configuration system, making it easy to create well-spaced, production-ready fonts from vector artwork.

## Quick Start

```bash
# Basic build using config defaults
python build.py

# Enable automatic sidebearing calculation
python build.py auto

# Custom family name with config style
python build.py MyFont

# Full custom with automatic sidebearing
python build.py auto MyFont Bold

# Show help
python build.py --help
```

### Command Line Arguments

- **`auto`** - Enable automatic sidebearing calculation from SVG bounds
- **`FAMILY`** - Font family name (overrides config default)
- **`STYLE`** - Font style name (overrides config default)

## Configuration System

All font settings are controlled through `font-config.json`:

### Font Metadata
```json
{
  "font": {
    "familyName": "DilloHand",
    "styleName": "Regular",
    "unitsPerEm": 1000,
    "ascender": 800,
    "descender": -200,
    "xHeight": 500,
    "capHeight": 750,
    "defaultAdvanceWidth": 1000
  }
}
```

### Build Settings
```json
{
  "build": {
    "svgYIsDown": true,
    "baselineSvgY": 200,
    "autoSidebearingMargin": 10
  }
}
```

### Manual Glyph Metrics
```json
{
  "glyphMetrics": {
    "space": {
      "width": 300,
      "leftMargin": 0,
      "rightMargin": 0
    },
    "uni0041": {
      "width": 700,
      "leftMargin": 50,
      "rightMargin": 50
    }
  }
}
```

### Stylistic Alternates ✨ FULLY AUTOMATIC
```json
{
  "_alternates_automatic": {
    "_comment": "Alternates are now auto-generated from SVG filenames",
    "_usage": "Just create files like U+0061-ss01.svg or U+0067-cv01.svg"
  }
}
```

No manual configuration needed! OpenType features are generated automatically based on your SVG filenames.

### Kerning Pairs
```json
{
  "kerning": {
    "uni0054": {
      "uni0041": -50,
      "uni002E": -80
    },
    "uni0056": {
      "uni0041": -40
    }
  }
}
```

## Automatic Sidebearing System

When using the `auto` flag, the tool:

1. **Analyzes SVG Files** - Scans all SVG files to detect actual vector bounds
2. **Calculates Optimal Spacing** - Adds configurable margin (`autoSidebearingMargin`) from glyph edges
3. **Positions Correctly** - Places glyphs with proper sidebearings without post-processing movement
4. **Reports Metrics** - Shows calculated width, margins, and positioning for each glyph

### Priority System
1. **Manual Override** - `glyphMetrics` in config (highest priority)
2. **Auto-calculation** - When `auto` flag is used
3. **Default Width** - Fallback from config

## SVG File Requirements

- Place SVG files in the `svgs/` directory
- Name files with Unicode codepoints: `U+0041.svg`, `0041.svg`, or `A.svg`
- Supported formats: Standard SVG paths, basic shapes (rect, circle, ellipse)
- **Alternate Support** - Add `-ss##` or `-cv##` suffixes for stylistic alternates

### Example File Names
```
svgs/
├── notdef.svg         # .notdef glyph (required)
├── U+0020.svg         # Space character → "space" glyph
├── U+0041.svg         # Letter A (standard) → "uni0041" glyph
├── U+0061.svg         # Letter a (standard) → "uni0061" glyph
├── U+0061-ss01.svg    # Letter a alternate → "uni0061.ss01" glyph (stylistic set)
├── U+0067.svg         # Letter g (standard) → "uni0067" glyph
├── U+0067-cv01.svg    # Letter g alternate → "uni0067.cv01" glyph (character variant)
├── 0042.svg           # Letter B → "uni0042" glyph
├── 0030.svg           # Digit 0 → "uni0030" glyph
└── U+002E.svg         # Period → "uni002E" glyph
```

### Glyph Processing
- **Regular Glyphs** - Get Unicode assignments and appear in standard character maps
- **Alternate Glyphs** - Created as separate glyphs without Unicode assignments
- **Duplicate Protection** - Multiple files resolving to same glyph name are detected and skipped
- **Processing Order** - Regular glyphs processed first, then alternates separately

## Installation

1. **Set up Python environment:**
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1  # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```bash
   python build.py --help
   ```

## Output

- **OTF Font** - Generated in `out/` directory
- **UFO Source** - Intermediate format in project root
- **Console Output** - Detailed metrics and processing information

## Advanced Features

### Stylistic Alternates & Character Variants ✨ NEW
Create multiple versions of letters that users can access in design programs through OpenType features:

- **Stylistic Sets (ss01-ss20)** - Thematic alternate styles (e.g., all letters without crossbars as a design theme)
- **Character Variants (cv01-cv99)** - Individual character alternates (e.g., single-story 'g', alternate 'a' forms)
- **Stylistic Alternates (salt)** - General access feature that includes ALL alternates (auto-generated)

The build system automatically detects alternate glyph files and generates the necessary OpenType features.

#### Naming Convention for Alternates
- `U+0061-ss01.svg` - Stylistic Set 01 version of 'a' → creates `uni0061.ss01` glyph
- `U+0067-cv01.svg` - Character Variant 01 version of 'g' → creates `uni0067.cv01` glyph  
- `U+0052-ss02.svg` - Stylistic Set 02 version of 'R' → creates `uni0052.ss02` glyph

#### Fully Automatic Processing ✨ NEW
1. **Detection** - Build system scans for `-ss##` and `-cv##` patterns in SVG filenames
2. **Glyph Creation** - Creates separate alternate glyphs (no Unicode assignments)  
3. **Feature Generation** - **Automatically generates OpenType features** based on detected files
4. **No Manual Config** - No need to edit JSON for alternates - just create the SVG files!
5. **Duplicate Protection** - Prevents alternate glyphs from overwriting regular glyphs

**Example Workflow:**
```bash
# 1. Create your SVG files
svgs/U+0061.svg        # Regular 'a'
svgs/U+0061-ss01.svg   # Stylistic Set 1 'a'
svgs/U+0021-cv01.svg   # Character Variant 1 '!' (first alternate)
svgs/U+0021-cv02.svg   # Character Variant 2 '!' (second alternate)

# 2. Run build (that's it!)
python build.py auto

# 3. OpenType features are auto-generated with proper syntax:
# feature ss01 { sub uni0061 by uni0061.ss01; }
# feature cv01 { sub uni0021 from [uni0021.cv01 uni0021.cv02]; }  # Multiple alternates!
# feature salt { sub uni0061 by uni0061.ss01; sub uni0021 from [uni0021.cv01 uni0021.cv02]; }
# feature aalt { feature salt; feature ss01; feature cv01; }
```

**🎯 Multiple Alternates Support:**
- **Same feature, same base**: `U+0021-cv01.svg` + `U+0021-cv02.svg` → `cv01` feature with choice UI
- **Proper OpenType syntax**: Uses alternate substitution `from [...]` for multiple choices
- **App compatibility**: Works correctly in Illustrator, InDesign, Figma, etc.

#### Access in Design Programs
- **Adobe InDesign** - OpenType panel → Stylistic Sets / Character Variants / Stylistic Alternates
- **Adobe Illustrator** - OpenType panel → Alternates (uses `salt` feature)
- **Figma** - Typography panel → OpenType features → Stylistic Sets
- **Sketch** - Typography inspector → OpenType features
- **Microsoft Word** - Home tab → Font dialog → Advanced → Stylistic Sets
- **Font Viewers** - Alternates appear as separate glyphs without Unicode codepoints

#### OpenType Feature Summary
- **`ss01-ss20`** - Stylistic Sets (for thematic alternate groups, uses single substitution)
- **`cv01-cv99`** - Character Variants (for individual alternates, supports multiple choices per base glyph)
- **`salt`** - Stylistic Alternates (general access to all alternates with proper choice UI)
- **`aalt`** - Access All Alternates (aggregate feature for maximum compatibility)

**Proper OpenType Implementation:**
- **Single alternates**: `sub uni0061 by uni0061.ss01;`
- **Multiple alternates**: `sub uni0021 from [uni0021.cv01 uni0021.cv02];` 
- **Choice UI**: Design apps show dropdown/cycle interface for multiple alternates

### Kerning Configuration
Define spacing adjustments between specific letter pairs. Negative values tighten spacing, positive values loosen it.

### Coordinate System Handling
Configure how SVG coordinates map to font coordinates through `svgYIsDown` and `baselineSvgY` settings.

### Flexible Metrics
Override individual glyph spacing or rely on intelligent automatic calculation based on actual artwork bounds.

## Troubleshooting

### Common Issues
- **Missing Dependencies** - Run `pip install -r requirements.txt`
- **SVG Parsing Errors** - Check SVG file format and path complexity
- **Upside-down Glyphs** - Adjust `svgYIsDown` in config
- **Spacing Issues** - Tune `autoSidebearingMargin` or use manual `glyphMetrics`
- **Alternates Not Detected** - Check filename format: `U+XXXX-ss##.svg` or `U+XXXX-cv##.svg`
- **Missing Base Glyphs** - Ensure base glyph exists (e.g., `U+0061.svg`) before creating alternates (`U+0061-ss01.svg`)
- **Duplicate Glyphs** - Build system will warn and skip duplicates automatically

### Stylistic Alternates Troubleshooting
- **Alternates Not Working** - Verify OpenType feature support in your design application
- **Wrong Substitutions** - Check `font-config.json` alternates configuration matches your glyph names
- **Missing Features** - Ensure both base and alternate glyphs exist in the font

### Debug Mode
Use verbose output to see detailed processing information:
```bash
python build.py auto MyFont Regular
```

Look for these messages:
- `Found X alternate glyphs:` - Confirms detection
- `Processing alternate glyph: uni0061.ss01 (variant of U+0061)` - Shows processing
- `Warning: Glyph X already processed` - Indicates duplicate protection

## License

This project is provided as-is for font development and prototyping.
