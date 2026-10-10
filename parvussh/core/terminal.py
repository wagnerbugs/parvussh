"""Open the user's own terminal, already running `ssh <alias>`.

The terminal is the user's, not ours — an embedded one is on the list of
things this app will not grow. The button runs the command the user would
type, in the program they would type it into, and it does so on the host side
of a sandbox, because that is where both the terminal and `ssh` live.

Two things here are not obvious:

1. **Which terminal.** The user's own choice, when they made one in the
   preferences. Otherwise Linux has no single answer: `xdg-terminal-exec` is
   the freedesktop proposal for "the terminal the user chose", and on Ubuntu
   it is what GNOME itself calls, so it goes first. After it come the
   terminals of the common desktops, each with the argument that separates its
   own options from the command it should run. That argument differs per
   program, which is why this is a table and not a guess.
2. **A failed connection must not vanish.** A terminal closes when its command
   exits, so an unreachable server would flash a window and take ssh's
   explanation with it. The command is wrapped in a few lines of `sh` that keep
   the window open when — and only when — ssh itself failed.

The connection reads the saved config, not the form. That is the difference
from `tester`, and it is deliberate: this is `ssh <alias>` exactly as the
terminal would run it a minute later, without the app in the way.
"""

from __future__ import annotations

import shlex
import subprocess
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePath

from parvussh.core import host

#: By absolute path: the test suite empties PATH, and through `flatpak-spawn`
#: the PATH is the host session's rather than ours. Every POSIX system has it.
SHELL = "/bin/sh"

#: Seconds to look a terminal up on the host. Only reached if the portal hangs.
FIND_TIMEOUT = 10

#: Seconds a terminal gets to fail before it counts as open. Long enough to
#: catch a program rejecting its arguments; the wait runs off the main thread.
SETTLE = 1.5

#: Prints the first of its arguments that is an installed program.
FIND = (
    'for name in "$@"; do '
    'if command -v "$name" >/dev/null 2>&1; then printf "%s" "$name"; exit 0; fi; '
    "done; exit 1"
)

#: Runs inside the terminal: `$1` is the alias, `$2` the sentence shown when
#: ssh failed. 255 is ssh's own status for a connection it could not make or
#: keep. A remote shell's status comes back unchanged, so a session that ends
#: on a failed command does not hold the window open with a wrong message.
HOLD = r"""printf '$ ssh %s\n' "$1"
ssh "$1"
status=$?
if [ "$status" -eq 255 ]; then
    printf '\n%s ' "$2"
    read -r _
fi
exit "$status"
"""

# Status codes, not sentences — the UI owns the words.
AUTOMATIC = "automatic"  # found in the table
CUSTOM = "custom"  # the user's own, and installed
MISSING = "missing"  # the user's own, and not installed
NO_TERMINAL = "no-terminal"  # nothing in the table is installed
OPENED = "opened"
FAILED = "failed"

DISPATCHER = "xdg-terminal-exec"


@dataclass(frozen=True)
class Terminal:
    name: str
    #: What goes between the program and the command it should run.
    separator: tuple[str, ...]


#: Tried in order; the first one installed wins. After `xdg-terminal-exec`,
#: the separators are the ones GLib uses to open `Terminal=true` applications,
#: plus Ptyxis, which GLib does not list and Ubuntu and Fedora now ship.
#: `x-terminal-emulator` is Debian's pick-your-own; its policy requires `-e`.
TERMINALS: tuple[Terminal, ...] = (
    Terminal(DISPATCHER, ("--",)),
    Terminal("ptyxis", ("--",)),
    Terminal("gnome-terminal", ("--",)),
    Terminal("kgx", ("-e",)),
    Terminal("konsole", ("-e",)),
    Terminal("xfce4-terminal", ("-x",)),
    Terminal("x-terminal-emulator", ("-e",)),
    Terminal("xterm", ("-e",)),
)


@dataclass(frozen=True)
class Choice:
    """Which terminal Acessar would open, and why."""

    status: str
    terminal: Terminal | None = None
    #: The program the user will see — Ptyxis, not the dispatcher that
    #: picked it. For `MISSING`, what they typed.
    name: str = ""


@dataclass(frozen=True)
class Launch:
    """What happened when the terminal was asked to open."""

    status: str
    terminal: str = ""
    returncode: int = 0


def find(candidates: Sequence[Terminal] = TERMINALS) -> Terminal | None:
    """The first of `candidates` installed where the terminal would open.

    Looked up by a shell on the host rather than with `shutil.which`, so the
    answer is the same inside a sandbox and outside one: `which` would search
    the sandbox, not the machine whose desktop the window appears on.
    """
    names = [candidate.name for candidate in candidates]
    try:
        result = subprocess.run(
            host.command([SHELL, "-c", FIND, "sh", *names]),
            capture_output=True,
            text=True,
            timeout=FIND_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    chosen = result.stdout.strip()
    return next((item for item in candidates if item.name == chosen), None)


def custom(command: str) -> Terminal:
    """The user's terminal command as a `Terminal`. Raises `ValueError` on bad quoting.

    A bare program the table knows — `/usr/bin/xterm` — gets the table's
    separator, so a path is all most people need to write. Anything else is
    taken word for word, with the command appended after it: `alacritty -e`,
    `wezterm start --`, or `foot`, which takes the command as it is.
    """
    program, *extra = shlex.split(command)
    if not extra:
        known = next((t for t in TERMINALS if t.name == PurePath(program).name), None)
        if known is not None:
            return Terminal(program, known.separator)
    return Terminal(program, tuple(extra))


def describe(terminal: Terminal) -> str:
    """The name of the program that will actually open, to show the user.

    `xdg-terminal-exec` only dispatches, so naming it would not answer the
    question. It is asked which desktop entry it would pick, and the last part
    of that ID is the name: `org.gnome.Ptyxis.desktop` is Ptyxis.
    """
    name = PurePath(terminal.name).name
    if name != DISPATCHER:
        return name
    try:
        result = subprocess.run(
            host.command([terminal.name, "--print-id"]),
            capture_output=True,
            text=True,
            timeout=FIND_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return name
    entry = result.stdout.strip().split(":")[0].removesuffix(".desktop")
    if result.returncode != 0 or not entry:
        return name
    return entry.rsplit(".", 1)[-1]


def choose(command: str = "") -> Choice:
    """The terminal for `command` from the preferences, or the system's own.

    A command the user set but that is not installed is `MISSING`, never a
    quiet fall back to the table: they chose something, and opening something
    else would hide that the choice is broken.
    """
    if not command.strip():
        found = find()
        if found is None:
            return Choice(NO_TERMINAL)
        return Choice(AUTOMATIC, found, describe(found))
    try:
        wanted = custom(command)
    except ValueError:
        return Choice(MISSING, name=command.strip())
    if find([wanted]) is None:
        return Choice(MISSING, name=wanted.name)
    return Choice(CUSTOM, wanted, describe(wanted))


def build_command(terminal: Terminal, alias: str, notice: str) -> list[str]:
    """The argv that opens `terminal` on `ssh alias`. Split out to be asserted on.

    The alias and the notice travel as positional arguments to `sh`, never
    pasted into the script, so neither can be read as shell code.
    """
    return host.command(
        [terminal.name, *terminal.separator, SHELL, "-c", HOLD, "sh", alias, notice]
    )


def launch(
    alias: str, notice: str, command: str = "", settle: float = SETTLE
) -> Launch:
    """Open a terminal on `ssh alias`. Blocks for up to `settle`.

    `notice` is the sentence shown under a failed connection; it arrives as an
    argument because `core` carries no translated text. `command` is the
    terminal from the preferences, empty for the system's own.

    Some terminals hand the window to an instance already running and exit 0
    at once; others run until the session ends. Both are success. Only a
    non-zero exit within `settle` seconds means the window never opened.
    """
    choice = choose(command)
    if choice.terminal is None:
        return Launch(choice.status, choice.name)
    try:
        process = subprocess.Popen(
            build_command(choice.terminal, alias, notice),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            # Its own session, so closing the app does not hang up on a
            # connection the user is still working in.
            start_new_session=True,
        )
    except OSError:
        # Found a moment ago and gone now, or not executable. Either way
        # there is no terminal this app can open.
        gone = MISSING if choice.status == CUSTOM else NO_TERMINAL
        return Launch(gone, choice.name)
    try:
        returncode = process.wait(timeout=settle)
    except subprocess.TimeoutExpired:
        # Still running, so the session lives in that window. Something has
        # to collect its exit status, or it lingers as a zombie.
        threading.Thread(target=process.wait, daemon=True).start()
        return Launch(OPENED, choice.name)
    if returncode == 0:
        return Launch(OPENED, choice.name)
    return Launch(FAILED, choice.name, returncode)
