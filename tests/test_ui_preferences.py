"""The preferences dialog: choosing the terminal, and seeing which one opens.

Every terminal is a `fake_bin` shim; the dialog only ever looks them up.
"""

from __future__ import annotations

import pytest

from parvussh.core import settings, terminal
from parvussh.core.settings import Settings
from parvussh.i18n import t

pytestmark = pytest.mark.gui


@pytest.fixture
def dialog(gtk, fake_bin):
    from parvussh.ui.preferences import PreferencesDialog

    return PreferencesDialog()


def settled(dialog, pump) -> terminal.Choice:
    """Wait for the lookup the dialog started on its own."""
    pump(lambda: dialog.last_choice is not None)
    return dialog.last_choice


def reapplied(dialog, pump, text: str) -> terminal.Choice:
    dialog.last_choice = None
    dialog.command.set_text(text)
    dialog.apply()
    return settled(dialog, pump)


def test_the_field_starts_with_what_was_saved(gtk, fake_bin) -> None:
    from parvussh.ui.preferences import PreferencesDialog

    settings.save(Settings(terminal="alacritty -e"))
    assert PreferencesDialog().command.get_text() == "alacritty -e"


def test_an_empty_field_shows_the_system_default(dialog, pump, fake_bin) -> None:
    fake_bin.install("ptyxis")
    from parvussh.ui.preferences import PreferencesDialog

    dialog = PreferencesDialog()

    assert settled(dialog, pump).status == terminal.AUTOMATIC
    assert dialog.in_use.get_subtitle() == t("prefs.terminal.automatic", name="ptyxis")


def test_applying_saves_the_choice(dialog, pump) -> None:
    reapplied(dialog, pump, "alacritty -e")
    assert settings.load().terminal == "alacritty -e"


def test_an_installed_choice_says_so(dialog, pump, fake_bin) -> None:
    fake_bin.install("xterm")

    choice = reapplied(dialog, pump, "xterm")

    assert choice.status == terminal.CUSTOM
    assert dialog.in_use.get_subtitle() == t("prefs.terminal.custom", name="xterm")


def test_a_choice_not_installed_says_what_to_do(dialog, pump) -> None:
    choice = reapplied(dialog, pump, "kitty")

    assert choice.status == terminal.MISSING
    assert dialog.in_use.get_subtitle() == t("prefs.terminal.missing", name="kitty")


def test_clearing_the_field_goes_back_to_the_default(dialog, pump, fake_bin) -> None:
    fake_bin.install("ptyxis")
    reapplied(dialog, pump, "kitty")

    choice = reapplied(dialog, pump, "")

    assert choice.status == terminal.AUTOMATIC
    assert settings.load().terminal == ""


def test_nothing_installed_and_nothing_chosen(dialog, pump) -> None:
    assert settled(dialog, pump).status == terminal.NO_TERMINAL
    assert dialog.in_use.get_subtitle() == t("prefs.terminal.none", name="")


def test_the_window_opens_it_without_a_selection(window) -> None:
    assert window.lookup_action("preferences").get_enabled() is True


# -- how many config copies to keep -----------------------------------------


def test_the_copies_row_starts_with_what_was_saved(gtk, fake_bin) -> None:
    from parvussh.ui.preferences import PreferencesDialog

    settings.save(Settings(backups=7))
    assert PreferencesDialog().backups.get_value() == 7


def test_the_copies_row_starts_at_three(dialog) -> None:
    assert dialog.backups.get_value() == 3


def test_opening_the_dialog_writes_nothing(dialog) -> None:
    assert not settings.path().exists()


def test_changing_the_copies_saves_them_and_keeps_the_terminal(gtk, fake_bin) -> None:
    from parvussh.ui.preferences import PreferencesDialog

    settings.save(Settings(terminal="xterm"))
    dialog = PreferencesDialog()

    dialog.backups.set_value(5)

    assert settings.load() == Settings(terminal="xterm", backups=5)


def test_fewer_than_one_copy_cannot_be_chosen(dialog) -> None:
    dialog.backups.set_value(0)

    assert dialog.backups.get_value() == 1
    assert settings.load().backups == 1


def test_applying_the_terminal_keeps_the_copies(dialog, pump) -> None:
    dialog.backups.set_value(6)
    reapplied(dialog, pump, "alacritty -e")
    assert settings.load() == Settings(terminal="alacritty -e", backups=6)
