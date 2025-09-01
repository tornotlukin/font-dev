# Font Build Script (`build.py`)

This project contains a Python script, `build.py`, that automates the process of converting SVG glyphs into a usable OpenType font (OTF) via the UFO (Unified Font Object) format.

## What Does `build.py` Do?

- **Reads SVG Glyphs:**
  - Scans the `svgs/` directory for SVG files, each representing a glyph.
  - Infers Unicode codepoints from SVG filenames (e.g., `0041.svg` for 'A').
- **Converts SVG Paths:**
  - Parses SVG path data and converts it into font contours, handling multiple contours and discontinuities robustly.
  - Flips and aligns glyphs as needed so they appear correctly in the font.
- **Builds a UFO Font:**
  - Assembles all glyphs into a UFO font structure, setting font metrics (ascender, descender, x-height, etc.).
- **Compiles to OTF:**
  - Uses `fontmake` to compile the UFO into an OTF font file, outputting to the `out/` directory.

## Usage

1. **Prepare Your Environment:**
   - Ensure you have Python 3.8+ and a virtual environment set up.
   - Install dependencies:
     ```sh
     pip install -r requirements.txt
     ```
     (Dependencies include `ufoLib2`, `fontTools`, `svgpathtools`, and `fontmake`.)

2. **Add SVG Glyphs:**
   - Place your SVG files in the `svgs/` directory.
   - Name each SVG file with the Unicode codepoint (e.g., `0041.svg` for 'A', `0020.svg` for space).

3. **Run the Build Script:**
   - Activate your virtual environment:
     ```sh
     .\.venv\Scripts\Activate.ps1  # On Windows PowerShell
     ```
   - Run the script:
     ```sh
     python build.py
     ```

4. **Output:**
   - The generated OTF font will be in the `out/` directory.
   - The intermediate UFO font will be in the project root (e.g., `DilloHand-Regular.ufo`).

## Customization

- **Font Metrics:**
  - Adjust UPM, ascender, descender, x-height, etc., at the top of `build.py`.
- **SVG Y-Axis Handling:**
  - If glyphs appear upside-down or misaligned, tweak the `SVG_Y_IS_DOWN` and `BASELINE_SVG_Y` settings.

## Troubleshooting

- If you encounter errors with SVG parsing or glyph orientation, check the comments in `build.py` for guidance on adjusting coordinate transforms.
- For complex SVGs, ensure paths are continuous or let the script handle discontinuities as designed.

## License

This project is provided as-is for font development and prototyping.
