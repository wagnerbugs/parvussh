"""The left column: every `Host` block in the config, filterable."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from parvussh.core.models import Block  # noqa: E402
from parvussh.i18n import t  # noqa: E402

MARGIN = 12
HOST_ICON = "network-server-symbolic"
PATTERN_ICON = "emblem-system-symbolic"


class Sidebar(Adw.NavigationPage):
    """`Adw.NavigationPage` holding the connection list."""

    def __init__(self, on_select: Callable[[Block | None], None]) -> None:
        super().__init__(title=t("sidebar.title"))
        self.on_select = on_select
        # Set while the list is being rebuilt: GTK emits `row-selected` as
        # rows come and go, and acting on that would load blocks the user
        # never clicked.
        self._rebuilding = False

        self.search = Gtk.SearchEntry(
            placeholder_text=t("sidebar.filter_placeholder"),
            margin_start=MARGIN,
            margin_end=MARGIN,
            margin_bottom=6,
        )
        self.search.connect("search-changed", self._on_search_changed)

        self.placeholder = Gtk.Label(
            wrap=True,
            justify=Gtk.Justification.CENTER,
            margin_top=24,
            margin_bottom=24,
            margin_start=MARGIN,
            margin_end=MARGIN,
            css_classes=["dim-label"],
        )

        self.listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.SINGLE,
            css_classes=["boxed-list"],
            margin_start=MARGIN,
            margin_end=MARGIN,
            margin_bottom=MARGIN,
            valign=Gtk.Align.START,
        )
        self.listbox.set_filter_func(self._matches_filter)
        self.listbox.set_placeholder(self.placeholder)
        self.listbox.connect("row-selected", self._on_row_selected)

        scroller = Gtk.ScrolledWindow(
            vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER
        )
        scroller.set_child(self.listbox)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self.search)
        content.append(scroller)

        view = Adw.ToolbarView()
        view.add_top_bar(self._header())
        view.set_content(content)
        self.set_child(view)
        self._update_placeholder()

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

    # -- filling -----------------------------------------------------------

    def set_blocks(self, blocks: list[Block], select: Block | None = None) -> None:
        """Rebuild the list, optionally leaving `select` selected afterwards."""
        self._rebuilding = True
        while (child := self.listbox.get_first_child()) is not None:
            self.listbox.remove(child)

        chosen = None
        for block in blocks:
            row = self._build_row(block)
            self.listbox.append(row)
            if block is select:
                chosen = row
        self._rebuilding = False

        self._update_placeholder()
        if chosen is not None:
            self.listbox.select_row(chosen)

    def _build_row(self, block: Block) -> Adw.ActionRow:
        row = Adw.ActionRow(
            # An alias may contain & or <, which Adw.ActionRow parses as markup.
            title=GLib.markup_escape_text(block.title),
            subtitle=block.subtitle() or self._missing_subtitle(block),
            activatable=True,
        )
        row.block = block
        icon = PATTERN_ICON if block.is_pattern else HOST_ICON
        row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        if block.is_pattern:
            row.set_tooltip_text(t("sidebar.wildcard_tooltip"))
        return row

    def _missing_subtitle(self, block: Block) -> str:
        """Core says nothing when there is no HostName; the wording is ours.

        A wildcard block is *supposed* to have no HostName — it sets defaults
        for other hosts. Saying "sem HostName" there would report a problem
        that does not exist, so it gets its own line.
        """
        if block.is_pattern:
            return t("sidebar.wildcard_subtitle")
        return t("sidebar.no_hostname") if block.kind == "host" else ""

    def _update_placeholder(self) -> None:
        """Say the right thing for an empty config and for an empty filter."""
        query = self.search.get_text().strip()
        if self.rows() == []:
            self.placeholder.set_text(t("sidebar.empty"))
        else:
            self.placeholder.set_text(t("sidebar.no_matches", query=query))

    # -- filtering ---------------------------------------------------------

    def _on_search_changed(self, *_args: object) -> None:
        self.listbox.invalidate_filter()
        self._update_placeholder()

    def _matches_filter(self, row: Adw.ActionRow) -> bool:
        query = self.search.get_text().strip().lower()
        if not query:
            return True
        block = row.block
        haystack = f"{block.title} {block.get('HostName')} {block.get('User')}"
        return query in haystack.lower()

    # -- selection ---------------------------------------------------------

    def _on_row_selected(self, _listbox: Gtk.ListBox, row: Adw.ActionRow) -> None:
        if self._rebuilding:
            return
        self.on_select(row.block if row is not None else None)

    def rows(self) -> list[Adw.ActionRow]:
        found = []
        index = 0
        while (row := self.listbox.get_row_at_index(index)) is not None:
            found.append(row)
            index += 1
        return found

    def visible_rows(self) -> list[Adw.ActionRow]:
        """Rows the current filter keeps.

        Computed from the predicate rather than read off the widgets: GTK
        applies a list box filter when the widget is mapped, so an unmapped
        window still reports every row as visible. This asks the question
        directly instead.
        """
        return [row for row in self.rows() if self._matches_filter(row)]

    def row_for(self, block: Block) -> Adw.ActionRow | None:
        return next((row for row in self.rows() if row.block is block), None)

    def select_silently(self, block: Block | None) -> None:
        """Move the selection without reporting it as a user choice.

        Used to put the selection back after a refused save: the list has
        already moved, but nobody asked to open a different connection.
        """
        row = self.row_for(block) if block is not None else None
        self._rebuilding = True
        self.listbox.select_row(row)
        self._rebuilding = False
