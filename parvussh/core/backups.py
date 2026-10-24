"""The dated copy left beside a config file before every write.

The name is a convention shared with any other program that edits the same
file: `<name>.bak-YYYYMMDD-HHMMSS` in local time, in the file's own directory,
with `-2`, `-3`, … appended when two copies land in the same second. Copies
made by another program under that pattern are part of the same family as
ours, so the rules here have to hold for theirs too.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

STAMP = "%Y%m%d-%H%M%S"
MODE = 0o600


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
