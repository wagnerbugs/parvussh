"""Rasterise the icons at the sizes that matter, on light and dark.

Development tool, not part of the package. Run it through `make icon-preview`.
It reads the *committed* SVGs, so the image in `docs/` can never drift from
the icon the app actually ships.

The 32px render is the one that decides whether a detail earns its place;
judge there, not at 128.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cairo
import gi

gi.require_version("Rsvg", "2.0")

from gi.repository import Rsvg  # noqa: E402

ICONS = Path("data/icons/hicolor")
APP = ICONS / "scalable" / "apps" / "io.github.wagnerbugs.ParvuSsh.svg"
SYMBOLIC = ICONS / "symbolic" / "apps" / "io.github.wagnerbugs.ParvuSsh-symbolic.svg"

APP_SIZES = (128, 64, 48, 32)
SYMBOLIC_SIZES = (32, 16)
GAP = 20
MARGIN = 20

#: GNOME's own light and dark backdrops, so contrast is judged in both.
LIGHT = (0.98, 0.98, 0.96)
DARK = (0.13, 0.13, 0.16)


def row_width() -> int:
    sizes = (*APP_SIZES, *SYMBOLIC_SIZES)
    return MARGIN * 2 + sum(sizes) + GAP * (len(sizes) - 1) + GAP


def draw_row(ctx: cairo.Context, top: int, symbolic_colour: tuple[float, float, float]):
    """One strip: the app icon shrinking, then the symbolic one."""
    tallest = max(APP_SIZES)
    left = MARGIN
    for path, sizes in ((APP, APP_SIZES), (SYMBOLIC, SYMBOLIC_SIZES)):
        handle = Rsvg.Handle.new_from_file(str(path))
        for size in sizes:
            rect = Rsvg.Rectangle()
            rect.x = left
            rect.y = top + (tallest - size) // 2
            rect.width = rect.height = size
            if path is SYMBOLIC:
                # GTK recolours symbolic icons; stand in for that here so the
                # preview shows what the shell will actually draw.
                ctx.push_group()
                handle.render_document(ctx, rect)
                pattern = ctx.pop_group()
                ctx.set_source_rgb(*symbolic_colour)
                ctx.mask(pattern)
            else:
                handle.render_document(ctx, rect)
            left += size + GAP
        left += GAP


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/icon-preview.png")
    for path in (APP, SYMBOLIC):
        if not path.is_file():
            raise SystemExit(f"missing {path}; run from the repository root")

    strip = max(APP_SIZES) + MARGIN * 2
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, row_width(), strip * 2)
    ctx = cairo.Context(surface)

    for index, (backdrop, ink) in enumerate(
        ((LIGHT, (0.1, 0.1, 0.12)), (DARK, (0.95, 0.95, 0.95)))
    ):
        ctx.set_source_rgb(*backdrop)
        ctx.rectangle(0, index * strip, row_width(), strip)
        ctx.fill()
        draw_row(ctx, index * strip + MARGIN, ink)

    out.parent.mkdir(parents=True, exist_ok=True)
    surface.write_to_png(str(out))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
