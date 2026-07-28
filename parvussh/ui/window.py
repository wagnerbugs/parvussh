"""The main window: connection list on the left, form on the right.

The window owns the `ConfigSet` and coordinates. It holds no config-parsing
logic of its own (CLAUDE.md §3) and no literal user-visible strings (D3) —
`Sidebar` and `Editor` own their widgets, `core` owns the file, `i18n` owns
the words.
"""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from parvussh import APP_NAME  # noqa: E402
from parvussh.core import tester  # noqa: E402
from parvussh.core.models import WILDCARD_CHARS, Block  # noqa: E402
from parvussh.core.store import ConfigSet  # noqa: E402
from parvussh.core.writer import ConfigError  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui.dialogs import TestResultDialog  # noqa: E402
from parvussh.ui.editor import Editor  # noqa: E402
from parvussh.ui.sidebar import Sidebar  # noqa: E402

WINDOW_SIZE = (1020, 700)
SIDEBAR_WIDTH = (280, 360)

#: Window actions and their accelerators. Every one exists from M6 on, even
#: where the handler is still a guard — an action that appears halfway through
#: a milestone is an action nobody wires a keyboard shortcut to.
ACCELERATORS = {
    "win.save": ["<Control>s"],
    "win.new": ["<Control>n"],
    "win.help": ["F1"],
}

#: Actions that need a selected connection to mean anything. Disabling the
#: *action* dims every button bound to it and leaves the header bar itself
#: alone — turning the whole header insensitive would also disable the window
#: controls, which is how you trap someone in a window they cannot close.
NEEDS_SELECTION = ("save", "test", "delete", "duplicate")


class ParvuSshWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_title(APP_NAME)
        self.set_default_size(*WINDOW_SIZE)

        self.config: ConfigSet | None = None
        self.current: Block | None = None
        self.last_test_result: tester.TestResult | None = None

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

        self._install_actions()
        self.reload()

    # -- actions -----------------------------------------------------------

    def _install_actions(self) -> None:
        handlers = {
            "help": self.show_help,
            "reload": self.reload,
            "new": self.new_host,
            "save": self.save_current,
            "test": self.test_current,
            "delete": self.delete_current,
            "duplicate": self.duplicate_current,
        }
        for name, handler in handlers.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_a, fn=handler: fn())
            self.add_action(action)

        application = self.get_application()
        if application is not None:
            for action_name, keys in ACCELERATORS.items():
                application.set_accels_for_action(action_name, keys)

    # -- loading -----------------------------------------------------------

    def reload(self) -> None:
        """Re-read `~/.ssh/config` from disk, dropping any unsaved edit."""
        try:
            self.config = ConfigSet.load()
        except OSError as error:
            self.show_message(t("error.read_config"), str(error))
            return
        self.current = None
        self.sidebar.set_blocks(self.config.hosts)
        self._show_block(None)

    def refresh_list(self, select: Block | None = None) -> None:
        """Rebuild the sidebar from the config in memory, keeping a selection."""
        self.sidebar.set_blocks(self.hosts, select=select)

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
        """Filled in at M13, once `data/guide.py` exists."""

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
        return True

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

    def duplicate_current(self) -> None:
        """Filled in at M13."""

    def delete_current(self) -> None:
        """Filled in at M13."""

    # -- talking to the user ----------------------------------------------

    def toast(self, text: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=text))

    def show_message(self, heading: str, body: str) -> None:
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", t("dialog.understood"))
        dialog.present(self)


def shorten_home(path: Path) -> str:
    """`/home/x/.ssh/config` -> `~/.ssh/config`. Left alone if not under home."""
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)


__all__ = ["ParvuSshWindow", "shorten_home"]
