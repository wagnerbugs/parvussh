"""The Acessar button: the user's terminal, on `ssh <alias>` as saved.

Every terminal here is a shim from `fake_bin`. A test that opened a real
window on the developer's screen would be its own bug.
"""

from __future__ import annotations

import pytest

from parvussh.core import terminal
from parvussh.core.terminal import HOLD, SHELL
from parvussh.i18n import t

pytestmark = pytest.mark.gui

CONFIG = """Host vps
    HostName 203.0.113.10
    User deploy

Host *
    ServerAliveInterval 60
"""


@pytest.fixture
def app(window, fake_home, fake_bin):
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


@pytest.fixture
def said(app, monkeypatch) -> list[str]:
    """Every toast, as text. A refusal is said at once, on the main thread.

    Checking `last_launch is None` instead would pass whether or not the
    refusal happened: the launch runs on a worker thread and reports later.
    """
    texts: list[str] = []
    monkeypatch.setattr(app, "toast", texts.append)
    return texts


def connect(app, pump) -> terminal.Launch:
    app.connect_current()
    pump(lambda: app.last_launch is not None)
    return app.last_launch


# -- what gets run ---------------------------------------------------------


def test_the_terminal_runs_ssh_on_the_alias(app, pump, fake_bin) -> None:
    fake_bin.install("xdg-terminal-exec")

    launch = connect(app, pump)

    assert launch.status == terminal.OPENED
    assert fake_bin.args("xdg-terminal-exec") == [
        "--",
        SHELL,
        "-c",
        HOLD,
        "sh",
        "vps",
        t("connect.notice"),
    ]


def test_connecting_writes_nothing(app, pump, fake_bin, fake_home) -> None:
    """A temp config would be the form; the terminal must read the real file."""
    fake_bin.install("xdg-terminal-exec")
    before = sorted(path.name for path in (fake_home / ".ssh").iterdir())

    connect(app, pump)

    assert sorted(path.name for path in (fake_home / ".ssh").iterdir()) == before


def test_the_action_follows_the_selection(window) -> None:
    assert window.lookup_action("connect").get_enabled() is False


# -- refusing to run -------------------------------------------------------


def test_an_unsaved_edit_is_refused(app, said) -> None:
    """The terminal reads the file, so it would reach the old address."""
    app.editor.hostname.set_text("198.51.100.7")

    app.connect_current()

    assert said == [t("connect.error.unsaved")]


def test_a_connection_never_saved_is_refused(app, said) -> None:
    """A new block is in memory only; `ssh` has never heard of its alias."""
    app.new_host()
    assert app.editor.dirty is False  # so it is the block's flag that stops it

    app.connect_current()

    assert said == [t("connect.error.unsaved")]


def test_saving_first_lets_it_through(app, pump, fake_bin, said) -> None:
    fake_bin.install("xdg-terminal-exec")
    app.editor.hostname.set_text("198.51.100.7")
    assert app.save_current(silent=True)

    assert connect(app, pump).status == terminal.OPENED
    assert said == []


def test_a_wildcard_alias_is_refused(app, said) -> None:
    app.sidebar.listbox.select_row(app.sidebar.rows()[1])

    app.connect_current()

    assert said == [t("connect.error.wildcard")]


def test_nothing_selected_does_nothing(window, fake_bin) -> None:
    fake_bin.install("xdg-terminal-exec")
    window.connect_current()
    assert window.last_launch is None


# -- when it cannot open ---------------------------------------------------


def test_no_terminal_installed_is_reported(app, pump) -> None:
    assert connect(app, pump).status == terminal.NO_TERMINAL


def test_a_terminal_that_fails_is_reported(app, pump, fake_bin) -> None:
    fake_bin.install("xterm", returncode=2)

    launch = connect(app, pump)

    assert launch.status == terminal.FAILED
    assert launch.terminal == "xterm"
