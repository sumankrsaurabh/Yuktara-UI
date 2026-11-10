"""Inspect HarfBuzz glyph shaping for a caller-supplied font file.

Example:
    python examples/native/harfbuzz_shaping.py ./NotoSansDevanagari-Regular.ttf \
        --family "Noto Sans Devanagari" --text "नमस्ते भारत"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from novaui.native import FontConfig, HarfBuzzShaper, TextMeasurer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path, help="font file to shape with")
    parser.add_argument("--family", default="Inter", help="installed Skia typeface family")
    parser.add_argument("--size", type=float, default=24.0)
    parser.add_argument("--direction", choices=("auto", "ltr", "rtl"), default="auto")
    parser.add_argument("--text", default="office — नमस्ते — العربية — क्षि")
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error(f"font file does not exist: {args.font}")

    config = FontConfig(
        family=args.family,
        size=args.size,
        fallback_families=(),
        font_path=str(args.font.resolve()),
    )
    measurer = TextMeasurer(shaper=HarfBuzzShaper(), base_direction=args.direction)
    layout = measurer.measure(args.text, config, wrap=False)
    print(f"text: {args.text}")
    print(f"size: {layout.width:.2f} × {layout.height:.2f}")
    for line_index, line in enumerate(layout.lines):
        print(f"line {line_index}: {line.text!r} ({line.width:.2f}px)")
        for run in line.glyph_runs:
            print(f"  {run.font_family} [{run.direction}] source={run.start}:{run.end}")
            print(f"    glyph IDs: {', '.join(map(str, run.glyph_ids))}")
            print(f"    positions: {run.positions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
