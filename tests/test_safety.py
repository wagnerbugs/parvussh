"""The suite must never see the developer's real ~/.ssh.

If these fail, stop and fix the fixture before running anything else.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.conftest import FakeTrash

REAL_HOME = Path(os.path.realpath(os.path.expanduser("~")))


def test_home_is_redirected_to_a_temporary_directory(fake_home: Path) -> None:
    assert Path.home() == fake_home
    assert Path.home() != REAL_HOME


def test_expanduser_follows_the_redirect(fake_home: Path) -> None:
    assert Path("~/.ssh/config").expanduser() == fake_home / ".ssh/config"


def test_the_redirected_ssh_directory_starts_empty(fake_home: Path) -> None:
    assert list((fake_home / ".ssh").iterdir()) == []


def test_the_app_s_settings_land_in_the_fake_home(fake_home: Path) -> None:
    """The one file of its own the app writes must not reach ~/.config either."""
    from parvussh.core import settings

    # Set, this variable would point past the fake home at the real ~/.config.
    assert "XDG_CONFIG_HOME" not in os.environ
    assert settings.path().is_relative_to(fake_home)


@pytest.mark.gui
def test_gui_tests_never_reach_the_real_trash(gtk, trash: FakeTrash) -> None:
    """Pruning old config copies would otherwise fill the developer's Trash."""
    from parvussh.ui import trash as module

    assert module.to_trash is trash


@pytest.mark.gui
def test_a_trash_error_arrives_as_the_oserror_core_expects(
    gtk, fake_home: Path
) -> None:
    """A path that does not exist: Gio refuses it before anything moves."""
    from parvussh.ui.trash import gio_trash

    with pytest.raises(OSError):
        gio_trash(fake_home / "nothing-here")
