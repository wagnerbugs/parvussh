"""Old config copies to the trash: the one step of pruning `core` cannot take.

`core` decides which copies go and is handed the way to send them; this is
that way. `Gio.File.trash` follows the freedesktop trash spec, and inside a
Flatpak it goes through the trash portal, so a copy lands in the user's own
Trash rather than in one private to the sandbox.
"""

from __future__ import annotations

import logging
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")

from gi.repository import Gio, GLib  # noqa: E402

from parvussh.core import backups  # noqa: E402

log = logging.getLogger(__name__)


def gio_trash(path: Path) -> None:
    """Move one file to the trash. Raises `OSError`, as `core` expects.

    A `GLib.Error` escaping from here would surface after a save that has
    already succeeded, as a crash instead of a toast.
    """
    try:
        Gio.File.new_for_path(str(path)).trash(None)
    except GLib.Error as error:
        raise OSError(error.message) from error


#: What pruning calls. A name of its own so the test suite can swap in a fake:
#: no file from the suite may ever reach the real trash.
to_trash = gio_trash


def prune(written: list[Path], keep: int) -> list[Path]:
    """Prune the copies of every file just written. Returns those left behind.

    Runs after a save that has already succeeded, so nothing here may raise:
    a trash that refuses is logged and reported back, and the save stands.
    `to_trash` is looked up on each call so the test suite can replace it.
    """
    left = []
    for path in written:
        try:
            refused = backups.prune(path, keep, to_trash)
        except OSError as error:  # the directory itself could not be listed
            refused = [(path, error)]
        for copy, error in refused:
            log.warning("could not move %s to the trash: %s", copy, error)
            left.append(copy)
    return left
