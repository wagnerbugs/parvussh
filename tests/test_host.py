"""Reaching the host's openssh from inside a sandbox, and from outside one.

Two behaviours are worth pinning: the argv grows a `flatpak-spawn --host`
prefix inside a Flatpak and nothing outside one, and the temp config lands
somewhere the host can actually read.

There is no Flatpak here, and there does not need to be. `in_sandbox()` reads
one path and `flatpak-spawn` is one more binary on `PATH`, so `fake_bin` and a
redirected `FLATPAK_INFO` reproduce both sides exactly.
"""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest

from parvussh.core import host, keys, tester, writer
from tests.conftest import FakeBin


@pytest.fixture
def sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Make `in_sandbox()` true, the way a Flatpak makes it true."""
    marker = tmp_path / "flatpak-info"
    marker.write_text("[Application]\n", encoding="utf-8")
    monkeypatch.setattr(host, "FLATPAK_INFO", marker)
    return marker


# -- which side of the sandbox we are on -----------------------------------


def test_a_plain_machine_is_not_a_sandbox() -> None:
    assert host.in_sandbox() is False


def test_the_flatpak_marker_is_what_says_otherwise(sandbox: Path) -> None:
    assert host.in_sandbox() is True


def test_the_argv_is_untouched_outside_a_sandbox() -> None:
    assert host.command(["ssh", "-G", "vps"]) == ["ssh", "-G", "vps"]


def test_the_argv_reaches_the_host_inside_a_sandbox(sandbox: Path) -> None:
    assert host.command(["ssh", "-G", "vps"]) == [
        "flatpak-spawn",
        "--host",
        "ssh",
        "-G",
        "vps",
    ]


def test_the_caller_s_list_is_not_mutated() -> None:
    """`command()` returns a new list; a caller may keep its own."""
    argv = ["ssh", "-G", "vps"]

    host.command(argv)

    assert argv == ["ssh", "-G", "vps"]


# -- the temp config -------------------------------------------------------


def test_the_temp_config_lives_where_the_host_can_read_it(fake_home: Path) -> None:
    with host.temp_config("Host vps\n") as path:
        assert Path(path).parent == fake_home / ".ssh"


def test_the_temp_config_is_private_and_hidden(fake_home: Path) -> None:
    with host.temp_config("Host vps\n") as path:
        mode = stat.S_IMODE(Path(path).stat().st_mode)
        assert mode == 0o600
        # A glob does not match a dotfile, so a user's `Include *` cannot
        # pick this up while it exists.
        assert Path(path).name.startswith(".")


def test_the_temp_config_holds_what_it_was_given(fake_home: Path) -> None:
    with host.temp_config("Host vps\n    User deploy\n") as path:
        assert Path(path).read_text(encoding="utf-8") == "Host vps\n    User deploy\n"


def test_the_temp_config_is_gone_afterwards(fake_home: Path) -> None:
    with host.temp_config("Host vps\n") as path:
        pass

    assert not Path(path).exists()


def test_the_temp_config_is_gone_even_when_the_body_raises(fake_home: Path) -> None:
    seen = ""
    with pytest.raises(RuntimeError), host.temp_config("Host vps\n") as path:
        seen = path
        raise RuntimeError("boom")

    assert seen and not Path(seen).exists()


def test_the_ssh_directory_is_created_when_it_is_missing(fake_home: Path) -> None:
    """First run on a machine that has never used ssh."""
    ssh = fake_home / ".ssh"
    for leftover in ssh.iterdir():
        leftover.unlink()
    ssh.rmdir()

    with host.temp_config("Host vps\n") as path:
        assert Path(path).exists()
    assert stat.S_IMODE(ssh.stat().st_mode) == 0o700


# -- the three callers -----------------------------------------------------


def test_validate_asks_the_host_ssh(fake_bin: FakeBin, sandbox: Path) -> None:
    fake_bin.install("flatpak-spawn", returncode=0)

    writer.validate("Host vps\n")

    assert fake_bin.args("flatpak-spawn")[:2] == ["--host", "ssh"]


def test_the_connection_test_asks_the_host_ssh(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    fake_bin.install("flatpak-spawn", returncode=0)

    tester.run("vps", "Host vps\n")

    assert fake_bin.args("flatpak-spawn")[:2] == ["--host", "ssh"]


def test_describing_a_key_asks_the_host_ssh_keygen(
    fake_bin: FakeBin, sandbox: Path, fake_home: Path
) -> None:
    fake_bin.install("flatpak-spawn", returncode=1)
    key = fake_home / ".ssh" / "id_ed25519"
    key.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n", encoding="utf-8")

    keys.describe(key)

    assert fake_bin.args("flatpak-spawn")[:2] == ["--host", "ssh-keygen"]


def test_generating_a_key_asks_the_host_ssh_keygen(sandbox: Path) -> None:
    argv = keys.generate_command(Path("/home/maria/.ssh/id_ed25519"))

    assert argv[:3] == ["flatpak-spawn", "--host", "ssh-keygen"]


def test_nothing_is_spawned_through_the_portal_outside_a_sandbox(
    fake_bin: FakeBin,
) -> None:
    """The whole seam has to be invisible on an ordinary install."""
    fake_bin.install("ssh", returncode=0)

    writer.validate("Host vps\n")
    tester.run("vps", "Host vps\n")

    assert fake_bin.calls("flatpak-spawn") == []
    assert fake_bin.args("ssh")[0] == "-F"


def test_a_missing_flatpak_spawn_reads_as_no_ssh(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    """Nothing is installed on PATH, so the spawn helper itself is absent."""
    assert tester.run("vps", "Host vps\n").status == tester.NO_SSH


# -- the portal refusing, told apart from ssh answering ---------------------


def test_a_refused_spawn_is_only_a_refusal_inside_a_sandbox(sandbox: Path) -> None:
    assert host.spawn_failed(1) is True


def test_the_same_code_from_a_real_ssh_is_left_alone() -> None:
    """Outside a sandbox, 1 is whatever ssh meant by it and nothing else."""
    assert host.spawn_failed(1) is False


@pytest.mark.parametrize("returncode", [0, 2, 42, 255])
def test_every_other_status_came_from_the_command(
    sandbox: Path, returncode: int
) -> None:
    """`flatpak-spawn` forwards the child's status untouched; only 1 is its own."""
    assert host.spawn_failed(returncode) is False


def test_no_openssh_on_the_host_reads_as_no_ssh(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    fake_bin.install("flatpak-spawn", returncode=1, stderr="Portal call failed: …")

    assert tester.run("vps", "Host vps\n").status == tester.NO_SSH


def test_no_openssh_on_the_host_does_not_stop_a_save(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    """The rule that already held outside a sandbox has to hold inside one.

    `validate()` skips rather than refuses when it cannot run ssh. Without
    this the portal's own exit status would read as ssh rejecting the config,
    and the user could never save anything.
    """
    fake_bin.install("flatpak-spawn", returncode=1, stderr="Portal call failed: …")

    writer.validate("Host vps\n")  # returns, raises nothing


def test_validate_still_forwards_what_the_host_ssh_refused(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    fake_bin.install(
        "flatpak-spawn", returncode=255, stderr="%F: line 2: Bad configuration option"
    )

    with pytest.raises(writer.ConfigError) as raised:
        writer.validate("Host vps\n    Nonsense yes\n")

    # The temp path is rewritten to the word the user knows it by, even
    # though it travelled through the portal on the way out.
    assert "Bad configuration option" in str(raised.value)
    assert str(raised.value).startswith("config:")


def test_a_hanging_host_ssh_does_not_block_the_save(
    monkeypatch: pytest.MonkeyPatch, sandbox: Path
) -> None:
    def hang(command: list[str], **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(command, 1)

    monkeypatch.setattr(subprocess, "run", hang)

    writer.validate("Host vps\n")  # returns, raises nothing
