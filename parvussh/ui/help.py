"""The help dialog: every option, the key guide, and how the file works."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from parvussh.data.guide import ABOUT_CONFIG, SECTIONS, Section  # noqa: E402
from parvussh.data.keywords import CATALOG, ENUM, GROUPS  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui.markup import group, text_row  # noqa: E402

SUBTITLE_LINES = 4


class HelpDialog(Adw.PreferencesDialog):
    """Searchable reference, opened with F1 or the `?` beside the options."""

    def __init__(self) -> None:
        super().__init__(title=t("help.title"), search_enabled=True)
        self.add(self._options_page())
        self.add(self._keys_page())
        self.add(self._about_page())

    def _options_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(
            title=t("help.page.options"), icon_name="view-list-symbolic"
        )
        for group_key in GROUPS:
            category = group(title=t(f"group.{group_key}"))
            for keyword in CATALOG:
                if keyword.group != group_key:
                    continue
                category.add(
                    text_row(
                        Adw.ActionRow,
                        title=keyword.name,
                        subtitle=option_subtitle(keyword),
                        subtitle_lines=SUBTITLE_LINES,
                    )
                )
            page.add(category)
        return page

    def _keys_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(
            title=t("help.page.keys"), icon_name="dialog-password-symbolic"
        )
        for section in SECTIONS:
            page.add(prose_group(section))
        return page

    def _about_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(
            title=t("help.page.about"), icon_name="help-about-symbolic"
        )
        page.add(prose_group(ABOUT_CONFIG))
        return page


def option_subtitle(keyword) -> str:
    """The description, plus whichever of example or allowed values applies."""
    if keyword.example:
        return t(
            "help.with_example",
            description=keyword.description,
            example=keyword.example,
        )
    if keyword.kind == ENUM and keyword.values:
        return t(
            "help.with_values",
            description=keyword.description,
            values=", ".join(keyword.values),
        )
    return keyword.description


def prose_group(section: Section) -> Adw.PreferencesGroup:
    """One guide section as a wrapped, selectable, copy-friendly block.

    The body is the one place markup is deliberate: `<tt>` around commands,
    escaped by hand at the source in `i18n/pt_br/guide.py`.
    """
    section_group = group(title=section.title)
    section_group.add(
        Gtk.Label(
            label=section.body,
            wrap=True,
            xalign=0,
            use_markup=True,
            # Selectable so the commands can be copied straight out.
            selectable=True,
        )
    )
    return section_group
