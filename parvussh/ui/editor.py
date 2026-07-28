"""The right column: the form for one connection."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from parvussh import APP_NAME  # noqa: E402
from parvussh.core.models import Block, Entry  # noqa: E402
from parvussh.data.keywords import BASIC, Keyword, for_option  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui.popovers import AddOptionPopover  # noqa: E402
from parvussh.ui.rows import OptionRow  # noqa: E402

EMPTY = "empty"
FORM = "form"
DIRTY_PREFIX = "• "
BASIC_LOWER = {name.lower() for name in BASIC}


class Editor(Adw.NavigationPage):
    """The connection form, its empty state, and the unsaved-changes flag."""

    def __init__(
        self,
        on_dirty: Callable[[], None] | None = None,
        toast: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(title=t("editor.title"))
        self.on_dirty = on_dirty
        self.toast = toast
        self.block: Block | None = None
        self.dirty = False
        # Set while fields are being filled from a block: a programmatic
        # set_text emits `changed` exactly like a keystroke, and without this
        # merely opening a connection would mark it edited.
        self._loading = False

        self.title_widget = Adw.WindowTitle(title=APP_NAME)
        self.header = self._header()

        self.placeholder = Adw.StatusPage(
            icon_name="network-server-symbolic",
            title=t("editor.empty.title"),
            description=t("editor.empty.description"),
        )

        self.stack = Gtk.Stack()
        self.stack.add_named(self.placeholder, EMPTY)
        self.stack.add_named(self._form(), FORM)

        view = Adw.ToolbarView()
        view.add_top_bar(self.header)
        view.set_content(self.stack)
        self.set_child(view)

    # -- construction ------------------------------------------------------

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

    def _form(self) -> Adw.PreferencesPage:
        self.host = Adw.EntryRow(title=t("editor.field.host"))
        self.hostname = Adw.EntryRow(title=t("editor.field.hostname"))
        self.user = Adw.EntryRow(title=t("editor.field.user"))
        self.port = Adw.EntryRow(title=t("editor.field.port"))
        self.port.set_input_purpose(Gtk.InputPurpose.DIGITS)

        basics = Adw.PreferencesGroup(
            title=t("editor.group.connection"),
            description=t("editor.group.connection_description"),
        )
        for row in (self.host, self.hostname, self.user, self.port):
            row.connect("changed", lambda *_a: self.mark_dirty())
            basics.add(row)

        self.options: list[OptionRow] = []
        self.extras = Adw.PreferencesGroup(title=t("editor.group.extras"))
        self.extras.set_header_suffix(self._extras_suffix())
        self.empty_extras = Gtk.Label(
            label=t("editor.group.extras_empty"),
            wrap=True,
            xalign=0,
            css_classes=["dim-label"],
        )
        self.extras.add(self.empty_extras)

        page = Adw.PreferencesPage()
        page.add(basics)
        page.add(self.extras)
        return page

    def _extras_suffix(self) -> Gtk.Box:
        self.add_popover = AddOptionPopover(
            on_pick=self.pick_option, used=self.used_options
        )
        box = Gtk.Box(spacing=6)
        box.append(
            Gtk.Button(
                icon_name="help-about-symbolic",
                action_name="win.help",
                tooltip_text=t("editor.help_tooltip"),
                css_classes=["flat"],
            )
        )
        box.append(
            Gtk.MenuButton(
                icon_name="list-add-symbolic",
                popover=self.add_popover,
                tooltip_text=t("addoption.tooltip"),
                css_classes=["flat"],
            )
        )
        return box

    # -- extra options -----------------------------------------------------

    def pick_option(self, keyword: Keyword) -> None:
        """Add an option the user chose from the popover, ready to type into."""
        option = self.add_option(keyword)
        self.mark_dirty()
        option.row.grab_focus()

    def add_option(self, keyword: Keyword, value: str = "", comments=None) -> OptionRow:
        """Put one option row on the form and return it."""
        option = OptionRow(
            keyword,
            value,
            comments,
            on_change=self.mark_dirty,
            on_remove=self.remove_option,
            toast=self.toast,
        )
        self.options.append(option)
        self.extras.add(option.row)
        self._sync_extras()
        return option

    def remove_option(self, option: OptionRow) -> None:
        self.extras.remove(option.row)
        self.options.remove(option)
        self._sync_extras()
        self.mark_dirty()

    def used_options(self) -> set[str]:
        """Lowercased names already on the form, so the `+` never offers them."""
        return {option.keyword.name.lower() for option in self.options}

    def _clear_options(self) -> None:
        for option in self.options:
            self.extras.remove(option.row)
        self.options = []

    def _sync_extras(self) -> None:
        self.empty_extras.set_visible(not self.options)

    def _basic_rows(self) -> tuple[tuple[str, Adw.EntryRow], ...]:
        """The three catalogued fields, in the order they are written out."""
        return (
            ("HostName", self.hostname),
            ("User", self.user),
            ("Port", self.port),
        )

    # -- loading -----------------------------------------------------------

    def show_block(self, block: Block | None, source: str = "") -> None:
        """Display `block`, or the empty state when nothing is selected."""
        self.block = block
        self.dirty = False

        if block is None:
            self.stack.set_visible_child_name(EMPTY)
            self.title_widget.set_title(APP_NAME)
            self.title_widget.set_subtitle("")
            return

        self._loading = True
        self.host.set_text(block.title)
        self.hostname.set_text(block.get("HostName"))
        self.user.set_text(block.get("User"))
        self.port.set_text(block.get("Port"))

        self._clear_options()
        for entry in block.entries:
            if entry.keyword.lower() in BASIC_LOWER:
                continue
            # An option missing from the catalog still gets a row — it is kept
            # as plain text and written back untouched (contract rule 3).
            self.add_option(for_option(entry.keyword), entry.value, entry.comments)
        self._loading = False

        self.title_widget.set_title(block.title)
        self.title_widget.set_subtitle(source)
        self.stack.set_visible_child_name(FORM)

    def focus_alias(self) -> None:
        self.host.grab_focus()

    def alias(self) -> str:
        """The first pattern in the Host field — what `ssh <alias>` would take."""
        patterns = self.host.get_text().split()
        return patterns[0] if patterns else ""

    def config_text(self) -> str:
        """The form as a standalone config, for testing before saving.

        Built from the widgets rather than from the block, so the connection
        being tested is the one on screen — which is the whole point of being
        able to test before committing anything to disk.
        """
        lines = [f"Host {self.alias()}"]
        for name, row in self._basic_rows():
            value = row.get_text().strip()
            if value:
                lines.append(f"    {name} {value}")
        lines.extend(option.config_line() for option in self.options if option.value())
        return "\n".join(lines) + "\n"

    # -- editing -----------------------------------------------------------

    def mark_dirty(self) -> None:
        if self._loading or self.block is None:
            return
        self.dirty = True
        self.title_widget.set_title(DIRTY_PREFIX + self.host.get_text().strip())
        if self.on_dirty is not None:
            self.on_dirty()

    def mark_clean(self) -> None:
        self.dirty = False
        if self.block is not None:
            self.title_widget.set_title(self.block.title)

    def apply(self) -> str | None:
        """Write the form back into the block. Returns a message, or None.

        Nothing reaches disk here — this only updates the in-memory block and
        marks it dirty. `ConfigSet.save()` is what writes.
        """
        block = self.block
        if block is None:
            return None

        alias = self.host.get_text().strip()
        if not alias:
            return t("editor.error.empty_alias")
        port = self.port.get_text().strip()
        if port and not port.isdigit():
            return t("editor.error.port_not_a_number")

        # Comments belong to the directive below them and must survive an edit.
        comments = {entry.keyword.lower(): entry.comments for entry in block.entries}
        entries = [
            Entry(name, row.get_text().strip(), comments.get(name.lower(), []))
            for name, row in self._basic_rows()
            if row.get_text().strip()
        ]
        entries.extend(
            Entry(option.keyword.name, option.value(), option.comments)
            for option in self.options
            if option.value()
        )

        patterns = alias.split()
        if block.patterns == patterns and block.entries == entries:
            # Nothing actually changed. Marking the block dirty anyway would
            # rewrite the file and leave a dated backup behind every time
            # someone pressed Ctrl+S, quietly filling ~/.ssh with copies.
            return None

        block.patterns = patterns
        block.entries = entries
        block.dirty = True
        return None
