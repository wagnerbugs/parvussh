"""The main window: connection list on the left, form on the right.

The window owns the `ConfigSet` and coordinates. It holds no config-parsing
logic of its own and no literal user-visible strings —
`Sidebar` and `Editor` own their widgets, `core` owns the file, `i18n` owns
the words.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from parvussh import APP_NAME  # noqa: E402
from parvussh.core import settings, terminal, tester  # noqa: E402
from parvussh.core.merge import ConfigConflict  # noqa: E402
from parvussh.core.models import WILDCARD_CHARS, Block  # noqa: E402
from parvussh.core.store import ConfigSet  # noqa: E402
from parvussh.core.writer import ConfigError  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui import trash  # noqa: E402
from parvussh.ui.dialogs import TestResultDialog  # noqa: E402
from parvussh.ui.editor import Editor  # noqa: E402
from parvussh.ui.help import HelpDialog  # noqa: E402
from parvussh.ui.paths import shorten_home  # noqa: E402
from parvussh.ui.preferences import PreferencesDialog  # noqa: E402
from parvussh.ui.sidebar import Sidebar  # noqa: E402
from parvussh.ui.watch import ConfigWatch  # noqa: E402

WINDOW_SIZE = (1020, 700)
SIDEBAR_WIDTH = (280, 360)

#: Window actions and their accelerators. Every one exists from M6 on, even
#: where the handler is still a guard — an action that appears halfway through
#: a milestone is an action nobody wires a keyboard shortcut to.
ACCELERATORS = {
    "win.save": ["<Control>s"],
    "win.new": ["<Control>n"],
    "win.help": ["F1"],
    "win.preferences": ["<Control>comma"],
}

#: Actions that need a selected connection to mean anything. Disabling the
#: *action* dims every button bound to it and leaves the header bar itself
#: alone — turning the whole header insensitive would also disable the window
#: controls, which is how you trap someone in a window they cannot close.
NEEDS_SELECTION = ("save", "test", "connect", "delete", "duplicate")


class ParvuSshWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_title(APP_NAME)
        self.set_default_size(*WINDOW_SIZE)

        self.config: ConfigSet | None = None
        self.current: Block | None = None
        self.last_test_result: tester.TestResult | None = None
        self.last_launch: terminal.Launch | None = None

        self.toasts = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView(
            min_sidebar_width=SIDEBAR_WIDTH[0], max_sidebar_width=SIDEBAR_WIDTH[1]
        )
        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        self.sidebar = Sidebar(on_select=self._on_block_selected)
        self.editor = Editor(toast=self.toast)

        self.split.set_sidebar(self.sidebar)
        self.split.set_content(self.editor)

        self.watch = ConfigWatch(self.on_disk_change)
        self._install_actions()
        self.reload()

    # -- actions -----------------------------------------------------------

    def _install_actions(self) -> None:
        handlers = {
            "help": self.show_help,
            "preferences": self.show_preferences,
            "reload": self.reload,
            "new": self.new_host,
            "save": self.save_current,
            "test": self.test_current,
            "connect": self.connect_current,
            "delete": self.delete_current,
            "duplicate": self.duplicate_current,
        }
        for name, handler in handlers.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_a, fn=handler: fn())
            self.add_action(action)

        # Stateful, so the menu shows which order is in use as a radio item.
        saved = settings.load().order
        order = Gio.SimpleAction.new_stateful(
            "order", GLib.VariantType.new("s"), GLib.Variant("s", saved)
        )
        order.connect("change-state", lambda _a, value: self.set_order(value.unpack()))
        self.add_action(order)
        self.sidebar.set_order(saved)

        application = self.get_application()
        if application is not None:
            for action_name, keys in ACCELERATORS.items():
                application.set_accels_for_action(action_name, keys)

    # -- loading -----------------------------------------------------------

    def reload(self, keep_open: bool = False) -> None:
        """Re-read `~/.ssh/config` from disk, dropping any unsaved edit.

        With `keep_open`, the connection on screen stays on screen, found
        again by its alias in what was read.
        """
        alias = self.current.title if keep_open and self.current else None
        try:
            self.config = ConfigSet.load()
        except OSError as error:
            self.show_message(t("error.read_config"), str(error))
            return
        found = next((b for b in self.config.hosts if b.title == alias), None)
        self.current = None
        self.sidebar.set_blocks(self.config.hosts, select=found)
        self._show_block(found)
        self.watch.follow([config.path for config in self.config.files])

    def on_disk_change(self) -> None:
        """Another program wrote a loaded file: show it, unless an edit waits.

        An edit on the form is never dropped for this. The list stays as it
        is, and the save reads the file again and replays the edit on top.
        """
        if self.config is None or not self.config.stale():
            return  # our own save, or a write that changed nothing
        if self.editor.dirty or self.config.dirty:
            return
        self.reload(keep_open=True)

    def refresh_list(self, select: Block | None = None) -> None:
        """Rebuild the sidebar from the config in memory, keeping a selection."""
        self.sidebar.set_blocks(self.hosts, select=select)

    def set_order(self, order: str) -> None:
        """Sort the list and remember the choice. The file stays as it is."""
        self.lookup_action("order").set_state(GLib.Variant("s", order))
        self.sidebar.set_order(order)
        try:
            settings.save(replace(settings.load(), order=order))
        except OSError as error:
            where = shorten_home(settings.path())
            self.toast(t("prefs.error.save", path=where, detail=error))

    @property
    def hosts(self) -> list[Block]:
        return self.config.hosts if self.config is not None else []

    def _on_block_selected(self, block: Block | None) -> None:
        switching_away = (
            self.editor.dirty and self.current is not None and block is not self.current
        )
        if switching_away:
            self._ask_about_unsaved(block)
            return
        self._show_block(block)

    def _ask_about_unsaved(self, pending: Block | None) -> None:
        """Offer to save before leaving a connection with unsaved edits."""
        leaving = self.current
        dialog = Adw.AlertDialog(
            heading=t("unsaved.heading"),
            body=t("unsaved.body", alias=leaving.title if leaving else ""),
        )
        dialog.add_response("discard", t("unsaved.discard"))
        dialog.add_response("save", t("editor.save"))
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("discard")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response == "save" and not self.save_current(silent=True):
                # The save was refused, so the edit still exists. Put the
                # selection back where it was rather than stranding the user
                # on a row whose form they never saw.
                self.sidebar.select_silently(leaving)
                return
            self.editor.mark_clean()
            self._show_block(pending)

        dialog.connect("response", answered)
        dialog.present(self)

    def _show_block(self, block: Block | None) -> None:
        self.current = block
        self.editor.show_block(block, self._source_label(block))
        for name in NEEDS_SELECTION:
            self.lookup_action(name).set_enabled(block is not None)

    def _source_label(self, block: Block | None) -> str:
        """`~/.ssh/config`, as the user knows the file rather than as a path."""
        if block is None or self.config is None:
            return ""
        return shorten_home(self.config.file_of(block).path)

    # -- the actions themselves -------------------------------------------

    def show_help(self) -> None:
        HelpDialog().present(self)

    def show_preferences(self) -> None:
        PreferencesDialog().present(self)

    def new_host(self) -> None:
        """Append an empty connection and put the cursor in its alias field."""
        if self.config is None:
            return
        block = self.config.add_host(t("new.alias"))
        self.refresh_list(select=block)
        self.editor.focus_alias()

    def save_current(self, silent: bool = False) -> bool:
        """Write the form to disk. Returns whether anything was saved."""
        if self.current is None or self.config is None:
            return False

        problem = self.editor.apply()
        if problem is not None:
            self.toast(problem)
            return False

        try:
            written = self.config.save()
        except ConfigConflict as conflict:
            self.report_conflict(conflict)
            return False
        except ConfigError as error:
            self.show_message(
                t("save.failed.heading"),
                f"{t('save.failed.body')}\n\n{error}".strip(),
            )
            return False
        except OSError as error:
            self.show_message(t("save.failed.heading"), str(error))
            return False

        self.editor.mark_clean()
        self.refresh_list(select=self.current)
        if not silent:
            self.toast(
                t("save.done", path=shorten_home(written[0]))
                if written
                else t("save.nothing_changed")
            )
        self.prune_backups(written)
        return True

    def prune_backups(self, written: list[Path]) -> None:
        """Keep the newest copies of each file just written; trash the rest.

        The save has already happened. A trash that refuses is said in a toast
        of its own, after the one confirming the save, and never as a failure
        of the edit.
        """
        left = trash.prune(written, settings.load().backups)
        if left:
            self.toast(t("backups.left", folder=shorten_home(left[0].parent)))

    def test_current(self) -> None:
        """Try to connect using the form as it stands, without saving first."""
        if self.current is None:
            return
        alias = self.editor.alias()
        if not alias:
            self.toast(t("test.error.no_alias"))
            return
        if any(char in alias for char in WILDCARD_CHARS):
            # `ssh *` is not a thing; there is no single server to reach.
            self.toast(t("test.error.wildcard"))
            return

        config_text = self.editor.config_text()
        running = Adw.Toast(title=t("test.running", alias=alias), timeout=0)
        self.toasts.add_toast(running)

        def work() -> None:
            result = tester.run(alias, config_text)
            GLib.idle_add(finish, result)

        def finish(result: tester.TestResult) -> bool:
            running.dismiss()
            self.last_test_result = result
            TestResultDialog(result).present(self)
            return False  # GLib.idle_add: run once

        # A worker thread, because ssh can sit for 25 seconds and a frozen
        # window is indistinguishable from a crashed one.
        threading.Thread(target=work, daemon=True).start()

    def connect_current(self) -> None:
        """Open the user's terminal on `ssh <alias>`, reading the saved file."""
        if self.current is None:
            return
        if self.editor.dirty or self.current.dirty:
            # The terminal reads ~/.ssh/config. With an edit still on the form
            # it would connect to something other than what is on screen.
            self.toast(t("connect.error.unsaved"))
            return
        alias = self.editor.alias()
        if any(char in alias for char in WILDCARD_CHARS):
            self.toast(t("connect.error.wildcard"))
            return

        notice = t("connect.notice")
        running = Adw.Toast(title=t("connect.running", alias=alias), timeout=0)
        self.toasts.add_toast(running)

        def work() -> None:
            # Read on every click, so a choice made a second ago in the
            # preferences — or by hand in the file — is the one that opens.
            command = settings.load().terminal
            GLib.idle_add(finish, terminal.launch(alias, notice, command))

        def finish(launch: terminal.Launch) -> bool:
            running.dismiss()
            self.last_launch = launch
            if launch.status == terminal.MISSING:
                self.show_message(
                    t("connect.missing.heading"),
                    t("connect.missing.body", name=launch.terminal),
                )
            elif launch.status == terminal.NO_TERMINAL:
                names = ", ".join(item.name for item in terminal.TERMINALS)
                self.show_message(
                    t("connect.no_terminal.heading"),
                    t("connect.no_terminal.body", names=names, alias=alias),
                )
            elif launch.status == terminal.FAILED:
                self.show_message(
                    t("connect.failed.heading"),
                    t(
                        "connect.failed.body",
                        terminal=launch.terminal,
                        code=launch.returncode,
                        alias=alias,
                    ),
                )
            return False  # GLib.idle_add: run once

        # Off the main thread: finding the terminal is a process of its own,
        # and `launch` then waits to see whether the terminal stayed up.
        threading.Thread(target=work, daemon=True).start()

    def duplicate_current(self) -> None:
        """Copy the connection under a free alias, left unsaved to be renamed."""
        if self.current is None or self.config is None:
            return
        copy = self.config.duplicate(self.current, self.free_alias(self.current.title))
        self.refresh_list(select=copy)
        self.toast(t("duplicate.done"))

    def free_alias(self, base: str) -> str:
        """`vps-copia`, then `vps-copia-2`, so a duplicate never shadows a host.

        Two blocks with the same alias is legal ssh_config but useless: the
        first one wins every lookup and the second is dead text.
        """
        taken = {block.title for block in self.hosts}
        candidate = t("duplicate.alias", alias=base)
        attempt = 2
        while candidate in taken:
            candidate = t("duplicate.alias_numbered", alias=base, number=attempt)
            attempt += 1
        return candidate

    def delete_current(self) -> None:
        """Remove the connection, after asking, and write the file immediately."""
        if self.current is None or self.config is None:
            return
        block = self.current

        dialog = Adw.AlertDialog(
            heading=t("delete.heading", alias=block.title), body=t("delete.body")
        )
        dialog.add_response("cancel", t("dialog.cancel"))
        dialog.add_response("delete", t("menu.delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response != "delete":
                return
            self.remove_block(block)

        dialog.connect("response", answered)
        dialog.present(self)

    def remove_block(self, block: Block) -> None:
        """The delete itself, split out so a test need not drive the dialog."""
        if self.config is None:
            return
        self.config.remove(block)
        try:
            written = self.config.save()
        except ConfigConflict as conflict:
            self.report_conflict(conflict)
            return
        except (ConfigError, OSError) as error:
            self.show_message(t("save.failed.heading"), str(error))
            self.reload()  # the in-memory set no longer matches the file
            return
        self.editor.mark_clean()
        self.refresh_list()
        self._show_block(None)
        self.toast(t("delete.done"))
        self.prune_backups(written)

    def report_conflict(self, conflict: ConfigConflict) -> None:
        """Another program changed what the user edited: say so, then reload.

        Showing the form again over the old file would only lead to the same
        refusal on the next save. The edit is gone with the reload, which is
        why the message asks for it to be made again.
        """
        path = shorten_home(conflict.path) if conflict.path else ""
        self.show_message(
            t("conflict.heading", path=path), t("conflict.body", path=path)
        )
        self.editor.mark_clean()
        self.reload()

    # -- talking to the user ----------------------------------------------

    def toast(self, text: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=text))

    def show_message(self, heading: str, body: str) -> None:
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", t("dialog.understood"))
        dialog.present(self)


__all__ = ["ParvuSshWindow", "shorten_home"]
