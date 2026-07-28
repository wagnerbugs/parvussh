"""Popovers that pick something for a form row.

The add-option popover is the app's main teaching surface: the user types what
they are trying to achieve, in Portuguese, and reads what each option does
before choosing one.
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from parvussh.data.keywords import Keyword, search  # noqa: E402
from parvussh.i18n import t  # noqa: E402

WIDTH = 420
LIST_HEIGHT = 320
PADDING = 10


class AddOptionPopover(Gtk.Popover):
    """Search the catalog by name or by what an option does, and add one."""

    def __init__(
        self,
        on_pick: Callable[[Keyword], None],
        used: Callable[[], set[str]] | None = None,
    ) -> None:
        super().__init__()
        self.on_pick = on_pick
        # A callable, not a set: what is already on the form changes every time
        # a row is added or removed, and a cached copy goes stale silently.
        self.used = used or set

        self.search = Gtk.SearchEntry(placeholder_text=t("addoption.placeholder"))
        self.search.connect("search-changed", lambda *_a: self.refresh())
        self.search.connect("activate", lambda *_a: self.pick_first())

        self.empty = Gtk.Label(
            label=t("addoption.no_matches"),
            wrap=True,
            margin_top=18,
            margin_bottom=18,
            css_classes=["dim-label"],
        )

        self.listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"]
        )
        self.listbox.set_placeholder(self.empty)
        self.listbox.connect("row-activated", self._on_activated)

        scroller = Gtk.ScrolledWindow(
            min_content_height=LIST_HEIGHT, hscrollbar_policy=Gtk.PolicyType.NEVER
        )
        scroller.set_child(self.listbox)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=PADDING,
            margin_top=PADDING,
            margin_bottom=PADDING,
            margin_start=PADDING,
            margin_end=PADDING,
        )
        box.set_size_request(WIDTH, -1)
        box.append(self.search)
        box.append(scroller)
        self.set_child(box)

        self.connect("show", self._on_show)
        self.refresh()

    # -- contents ----------------------------------------------------------

    def _on_show(self, *_args: object) -> None:
        """Start from a clean slate every time, with the cursor ready."""
        self.search.set_text("")
        self.refresh()
        self.search.grab_focus()

    def refresh(self) -> None:
        """Rebuild the list for the current query, minus what is already used."""
        while (child := self.listbox.get_first_child()) is not None:
            self.listbox.remove(child)
        for keyword in search(self.search.get_text(), self.used()):
            row = Adw.ActionRow(
                title=keyword.name,
                subtitle=keyword.description,
                subtitle_lines=2,
                activatable=True,
            )
            row.keyword = keyword
            self.listbox.append(row)

    def rows(self) -> list[Adw.ActionRow]:
        found = []
        index = 0
        while (row := self.listbox.get_row_at_index(index)) is not None:
            found.append(row)
            index += 1
        return found

    # -- picking -----------------------------------------------------------

    def pick_first(self) -> None:
        """Enter takes the best match, so adding an option never needs the mouse."""
        row = self.listbox.get_row_at_index(0)
        if row is not None:
            self._on_activated(self.listbox, row)

    def _on_activated(self, _listbox: Gtk.ListBox, row: Adw.ActionRow) -> None:
        self.popdown()
        self.on_pick(row.keyword)
