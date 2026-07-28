"""Config text is data, not markup.

Regression tests for the bug that shipped in M13: `Adw.PreferencesRow` parses
its title and subtitle as Pango markup by default, so the perfectly ordinary
`RemoteCommand cd /srv/app && bash -l` made GTK drop the text and warn.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.data.keywords import CATALOG

pytestmark = pytest.mark.gui

# Every shape of ampersand and angle bracket a real config can hold.
NASTY = """Host a&b
    HostName 203.0.113.10
    User dev<test>
    RemoteCommand cd /srv/app && bash -l
    ProxyCommand sh -c 'nc %h %p < /dev/null'
    SetEnv GREETING=me&you
"""


@pytest.fixture
def config_file(fake_home: Path) -> Path:
    return fake_home / ".ssh" / "config"


# -- the rows we build -----------------------------------------------------


def test_every_option_row_treats_its_text_as_data(gtk) -> None:
    from parvussh.ui.rows import OptionRow

    for keyword in CATALOG:
        row = OptionRow(keyword)
        assert row.row.get_use_markup() is False, keyword.name


def test_a_row_holding_an_ampersand_keeps_it(gtk) -> None:
    from parvussh.data.keywords import get
    from parvussh.ui.rows import OptionRow

    row = OptionRow(get("RemoteCommand"), "cd /srv/app && bash -l")

    assert row.value() == "cd /srv/app && bash -l"
    assert row.config_line() == "    RemoteCommand cd /srv/app && bash -l"


def test_the_sidebar_rows_treat_aliases_as_data(window, config_file: Path) -> None:
    config_file.write_text(NASTY, encoding="utf-8")

    window.reload()

    row = window.sidebar.rows()[0]
    assert row.get_use_markup() is False
    # The literal alias, not an escaped one: escaping would show `a&amp;b`.
    assert row.get_title() == "a&b"


def test_the_basic_form_rows_treat_their_text_as_data(window) -> None:
    editor = window.editor
    for row in (editor.host, editor.hostname, editor.user, editor.port):
        assert row.get_use_markup() is False


def test_the_add_option_popover_rows_treat_text_as_data(window) -> None:
    window.editor.add_popover.refresh()

    for row in window.editor.add_popover.rows():
        assert row.get_use_markup() is False, row.get_title()


# -- end to end ------------------------------------------------------------


def test_a_config_full_of_ampersands_opens_without_complaint(
    window, config_file: Path
) -> None:
    """The exact failure the user hit, from the file to the rendered form."""
    config_file.write_text(NASTY, encoding="utf-8")

    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])

    # The `gtk` fixture asserts GTK logged nothing on the way out.
    assert window.editor.host.get_text() == "a&b"
    assert window.editor.user.get_text() == "dev<test>"


def test_such_a_config_survives_a_save(window, config_file: Path) -> None:
    config_file.write_text(NASTY, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])

    window.editor.hostname.set_text("198.51.100.9")
    window.save_current()

    text = config_file.read_text()
    assert "RemoteCommand cd /srv/app && bash -l" in text
    assert "SetEnv GREETING=me&you" in text
    assert "User dev<test>" in text


def test_the_help_dialog_shows_every_example_without_complaint(gtk) -> None:
    """`RemoteCommand`'s example contains `&&`; the help page renders it."""
    from parvussh.ui.help import HelpDialog

    HelpDialog()  # the `gtk` fixture fails the test if GTK warns


def test_the_catalog_really_does_contain_markup_characters() -> None:
    """If this ever fails, the tests above stopped proving anything."""
    risky = [
        keyword.name
        for keyword in CATALOG
        if any(char in f"{keyword.description}{keyword.example}" for char in "&<>")
    ]
    assert "RemoteCommand" in risky
