"""Saving over a file that another program changed after we read it.

The case that matters: the app is open, a provisioning script moves one server
from `Port 22` to `Port 1310`, and the user then saves a different connection.
The script's change must survive the save.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.core.merge import ConfigConflict
from parvussh.core.models import Entry
from parvussh.core.store import ConfigSet
from parvussh.core.writer import ConfigError
from tests.conftest import FakeBin

ORIGINAL = """# my servers
Host web
    HostName 203.0.113.10
    Port 22

Host db
    HostName 203.0.113.20
    User postgres
"""


@pytest.fixture
def config(fake_home: Path) -> Path:
    path = fake_home / ".ssh" / "config"
    path.write_text(ORIGINAL, encoding="utf-8")
    return path


@pytest.fixture
def loaded(config: Path, fake_bin: FakeBin) -> ConfigSet:
    fake_bin.install("ssh", returncode=0)
    return ConfigSet.load()


def host(config_set: ConfigSet, alias: str):
    return next(block for block in config_set.hosts if block.title == alias)


def edit(config_set: ConfigSet, alias: str, **values: str) -> None:
    """What the form does: replace the entries and mark the block dirty."""
    block = host(config_set, alias)
    block.entries = [Entry(keyword, value) for keyword, value in values.items()]
    block.dirty = True


def backups(config: Path) -> list[Path]:
    return sorted(config.parent.glob("config.bak-*"))


# -- the change on disk survives -------------------------------------------


def test_a_port_changed_elsewhere_survives_saving_another_host(
    loaded: ConfigSet, config: Path
) -> None:
    config.write_text(ORIGINAL.replace("Port 22", "Port 1310"), encoding="utf-8")
    edit(loaded, "db", HostName="203.0.113.20", User="admin")

    loaded.save()

    assert config.read_text() == (
        "# my servers\n"
        "Host web\n"
        "    HostName 203.0.113.10\n"
        "    Port 1310\n"
        "\n"
        "Host db\n"
        "    HostName 203.0.113.20\n"
        "    User admin\n"
    )


def test_a_host_appended_elsewhere_survives_editing_the_last_one(
    loaded: ConfigSet, config: Path
) -> None:
    """Appending moves the blank line above the new host out of our block."""
    appended = ORIGINAL + "\nHost new-vps\n    HostName 203.0.113.30\n"
    config.write_text(appended, encoding="utf-8")
    edit(loaded, "db", HostName="203.0.113.20", User="admin")

    loaded.save()

    assert config.read_text() == appended.replace("User postgres", "User admin")


def test_a_host_added_here_goes_after_the_one_added_elsewhere(
    loaded: ConfigSet, config: Path
) -> None:
    config.write_text(ORIGINAL + "\nHost new-vps\n", encoding="utf-8")
    loaded.add_host("mine")

    loaded.save()

    assert [block.title for block in ConfigSet.load().hosts] == [
        "web",
        "db",
        "new-vps",
        "mine",
    ]


def test_a_duplicate_stays_below_its_original(loaded: ConfigSet, config: Path) -> None:
    config.write_text(ORIGINAL.replace("postgres", "admin"), encoding="utf-8")
    loaded.duplicate(host(loaded, "db"), "db-copy")
    # Not at the end, so its place is found through the neighbour above.
    loaded.duplicate(host(loaded, "web"), "web-copy")

    loaded.save()

    reread = ConfigSet.load()
    assert [block.title for block in reread.hosts] == [
        "web",
        "web-copy",
        "db",
        "db-copy",
    ]
    assert host(reread, "db").get("User") == "admin"


def test_a_duplicate_of_an_edited_host_stays_below_it(
    loaded: ConfigSet, config: Path
) -> None:
    config.write_text(ORIGINAL + "\nHost new-vps\n", encoding="utf-8")
    edit(loaded, "web", HostName="203.0.113.11")
    loaded.duplicate(host(loaded, "web"), "web-copy")

    loaded.save()

    assert [block.title for block in ConfigSet.load().hosts] == [
        "web",
        "web-copy",
        "db",
        "new-vps",
    ]


def test_a_delete_here_keeps_a_change_made_elsewhere(
    loaded: ConfigSet, config: Path
) -> None:
    config.write_text(ORIGINAL.replace("Port 22", "Port 1310"), encoding="utf-8")
    loaded.remove(host(loaded, "db"))

    loaded.save()

    reread = ConfigSet.load()
    assert [block.title for block in reread.hosts] == ["web"]
    assert host(reread, "web").get("Port") == "1310"


def test_an_unchanged_block_stays_byte_identical_after_a_rebase(
    loaded: ConfigSet, config: Path
) -> None:
    changed = ORIGINAL.replace("Port 22", "Port   1310    # moved")
    config.write_text(changed, encoding="utf-8")
    edit(loaded, "db", HostName="203.0.113.20", User="admin")

    loaded.save()

    assert "    Port   1310    # moved\n" in config.read_text()


def test_the_backup_holds_the_file_as_the_other_program_left_it(
    loaded: ConfigSet, config: Path
) -> None:
    """The copy is of what was on disk, not of what we read an hour ago."""
    changed = ORIGINAL.replace("Port 22", "Port 1310")
    config.write_text(changed, encoding="utf-8")
    edit(loaded, "db", HostName="203.0.113.20", User="admin")

    loaded.save()

    assert [path.read_text() for path in backups(config)] == [changed]


def test_the_model_follows_the_file_after_a_rebased_save(
    loaded: ConfigSet, config: Path
) -> None:
    config.write_text(ORIGINAL.replace("Port 22", "Port 1310"), encoding="utf-8")
    edit(loaded, "db", HostName="203.0.113.20", User="admin")

    loaded.save()

    assert host(loaded, "web").get("Port") == "1310"
    edit(loaded, "web", HostName="203.0.113.11", Port="1310")
    loaded.save()  # the second save starts from what the first one wrote
    assert "HostName 203.0.113.11" in config.read_text()
    assert "User admin" in config.read_text()


def test_an_included_file_is_caught_up_on_its_own(
    fake_home: Path, fake_bin: FakeBin
) -> None:
    ssh = fake_home / ".ssh"
    (ssh / "extra.conf").write_text("Host a\n    Port 22\n\nHost b\n    User x\n")
    (ssh / "config").write_text("Include extra.conf\n")
    fake_bin.install("ssh", returncode=0)
    config_set = ConfigSet.load()

    (ssh / "extra.conf").write_text("Host a\n    Port 1310\n\nHost b\n    User x\n")
    edit(config_set, "b", User="y")
    config_set.save()

    assert (ssh / "extra.conf").read_text() == (
        "Host a\n    Port 1310\n\nHost b\n    User y\n"
    )


def test_an_unchanged_file_is_not_rebased(loaded: ConfigSet) -> None:
    """Nothing changed on disk, so the blocks we hold are the ones written."""
    blocks = list(loaded.main_file.blocks)
    edit(loaded, "db", HostName="203.0.113.20", User="admin")

    loaded.save()

    assert all(a is b for a, b in zip(loaded.main_file.blocks, blocks, strict=True))


# -- when the edit cannot be replayed, nothing is written -------------------


def assert_refused(loaded: ConfigSet, config: Path, on_disk: str) -> None:
    with pytest.raises(ConfigConflict) as raised:
        loaded.save()
    assert raised.value.path == config.resolve()
    assert config.read_text() == on_disk
    assert backups(config) == []


def test_the_same_host_changed_on_both_sides_is_a_conflict(
    loaded: ConfigSet, config: Path
) -> None:
    changed = ORIGINAL.replace("Port 22", "Port 1310")
    config.write_text(changed, encoding="utf-8")
    edit(loaded, "web", HostName="203.0.113.99", Port="22")

    assert_refused(loaded, config, changed)
    # The edit is still there, unsaved, for the caller to report.
    assert host(loaded, "web").dirty is True
    assert host(loaded, "web").get("HostName") == "203.0.113.99"


def test_deleting_a_host_changed_elsewhere_is_a_conflict(
    loaded: ConfigSet, config: Path
) -> None:
    changed = ORIGINAL.replace("Port 22", "Port 1310")
    config.write_text(changed, encoding="utf-8")
    loaded.remove(host(loaded, "web"))

    assert_refused(loaded, config, changed)


def test_a_host_removed_elsewhere_is_a_conflict_when_edited_here(
    loaded: ConfigSet, config: Path
) -> None:
    changed = ORIGINAL.split("\nHost db")[0]
    config.write_text(changed, encoding="utf-8")
    edit(loaded, "db", User="admin")

    assert_refused(loaded, config, changed)


def test_a_duplicate_whose_original_changed_elsewhere_is_a_conflict(
    loaded: ConfigSet, config: Path
) -> None:
    """Below the original is where it goes, and the original is gone."""
    changed = ORIGINAL.replace("Port 22", "Port 1310")
    config.write_text(changed, encoding="utf-8")
    loaded.duplicate(host(loaded, "web"), "web-copy")

    assert_refused(loaded, config, changed)


def test_two_identical_blocks_are_a_conflict_rather_than_a_guess(
    fake_home: Path, fake_bin: FakeBin
) -> None:
    config = fake_home / ".ssh" / "config"
    # The leading host gives both twins the same blank line above them.
    twins = "Host z\n\nHost a\n    User x\n\nHost a\n    User x\n"
    config.write_text(twins)
    fake_bin.install("ssh", returncode=0)
    config_set = ConfigSet.load()

    changed = twins + "\nHost c\n"
    config.write_text(changed)
    config_set.hosts[1].entries = [Entry("User", "y")]
    config_set.hosts[1].dirty = True

    assert_refused(config_set, config, changed)


def test_a_block_copied_elsewhere_is_a_conflict_when_edited_here(
    loaded: ConfigSet, config: Path
) -> None:
    """Two copies on disk now, and no telling which one the edit belongs to."""
    changed = ORIGINAL + "\nHost db\n    HostName 203.0.113.20\n    User postgres\n"
    config.write_text(changed, encoding="utf-8")
    edit(loaded, "db", User="admin")

    assert_refused(loaded, config, changed)


def test_one_of_two_twins_changed_elsewhere_is_a_conflict(
    fake_home: Path, fake_bin: FakeBin
) -> None:
    """The twin left on disk may be the other one; replacing it would be a guess."""
    config = fake_home / ".ssh" / "config"
    twins = "Host z\n\nHost a\n    User x\n\nHost a\n    User x\n"
    config.write_text(twins)
    fake_bin.install("ssh", returncode=0)
    config_set = ConfigSet.load()

    changed = twins.replace("User x", "User w", 1)
    config.write_text(changed)
    config_set.hosts[1].entries = [Entry("User", "y")]
    config_set.hosts[1].dirty = True

    assert_refused(config_set, config, changed)


# -- the bookkeeping that makes the next save right -------------------------


def test_our_own_write_is_not_mistaken_for_another_program(
    loaded: ConfigSet,
) -> None:
    edit(loaded, "db", User="admin")
    loaded.save()
    blocks = list(loaded.main_file.blocks)

    edit(loaded, "web", HostName="203.0.113.11")
    loaded.save()

    assert all(a is b for a, b in zip(loaded.main_file.blocks, blocks, strict=True))


def test_a_host_saved_earlier_is_not_added_twice_by_a_later_rebase(
    loaded: ConfigSet, config: Path
) -> None:
    loaded.add_host("mine")
    loaded.save()

    config.write_text(config.read_text().replace("Port 22", "Port 1310"))
    edit(loaded, "db", User="admin")
    loaded.save()

    assert [block.title for block in ConfigSet.load().hosts] == ["web", "db", "mine"]


def test_a_refused_save_after_a_rebase_can_be_retried(
    loaded: ConfigSet, config: Path, fake_bin: FakeBin
) -> None:
    """ssh refuses the first try; the file changes again before the second."""
    config.write_text(ORIGINAL.replace("Port 22", "Port 1310"), encoding="utf-8")
    edit(loaded, "db", User="admin")
    fake_bin.install("ssh", returncode=255, stderr="nope")
    with pytest.raises(ConfigError):
        loaded.save()
    blocks = list(loaded.main_file.blocks)

    fake_bin.install("ssh", returncode=0)
    loaded.save()  # nothing new on disk: no second rebase
    assert all(a is b for a, b in zip(loaded.main_file.blocks, blocks, strict=True))


def test_an_edit_survives_two_rebases_in_a_row(
    loaded: ConfigSet, config: Path, fake_bin: FakeBin
) -> None:
    config.write_text(ORIGINAL.replace("Port 22", "Port 1310"), encoding="utf-8")
    edit(loaded, "db", User="admin")
    fake_bin.install("ssh", returncode=255, stderr="nope")
    with pytest.raises(ConfigError):
        loaded.save()

    config.write_text(config.read_text() + "\nHost new-vps\n")
    fake_bin.install("ssh", returncode=0)
    loaded.save()

    reread = ConfigSet.load()
    assert [block.title for block in reread.hosts] == ["web", "db", "new-vps"]
    assert host(reread, "db").get("User") == "admin"
    assert host(reread, "web").get("Port") == "1310"


# -- noticing the change before a save -------------------------------------


def test_a_freshly_loaded_set_is_not_stale(loaded: ConfigSet) -> None:
    assert loaded.stale() is False


def test_a_write_from_elsewhere_makes_it_stale(loaded: ConfigSet, config: Path) -> None:
    config.write_text(ORIGINAL.replace("Port 22", "Port 1310"), encoding="utf-8")
    assert loaded.stale() is True


def test_our_own_save_does_not_make_it_stale(loaded: ConfigSet) -> None:
    edit(loaded, "db", User="admin")
    loaded.save()
    assert loaded.stale() is False


def test_a_file_that_cannot_be_read_right_now_is_not_counted(
    loaded: ConfigSet, config: Path
) -> None:
    """Reloading a file another program is replacing would recreate it empty."""
    config.unlink()
    assert loaded.stale() is False


def test_the_set_is_dirty_while_an_edit_is_unsaved(loaded: ConfigSet) -> None:
    assert loaded.dirty is False
    edit(loaded, "db", User="admin")
    assert loaded.dirty is True
    loaded.save()
    assert loaded.dirty is False
