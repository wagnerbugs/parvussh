"""The dated copy beside the config, named by a convention other tools share."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest

from parvussh.core import backups
from tests.conftest import FakeTrash

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


# -- keeping the newest few --------------------------------------------------


def make(directory: Path, *names: str) -> None:
    for item in names:
        (directory / item).write_text(item)


def test_the_newest_three_stay_and_the_rest_go_to_the_trash(
    config: Path, trash: FakeTrash
) -> None:
    ssh = config.parent
    make(
        ssh,
        "config.bak-20261012-100855",
        "config.bak-20261015-142125",
        "config.bak-20261024-124225",
        "config.bak-20261024-131455",
        "config.bak-20261024-131455-2",
    )

    assert backups.prune(config, 3, trash) == []

    assert trash.names == ["config.bak-20261012-100855", "config.bak-20261015-142125"]
    assert sorted(item.name for item in ssh.iterdir()) == [
        "config",
        "config.bak-20261024-124225",
        "config.bak-20261024-131455",
        "config.bak-20261024-131455-2",
    ]


def test_newest_is_read_from_the_name_not_the_modification_time(
    config: Path, trash: FakeTrash
) -> None:
    """Our copies keep the original's mtime, so an old date can be on a new copy."""
    old, new = (
        config.with_name("config.bak-20250101-000000"),
        config.with_name("config.bak-20261024-131455"),
    )
    make(config.parent, old.name, new.name)
    os.utime(new, (1_000_000_000, 1_000_000_000))  # 2001

    backups.prune(config, 1, trash)

    assert trash.names == [old.name]


def test_the_number_counts_as_a_number(config: Path, trash: FakeTrash) -> None:
    """As text, `-10` sorts before `-2`; the tenth copy of a second is newer."""
    make(
        config.parent,
        *(f"config.bak-20261024-131455{suffix}" for suffix in ["", "-2", "-10"]),
    )

    backups.prune(config, 2, trash)

    assert trash.names == ["config.bak-20261024-131455"]
    assert backups.family(config) == [
        config.with_name("config.bak-20261024-131455-10"),
        config.with_name("config.bak-20261024-131455-2"),
    ]


def test_nothing_outside_the_exact_pattern_is_ever_touched(
    config: Path, trash: FakeTrash
) -> None:
    ssh = config.parent
    strangers = [
        "known_hosts.old",
        "config.bak-2026-10-12",  # made by hand
        "config.bak-20261015-pcd1310",  # made by hand
        "config.bak-20261024-131455.tmp",
        "config.bak-20261024-131455\n",  # `$` in a regex would let this in
        "config.bak-٢٠٢٦١٠٢٤-131455",  # `\d` without ASCII would too
        "config.bak",
        "config.antes-20261024-131455",
        "xconfig.bak-20261024-131455",
        "work.conf.bak-20261024-131455",  # another file's family
    ]
    make(ssh, *strangers)
    (ssh / "config.bak-20261024-000000").mkdir()
    (ssh / "config.bak-20261024-000001").symlink_to(ssh / "known_hosts.old")
    # The newest real copy, so anything else counted would be pruned.
    make(ssh, "config.bak-20991231-235959")

    backups.prune(config, 1, trash)

    assert trash.names == []
    assert (ssh / "config.bak-20261024-000000").is_dir()
    for name in strangers:
        assert (ssh / name).read_text() == name


def test_each_file_has_its_own_family(config: Path, trash: FakeTrash) -> None:
    included = config.with_name("work.conf")
    included.write_text("Host w\n")
    make(
        config.parent,
        "work.conf.bak-20261023-000000",
        "work.conf.bak-20261024-000000",
        "config.bak-20261023-000000",
    )

    backups.prune(included, 1, trash)

    assert trash.names == ["work.conf.bak-20261023-000000"]


def test_at_least_one_copy_always_stays(config: Path, trash: FakeTrash) -> None:
    make(config.parent, "config.bak-20261023-000000", "config.bak-20261024-000000")

    backups.prune(config, 0, trash)

    assert trash.names == ["config.bak-20261023-000000"]


def test_a_refused_copy_stays_and_the_others_still_go(
    config: Path, trash: FakeTrash
) -> None:
    make(
        config.parent,
        "config.bak-20261021-000000",
        "config.bak-20261022-000000",
        "config.bak-20261023-000000",
    )
    trash.refuse = {"config.bak-20261022-000000"}

    refused = backups.prune(config, 1, trash)

    assert [path.name for path, _ in refused] == ["config.bak-20261022-000000"]
    assert (config.parent / "config.bak-20261022-000000").exists()  # not deleted
    assert trash.names == ["config.bak-20261021-000000"]


def test_a_copy_made_by_save_joins_the_family(config: Path, trash: FakeTrash) -> None:
    make(config.parent, "config.bak-20000101-000000")

    made = backups.create(config)

    assert backups.family(config) == [
        made,
        config.with_name("config.bak-20000101-000000"),
    ]
