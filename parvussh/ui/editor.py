"""The right column: the form for one connection.

At M6 this is the header bar and the empty state. M8 adds the form.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from parvussh import APP_NAME  # noqa: E402
from parvussh.core.models import Block  # noqa: E402
from parvussh.i18n import t  # noqa: E402

EMPTY = "empty"
FORM = "form"


class Editor(Adw.NavigationPage):
    """`Adw.NavigationPage` holding the connection form and its empty state."""

    def __init__(self) -> None:
        super().__init__(title=t("editor.title"))

        self.title_widget = Adw.WindowTitle(title=APP_NAME)
        self.header = self._header()

        self.placeholder = Adw.StatusPage(
            icon_name="network-server-symbolic",
            title=t("editor.empty.title"),
            description=t("editor.empty.description"),
        )

        self.stack = Gtk.Stack()
        self.stack.add_named(self.placeholder, EMPTY)

        view = Adw.ToolbarView()
        view.add_top_bar(self.header)
        view.set_content(self.stack)
        self.set_child(view)

    def _header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar(title_widget=self.title_widget)

        more = Gio.Menu()
        more.append(t("menu.duplicate"), "win.duplicate")
        more.append(t("menu.delete"), "win.delete")

        header.pack_end(
            Gtk.Button(
                label=t("editor.save"),
                action_name="win.save",
                css_classes=["suggested-action"],
            )
        )
        header.pack_end(
            Gtk.Button(
                label=t("editor.test"),
                action_name="win.test",
                tooltip_text=t("editor.test_tooltip"),
            )
        )
        header.pack_end(
            Gtk.MenuButton(
                icon_name="view-more-symbolic",
                menu_model=more,
                tooltip_text=t("editor.more_tooltip"),
            )
        )
        return header

    def show_block(self, block: Block | None, source: str = "") -> None:
        """Display `block`, or the empty state when there is nothing selected."""
        if block is None:
            self.stack.set_visible_child_name(EMPTY)
            self.title_widget.set_title(APP_NAME)
            self.title_widget.set_subtitle("")
            return

        self.title_widget.set_title(block.title)
        self.title_widget.set_subtitle(source)
        self.stack.set_visible_child_name(FORM)
