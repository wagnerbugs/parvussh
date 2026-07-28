"""The left column: every `Host` block in the config, filterable.

At M6 this is the header bar and an empty list. M7 fills it.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from parvussh.core.models import Block  # noqa: E402
from parvussh.i18n import t  # noqa: E402

MARGIN = 12


class Sidebar(Adw.NavigationPage):
    """`Adw.NavigationPage` holding the connection list."""

    def __init__(self, on_select: Callable[[Block | None], None]) -> None:
        super().__init__(title=t("sidebar.title"))
        self.on_select = on_select

        self.listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.SINGLE,
            css_classes=["boxed-list"],
            margin_start=MARGIN,
            margin_end=MARGIN,
            margin_bottom=MARGIN,
            valign=Gtk.Align.START,
        )

        scroller = Gtk.ScrolledWindow(
            vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER
        )
        scroller.set_child(self.listbox)

        view = Adw.ToolbarView()
        view.add_top_bar(self._header())
        view.set_content(scroller)
        self.set_child(view)

    def _header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        header.pack_start(
            Gtk.Button(
                icon_name="list-add-symbolic",
                tooltip_text=t("sidebar.new_tooltip"),
                action_name="win.new",
            )
        )

        menu = Gio.Menu()
        menu.append(t("menu.help"), "win.help")
        menu.append(t("menu.reload"), "win.reload")
        menu.append(t("menu.about"), "app.about")
        header.pack_end(
            Gtk.MenuButton(
                icon_name="open-menu-symbolic",
                menu_model=menu,
                tooltip_text=t("sidebar.menu_tooltip"),
            )
        )
        return header
