"""Verify the docs palette meets WCAG AA contrast targets.

Run: uv run python scripts/check_contrast.py
"""

from __future__ import annotations

import sys

# (label, foreground, background, minimum ratio)
PAIRS: list[tuple[str, str, str, float]] = [
    ("dark: body text on ground", "#ffffff", "#030712", 4.5),
    ("dark: muted text on ground", "#9ca3af", "#030712", 4.5),
    ("dark: accent link on ground", "#ff6900", "#030712", 4.5),
    ("dark: body text on surface", "#ffffff", "#0b0f19", 4.5),
    ("light: body text on ground", "#111827", "#faf9f7", 4.5),
    ("light: accent link on ground", "#c2410c", "#faf9f7", 4.5),
]


def _channel(value: int) -> float:
    srgb = value / 255
    if srgb <= 0.03928:
        return srgb / 12.92
    return ((srgb + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def ratio(fg: str, bg: str) -> float:
    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def main() -> int:
    failures = 0
    for label, fg, bg, minimum in PAIRS:
        value = ratio(fg, bg)
        ok = value >= minimum
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {value:5.2f}:1  (min {minimum})  {label}")
    if failures:
        print(f"\n{failures} pair(s) below target.", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
