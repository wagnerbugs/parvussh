"""Opening the user's terminal on `ssh <alias>`.

No test here may open a real terminal on the developer's screen. `fake_bin`
empties PATH, so the lookup only ever finds the shims a test installed, and a
shim records its argv instead of opening anything.

The wrapper that keeps a failed connection on screen is a real `sh` script,
and it runs for real below — against a fake `ssh`, with no terminal around it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from parvussh.core import host, terminal
from parvussh.core.terminal import (
    AUTOMATIC,
    CUSTOM,
    FAILED,
    HOLD,
    MISSING,
    NO_TERMINAL,
    OPENED,
    SHELL,
    TERMINALS,
    Choice,
    Terminal,
    build_command,
    choose,
    custom,
    describe,
    find,
    launch,
)
from tests.conftest import FakeBin

NOTICE = "Press Enter to close."
PTYXIS = Terminal("ptyxis", ("--",))


@pytest.fixture
def sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Make `in_sandbox()` true, the way a Flatpak makes it true."""
    marker = tmp_path / "flatpak-info"
    marker.write_text("[Application]\n", encoding="utf-8")
    monkeypatch.setattr(host, "FLATPAK_INFO", marker)
    return marker


# -- the table -------------------------------------------------------------


def test_the_user_s_own_choice_is_asked_first() -> None:
    """`xdg-terminal-exec` is the one that knows which terminal they picked."""
    assert TERMINALS[0].name == "xdg-terminal-exec"


def test_every_terminal_is_listed_once() -> None:
    names = [item.name for item in TERMINALS]
    assert len(names) == len(set(names))


def test_every_terminal_says_where_its_options_end() -> None:
    """Without a separator, `-c` would be read as the terminal's own option."""
    assert all(item.separator for item in TERMINALS)


# -- finding one -----------------------------------------------------------


def test_nothing_installed_finds_nothing(fake_bin: FakeBin) -> None:
    assert find() is None


def test_the_only_one_installed_is_found(fake_bin: FakeBin) -> None:
    fake_bin.install("xterm")
    assert find() == Terminal("xterm", ("-e",))


def test_the_table_order_beats_the_install_order(fake_bin: FakeBin) -> None:
    fake_bin.install("xterm")
    fake_bin.install("ptyxis")
    assert find() == PTYXIS


def test_looking_up_runs_nothing_it_finds(fake_bin: FakeBin) -> None:
    """`command -v` only checks; it must not start the terminal."""
    fake_bin.install("ptyxis")

    find()

    assert fake_bin.calls("ptyxis") == []


def test_inside_a_sandbox_the_host_is_searched(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    """The sandbox's own PATH says nothing about the user's desktop."""
    fake_bin.install("flatpak-spawn", stdout="ptyxis")

    assert find() == PTYXIS
    args = fake_bin.args("flatpak-spawn")
    assert args[:3] == ["--host", SHELL, "-c"]
    assert args[-len(TERMINALS) :] == [item.name for item in TERMINALS]


def test_a_refused_portal_finds_nothing(fake_bin: FakeBin, sandbox: Path) -> None:
    fake_bin.install("flatpak-spawn", returncode=1, stderr="Portal call failed")
    assert find() is None


def test_an_answer_outside_the_table_is_ignored(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    fake_bin.install("flatpak-spawn", stdout="rm")
    assert find() is None


# -- the user's own choice -------------------------------------------------


def test_a_bare_path_to_a_known_terminal_gets_its_separator() -> None:
    """A path is all most people should need to write."""
    assert custom("/usr/bin/xterm") == Terminal("/usr/bin/xterm", ("-e",))


def test_arguments_written_out_are_taken_as_they_are() -> None:
    assert custom("alacritty -e") == Terminal("alacritty", ("-e",))
    assert custom("wezterm start --") == Terminal("wezterm", ("start", "--"))


def test_written_arguments_win_over_the_table() -> None:
    """Whoever wrote `xterm -hold -e` meant every word of it."""
    assert custom("xterm -hold -e") == Terminal("xterm", ("-hold", "-e"))


def test_an_unknown_bare_program_gets_nothing_added() -> None:
    """`foot` takes the command as it is; guessing `-e` would break it."""
    assert custom("foot") == Terminal("foot", ())


def test_a_quoted_path_keeps_its_spaces() -> None:
    assert custom('"/opt/My Term/term" -e') == Terminal("/opt/My Term/term", ("-e",))


def test_unbalanced_quotes_are_refused() -> None:
    with pytest.raises(ValueError):
        custom('"/opt/term')


def test_no_preference_takes_the_table(fake_bin: FakeBin) -> None:
    fake_bin.install("ptyxis")
    assert choose("") == Choice(AUTOMATIC, PTYXIS, "ptyxis")


def test_no_preference_and_nothing_installed(fake_bin: FakeBin) -> None:
    assert choose("") == Choice(NO_TERMINAL)


def test_an_installed_preference_is_used(fake_bin: FakeBin) -> None:
    fake_bin.install("ptyxis")
    fake_bin.install("xterm")

    choice = choose("xterm")

    assert choice == Choice(CUSTOM, Terminal("xterm", ("-e",)), "xterm")


def test_a_preference_by_absolute_path_is_found(fake_bin: FakeBin) -> None:
    fake_bin.install("myterm")
    program = str(fake_bin.bindir / "myterm")

    choice = choose(f"{program} --run")

    assert choice.status == CUSTOM
    assert choice.terminal == Terminal(program, ("--run",))
    assert choice.name == "myterm"


def test_a_missing_preference_never_falls_back(fake_bin: FakeBin) -> None:
    """They chose something; opening something else would hide that it broke."""
    fake_bin.install("ptyxis")
    assert choose("kitty") == Choice(MISSING, name="kitty")


def test_a_preference_with_bad_quoting_is_missing(fake_bin: FakeBin) -> None:
    assert choose('"/opt/term').status == MISSING


# -- naming what opens -----------------------------------------------------


def test_a_plain_terminal_is_named_after_its_program() -> None:
    assert describe(Terminal("/usr/bin/xterm", ("-e",))) == "xterm"


def test_the_dispatcher_is_asked_what_it_picked(fake_bin: FakeBin) -> None:
    """`xdg-terminal-exec` does not answer "which terminal?"; Ptyxis does."""
    fake_bin.install(
        "xdg-terminal-exec", stdout="org.gnome.Ptyxis.desktop:new-window\n"
    )

    assert describe(TERMINALS[0]) == "Ptyxis"
    assert fake_bin.args("xdg-terminal-exec") == ["--print-id"]


def test_an_entry_id_without_dots_is_used_whole(fake_bin: FakeBin) -> None:
    fake_bin.install("xdg-terminal-exec", stdout="kitty.desktop\n")
    assert describe(TERMINALS[0]) == "kitty"


def test_a_dispatcher_that_cannot_say_keeps_its_own_name(fake_bin: FakeBin) -> None:
    fake_bin.install("xdg-terminal-exec", returncode=1)
    assert describe(TERMINALS[0]) == "xdg-terminal-exec"


def test_inside_a_sandbox_the_host_s_dispatcher_is_asked(
    fake_bin: FakeBin, sandbox: Path
) -> None:
    fake_bin.install_sequence(
        "flatpak-spawn",
        [
            {"returncode": 0, "stdout": "xdg-terminal-exec", "stderr": ""},
            {"returncode": 0, "stdout": "org.gnome.Ptyxis.desktop", "stderr": ""},
        ],
    )

    assert choose("").name == "Ptyxis"
    assert fake_bin.args("flatpak-spawn", 1) == [
        "--host",
        "xdg-terminal-exec",
        "--print-id",
    ]


# -- the argv --------------------------------------------------------------


def test_the_command_runs_the_wrapper_with_alias_and_notice() -> None:
    assert build_command(PTYXIS, "vps", NOTICE) == [
        "ptyxis",
        "--",
        SHELL,
        "-c",
        HOLD,
        "sh",
        "vps",
        NOTICE,
    ]


def test_inside_a_sandbox_the_terminal_opens_on_the_host(sandbox: Path) -> None:
    argv = build_command(PTYXIS, "vps", NOTICE)
    assert argv[:3] == ["flatpak-spawn", "--host", "ptyxis"]


# -- the wrapper, run for real ---------------------------------------------


def hold(alias: str, keys: str = "") -> subprocess.CompletedProcess[str]:
    """What the terminal would run, minus the terminal. Needs `fake_bin` active."""
    return subprocess.run(
        [SHELL, "-c", HOLD, "sh", alias, NOTICE],
        input=keys,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_the_command_is_shown_before_it_runs(fake_bin: FakeBin) -> None:
    """The button is `ssh <alias>` and nothing more; the window says so."""
    fake_bin.install("ssh")
    assert hold("vps").stdout.startswith("$ ssh vps\n")


def test_ssh_is_given_the_alias_and_nothing_else(fake_bin: FakeBin) -> None:
    fake_bin.install("ssh")

    hold("vps")

    assert fake_bin.args("ssh") == ["vps"]


def test_a_session_that_ends_well_closes_the_window(fake_bin: FakeBin) -> None:
    fake_bin.install("ssh", returncode=0)

    result = hold("vps")

    assert result.returncode == 0
    assert NOTICE not in result.stdout


def test_a_failed_connection_explains_how_to_close(fake_bin: FakeBin) -> None:
    fake_bin.install("ssh", returncode=255, stderr="Connection refused\n")

    result = hold("vps", keys="\n")

    assert result.returncode == 255
    assert NOTICE in result.stdout
    assert "Connection refused" in result.stderr


def test_a_failed_connection_waits_for_enter(fake_bin: FakeBin) -> None:
    """Otherwise the window closes and takes ssh's explanation with it."""
    fake_bin.install("ssh", returncode=255)
    process = subprocess.Popen(
        [SHELL, "-c", HOLD, "sh", "vps", NOTICE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )

    with pytest.raises(subprocess.TimeoutExpired):
        process.wait(timeout=1)
    process.communicate("\n", timeout=10)

    assert process.returncode == 255


def test_a_remote_command_s_failure_is_not_ssh_s(fake_bin: FakeBin) -> None:
    """A session that ends on a failed command did connect; say nothing."""
    fake_bin.install("ssh", returncode=1)

    result = hold("vps")

    assert result.returncode == 1
    assert NOTICE not in result.stdout


def test_the_alias_is_never_read_as_shell_code(
    fake_bin: FakeBin, fake_home: Path
) -> None:
    alias = f"vps; touch {fake_home}/pwned"
    fake_bin.install("ssh")

    hold(alias)

    assert fake_bin.args("ssh") == [alias]
    assert not (fake_home / "pwned").exists()


# -- launching -------------------------------------------------------------


def test_no_terminal_is_reported_as_such(fake_bin: FakeBin) -> None:
    assert launch("vps", NOTICE).status == NO_TERMINAL


def test_a_terminal_that_returns_at_once_opened(fake_bin: FakeBin) -> None:
    """Ptyxis and gnome-terminal hand the window over and exit 0."""
    fake_bin.install("ptyxis", returncode=0)

    result = launch("vps", NOTICE)

    assert result.status == OPENED
    assert result.terminal == "ptyxis"
    assert fake_bin.args("ptyxis") == ["--", SHELL, "-c", HOLD, "sh", "vps", NOTICE]


def test_a_terminal_still_running_opened(fake_bin: FakeBin) -> None:
    """xterm runs until the session ends; still being there is success."""
    script = fake_bin.bindir / "xterm"
    script.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(1)\n")
    script.chmod(0o755)

    result = launch("vps", NOTICE, settle=0.1)

    assert result.status == OPENED
    assert result.terminal == "xterm"


def test_a_terminal_that_exits_with_an_error_failed(fake_bin: FakeBin) -> None:
    fake_bin.install("ptyxis", returncode=2, stderr="Unknown option -e")

    result = launch("vps", NOTICE)

    assert result.status == FAILED
    assert result.terminal == "ptyxis"
    assert result.returncode == 2


def test_the_preference_is_what_opens(fake_bin: FakeBin) -> None:
    fake_bin.install("ptyxis")
    fake_bin.install("myterm")

    result = launch("vps", NOTICE, command="myterm --go")

    assert result == terminal.Launch(OPENED, "myterm")
    assert fake_bin.calls("ptyxis") == []
    assert fake_bin.args("myterm")[:2] == ["--go", SHELL]


def test_a_missing_preference_is_reported_as_such(fake_bin: FakeBin) -> None:
    fake_bin.install("ptyxis")

    result = launch("vps", NOTICE, command="kitty")

    assert result == terminal.Launch(MISSING, "kitty")
    assert fake_bin.calls("ptyxis") == []


def test_a_terminal_gone_before_it_starts_is_no_terminal(
    fake_bin: FakeBin, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Found, then uninstalled before `Popen` — a race, but a real one."""
    monkeypatch.setattr(terminal, "find", lambda candidates=TERMINALS: PTYXIS)
    assert launch("vps", NOTICE).status == NO_TERMINAL


def test_a_preference_gone_before_it_starts_is_missing(
    fake_bin: FakeBin, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(terminal, "find", lambda candidates=TERMINALS: PTYXIS)
    assert launch("vps", NOTICE, command="ptyxis").status == MISSING
