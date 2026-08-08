"""Reaching the user's own openssh, from inside a sandbox or outside one.

`docs/DECISIONS.md` D5: in the Flatpak the app runs the host's `ssh` and
`ssh-keygen` through `flatpak-spawn --host`, because a bundled copy would be a
different program from the one the user runs in their terminal. Two things
follow from that, and both live here so the rest of `core` does not have to
know which side of a sandbox it is on:

1. **The argv gets a prefix.** `command()` adds it, or does not.
2. **A temp file is not a temp file.** Inside a Flatpak `/tmp` is private to
   the sandbox, so a config written there is invisible to the host `ssh` we
   hand the path to. `temp_config()` puts it where both sides can see it.

Still open, and deliberately not guessed at: what `flatpak-spawn` exits with
when the host has no openssh at all. Outside a sandbox that case arrives as
`FileNotFoundError` and every caller already handles it; inside one it arrives
as some exit status, and which one is a measurement to take against a real
bundle rather than a constant to invent here. See M17's checklist.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

#: Exists only inside a Flatpak. A module-level name so a test can point it
#: somewhere else; read on every call, because one `stat` is cheaper than a
#: cache that lies.
FLATPAK_INFO = Path("/.flatpak-info")

#: What turns our argv into the host's. `--host` is the whole point: without
#: it the command runs in the sandbox, where there is no openssh.
SPAWN: tuple[str, ...] = ("flatpak-spawn", "--host")

CONFIG_MODE = 0o600
SSH_DIR_MODE = 0o700


def in_sandbox() -> bool:
    """Whether this process is running inside a Flatpak."""
    return FLATPAK_INFO.exists()


def command(argv: Sequence[str]) -> list[str]:
    """`argv` as it has to be run to reach the user's own binary."""
    if in_sandbox():
        return [*SPAWN, *argv]
    return list(argv)


def shared_dir() -> Path:
    """A directory this process and the host both see, under the same path.

    `~/.ssh` rather than the system temp directory: it is granted by the same
    permission that lets us edit the config at all, it exists on any machine
    that has ever used ssh, and `write_atomic()` already puts its own temp
    file there. Resolved on every call, because the tests redirect `home()`.
    """
    folder = Path.home() / ".ssh"
    folder.mkdir(mode=SSH_DIR_MODE, parents=True, exist_ok=True)
    return folder


@contextmanager
def temp_config(text: str) -> Iterator[str]:
    """`text` as an ssh config the host can read, removed on the way out.

    `0600` because it is an ssh config sitting in the user's own `~/.ssh`, and
    the leading dot keeps it out of a careless `Include *` — a glob does not
    match a dotfile.
    """
    handle, path = tempfile.mkstemp(
        dir=str(shared_dir()), prefix=".parvussh-", suffix=".sshconfig"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.chmod(path, CONFIG_MODE)
        yield path
    finally:
        Path(path).unlink(missing_ok=True)
