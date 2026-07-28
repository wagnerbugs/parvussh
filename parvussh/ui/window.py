"""The main window: connection list on the left, form on the right.

The window owns the `ConfigSet` and coordinates. It holds no config-parsing
logic of its own (CLAUDE.md §3) and no literal user-visible strings (D3) —
`Sidebar` and `Editor` own their widgets, `core` owns the file, `i18n` owns
the words.
"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio  # noqa: E402

from parvussh import APP_NAME  # noqa: E402
from parvussh.core.models import Block  # noqa: E402
from parvussh.core.store import ConfigSet  # noqa: E402
from parvussh.i18n import t  # noqa: E402
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

        self.toasts = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView(
            min_sidebar_width=SIDEBAR_WIDTH[0], max_sidebar_width=SIDEBAR_WIDTH[1]
        )
        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        self.sidebar = Sidebar(on_select=self._on_block_selected)
        self.editor = Editor()
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
        self._show_block(None)
        # The sidebar starts rendering this list at M7.

    @property
    def hosts(self) -> list[Block]:
        return self.config.hosts if self.config is not None else []

    def _on_block_selected(self, block: Block | None) -> None:
        self._show_block(block)

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
        """Filled in at M8, once the editor can write a block back."""

    def save_current(self) -> bool:
        """Filled in at M8."""
        return False

    def test_current(self) -> None:
        """Filled in at M12."""

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
