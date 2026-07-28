"""Loading the config set, editing it, and writing it back safely."""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.core.models import Entry
from parvussh.core.store import ConfigSet, main_config_path
from parvussh.core.writer import ConfigError
from tests.conftest import FakeBin, fixture_text

MAIN = """Host vps
    HostName 203.0.113.10
    User deploy

Host *
    ServerAliveInterval 60
"""


@pytest.fixture
def ssh(fake_home: Path) -> Path:
    return fake_home / ".ssh"


@pytest.fixture
def loaded(ssh: Path, fake_bin: FakeBin) -> ConfigSet:
    """A config set whose saves are validated by a shim that always agrees."""
    (ssh / "config").write_text(MAIN, encoding="utf-8")
    fake_bin.install("ssh", returncode=0)
    return ConfigSet.load()


def aliases(config_set: ConfigSet) -> list[str]:
    return [block.title for block in config_set.hosts]


# -- loading ---------------------------------------------------------------


def test_load_creates_the_config_on_first_run(ssh: Path) -> None:
    (ssh / "config").unlink(missing_ok=True)

    config_set = ConfigSet.load()

    assert (ssh / "config").exists()
    assert config_set.hosts == []
    assert config_set.main == main_config_path().resolve()


def test_load_reads_hosts_in_file_order(loaded: ConfigSet) -> None:
    assert aliases(loaded) == ["vps", "*"]


def test_load_follows_include_and_makes_its_hosts_editable(ssh: Path) -> None:
    (ssh / "config.d").mkdir()
    (ssh / "config.d" / "work.conf").write_text("Host trabalho\n    User dev\n")
    (ssh / "config").write_text("Include config.d/*.conf\n\n" + MAIN)

    config_set = ConfigSet.load()

    assert aliases(config_set) == ["vps", "*", "trabalho"]
    assert len(config_set.files) == 2
    trabalho = next(b for b in config_set.hosts if b.title == "trabalho")
    assert config_set.file_of(trabalho).path.name == "work.conf"


def test_include_resolves_a_relative_path_against_the_ssh_directory(
    ssh: Path,
) -> None:
    (ssh / "extra.conf").write_text("Host extra\n")
    (ssh / "config").write_text("Include extra.conf\n")

    assert aliases(ConfigSet.load()) == ["extra"]


def test_include_expands_a_tilde(ssh: Path) -> None:
    (ssh / "extra.conf").write_text("Host extra\n")
    (ssh / "config").write_text("Include ~/.ssh/extra.conf\n")

    assert aliases(ConfigSet.load()) == ["extra"]


def test_include_handles_a_quoted_path_with_spaces(ssh: Path) -> None:
    (ssh / "com espaco.conf").write_text("Host espacado\n")
    (ssh / "config").write_text('Include "com espaco.conf"\n')

    assert aliases(ConfigSet.load()) == ["espacado"]


def test_include_with_an_unbalanced_quote_does_not_crash(ssh: Path) -> None:
    (ssh / "config").write_text('Include "sem-fechar\n')
    assert ConfigSet.load().hosts == []


def test_include_pointing_nowhere_is_ignored(ssh: Path) -> None:
    (ssh / "config").write_text("Include nao-existe/*.conf\n" + MAIN)
    assert aliases(ConfigSet.load()) == ["vps", "*"]


def test_an_include_cycle_terminates(ssh: Path) -> None:
    (ssh / "a.conf").write_text("Include b.conf\nHost a\n")
    (ssh / "b.conf").write_text("Include a.conf\nHost b\n")
    (ssh / "config").write_text("Include a.conf\n")

    config_set = ConfigSet.load()

    assert sorted(aliases(config_set)) == ["a", "b"]
    assert len(config_set.files) == 3


def test_a_file_including_itself_terminates(ssh: Path) -> None:
    (ssh / "config").write_text("Include config\nHost so-eu\n")
    assert aliases(ConfigSet.load()) == ["so-eu"]


def test_a_crlf_include_keeps_its_own_line_endings(ssh: Path) -> None:
    (ssh / "messy.config").write_bytes(fixture_text("messy.config").encode("utf-8"))
    (ssh / "config").write_text("Include messy.config\n")

    config_set = ConfigSet.load()

    included = next(f for f in config_set.files if f.path.name == "messy.config")
    assert included.newline == "\r\n"
    assert config_set.main_file.newline == "\n"


def test_saving_a_crlf_file_writes_crlf_back(ssh: Path, fake_bin: FakeBin) -> None:
    """A config saved on Windows must not silently become an LF file."""
    (ssh / "messy.config").write_bytes(fixture_text("messy.config").encode("utf-8"))
    (ssh / "config").write_text("Include messy.config\n")
    fake_bin.install("ssh", returncode=0)
    config_set = ConfigSet.load()

    block = next(b for b in config_set.hosts if b.title == "crlf-host")
    block.entries = [Entry("HostName", "198.51.100.9")]
    block.dirty = True
    config_set.save()

    written = (ssh / "messy.config").read_bytes()
    assert b"HostName 198.51.100.9\r\n" in written
    assert b"\n" in written
    assert written.replace(b"\r\n", b"").count(b"\n") == 0  # no bare LF anywhere


# -- editing ---------------------------------------------------------------


def test_add_host_appends_to_the_main_file(loaded: ConfigSet) -> None:
    block = loaded.add_host("nova")

    assert aliases(loaded) == ["vps", "*", "nova"]
    assert loaded.file_of(block) is loaded.main_file
    assert loaded.main_file.dirty


def test_duplicate_copies_entries_and_comments_below_the_original(
    loaded: ConfigSet,
) -> None:
    original = loaded.hosts[0]
    original.entries[0].comments = ["    # endereço de produção"]

    copy = loaded.duplicate(original, "vps-copia")

    assert aliases(loaded) == ["vps", "vps-copia", "*"]
    assert copy.get("HostName") == "203.0.113.10"
    assert copy.comments_for("HostName") == ["    # endereço de produção"]
    # A copy, not a shared reference: editing one must not touch the other.
    copy.entries[0].value = "203.0.113.99"
    assert original.get("HostName") == "203.0.113.10"


def test_remove_deletes_the_block_it_was_given(loaded: ConfigSet) -> None:
    loaded.remove(loaded.hosts[0])
    assert aliases(loaded) == ["*"]


def test_remove_picks_by_identity_not_by_equal_contents(loaded: ConfigSet) -> None:
    """Two blocks can hold identical text; only the chosen one may go."""
    first = loaded.add_host("igual")
    second = loaded.add_host("igual")

    loaded.remove(second)

    assert [b for b in loaded.hosts if b is first] == [first]
    assert [b for b in loaded.hosts if b is second] == []


def test_file_of_rejects_a_block_we_never_loaded(loaded: ConfigSet) -> None:
    stray = ConfigSet.load().hosts[0]
    with pytest.raises(ConfigError):
        loaded.file_of(stray)


# -- saving ----------------------------------------------------------------


def test_save_writes_only_dirty_files(ssh: Path, fake_bin: FakeBin) -> None:
    (ssh / "extra.conf").write_text("Host extra\n    User dev\n")
    (ssh / "config").write_text("Include extra.conf\n\n" + MAIN)
    fake_bin.install("ssh", returncode=0)
    config_set = ConfigSet.load()
    untouched = (ssh / "extra.conf").read_bytes()

    config_set.hosts[0].dirty = True
    written = config_set.save()

    assert written == [ssh / "config"]
    assert (ssh / "extra.conf").read_bytes() == untouched


def test_a_second_save_with_no_changes_writes_nothing(loaded: ConfigSet) -> None:
    loaded.hosts[0].dirty = True
    assert loaded.save() != []
    assert loaded.save() == []


def test_save_clears_the_dirty_flags_and_refreshes_raw(loaded: ConfigSet) -> None:
    block = loaded.hosts[0]
    block.entries = [Entry("HostName", "203.0.113.55")]
    block.dirty = True

    loaded.save()

    assert block.dirty is False
    assert block.raw == ["Host vps", "    HostName 203.0.113.55"]
    assert (
        "203.0.113.55" in (loaded.main / "..").resolve().joinpath("config").read_text()
    )


def test_saving_an_edit_leaves_every_other_block_byte_identical(
    loaded: ConfigSet, ssh: Path
) -> None:
    block = loaded.hosts[0]
    block.entries = [Entry("HostName", "203.0.113.55"), Entry("User", "deploy")]
    block.dirty = True

    loaded.save()
    text = (ssh / "config").read_text()

    assert "HostName 203.0.113.55" in text
    assert "Host *\n    ServerAliveInterval 60\n" in text


def test_a_refused_config_leaves_the_file_untouched(
    ssh: Path, fake_bin: FakeBin
) -> None:
    (ssh / "config").write_text(MAIN, encoding="utf-8")
    fake_bin.install("ssh", returncode=0)
    config_set = ConfigSet.load()
    before = (ssh / "config").read_bytes()

    fake_bin.install(
        "ssh", returncode=255, stderr="%F: line 2: Bad configuration option"
    )
    config_set.hosts[0].entries = [Entry("Nonsense", "x")]
    config_set.hosts[0].dirty = True

    with pytest.raises(ConfigError):
        config_set.save()

    assert (ssh / "config").read_bytes() == before
    assert list(ssh.glob("config.bak-*")) == []
    assert config_set.hosts[0].dirty is True  # still unsaved, and it says so


def test_one_bad_file_stops_the_whole_save(ssh: Path, fake_bin: FakeBin) -> None:
    """SPEC §3 validates per file; we validate all of them before writing any.

    Otherwise an early file lands on disk and a later one is refused, leaving
    the user with half a save and no way to tell which half.
    """
    (ssh / "extra.conf").write_text("Host extra\n")
    (ssh / "config").write_text("Include extra.conf\n\n" + MAIN)
    fake_bin.install("ssh", returncode=0)
    config_set = ConfigSet.load()
    before = {f.path: f.path.read_bytes() for f in config_set.files}

    for block in config_set.hosts:
        block.dirty = True
    # The first file passes, the second is refused. Code that writes as it
    # validates would already have committed the first one by then.
    fake_bin.install_sequence(
        "ssh",
        [
            {"returncode": 0, "stdout": "", "stderr": ""},
            {"returncode": 255, "stdout": "", "stderr": "%F: line 1: nope"},
        ],
    )

    with pytest.raises(ConfigError):
        config_set.save()

    assert {f.path: f.path.read_bytes() for f in config_set.files} == before
    assert len(fake_bin.calls("ssh")) == 2  # both checked before either was written
    # Content equality alone would not prove it: re-rendering an unchanged
    # block produces the same bytes. A backup only exists if we wrote.
    assert list(ssh.glob("*.bak-*")) == []


def test_save_backs_up_before_overwriting(loaded: ConfigSet, ssh: Path) -> None:
    loaded.hosts[0].entries = [Entry("HostName", "203.0.113.55")]
    loaded.hosts[0].dirty = True

    loaded.save()

    backups = list(ssh.glob("config.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == MAIN
