"""The list follows the file when another program writes it.

The events are real: Gio watches the throwaway `~/.ssh`, and the tests write to
it the way another program would.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

CONFIG = """Host vps-blog
    HostName 203.0.113.10
    Port 22

Host github.com
    User git
"""
MOVED = CONFIG.replace("Port 22", "Port 1310")


@pytest.fixture
def config_file(fake_home: Path) -> Path:
    return fake_home / ".ssh" / "config"


@pytest.fixture
def app(window, config_file: Path):
    """A window over `CONFIG`, watching it, with `vps-blog` open."""
    config_file.write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


def replace_file(path: Path, text: str) -> None:
    """Write the way a careful program does: a temp file renamed over it."""
    temp = path.with_name(".other-program.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def settle(seconds: float = 0.6) -> None:
    """Run the main loop for longer than the watch waits before reporting."""
    from gi.repository import GLib

    context = GLib.MainContext.default()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        time.sleep(0.01)


def test_a_write_from_elsewhere_reaches_the_list(app, config_file, pump) -> None:
    replace_file(config_file, MOVED)

    pump(lambda: app.hosts[0].get("Port") == "1310", timeout=3)


def test_the_open_connection_stays_open(app, config_file, pump) -> None:
    before = app.current
    replace_file(config_file, MOVED)

    pump(lambda: app.current is not before, timeout=3)

    assert app.current.title == "vps-blog"
    assert app.editor.port.get_text() == "1310"
    assert app.sidebar.listbox.get_selected_row().block is app.current


def test_an_unsaved_edit_is_never_dropped(app, config_file) -> None:
    app.editor.hostname.set_text("203.0.113.99")
    before = app.current
    replace_file(config_file, MOVED)

    app.on_disk_change()

    assert app.current is before
    assert app.editor.dirty is True
    assert app.editor.hostname.get_text() == "203.0.113.99"


def test_a_connection_left_unsaved_is_never_dropped(app, config_file) -> None:
    """A duplicate waits unsaved in the set, with nothing typed on the form."""
    app.duplicate_current()
    replace_file(config_file, MOVED)

    app.on_disk_change()

    assert "vps-blog-copia" in [block.title for block in app.hosts]


def test_our_own_save_does_not_reload(app) -> None:
    app.editor.hostname.set_text("203.0.113.99")
    app.save_current()
    saved = app.current

    settle()

    assert app.current is saved


def test_a_write_that_changes_nothing_does_not_reload(app, config_file) -> None:
    before = app.current
    replace_file(config_file, CONFIG)

    settle()

    assert app.current is before


def test_a_file_gone_for_a_moment_is_not_recreated(app, config_file) -> None:
    """Another program may delete it before writing it again."""
    config_file.unlink()

    app.on_disk_change()

    assert not config_file.exists()


def test_an_included_file_is_watched_too(window, config_file, pump) -> None:
    extra = config_file.with_name("extra.conf")
    extra.write_text("Host extra\n    Port 22\n", encoding="utf-8")
    config_file.write_text("Include extra.conf\n", encoding="utf-8")
    window.reload()

    replace_file(extra, "Host extra\n    Port 1310\n")

    pump(lambda: window.hosts[0].get("Port") == "1310", timeout=3)
