"""One widget per option kind, plus the rule for when not to use it.

A typed widget is a promise that every value it can hold round-trips. A
`Adw.SpinRow` bounded 0..3600 cannot hold `ConnectTimeout 99999`, and a
`Adw.SwitchRow` cannot hold `Compression maybe` — both would quietly rewrite
the user's file the first time it was saved. So a row whose current value does
not fit its widget falls back to plain text, where anything survives
(CLAUDE.md §4, rules 1 and 3).
"""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from parvussh.data.keywords import BOOL, ENUM, INT, Keyword  # noqa: E402
from parvussh.i18n import t  # noqa: E402

#: ssh accepts exactly these for a boolean option; anything else is not one.
YES, NO = "yes", "no"
BOOLEAN_VALUES = (YES, NO)


def fits_widget(keyword: Keyword, value: str) -> bool:
    """Whether `value` survives a round trip through `keyword`'s typed widget.

    An empty value always fits: that is a freshly added option, not something
    read out of the user's file.
    """
    if not value:
        return True
    if keyword.kind == BOOL:
        return value.strip().lower() in BOOLEAN_VALUES
    if keyword.kind == INT:
        try:
            number = int(value.strip())
        except ValueError:
            return False
        return keyword.lo <= number <= keyword.hi
    # ENUM keeps an unlisted value by adding it to the model, and every other
    # kind is already free text.
    return True


class OptionRow:
    """One ssh option in the form, wrapping whichever widget suits its kind."""

    def __init__(
        self,
        keyword: Keyword,
        value: str = "",
        comments: list[str] | None = None,
        on_change: Callable[[], None] | None = None,
        on_remove: Callable[[OptionRow], None] | None = None,
    ) -> None:
        self.keyword = keyword
        self.comments = list(comments or [])
        self.on_change = on_change
        self.on_remove = on_remove
        # False when the value forced a fallback to a text row; `value()` reads
        # the widget that was actually built, not the one the kind implies.
        self.typed = fits_widget(keyword, value)

        self.row = self._build(value)
        self.row.add_suffix(self._remove_button())

    # -- construction ------------------------------------------------------

    def _build(self, value: str) -> Adw.PreferencesRow:
        kind = self.keyword.kind if self.typed else None
        if kind == BOOL:
            return self._switch(value)
        if kind == ENUM:
            return self._combo(value)
        if kind == INT:
            return self._spin(value)
        return self._entry(value)

    def _switch(self, value: str) -> Adw.SwitchRow:
        row = Adw.SwitchRow(title=self.keyword.name, subtitle=self.keyword.description)
        # A newly added boolean starts off, matching ssh's own default. The
        # switch is right there if that is not what they wanted.
        row.set_active(value.strip().lower() == YES)
        row.connect("notify::active", self._changed)
        return row

    def _combo(self, value: str) -> Adw.ComboRow:
        values = list(self.keyword.values)
        if value and value not in values:
            # Keep a value we do not recognise rather than snapping it to one
            # we do.
            values.append(value)
        self.model = Gtk.StringList.new(values)
        row = Adw.ComboRow(
            title=self.keyword.name,
            subtitle=self.keyword.description,
            model=self.model,
        )
        if value in values:
            row.set_selected(values.index(value))
        row.connect("notify::selected", self._changed)
        return row

    def _spin(self, value: str) -> Adw.SpinRow:
        row = Adw.SpinRow.new_with_range(self.keyword.lo, self.keyword.hi, 1)
        row.set_title(self.keyword.name)
        row.set_subtitle(self._hint())
        row.set_value(int(value.strip()) if value.strip() else self.keyword.lo)
        row.connect("notify::value", self._changed)
        return row

    def _entry(self, value: str) -> Adw.EntryRow:
        row = Adw.EntryRow(title=self.keyword.name)
        row.set_text(value)
        row.set_tooltip_text(self._hint())
        row.connect("changed", self._changed)
        return row

    def _hint(self) -> str:
        """Description, plus an example when the catalog offers one."""
        if self.keyword.example:
            return t(
                "rows.hint_with_example",
                description=self.keyword.description,
                example=self.keyword.example,
            )
        return self.keyword.description

    def _remove_button(self) -> Gtk.Button:
        button = Gtk.Button(
            icon_name="user-trash-symbolic",
            valign=Gtk.Align.CENTER,
            tooltip_text=t("rows.remove_tooltip", name=self.keyword.name),
            css_classes=["flat", "circular"],
        )
        button.connect("clicked", self._remove)
        return button

    # -- signals -----------------------------------------------------------

    def _changed(self, *_args: object) -> None:
        if self.on_change is not None:
            self.on_change()

    def _remove(self, *_args: object) -> None:
        if self.on_remove is not None:
            self.on_remove(self)

    # -- reading -----------------------------------------------------------

    def value(self) -> str:
        """The value as it would be written to the config file."""
        if not self.typed:
            return self.row.get_text().strip()
        if self.keyword.kind == BOOL:
            return YES if self.row.get_active() else NO
        if self.keyword.kind == ENUM:
            return self.model.get_string(self.row.get_selected()) or ""
        if self.keyword.kind == INT:
            return str(int(self.row.get_value()))
        return self.row.get_text().strip()

    def config_line(self, indent: str = "    ") -> str:
        """How this row renders into the file. Handy in tests and in the tester."""
        return f"{indent}{self.keyword.name} {self.value()}".rstrip()
