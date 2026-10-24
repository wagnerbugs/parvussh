"""The dated copies left beside a config file, and how many of them stay.

The name is a convention shared with any other program that edits the same
file: `<name>.bak-YYYYMMDD-HHMMSS` in local time, in the file's own directory,
with `-2`, `-3`, … appended when two copies land in the same second. Copies
made by another program under that pattern are part of the same family as
ours — the family belongs to the file, not to whoever wrote it — so the
pattern and the order below must stay exactly what the other programs use.

Only the newest few are kept. The rest go to the trash, never straight to
deletion: the trash is where a user looks for something they did not mean to
lose. Moving a file there is the desktop's job, so `core`, which imports no
GTK, is handed the way to do it.
"""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from pathlib import Path

STAMP = "%Y%m%d-%H%M%S"
MODE = 0o600
KEEP = 3


def create(path: Path) -> Path:
    """Copy `path` to the first free name of its family, and return it.

    The copy is the file's exact bytes, `0600` from the moment it exists — a
    config readable by others would be a leak, even for an instant — and
    keeps the original's modification time. If anything fails the copy is
    removed and the error raised, so the caller writes nothing.

    `O_EXCL` makes "is this name free?" and "take it" one step. Checking
    first and copying after would let another program take the same name in
    between, and one of the two copies would overwrite the other.
    """
    data = path.read_bytes()
    times = path.stat()
    stamp = time.strftime(STAMP)
    number = 1
    while True:
        target = path.with_name(name(path.name, stamp, number))
        try:
            handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, MODE)
        except FileExistsError:
            number += 1
            continue
        break
    try:
        with os.fdopen(handle, "wb") as stream:
            # The umask can only narrow the mode `os.open` was given; this
            # makes it exactly 0600 rather than "at most".
            os.fchmod(stream.fileno(), MODE)
            stream.write(data)
        os.utime(target, ns=(times.st_atime_ns, times.st_mtime_ns))
    except OSError:
        target.unlink(missing_ok=True)
        raise
    return target


def name(original: str, stamp: str, number: int = 1) -> str:
    """`config.bak-20261024-131455`, or `…-131455-2` for the second that second."""
    suffix = f"-{number}" if number > 1 else ""
    return f"{original}.bak-{stamp}{suffix}"


def family(path: Path) -> list[Path]:
    """Every copy of `path` that matches the pattern exactly, newest first.

    Newest by the date in the name, never by modification time: our copies
    keep the original's, and another program's may not. Within one second the
    number decides, read as a number so `-10` is newer than `-2`; no number
    counts as 1. Anything else in the directory — the file itself, OpenSSH's
    `known_hosts.old`, a `config.bak-2026-10-12` made by hand, a directory or
    a link under a matching name — is not part of the family.
    """
    # ASCII: `\d` alone also matches Arabic-Indic and other Unicode digits.
    pattern = re.compile(
        rf"{re.escape(path.name)}\.bak-(\d{{8}}-\d{{6}})(?:-(\d+))?", re.ASCII
    )
    found = []
    for candidate in path.parent.iterdir():
        match = pattern.fullmatch(candidate.name)
        if match is None or candidate.is_symlink() or not candidate.is_file():
            continue
        found.append(((match[1], int(match[2] or 1), candidate.name), candidate))
    return [candidate for _, candidate in sorted(found, reverse=True)]


def prune(
    path: Path, keep: int, trash: Callable[[Path], None]
) -> list[tuple[Path, OSError]]:
    """Send every copy of `path` past the newest `keep` to `trash`.

    `keep` is at least 1: the copy of what was there before the last write is
    the one a user reaches for. Returns the copies `trash` refused, with its
    reason; those stay where they are and the rest are still moved, so one
    stuck file does not stop the family from shrinking.
    """
    refused = []
    for old in family(path)[max(keep, 1) :]:
        try:
            trash(old)
        except OSError as error:
            refused.append((old, error))
    return refused
