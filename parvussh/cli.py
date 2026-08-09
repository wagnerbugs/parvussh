"""The process entry point: `parvussh` opens the window, `--list` prints.

Argument handling lives here rather than in `ui/app.py` so that `--list` never
imports GTK. Listing the aliases is exactly what you want over ssh on a machine
with no graphical stack installed, and `core` imports no `gi`
precisely so that is possible. The UI is imported lazily, inside `main`.

Unrecognised arguments are handed to GTK rather than refused: `--display`,
`--gtk-debug` and friends belong to it, and they used to reach it when this
module did not exist.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from parvussh import APP_NAME, __version__
from parvussh.core.models import Block
from parvussh.core.store import ConfigSet, main_config_path
from parvussh.core.writer import ConfigError
from parvussh.i18n import t

#: Two spaces between columns: enough to read, narrow enough for a long alias
#: and a long `user@host:port` to still fit an 80-column terminal.
GAP = "  "


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parvussh", description=t("cli.description"))
    parser.add_argument("-l", "--list", action="store_true", help=t("cli.list_help"))
    parser.add_argument(
        "--version", action="version", version=f"{APP_NAME} {__version__}"
    )
    return parser


def describe(block: Block) -> str:
    """The sidebar's second line, for a terminal.

    Core says nothing when there is no `HostName`; the wording is ours, and a
    wildcard block is supposed to have none — it sets defaults for other hosts,
    so reporting it as missing would name a problem that is not there.
    """
    subtitle = block.subtitle()
    if subtitle:
        return subtitle
    return t("cli.wildcard") if block.is_pattern else t("cli.no_hostname")


def list_hosts(stream: TextIO, main: Path | None = None) -> int:
    """Print one line per `Host` block. Returns the process exit code.

    A config that does not exist yet is not an error and is not created: the
    listing only reads, and `ConfigSet.load` would touch the disk on first run.
    """
    path = (main or main_config_path()).expanduser()
    if not path.exists():
        print(t("cli.no_config", path=path), file=stream)
        return 0

    try:
        config = ConfigSet.load(path)
    except (ConfigError, OSError) as error:
        print(t("cli.error.load", path=path, detail=error), file=sys.stderr)
        return 1

    hosts = config.hosts
    if not hosts:
        print(t("cli.empty", path=path), file=stream)
        return 0

    # The source column only earns its width when `Include` brought in more
    # than one file; with a single config it would repeat the same path.
    show_source = len({file.path for file in config.files}) > 1
    alias_width = max(len(block.title) for block in hosts)
    detail_width = max(len(describe(block)) for block in hosts)

    for block in hosts:
        columns = [f"{block.title:<{alias_width}}"]
        detail = describe(block)
        columns.append(f"{detail:<{detail_width}}" if show_source else detail)
        if show_source and block.source is not None:
            columns.append(str(block.source))
        print(GAP.join(columns).rstrip(), file=stream)
    return 0


def open_window(argv: list[str]) -> int:
    """Hand over to the UI. The import is inside on purpose — see the module
    docstring — and having it in a function of its own means a test can stand
    in for the whole handover instead of opening a real window."""
    from parvussh.ui.app import main as run_app

    return run_app(argv)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    args, rest = build_parser().parse_known_args(argv[1:])
    if args.list:
        return list_hosts(sys.stdout)
    return open_window([argv[0], *rest])


if __name__ == "__main__":
    raise SystemExit(main())
