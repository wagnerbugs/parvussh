"""Paths as the user knows them, rather than as the filesystem spells them."""

from __future__ import annotations

from pathlib import Path


def shorten_home(path: Path) -> str:
    """`/home/x/.ssh/config` -> `~/.ssh/config`. Left alone if not under home."""
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)
