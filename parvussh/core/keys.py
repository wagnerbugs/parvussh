"""Find the keys already in `~/.ssh`, and make new ones.

Describing a key uses `ssh-keygen -l`, which reads the *public* half and never
prompts for a passphrase. Nothing here can lock the interface waiting for
input the user cannot see.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from parvussh.core import host

KEY_TYPES: tuple[str, ...] = ("ed25519", "ecdsa", "rsa")
DEFAULT_KEY_TYPE = "ed25519"
RSA_BITS = 4096
KEY_MODE = 0o600
DESCRIBE_TIMEOUT = 10
GENERATE_TIMEOUT = 120

# Files in ~/.ssh that are never private keys, however they are named.
SKIP_NAMES = frozenset(
    {
        "config",
        "known_hosts",
        "known_hosts.old",
        "authorized_keys",
        "environment",
        "rc",
        "agent.env",
        "allowed_signers",
    }
)
SKIP_SUFFIXES = (".pub", ".bak", ".old", ".tmp", ".conf", ".sock")
PRIVATE_MARKER = b"PRIVATE KEY"
SNIFF_BYTES = 200

# `256 SHA256:abc123... user@laptop (ED25519)`
DESCRIPTION = re.compile(r"^(\d+)\s+(\S+)\s+(.*?)\s+\(([A-Z0-9-]+)\)\s*$")


class KeyToolError(Exception):
    """`ssh-keygen` refused the job. The message is its own output, if any.

    Core raises typed errors rather than sentences; the UI decides what to
    say (docs/DECISIONS.md D3).
    """


class KeyExistsError(KeyToolError):
    """The target path is taken. Carries the path so the UI can name it."""

    def __init__(self, path: Path) -> None:
        super().__init__(str(path))
        self.path = path


class KeyToolMissing(KeyToolError):
    """No `ssh-keygen` on PATH — openssh-client is not installed."""


@dataclass(frozen=True)
class SshKey:
    """A private key file, described as far as `ssh-keygen` would tell us."""

    path: Path
    bits: int = 0
    fingerprint: str = ""
    comment: str = ""
    kind: str = ""

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def display_path(self) -> str:
        """`~/...` when the key sits under `$HOME`, so the config stays portable."""
        try:
            return f"~/{self.path.relative_to(Path.home())}"
        except ValueError:
            return str(self.path)

    @property
    def described(self) -> bool:
        return bool(self.fingerprint)


def ssh_dir() -> Path:
    return Path.home() / ".ssh"


def looks_like_a_key(path: Path) -> bool:
    """True when `path` is plausibly a private key rather than housekeeping."""
    name = path.name
    if name in SKIP_NAMES or name.startswith("."):
        return False
    if name.startswith("config.d") or ".bak-" in name:
        return False
    if name.endswith(SKIP_SUFFIXES):
        return False
    if path.with_name(f"{name}.pub").is_file():
        return True
    try:
        with path.open("rb") as stream:
            return PRIVATE_MARKER in stream.read(SNIFF_BYTES)
    except OSError:
        return False


def list_keys(directory: Path | None = None) -> list[SshKey]:
    """Every private key in `~/.ssh`, described, sorted by file name."""
    folder = directory or ssh_dir()
    if not folder.is_dir():
        return []
    found = [
        path for path in folder.iterdir() if path.is_file() and looks_like_a_key(path)
    ]
    return [describe(path) for path in sorted(found, key=lambda p: p.name)]


def describe(path: Path) -> SshKey:
    """Read a key's fingerprint and type. Degrades to the filename alone."""
    try:
        result = subprocess.run(
            host.command(["ssh-keygen", "-l", "-f", str(path)]),
            capture_output=True,
            text=True,
            timeout=DESCRIBE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return SshKey(path)
    if result.returncode != 0:
        return SshKey(path)
    match = DESCRIPTION.match(result.stdout.strip())
    if match is None:
        return SshKey(path)
    return SshKey(
        path=path,
        bits=int(match.group(1)),
        fingerprint=match.group(2),
        comment=match.group(3),
        kind=match.group(4),
    )


def generate_command(
    path: Path,
    kind: str = DEFAULT_KEY_TYPE,
    passphrase: str = "",
    comment: str = "",
) -> list[str]:
    """The exact argv we would run. Split out so a test can assert on it.

    Inside a Flatpak it arrives wrapped in `flatpak-spawn --host`, so the key
    is made by the same `ssh-keygen` the user has in their terminal (D5).
    """
    argv = ["ssh-keygen", "-t", kind, "-f", str(path), "-N", passphrase]
    if kind == "rsa":
        argv += ["-b", str(RSA_BITS)]
    if comment:
        argv += ["-C", comment]
    return host.command(argv)


def generate(
    path: Path,
    kind: str = DEFAULT_KEY_TYPE,
    passphrase: str = "",
    comment: str = "",
) -> SshKey:
    """Create a key pair at `path`.

    Refuses an existing path rather than letting `ssh-keygen` stop at an
    interactive overwrite prompt the user would never see.

    Known limitation, documented in the README: the passphrase is an argv
    element, so it is briefly visible in `ps` to other users of the same
    machine. Acceptable on a personal desktop.
    """
    if kind not in KEY_TYPES:
        raise KeyToolError(f"unsupported key type: {kind}")
    path = path.expanduser()
    if path.exists():
        raise KeyExistsError(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            generate_command(path, kind, passphrase, comment),
            capture_output=True,
            text=True,
            timeout=GENERATE_TIMEOUT,
            check=False,
        )
    except FileNotFoundError as error:
        raise KeyToolMissing() from error
    except subprocess.TimeoutExpired as error:
        raise KeyToolError("") from error
    if result.returncode != 0:
        raise KeyToolError((result.stderr or result.stdout).strip())

    os.chmod(path, KEY_MODE)
    return describe(path)


def copy_id_command(key: SshKey, alias: str) -> str:
    """The `ssh-copy-id` line that installs this key on `alias`."""
    return f"ssh-copy-id -i {key.display_path}.pub {alias}"
