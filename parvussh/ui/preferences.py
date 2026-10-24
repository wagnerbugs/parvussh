"""The preferences dialog: the terminal Acessar opens, and how many backups stay."""

from __future__ import annotations

import threading
from dataclasses import replace

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from parvussh.core import settings, terminal  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui.markup import group, text_row  # noqa: E402
from parvussh.ui.paths import shorten_home  # noqa: E402

#: Bounds of the backups row. One, because a write must always leave a copy
#: of what it replaced; the top is only there because a spin row needs one.
BACKUPS_RANGE = (1, 99)

#: What the "Em uso" row says for each answer `terminal.choose()` can give.
IN_USE = {
    terminal.AUTOMATIC: "prefs.terminal.automatic",
    terminal.CUSTOM: "prefs.terminal.custom",
    terminal.MISSING: "prefs.terminal.missing",
    terminal.NO_TERMINAL: "prefs.terminal.none",
}


class PreferencesDialog(Adw.PreferencesDialog):
    """Choose the terminal and see which one would open; set how many copies stay."""

    def __init__(self) -> None:
        super().__init__(title=t("prefs.title"))
        self.last_choice: terminal.Choice | None = None
        # Each lookup takes a number; only the latest may write the row, so
        # a slow answer to an old question cannot overwrite a newer one.
        self._asked = 0

        # A text field and no file chooser: inside the Flatpak the chooser
        # hands back a document-portal path, and the terminal runs on the host,
        # where that path means nothing.
        self.command = text_row(Adw.EntryRow, title=t("prefs.terminal.command"))
        self.command.set_text(settings.load().terminal)
        self.command.set_show_apply_button(True)
        self.command.connect("apply", lambda _row: self.apply())

        self.in_use = text_row(
            Adw.ActionRow,
            title=t("prefs.terminal.in_use"),
            subtitle=t("prefs.terminal.checking"),
        )

        section = group(
            title=t("prefs.terminal.title"),
            description=t("prefs.terminal.description"),
        )
        section.add(self.command)
        section.add(self.in_use)

        page = Adw.PreferencesPage()
        page.add(section)
        page.add(self._backups_section())
        self.add(page)
        self.refresh()

    def _backups_section(self) -> Adw.PreferencesGroup:
        lower, upper = BACKUPS_RANGE
        self.backups = text_row(
            Adw.SpinRow,
            title=t("prefs.backups.keep"),
            adjustment=Gtk.Adjustment(
                lower=lower, upper=upper, step_increment=1, page_increment=5
            ),
        )
        # Set before connecting: opening the dialog must not write the file.
        self.backups.set_value(settings.load().backups)
        self.backups.connect("notify::value", lambda *_a: self.apply_backups())

        section = group(
            title=t("prefs.backups.title"),
            description=t("prefs.backups.description"),
        )
        section.add(self.backups)
        return section

    def apply_backups(self) -> None:
        """Save the number as soon as it changes, as a spin row is expected to.

        No toast on success: a click on the arrows would raise one each time.
        """
        target = settings.path()
        count = int(self.backups.get_value())
        try:
            settings.save(replace(settings.load(), backups=count))
        except OSError as error:
            message = t("prefs.error.save", path=shorten_home(target), detail=error)
            self.add_toast(Adw.Toast(title=message))

    def apply(self) -> None:
        """Save the field as it stands, then look again at what it opens."""
        target = settings.path()
        try:
            written = settings.save(
                replace(settings.load(), terminal=self.command.get_text())
            )
        except OSError as error:
            message = t("prefs.error.save", path=shorten_home(target), detail=error)
            self.add_toast(Adw.Toast(title=message))
            return
        self.add_toast(Adw.Toast(title=t("save.done", path=shorten_home(written))))
        self.refresh()

    def refresh(self) -> None:
        """Ask, off the main thread, which terminal Acessar would open."""
        command = self.command.get_text()
        self.in_use.set_subtitle(t("prefs.terminal.checking"))
        self._asked += 1
        asked = self._asked

        def work() -> None:
            GLib.idle_add(show, terminal.choose(command))

        def show(choice: terminal.Choice) -> bool:
            if asked == self._asked:
                self.last_choice = choice
                self.in_use.set_subtitle(t(IN_USE[choice.status], name=choice.name))
            return False  # GLib.idle_add: run once

        # Finding the terminal starts a process, and inside the Flatpak it
        # goes through the portal; neither belongs on the main loop.
        threading.Thread(target=work, daemon=True).start()
