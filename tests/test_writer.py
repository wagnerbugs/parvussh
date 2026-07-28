"""The write path: validate, back up, replace. Nothing half-done reaches disk."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import pytest

from parvussh.core.writer import (
    CONFIG_MODE,
    ConfigError,
    backup_path,
    ensure_exists,
    validate,
    write_atomic,
)
from tests.conftest import FakeBin

BACKUP_PATTERN = re.compile(r"^config\.bak-\d{8}-\d{6}(-\d+)?$")
ORIGINAL = "Host antigo\n    HostName 203.0.113.1\n"
REPLACEMENT = "Host novo\n    HostName 203.0.113.2\n"


@pytest.fixture
def config(fake_home: Path) -> Path:
    path = fake_home / ".ssh" / "config"
    path.write_text(ORIGINAL, encoding="utf-8")
    path.chmod(CONFIG_MODE)
    return path


def mode_of(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


# -- first run -------------------------------------------------------------


def test_ensure_exists_creates_the_ssh_directory_and_an_empty_config(
    fake_home: Path,
) -> None:
    (fake_home / ".ssh").rmdir()
    path = fake_home / ".ssh" / "config"

    ensure_exists(path)

    assert path.read_text() == ""
    assert mode_of(path) == CONFIG_MODE
    assert mode_of(path.parent) == 0o700


def test_ensure_exists_leaves_an_existing_config_alone(config: Path) -> None:
    ensure_exists(config)
    assert config.read_text() == ORIGINAL


# -- validation ------------------------------------------------------------


def test_validation_passes_when_ssh_is_happy(fake_bin: FakeBin) -> None:
    fake_bin.install("ssh", returncode=0)
    validate(REPLACEMENT)  # does not raise
    assert fake_bin.args("ssh")[:1] == ["-F"]
    assert fake_bin.args("ssh")[-2:] == ["-G", "parvussh-validation.invalid"]


def test_validation_failure_raises_with_ssh_own_message(fake_bin: FakeBin) -> None:
    fake_bin.install(
        "ssh", returncode=255, stderr="line 2: Bad configuration option: X"
    )

    with pytest.raises(ConfigError) as raised:
        validate(REPLACEMENT)

    assert "Bad configuration option: X" in str(raised.value)


def test_validation_hides_the_temp_path_behind_the_word_config(
    fake_bin: FakeBin,
) -> None:
    """The user never saw our temp file; naming it would only confuse them."""
    # %F expands to whatever path validate() passed after -F.
    fake_bin.install(
        "ssh", returncode=255, stderr="%F: line 2: Bad configuration option: X"
    )

    with pytest.raises(ConfigError) as raised:
        validate(REPLACEMENT)

    temp = fake_bin.args("ssh")[1]
    assert temp.startswith("/")  # it really was a path, so the check has teeth
    assert temp not in str(raised.value)
    assert str(raised.value) == "config: line 2: Bad configuration option: X"


def test_validation_is_skipped_when_ssh_is_not_installed(fake_bin: FakeBin) -> None:
    """No openssh-client is a reason to skip the check, not to block a save."""
    validate("Host x\n")  # nothing installed on the empty PATH
    assert fake_bin.calls("ssh") == []


def test_validation_writes_a_private_temp_file_and_removes_it(
    fake_bin: FakeBin,
) -> None:
    fake_bin.install("ssh", returncode=0)
    validate(REPLACEMENT)
    temp = Path(fake_bin.args("ssh")[1])
    assert not temp.exists()


def test_validation_removes_the_temp_file_even_when_it_raises(
    fake_bin: FakeBin,
) -> None:
    fake_bin.install("ssh", returncode=1, stderr="nope")
    with pytest.raises(ConfigError):
        validate(REPLACEMENT)
    assert (
        list(Path(os.environ.get("TMPDIR", "/tmp")).glob("parvussh-*.sshconfig")) == []
    )


# -- writing ---------------------------------------------------------------


def test_write_creates_a_dated_backup(config: Path) -> None:
    backup = write_atomic(config, REPLACEMENT)

    assert backup is not None
    assert BACKUP_PATTERN.match(backup.name), backup.name
    assert backup.read_text() == ORIGINAL
    assert config.read_text() == REPLACEMENT


def test_two_saves_in_the_same_second_keep_both_backups(config: Path) -> None:
    """Losing the earlier state to a name collision defeats the point."""
    first = write_atomic(config, REPLACEMENT)
    second = write_atomic(config, "Host terceiro\n")

    assert first != second
    assert first is not None and second is not None
    assert first.read_text() == ORIGINAL
    assert second.read_text() == REPLACEMENT


def test_backup_path_counts_up_past_an_existing_name(config: Path) -> None:
    taken = backup_path(config)
    taken.touch()
    assert backup_path(config).name.startswith(taken.name)
    assert backup_path(config) != taken


def test_a_brand_new_file_gets_no_backup(fake_home: Path) -> None:
    path = fake_home / ".ssh" / "config"
    assert write_atomic(path, REPLACEMENT) is None
    assert path.read_text() == REPLACEMENT


def test_the_written_file_is_private(config: Path) -> None:
    write_atomic(config, REPLACEMENT)
    assert mode_of(config) == CONFIG_MODE


def test_the_write_leaves_no_temp_file_behind(config: Path) -> None:
    write_atomic(config, REPLACEMENT)
    leftovers = [p.name for p in config.parent.iterdir() if p.name.startswith(".")]
    assert leftovers == []
