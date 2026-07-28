"""The suite must never see the developer's real ~/.ssh.

If these fail, stop and fix the fixture before running anything else.
"""

from __future__ import annotations

import os
from pathlib import Path

REAL_HOME = Path(os.path.realpath(os.path.expanduser("~")))


def test_home_is_redirected_to_a_temporary_directory(fake_home: Path) -> None:
    assert Path.home() == fake_home
    assert Path.home() != REAL_HOME


def test_expanduser_follows_the_redirect(fake_home: Path) -> None:
    assert Path("~/.ssh/config").expanduser() == fake_home / ".ssh/config"


def test_the_redirected_ssh_directory_starts_empty(fake_home: Path) -> None:
    assert list((fake_home / ".ssh").iterdir()) == []
