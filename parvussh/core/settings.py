"""The app's own preferences — the one file it keeps that is not ssh's.

Connections never live here; they live in `~/.ssh/config` and nowhere else.
This holds only how the app itself behaves, so deleting it loses a preference
and never a server. It sits where the XDG base directory spec says user
configuration goes: `$XDG_CONFIG_HOME/parvussh/settings.ini`, which is
`~/.config/…` on a plain install and the app's own directory under
`~/.var/app/` inside a Flatpak.

An `.ini` rather than GSettings because `core` imports no GTK, and a schema
would have to be compiled and installed before `make run` could start.
"""

from __future__ import annotations

import configparser
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from parvussh.core.backups import KEEP
from parvussh.core.order import BY_FILE, ORDERS

DIRECTORY = "parvussh"
FILENAME = "settings.ini"
TERMINAL = "terminal"
COMMAND = "command"
BACKUPS = "backups"
COUNT = "keep"
LIST = "list"
ORDER = "order"


@dataclass(frozen=True)
class Settings:
    #: What Acessar opens, as typed by the user. Empty means the system's own.
    terminal: str = ""
    #: How many dated copies of each config file stay; older ones are trashed.
    backups: int = KEEP
    #: How the connection list is sorted. Only the list: the file never moves.
    order: str = BY_FILE


def path() -> Path:
    """Where the settings live. Resolved on every call: tests move `home()`."""
    base = os.environ.get("XDG_CONFIG_HOME", "").strip()
    # The spec says a relative value is invalid and must be ignored.
    root = Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"
    return root / DIRECTORY / FILENAME


def load() -> Settings:
    """The saved settings, or the defaults when there are none to read.

    A file that cannot be parsed is treated as absent rather than fatal: it
    holds one preference, and a window that refuses to open over it would be
    a worse answer than the system's default terminal.
    """
    parser = _parser()
    try:
        parser.read_string(path().read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, configparser.Error):
        return Settings()
    return Settings(
        terminal=parser.get(TERMINAL, COMMAND, fallback="").strip(),
        backups=_count(parser.get(BACKUPS, COUNT, fallback="")),
        order=_order(parser.get(LIST, ORDER, fallback="")),
    )


def save(settings: Settings) -> Path:
    """Write `settings` atomically and return the path written."""
    parser = _parser()
    parser[TERMINAL] = {COMMAND: settings.terminal.strip()}
    parser[BACKUPS] = {COUNT: str(max(settings.backups, 1))}
    parser[LIST] = {ORDER: _order(settings.order)}
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=target.parent, prefix=f".{FILENAME}-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            parser.write(stream)
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
    return target


def _count(text: str) -> int:
    """The number of copies to keep: a typo means the default, never zero.

    Keeping none would leave a write with nothing to undo it by.
    """
    try:
        return max(int(text), 1)
    except ValueError:
        return KEEP


def _order(text: str) -> str:
    """A known order, or the file's: a hand edit may have written any word."""
    text = text.strip()
    return text if text in ORDERS else BY_FILE


def _parser() -> configparser.ConfigParser:
    # No interpolation: a terminal command may well contain a `%`.
    return configparser.ConfigParser(interpolation=None)
