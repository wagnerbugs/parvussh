"""Dialogs: creating a key, and reporting what happened."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from parvussh.core import keys  # noqa: E402
from parvussh.i18n import t  # noqa: E402

DIALOG_WIDTH = 460


class NewKeyDialog(Adw.Dialog):
    """Create a key pair in `~/.ssh` without leaving the app."""

    def __init__(
        self,
        on_created: Callable[[str], None] | None = None,
        toast: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(title=t("newkey.title"), content_width=DIALOG_WIDTH)
        self.on_created = on_created
        self.toast = toast

        self.name = Adw.EntryRow(title=t("newkey.field.name"))
        self.name.set_text(t("newkey.default_name"))
        self.kind = Adw.ComboRow(
            title=t("newkey.field.kind"),
            subtitle=t("newkey.field.kind_subtitle"),
            model=Gtk.StringList.new(list(keys.KEY_TYPES)),
        )
        self.comment = Adw.EntryRow(title=t("newkey.field.comment"))
        self.comment.set_text(f"{GLib.get_user_name()}@{GLib.get_host_name()}")
        self.passphrase = Adw.PasswordEntryRow(title=t("newkey.field.passphrase"))
        self.confirm = Adw.PasswordEntryRow(title=t("newkey.field.confirm"))

        group = Adw.PreferencesGroup()
        for row in (self.name, self.kind, self.comment, self.passphrase, self.confirm):
            group.add(row)
        group.add(
            Gtk.Label(
                label=t("newkey.note"),
                wrap=True,
                xalign=0,
                margin_top=6,
                css_classes=["dim-label", "caption"],
            )
        )

        page = Adw.PreferencesPage()
        page.add(group)

        cancel = Gtk.Button(label=t("dialog.cancel"))
        cancel.connect("clicked", lambda *_a: self.close())
        create = Gtk.Button(label=t("newkey.create"), css_classes=["suggested-action"])
        create.connect("clicked", lambda *_a: self.create())

        header = Adw.HeaderBar(
            show_start_title_buttons=False, show_end_title_buttons=False
        )
        header.pack_start(cancel)
        header.pack_end(create)

        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(page)
        self.set_child(view)

    def create(self) -> bool:
        """Generate the key. Returns whether it worked; reports why if not."""
        name = self.name.get_text().strip()
        if not name:
            self._complain(t("newkey.error.empty_name"))
            return False
        if self.passphrase.get_text() != self.confirm.get_text():
            self._complain(t("newkey.error.mismatch"))
            return False

        path = keys.ssh_dir() / name
        kind = keys.KEY_TYPES[self.kind.get_selected()]
        try:
            key = keys.generate(
                path,
                kind=kind,
                passphrase=self.passphrase.get_text(),
                comment=self.comment.get_text().strip(),
            )
        except keys.KeyExistsError as error:
            self._complain(t("newkey.error.exists", path=display_path(error.path)))
            return False
        except keys.KeyToolMissing:
            self._complain(t("newkey.error.no_tool"))
            return False
        except (keys.KeyToolError, OSError) as error:
            self._report(t("newkey.failed.heading"), str(error))
            return False

        self.close()
        self._announce(t("newkey.created", path=key.display_path))
        if self.on_created is not None:
            self.on_created(key.display_path)
        return True

    # -- talking back ------------------------------------------------------

    def _complain(self, text: str) -> None:
        """A correctable mistake: say it and leave the dialog open."""
        self._report(t("newkey.failed.heading"), text)

    def _announce(self, text: str) -> None:
        if self.toast is not None:
            self.toast(text)

    def _report(self, heading: str, body: str) -> None:
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", t("dialog.understood"))
        dialog.present(self)


def display_path(path: Path) -> str:
    """`~/...` when under `$HOME`, so messages read the way the user thinks."""
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)
