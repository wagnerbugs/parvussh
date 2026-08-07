"""`parvussh --list`, and the promise that it never needs a display.

The listing exists so the aliases can be recalled from a terminal — over ssh,
on a server, on a machine with no GTK installed. That is only true while
`parvussh.cli` keeps GTK behind a lazy import, so one test here asserts exactly
that in a fresh interpreter.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from parvussh import cli
from parvussh.i18n import t

TWO_HOSTS = """\
Host vps-blog
    HostName 203.0.113.10
    User deploy
    Port 2222

Host github.com
    User git
"""


def write_config(text: str, home: Path) -> Path:
    path = home / ".ssh" / "config"
    path.write_text(text, encoding="utf-8")
    return path


def run_list(capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    code = cli.list_hosts(sys.stdout)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# -- the listing -----------------------------------------------------------


def test_each_host_gets_a_line_with_its_destination(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config(TWO_HOSTS, fake_home)
    code, out, _ = run_list(capsys)

    assert code == 0
    lines = out.splitlines()
    assert len(lines) == 2
    assert lines[0].split() == ["vps-blog", "deploy@203.0.113.10:2222"]
    # No HostName: the destination column says so rather than sitting empty.
    assert lines[1].split() == ["github.com", *t("cli.no_hostname").split()]


def test_the_destinations_line_up(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Scanning a column of destinations is the whole point of the command."""
    write_config(TWO_HOSTS, fake_home)
    _, out, _ = run_list(capsys)

    starts = {re.search(r" {2,}", line).end() for line in out.splitlines()}  # type: ignore[union-attr]
    assert len(starts) == 1


def test_a_wildcard_block_is_not_reported_as_missing_a_hostname(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config("Host *\n    ServerAliveInterval 60\n", fake_home)
    _, out, _ = run_list(capsys)

    assert t("cli.wildcard") in out
    assert t("cli.no_hostname") not in out


def test_match_blocks_are_left_out(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`Match host *.interno` is not a connection you can `ssh` by name."""
    write_config(
        "Host vps\n    HostName 203.0.113.10\n\nMatch host *.interno\n"
        "    ProxyJump bastion\n",
        fake_home,
    )
    _, out, _ = run_list(capsys)

    assert out.splitlines() == ["vps  203.0.113.10"]


# -- Include ---------------------------------------------------------------


def test_the_source_column_appears_only_when_include_brought_in_a_file(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ssh = fake_home / ".ssh"
    (ssh / "work.config").write_text(
        "Host work\n    HostName 198.51.100.7\n", encoding="utf-8"
    )
    write_config(
        "Include work.config\n\nHost vps\n    HostName 203.0.113.10\n", fake_home
    )
    _, with_include, _ = run_list(capsys)

    assert str(ssh / "work.config") in with_include
    assert str(ssh / "config") in with_include

    write_config("Host vps\n    HostName 203.0.113.10\n", fake_home)
    _, single, _ = run_list(capsys)

    assert str(ssh / "config") not in single


# -- nothing to show -------------------------------------------------------


def test_a_config_that_does_not_exist_yet_invites_an_action(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, _ = run_list(capsys)

    assert code == 0
    assert t("cli.no_config", path=fake_home / ".ssh" / "config") in out


def test_listing_never_creates_the_config(fake_home: Path) -> None:
    """`ConfigSet.load` creates the file on first run; a read must not."""
    cli.list_hosts(sys.stdout)

    assert not (fake_home / ".ssh" / "config").exists()


def test_an_empty_config_invites_an_action(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config("# nothing here yet\n", fake_home)
    code, out, _ = run_list(capsys)

    assert code == 0
    assert t("cli.empty", path=path) in out


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a 0o000 file anyway")
def test_an_unreadable_config_fails_with_a_sentence(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_config(TWO_HOSTS, fake_home)
    path.chmod(0o000)
    try:
        code, out, err = run_list(capsys)
    finally:
        path.chmod(0o600)

    assert code == 1
    assert out == ""
    assert str(path) in err


# -- argument handling -----------------------------------------------------


def test_main_lists_and_exits_without_opening_anything(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config(TWO_HOSTS, fake_home)

    assert cli.main(["parvussh", "--list"]) == 0
    assert "vps-blog" in capsys.readouterr().out


def test_the_short_flag_does_the_same(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config(TWO_HOSTS, fake_home)

    assert cli.main(["parvussh", "-l"]) == 0
    assert "vps-blog" in capsys.readouterr().out


@pytest.fixture
def handover(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Stand in for `open_window`, recording the argv it would have received.

    Patching the handover rather than `sys.modules` keeps this suite honest
    about the failure it is worth catching: with the GTK import made eager,
    a `sys.modules` stub is bound too late and the test opens a real window
    and hangs forever instead of failing.
    """
    seen: list[list[str]] = []

    def fake(argv: list[str]) -> int:
        seen.append(list(argv))
        return 0

    monkeypatch.setattr(cli, "open_window", fake)
    return seen


def test_no_arguments_opens_the_window(handover: list[list[str]]) -> None:
    assert cli.main(["parvussh"]) == 0
    assert handover == [["parvussh"]]


def test_unknown_arguments_are_handed_to_gtk(handover: list[list[str]]) -> None:
    """`--display` and friends belong to GTK, not to us."""
    assert cli.main(["parvussh", "--display=:1"]) == 0
    assert handover == [["parvussh", "--display=:1"]]


def test_version_prints_and_exits(capsys: pytest.CaptureFixture[str]) -> None:
    from parvussh import APP_NAME, __version__

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["parvussh", "--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"{APP_NAME} {__version__}"


# -- the headless promise --------------------------------------------------


def test_importing_the_cli_does_not_import_gtk(fake_home: Path) -> None:
    """A fresh interpreter, because the gui suite has already imported gi."""
    result = subprocess.run(
        [sys.executable, "-c", "import parvussh.cli, sys; print('gi' in sys.modules)"],
        capture_output=True,
        text=True,
        env={"HOME": str(fake_home), "PATH": "/usr/bin:/bin"},
        check=True,
    )

    assert result.stdout.strip() == "False"
