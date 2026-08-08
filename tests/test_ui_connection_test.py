"""The Testar button: the form as it stands, checked without saving."""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.core import tester

pytestmark = pytest.mark.gui

CONFIG = """Host vps
    HostName 203.0.113.10
    User deploy
    Port 2222
    Compression yes

Host *
    ServerAliveInterval 60
"""


@pytest.fixture
def app(window, fake_home: Path, fake_bin):
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


def run_test(app, pump):
    app.test_current()
    pump(lambda: app.last_test_result is not None)
    return app.last_test_result


# -- what gets sent to ssh -------------------------------------------------


def test_the_test_uses_the_form_not_the_saved_file(
    app, pump, fake_bin, fake_home
) -> None:
    """Testing before saving is the entire point of the feature."""
    fake_bin.install("ssh", returncode=0)
    app.editor.hostname.set_text("198.51.100.7")

    run_test(app, pump)

    config = Path(fake_bin.args("ssh")[1])
    # Not the saved config, and not the system temp directory either: D5 puts
    # it in ~/.ssh, where a sandboxed build's host ssh can still read it.
    assert config.name.startswith(".parvussh-")
    assert config.parent == fake_home / ".ssh"
    assert config != fake_home / ".ssh" / "config"
    # The temp file is deleted by then, so check what the form would produce.
    assert "HostName 198.51.100.7" in app.editor.config_text()


def test_the_generated_config_carries_the_extra_options(app) -> None:
    text = app.editor.config_text()

    assert text.startswith("Host vps\n")
    assert "    HostName 203.0.113.10" in text
    assert "    Port 2222" in text
    assert "    Compression yes" in text


def test_an_option_left_empty_is_not_sent(app) -> None:
    app.editor.user.set_text("")
    assert "User" not in app.editor.config_text()


def test_ssh_is_asked_for_the_alias_only(app, pump, fake_bin) -> None:
    fake_bin.install("ssh", returncode=0)

    run_test(app, pump)

    assert fake_bin.args("ssh")[-2:] == ["vps", "true"]


# -- refusing to run -------------------------------------------------------


def test_a_wildcard_alias_is_refused(app, fake_bin) -> None:
    """There is no single server behind `Host *` to connect to."""
    fake_bin.install("ssh", returncode=0)
    app.sidebar.listbox.select_row(app.sidebar.rows()[1])

    app.test_current()

    assert app.last_test_result is None
    assert fake_bin.calls("ssh") == []


def test_an_empty_alias_is_refused(app, fake_bin) -> None:
    fake_bin.install("ssh", returncode=0)
    app.editor.host.set_text("")

    app.test_current()

    assert app.last_test_result is None
    assert fake_bin.calls("ssh") == []


def test_nothing_selected_does_nothing(window, fake_bin) -> None:
    fake_bin.install("ssh", returncode=0)
    window.test_current()
    assert window.last_test_result is None


# -- verdicts --------------------------------------------------------------


def test_a_successful_login_reports_success(app, pump, fake_bin) -> None:
    fake_bin.install("ssh", returncode=0)

    result = run_test(app, pump)

    assert result.status == tester.AUTH
    assert result.ok is True


def test_permission_denied_reports_success(app, pump, fake_bin) -> None:
    """Reaching the password prompt proves host, port and network are right."""
    fake_bin.install(
        "ssh", returncode=255, stderr="vps: Permission denied (publickey)."
    )

    result = run_test(app, pump)

    assert result.status == tester.REACHABLE
    assert result.ok is True


def test_a_refused_connection_reports_failure(app, pump, fake_bin) -> None:
    fake_bin.install(
        "ssh",
        returncode=255,
        stderr="connect to host ... port 2222: Connection refused",
    )

    result = run_test(app, pump)

    assert result.status == tester.REFUSED
    assert result.ok is False


def test_a_missing_ssh_is_reported(app, pump, fake_bin) -> None:
    # The config loaded fine a moment ago; now openssh-client is gone.
    fake_bin.uninstall("ssh")

    result = run_test(app, pump)

    assert result.status == tester.NO_SSH
    assert result.ok is False


def test_the_raw_ssh_output_comes_back_for_the_expander(app, pump, fake_bin) -> None:
    fake_bin.install("ssh", returncode=255, stderr="Permission denied (publickey).")

    result = run_test(app, pump)

    assert "Permission denied" in result.output


# -- the dialog ------------------------------------------------------------


def test_the_dialog_explains_the_verdict_in_portuguese(gtk) -> None:
    from parvussh.ui.dialogs import TestResultDialog

    dialog = TestResultDialog(tester.TestResult(tester.REACHABLE, "denied", 255))

    assert dialog.get_heading() == "Servidor respondeu"
    assert "chegou a pedir" in dialog.get_body()


def test_the_dialog_folds_the_ssh_output_away(gtk) -> None:
    from parvussh.ui.dialogs import TestResultDialog

    dialog = TestResultDialog(tester.TestResult(tester.REFUSED, "recusado", 255))

    expander = dialog.get_extra_child()
    assert expander is not None
    assert expander.get_expanded() is False  # collapsed until asked for


def test_a_verdict_with_no_output_has_no_expander(gtk) -> None:
    from parvussh.ui.dialogs import TestResultDialog

    dialog = TestResultDialog(tester.TestResult(tester.NO_SSH))

    assert dialog.get_extra_child() is None


def test_the_unknown_verdict_names_the_exit_code(gtk) -> None:
    from parvussh.ui.dialogs import TestResultDialog

    dialog = TestResultDialog(tester.TestResult(tester.UNKNOWN, "algo", 3))

    assert "código 3" in dialog.get_body()


@pytest.mark.parametrize(
    "status",
    [
        tester.AUTH,
        tester.REACHABLE,
        tester.DNS,
        tester.REFUSED,
        tester.TIMEOUT_STATUS,
        tester.NETWORK,
        tester.HOSTKEY,
        tester.CONFIG,
        tester.NO_SSH,
        tester.UNKNOWN,
    ],
)
def test_every_status_has_a_translated_verdict(gtk, status: str) -> None:
    """A status with no wording would show `test.dns.title` to the user."""
    from parvussh.ui.dialogs import TestResultDialog

    dialog = TestResultDialog(tester.TestResult(status, "saída", 255))

    assert not dialog.get_heading().startswith("test.")
    assert not dialog.get_body().startswith("test.")
