"""Shared fixtures.

Safety rule from CLAUDE.md §8: no test may read or write the developer's real
`~/.ssh`. Everything that touches a home directory goes through `fake_home`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    """Raw bytes of a fixture — the round-trip test compares these exactly."""
    return (FIXTURES / name).read_bytes()


def fixture_text(name: str) -> str:
    return fixture_bytes(name).decode("utf-8")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(autouse=True)
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway `$HOME` with an empty `.ssh`, patched into `Path.home()`.

    Autouse on purpose: the developer's real `~/.ssh` must be unreachable from
    the suite even by accident, so isolation is the default rather than
    something a test has to remember to ask for.
    """
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home
