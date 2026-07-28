"""Pango markup is on by default in libadwaita, and that is a trap.

Every `Adw.PreferencesRow` — ActionRow, EntryRow, SwitchRow, SpinRow — parses
its title and subtitle as Pango markup, and so does `Adw.PreferencesGroup`.
Almost everything we put in them is *data*: a host alias, a user name, an
option description, an example command. Any of those may legitimately contain
`&` or `<`.

`RemoteCommand cd /srv/app && bash -l` is an ordinary config line. Fed to a row
as markup, GTK drops the whole string and prints a warning nobody reads.

**Order matters.** `Adw.ActionRow(title=...)` parses the title *during*
construction, so turning markup off afterwards is too late: the warning has
already fired and the label is already empty. `text_row()` builds the widget
first, disables markup, and only then puts the text in.

Two ways out, and the right one depends on the widget:

- Rows have a switch, so turn markup **off**. The text is content.
- `Adw.PreferencesGroup` has no switch, so **escape** on the way in.

Anything that genuinely is markup — the guide's `<tt>` commands — goes into a
`Gtk.Label` with `use_markup=True` and is escaped by hand at the source.
"""

from __future__ import annotations

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib  # noqa: E402


def no_markup(row: Adw.PreferencesRow) -> Adw.PreferencesRow:
    """Turn Pango markup off. Call this *before* putting any text in."""
    row.set_use_markup(False)
    return row


def text_row(
    kind: type[Adw.PreferencesRow],
    title: str = "",
    subtitle: str | None = None,
    **kwargs: Any,
) -> Adw.PreferencesRow:
    """Build a preferences row whose title and subtitle are text, not markup."""
    row = kind(**kwargs)
    row.set_use_markup(False)
    if title:
        row.set_title(title)
    if subtitle is not None:
        row.set_subtitle(subtitle)
    return row


def escape(text: str) -> str:
    """Escape text for a widget that gives us no way to turn markup off."""
    return GLib.markup_escape_text(text)


def group(title: str = "", description: str = "") -> Adw.PreferencesGroup:
    """An `Adw.PreferencesGroup` whose heading is treated as text."""
    return Adw.PreferencesGroup(title=escape(title), description=escape(description))
