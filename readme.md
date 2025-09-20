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

### Example File Names
```
svgs/
├── notdef.svg      # .notdef glyph (required)
├── U+0020.svg      # Space character
├── U+0041.svg      # Letter A
├── 0042.svg        # Letter B
├── 0030.svg        # Digit 0
└── U+002E.svg      # Period
```

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

### Debug Mode
Use verbose output to see detailed processing information:
```bash
python build.py auto MyFont Regular
```

## License

This project is provided as-is for font development and prototyping.
