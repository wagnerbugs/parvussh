"""Everything between "the user pressed Salvar" and bytes on disk.

The order is not negotiable: validate, then back up, then write atomically.
A config that ssh refuses never reaches the file, and a file we do overwrite
always has a dated copy beside it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from parvussh.core import host

# A name that cannot resolve: we want ssh to parse the file, not connect.
VALIDATION_HOST = "parvussh-validation.invalid"
VALIDATION_TIMEOUT = 10

CONFIG_MODE = 0o600
SSH_DIR_MODE = 0o700
BACKUP_STAMP = "%Y%m%d-%H%M%S"


class ConfigError(Exception):
    """The file was not written.

    The message is ssh's own output, forwarded verbatim so the user sees which
    option was refused. It may be empty when ssh said nothing; the UI supplies
    the wording in that case, because core carries no translated text.
    """


def ensure_exists(path: Path) -> None:
    """Create `~/.ssh` (0700) and an empty config (0600) on first run."""
    path.parent.mkdir(mode=SSH_DIR_MODE, parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=CONFIG_MODE)


def validate(text: str) -> None:
    """Ask ssh whether it accepts this config; raise `ConfigError` if not.

    A missing or hanging `ssh` is not an error. Refusing to save on a machine
    without openssh-client would trade a real capability for a check we cannot
    run, so validation is skipped instead.
    """
    with host.temp_config(text) as tmp:
        try:
            result = subprocess.run(
                host.command(["ssh", "-F", tmp, "-G", VALIDATION_HOST]),
                capture_output=True,
                text=True,
                timeout=VALIDATION_TIMEOUT,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return
        if host.spawn_failed(result.returncode):
            # The host has no openssh. Same as this machine not having it:
            # a check we cannot run must never be what stops a save.
            return
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            # ssh quotes the temp path back at us; the user knows it as
            # their config.
            raise ConfigError(message.replace(tmp, "config"))


def backup_path(path: Path) -> Path:
    """A free `<name>.bak-YYYYMMDD-HHMMSS`, counting up within the same second.

    Two saves inside one second must not leave the user with one backup: the
    second would overwrite the copy of the state they may want back.
    """
    stamp = time.strftime(BACKUP_STAMP)
    candidate = path.with_name(f"{path.name}.bak-{stamp}")
    attempt = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.bak-{stamp}-{attempt}")
        attempt += 1
    return candidate


def write_atomic(path: Path, text: str) -> Path | None:
    """Back the file up, then replace it in one step. Returns the backup path.

    The temp file is created in the target's own directory so `os.replace` is
    a rename within one filesystem — either the old file or the new one is
    there, never a half-written mixture.
    """
    backup = None
    if path.exists():
        backup = backup_path(path)
        shutil.copy2(path, backup)

    handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".parvussh-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.chmod(tmp, CONFIG_MODE)
        os.replace(tmp, path)
    except OSError:
        Path(tmp).unlink(missing_ok=True)
        raise
    return backup
