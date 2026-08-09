"""Check that this machine can run ParvuSsh, and say what to install if not.

Stdlib only, and it never imports parvussh: this runs with the system python3,
before the venv exists, on a machine that may be missing everything it looks
for. Anything cleverer than that would fail before it could explain itself.

The floor it enforces is the one the README states. When that moves, this
moves with it.
"""

from __future__ import annotations

import importlib
import shutil
import sys

MINIMUM_PYTHON = (3, 11)
MINIMUM_GTK = (4, 12)
MINIMUM_ADW = (1, 5)

# One entry per package manager we can name packages for. The command is
# printed, never run: this script does not invoke sudo on anyone's behalf.
#
# The apt names are the ones this project has always used. The others are
# best-effort and have not been exercised on a real machine of that family --
# if one is wrong, fixing the table here is the whole fix.
PACKAGE_MANAGERS: dict[str, tuple[str, list[str], list[str]]] = {
    "apt": (
        "sudo apt install",
        [
            "python3-gi",
            "python3-gi-cairo",
            "gir1.2-gtk-4.0",
            "gir1.2-adw-1",
            "openssh-client",
            "python3-venv",
        ],
        ["xvfb"],
    ),
    "pacman": (
        "sudo pacman -S",
        ["python-gobject", "python-cairo", "gtk4", "libadwaita", "openssh"],
        ["xorg-server-xvfb"],
    ),
    "dnf": (
        "sudo dnf install",
        ["python3-gobject", "python3-cairo", "gtk4", "libadwaita", "openssh-clients"],
        ["xorg-x11-server-Xvfb"],
    ),
}


def version_of(module: str, spec: str) -> tuple[int, int] | None:
    """The major.minor of an installed typelib, or None if it is not there."""
    try:
        import gi

        gi.require_version(module, spec)
        namespace = importlib.import_module(f"gi.repository.{module}")
    except (ImportError, ValueError):
        return None
    return (namespace.get_major_version(), namespace.get_minor_version())


def as_text(version: tuple[int, int]) -> str:
    return ".".join(str(part) for part in version)


def detect_manager() -> tuple[str, str, list[str], list[str]] | None:
    for manager, (command, runtime, testing) in PACKAGE_MANAGERS.items():
        if shutil.which(manager):
            return manager, command, runtime, testing
    return None


def check() -> list[str]:
    """Everything wrong with this machine, phrased for someone installing."""
    problems: list[str] = []

    running = sys.version_info[:2]
    if running < MINIMUM_PYTHON:
        problems.append(
            f"Python {as_text(running)} is older than the minimum "
            f"{as_text(MINIMUM_PYTHON)}."
        )

    for module, spec, floor, label in (
        ("Gtk", "4.0", MINIMUM_GTK, "GTK"),
        ("Adw", "1", MINIMUM_ADW, "libadwaita"),
    ):
        found = version_of(module, spec)
        if found is None:
            problems.append(f"{label} {as_text(floor)} or newer is not installed.")
        elif found < floor:
            problems.append(
                f"{label} {as_text(found)} is older than the minimum "
                f"{as_text(floor)}. This one cannot be worked around: the app "
                f"needs widgets that version does not have."
            )
        else:
            print(f"{label} {as_text(found)}")

    for binary in ("ssh", "ssh-keygen"):
        if shutil.which(binary) is None:
            problems.append(f"`{binary}` is not on PATH. Install openssh.")

    return problems


def main() -> int:
    print(f"Python {as_text(sys.version_info[:2])}")
    problems = check()
    if not problems:
        print("This machine can run ParvuSsh.")
        return 0

    # The findings above went to stdout and the failure goes to stderr; without
    # this the two streams reach a terminal out of order.
    sys.stdout.flush()

    print("\nParvuSsh cannot run here yet:\n", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)

    detected = detect_manager()
    if detected is None:
        print(
            "\nInstall PyGObject, GTK 4, libadwaita and openssh with this "
            "system's package manager, then run this again.",
            file=sys.stderr,
        )
        return 1

    manager, command, runtime, testing = detected
    print(f"\nThis machine uses {manager}:\n", file=sys.stderr)
    print(f"  {command} {' '.join(runtime)}\n", file=sys.stderr)
    print(
        f"Add {' '.join(testing)} as well to run `make test-gui`.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
