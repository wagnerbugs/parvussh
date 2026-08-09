"""Reaching the user's own openssh, from inside a sandbox or outside one.

In the Flatpak the app runs the host's `ssh` and `ssh-keygen` through
`flatpak-spawn --host`, because a bundled copy would be a different program
from the one the user runs in their terminal. Three things follow from that,
and all of them live here so the rest of `core` does not have to know which
side of a sandbox it is on:

1. **The argv gets a prefix.** `command()` adds it, or does not.
2. **A temp file is not a temp file.** Inside a Flatpak `/tmp` is private to
   the sandbox, so a config written there is invisible to the host `ssh` we
   hand the path to. `temp_config()` puts it where both sides can see it.

3. **A missing openssh stops looking like one.** Outside a sandbox it arrives
   as `FileNotFoundError`; through the portal it arrives as an exit status,
   and a status is what `interpret()` reads as ssh's own verdict.
   `spawn_failed()` tells the two apart.

Note for anyone expecting an empty sandbox: the GNOME runtime does ship
`/usr/bin/ssh`. That makes the seam more necessary, not less — the app would
otherwise find a plausible ssh, validate against a version the user does not
run, and fail only on the options that need the host.
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
#: it the command runs against the runtime's own copy of ssh, which is not the
#: program the user runs in their terminal.
SPAWN: tuple[str, ...] = ("flatpak-spawn", "--host")

#: What `flatpak-spawn` exits with when it could not start the command at all.
SPAWN_FAILED = 1

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


def spawn_failed(returncode: int) -> bool:
    """Whether the portal refused, rather than the command having answered.

    Measured on flatpak 1.16.6 against `org.gnome.Platform//50`: with no such
    binary on the host, `flatpak-spawn` exits 1 and says `Portal call failed`
    on stderr; otherwise it forwards the child's own status untouched — 42
    comes back 42 and 255 comes back 255.

    That leaves 1 to mean one thing, because the real `ssh` never returns it
    in either shape we run. `ssh -F … -G host` exits 0 or 255 — a bad option,
    a missing config file and a failed lookup are all 255 — and the
    connection test runs `true` on the far side, which cannot exit 1 either.
    Matching on the message instead would mean matching on a sentence the
    portal translates.
    """
    return returncode == SPAWN_FAILED and in_sandbox()


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
