"""The names GNOME matches on, and the promises the docs make.

CLAUDE.md §1: two filenames must equal the app id exactly, or the shell shows
a generic icon under Wayland and a Flathub submission is rejected. Nothing
about that fails loudly at runtime, so it is pinned here.
"""

from __future__ import annotations

import configparser
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import parvussh
from parvussh import APP_ID, __version__

ROOT = Path(parvussh.__file__).parent.parent
DATA = ROOT / "data"
ICONS = DATA / "icons" / "hicolor"

DESKTOP = DATA / f"{APP_ID}.desktop"
METAINFO = DATA / f"{APP_ID}.metainfo.xml"
ICON = ICONS / "scalable" / "apps" / f"{APP_ID}.svg"
SYMBOLIC = ICONS / "symbolic" / "apps" / f"{APP_ID}-symbolic.svg"


def desktop_entry() -> configparser.SectionProxy:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str  # keys are case-sensitive in .desktop files
    parser.read(DESKTOP, encoding="utf-8")
    return parser["Desktop Entry"]


# -- the names -------------------------------------------------------------


@pytest.mark.parametrize("path", [DESKTOP, METAINFO, ICON, SYMBOLIC])
def test_the_packaging_file_exists(path: Path) -> None:
    assert path.is_file(), f"{path} is missing"


def test_the_app_id_is_settled() -> None:
    assert APP_ID == "io.github.wagnerbugs.ParvuSsh"


def test_the_owner_placeholder_is_gone() -> None:
    """CLAUDE.md §1 forbids the literal string anywhere in the tree."""
    tracked = [
        path
        for pattern in ("*.py", "*.md", "*.toml", "*.xml", "*.desktop", "Makefile")
        for path in ROOT.rglob(pattern)
        if ".venv" not in path.parts and ".git" not in path.parts
    ]
    # Assembled at runtime so this file does not match itself.
    forbidden = "io.github." + "OWNER"
    guilty = [
        path.relative_to(ROOT)
        for path in tracked
        if forbidden in path.read_text(encoding="utf-8", errors="replace")
    ]
    assert guilty == []


# -- the desktop entry -----------------------------------------------------


def test_the_desktop_entry_points_at_our_icon() -> None:
    assert desktop_entry()["Icon"] == APP_ID


def test_the_window_class_matches_the_app_id() -> None:
    """Wayland binds the icon to the window through this, or not at all."""
    assert desktop_entry()["StartupWMClass"] == APP_ID


def test_the_desktop_entry_is_a_normal_application() -> None:
    entry = desktop_entry()
    assert entry["Type"] == "Application"
    assert entry["Terminal"] == "false"
    assert entry["Exec"].startswith("parvussh")


def test_the_desktop_categories_are_the_documented_ones() -> None:
    assert desktop_entry()["Categories"] == "Network;RemoteAccess;"


def test_the_desktop_entry_is_translated() -> None:
    """freedesktop: the unsuffixed value is English, `[pt_BR]` translates it."""
    entry = desktop_entry()
    assert "SSH connections" in entry["Comment"]
    assert "conexões SSH" in entry["Comment[pt_BR]"]
    assert "conexão" in entry["Keywords[pt_BR]"]


def test_every_shipped_locale_is_declared_in_the_metainfo() -> None:
    """App stores use this to say whether the app speaks the user's language."""
    from parvussh.i18n import available_locales

    root = ET.parse(METAINFO).getroot()
    languages = root.find("languages")
    assert languages is not None
    declared = {(lang.text or "").lower() for lang in languages}
    assert declared == {locale.lower() for locale in available_locales()}


# -- the appstream metadata ------------------------------------------------


def test_the_metainfo_parses() -> None:
    ET.parse(METAINFO)


def test_the_metainfo_id_matches_the_app_id() -> None:
    root = ET.parse(METAINFO).getroot()
    assert root.findtext("id") == APP_ID


def test_the_metainfo_launches_our_desktop_file() -> None:
    root = ET.parse(METAINFO).getroot()
    assert root.findtext("launchable") == DESKTOP.name


def test_the_declared_licence_matches_the_one_we_ship() -> None:
    root = ET.parse(METAINFO).getroot()
    assert root.findtext("project_license") == "GPL-3.0-or-later"
    assert (ROOT / "LICENSE").read_text().startswith("                    GNU")


def test_the_newest_release_matches_the_package_version() -> None:
    root = ET.parse(METAINFO).getroot()
    releases = root.find("releases")
    assert releases is not None
    assert releases[0].get("version") == __version__


def test_the_changelog_documents_this_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{__version__}]" in changelog


# -- the icons -------------------------------------------------------------


@pytest.mark.parametrize("path", [ICON, SYMBOLIC])
def test_the_icon_is_valid_xml(path: Path) -> None:
    ET.parse(path)


def test_the_symbolic_icon_is_the_size_gnome_expects() -> None:
    root = ET.parse(SYMBOLIC).getroot()
    assert root.get("viewBox") == "0 0 16 16"


def test_the_app_icon_is_square() -> None:
    root = ET.parse(ICON).getroot()
    assert root.get("width") == root.get("height")


def test_the_app_icon_uses_the_canvas_gnome_expects() -> None:
    root = ET.parse(ICON).getroot()
    assert root.get("viewBox") == "0 0 128 128"


@pytest.mark.parametrize("path", [ICON, SYMBOLIC])
def test_the_icon_names_itself(path: Path) -> None:
    """`<title>` is what a screen reader announces, and proof of a whole file."""
    root = ET.parse(path).getroot()
    title = root.find("{http://www.w3.org/2000/svg}title")
    assert title is not None and title.text == "ParvuSsh"


@pytest.mark.parametrize("path", [ICON, SYMBOLIC])
def test_the_icons_are_licensed(path: Path) -> None:
    assert "SPDX-License-Identifier: GPL-3.0-or-later" in path.read_text()


def test_the_icon_preview_is_present() -> None:
    """docs/ICONS.md embeds it; a missing file leaves a broken image."""
    assert (ROOT / "docs" / "icon-preview.png").is_file()
