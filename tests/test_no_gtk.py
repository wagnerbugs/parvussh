"""`core`, `data` and `i18n` must stay importable without a display.

Only `parvussh/ui/**` may touch GTK. This keeps the logic
testable headless and keeps a future CLI or TUI possible. The check parses the
source instead of grepping, so the word "gi" inside a comment or a Portuguese
string never trips it and never hides a real import either.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import parvussh

PACKAGE_ROOT = Path(parvussh.__file__).parent
HEADLESS_PACKAGES = ("core", "data", "i18n")
FORBIDDEN_ROOTS = {"gi", "gtk", "gobject"}

#: `cli.py` may name `parvussh.ui`, since choosing between the listing and the
#: window is its job — but only from inside a function, so `parvussh --list`
#: still runs where GTK is not installed. `tests/test_cli.py` proves the lazy
#: import holds in a fresh interpreter; here we only forbid the import itself.
ENTRY_POINT = PACKAGE_ROOT / "cli.py"


def headless_sources() -> list[Path]:
    return sorted(
        path
        for package in HEADLESS_PACKAGES
        for path in (PACKAGE_ROOT / package).rglob("*.py")
    )


def imported_roots(source: str) -> set[str]:
    """Top-level module names this file imports, however it phrases it."""
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_the_scan_actually_finds_files() -> None:
    """A test that checks nothing is worse than no test at all."""
    assert len(headless_sources()) >= 5


@pytest.mark.parametrize("path", headless_sources(), ids=lambda p: p.name)
def test_headless_package_does_not_import_gtk(path: Path) -> None:
    roots = imported_roots(path.read_text(encoding="utf-8"))
    assert not (roots & FORBIDDEN_ROOTS), f"{path} imports {roots & FORBIDDEN_ROOTS}"


@pytest.mark.parametrize("path", headless_sources(), ids=lambda p: p.name)
def test_headless_package_does_not_reach_into_ui(path: Path) -> None:
    """Import direction is one-way: ui depends on core, never the reverse."""
    source = path.read_text(encoding="utf-8")
    assert "parvussh.ui" not in source, f"{path} depends on the UI layer"


def test_the_entry_point_does_not_import_gtk() -> None:
    roots = imported_roots(ENTRY_POINT.read_text(encoding="utf-8"))
    assert not (roots & FORBIDDEN_ROOTS), f"{ENTRY_POINT} imports GTK"


def test_the_entry_point_reaches_the_ui_only_from_inside_a_function() -> None:
    """A top-level `parvussh.ui` import pulls GTK in through the back door.

    `tests/test_cli.py` catches that too, by asking a fresh interpreter, but
    this says which line is at fault instead of only that something is.
    """
    tree = ast.parse(ENTRY_POINT.read_text(encoding="utf-8"))
    top_level = [
        node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    named = {
        *(
            alias.name
            for node in top_level
            if isinstance(node, ast.Import)
            for alias in node.names
        ),
        *(node.module or "" for node in top_level if isinstance(node, ast.ImportFrom)),
    }
    offenders = {name for name in named if name.startswith("parvussh.ui")}
    assert offenders == set(), f"{ENTRY_POINT} imports {offenders} at module level"


def test_the_forbidden_import_detector_works() -> None:
    assert imported_roots("import gi") == {"gi"}
    assert imported_roots("from gi.repository import Gtk") == {"gi"}
    assert imported_roots("# import gi\nx = 'import gi'") == set()
