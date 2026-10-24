"""The dated copy beside the config, named by a convention other tools share."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest

from parvussh.core import backups

STAMP = "20261024-131455"


@pytest.fixture
def config(fake_home: Path) -> Path:
    path = fake_home / ".ssh" / "config"
    path.write_text("Host a\n", encoding="utf-8")
    return path


@pytest.fixture
def frozen(monkeypatch: pytest.MonkeyPatch) -> str:
    """Every copy made inside the same second."""
    monkeypatch.setattr(backups.time, "strftime", lambda _format: STAMP)
    return STAMP


@pytest.fixture(params=[0o000, 0o277], ids=["umask-000", "umask-277"])
def umask(request: pytest.FixtureRequest) -> Iterator[None]:
    """One umask that narrows nothing, one that would leave the copy 0400."""
    previous = os.umask(request.param)
    yield
    os.umask(previous)


def test_the_name_is_the_file_name_and_a_local_timestamp(config: Path) -> None:
    copy = backups.create(config)

    assert copy.parent == config.parent
    assert copy.name.startswith("config.bak-")
    stamp = copy.name.removeprefix("config.bak-")
    assert len(stamp) == len("YYYYMMDD-HHMMSS")
    assert stamp[8] == "-"
    assert stamp.replace("-", "").isdigit()


def test_copies_in_the_same_second_count_up_from_two(config: Path, frozen: str) -> None:
    names = [backups.create(config).name for _ in range(3)]

    assert names == [
        f"config.bak-{frozen}",
        f"config.bak-{frozen}-2",
        f"config.bak-{frozen}-3",
    ]


def test_a_copy_already_there_is_never_overwritten(config: Path, frozen: str) -> None:
    """Another program may have taken the name; its copy is not ours to replace."""
    theirs = config.with_name(f"config.bak-{frozen}")
    theirs.write_text("their copy")

    ours = backups.create(config)

    assert theirs.read_text() == "their copy"
    assert ours.name == f"config.bak-{frozen}-2"


def test_the_copy_holds_the_exact_bytes(config: Path) -> None:
    original = b"Host a\r\n    User \xff\r\n"
    config.write_bytes(original)

    assert backups.create(config).read_bytes() == original


def test_the_copy_is_exactly_0600_whatever_the_file_and_umask(
    config: Path, umask: None
) -> None:
    config.chmod(0o644)

    copy = backups.create(config)

    assert stat.S_IMODE(copy.stat().st_mode) == 0o600


def test_the_copy_keeps_the_original_modification_time(config: Path) -> None:
    os.utime(config, ns=(1_700_000_000_000_000_000, 1_700_000_000_000_000_000))

    copy = backups.create(config)

    assert copy.stat().st_mtime_ns == 1_700_000_000_000_000_000


def test_a_copy_that_fails_halfway_leaves_nothing_behind(
    config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("no")

    monkeypatch.setattr(backups.os, "utime", refuse)

    with pytest.raises(PermissionError):
        backups.create(config)

    assert [path.name for path in config.parent.iterdir()] == ["config"]
