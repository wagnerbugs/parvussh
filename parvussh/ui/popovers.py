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

from parvussh.core.keys import SshKey, list_keys  # noqa: E402
from parvussh.data.keywords import Keyword, search  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui.markup import text_row  # noqa: E402

WIDTH = 420
LIST_HEIGHT = 320
KEY_LIST_WIDTH = 340
KEY_LIST_HEIGHT = 260
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
            row = text_row(
                Adw.ActionRow,
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


def key_summary(key: SshKey) -> str:
    """`ED25519 · 256 bits · wagner@notebook`, or the filename alone."""
    if not key.described:
        return t("keypicker.undescribed")
    if key.comment:
        return t(
            "keypicker.summary",
            kind=key.kind,
            bits=key.bits,
            comment=key.comment,
        )
    return t("keypicker.summary_no_comment", kind=key.kind, bits=key.bits)


class KeyPickerPopover(Gtk.Popover):
    """Choose a private key from `~/.ssh`, create one, or browse for a file.

    The list is rebuilt on every `show` and never cached: a key created a
    minute ago in the same session has to appear without restarting the app.
    """

    def __init__(
        self,
        on_pick: Callable[[str], None],
        on_create: Callable[[], None],
        on_browse: Callable[[], None],
    ) -> None:
        super().__init__()
        self.on_pick = on_pick
        self.on_create = on_create
        self.on_browse = on_browse
        self.connect("show", lambda *_a: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        self.keys = list_keys()
        box.append(self._key_list() if self.keys else self._nothing_found())

        create = Gtk.Button(label=t("keypicker.create"))
        create.connect("clicked", lambda *_a: self._run(self.on_create))
        box.append(create)

        browse = Gtk.Button(label=t("keypicker.browse"), css_classes=["flat"])
        browse.connect("clicked", lambda *_a: self._run(self.on_browse))
        box.append(browse)

        self.set_child(box)

    def _key_list(self) -> Gtk.ScrolledWindow:
        listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"]
        )
        for key in self.keys:
            # A key's comment is whatever the user typed at ssh-keygen time.
            row = text_row(
                Adw.ActionRow,
                title=key.name,
                subtitle=key_summary(key),
                activatable=True,
            )
            row.key = key
            # Per row rather than the list box's `row-activated`: an
            # Adw.ActionRow emits `activated` itself, which keeps the handler
            # reachable from a test without synthesising a click.
            row.connect("activated", self._on_activated)
            listbox.append(row)
        self.listbox = listbox

        scroller = Gtk.ScrolledWindow(
            min_content_width=KEY_LIST_WIDTH,
            max_content_height=KEY_LIST_HEIGHT,
            propagate_natural_height=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        scroller.set_child(listbox)
        return scroller

    def _nothing_found(self) -> Gtk.Label:
        self.listbox = None
        return Gtk.Label(
            label=t("keypicker.empty"), wrap=True, css_classes=["dim-label"]
        )

    def rows(self) -> list[Adw.ActionRow]:
        if self.listbox is None:
            return []
        found = []
        index = 0
        while (row := self.listbox.get_row_at_index(index)) is not None:
            found.append(row)
            index += 1
        return found

    def _on_activated(self, row: Adw.ActionRow) -> None:
        self.popdown()
        # The `~/...` form, so the config stays portable between machines.
        self.on_pick(row.key.display_path)

    def _run(self, action: Callable[[], None]) -> None:
        self.popdown()
        action()
