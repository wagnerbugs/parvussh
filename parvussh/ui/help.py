"""The help dialog: every option, the key guide, and how the file works."""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk, Pango  # noqa: E402

from parvussh.data.guide import ABOUT_CONFIG, SECTIONS, Section  # noqa: E402
from parvussh.data.keywords import CATALOG, ENUM, GROUPS  # noqa: E402
from parvussh.i18n import t  # noqa: E402
from parvussh.ui.markup import group, text_row  # noqa: E402

SUBTITLE_LINES = 4
SPACING = 12
#: How long "copied" stays up. Short, since the next copy is often a second
#: away, and each one replaces the last.
COPIED_SECONDS = 2

#: A line of the guide that is nothing but one `<tt>…</tt>`: a command, or a
#: config line, shown in its own block. `<tt>` inside a sentence is not this.
COMMAND_LINE = re.compile(r"<tt>([^<]*)</tt>")


@dataclass(frozen=True)
class Commands:
    """Consecutive command lines, as the plain text a terminal wants."""

    lines: tuple[str, ...]


class HelpDialog(Adw.PreferencesDialog):
    """Searchable reference, opened with F1 or the `?` beside the options."""

    def __init__(self) -> None:
        super().__init__(title=t("help.title"), search_enabled=True)
        self._copied: Adw.Toast | None = None
        # Kept because an `Adw.Dialog` parents its pages only once presented,
        # so they cannot be reached through the dialog's own widget tree.
        self.pages = (self._options_page(), self._keys_page(), self._about_page())
        for page in self.pages:
            self.add(page)

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
            page.add(prose_group(section, self.copy))
        return page

    def _about_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(
            title=t("help.page.about"), icon_name="help-about-symbolic"
        )
        page.add(prose_group(ABOUT_CONFIG, self.copy))
        return page

    def copy(self, text: str) -> None:
        """Put `text` on the clipboard and say so, replacing the last notice."""
        self.get_clipboard().set(text)
        if self._copied is not None:
            self._copied.dismiss()
        self._copied = Adw.Toast(title=t("help.copied"), timeout=COPIED_SECONDS)
        self.add_toast(self._copied)


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


def split_body(body: str) -> list[str | Commands]:
    """A guide body as prose paragraphs and blocks of commands, in order.

    Prose stays Pango markup. A run of lines that are each a whole `<tt>…</tt>`
    becomes one `Commands`, unescaped, and a blank line ends the run. A
    sentence leading into commands on the very next line keeps its own
    paragraph: "Em /etc/ssh/sshd_config, no servidor:" is not a command.
    """
    parts: list[str | Commands] = []
    prose: list[str] = []
    commands: list[str] = []

    def end_prose() -> None:
        text = "\n".join(prose).strip("\n")
        if text:
            parts.append(text)
        prose.clear()

    def end_commands() -> None:
        if commands:
            parts.append(Commands(tuple(commands)))
        commands.clear()

    for line in body.split("\n"):
        command = COMMAND_LINE.fullmatch(line)
        if command is None:
            end_commands()
            prose.append(line)
        else:
            end_prose()
            commands.append(html.unescape(command.group(1)))
    end_commands()
    end_prose()
    return parts


def prose_group(section: Section, copy: Callable[[str], None]) -> Adw.PreferencesGroup:
    """One guide section: wrapped, selectable prose, and commands set apart.

    The body is the one place markup is deliberate: `<tt>` around commands,
    escaped by hand at the source in `i18n/pt_br/guide.py`.
    """
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING)
    for part in split_body(section.body):
        if isinstance(part, Commands):
            content.append(command_block(part, copy))
        else:
            content.append(
                # Selectable so a file name in a sentence can be copied too.
                Gtk.Label(
                    label=part, wrap=True, xalign=0, use_markup=True, selectable=True
                )
            )
    section_group = group(title=section.title)
    section_group.add(content)
    return section_group


def command_block(commands: Commands, copy: Callable[[str], None]) -> Gtk.Box:
    """A `card` of monospace lines, each with its own copy button.

    One button per line, not per block: "test the config, then reload" is two
    commands, and the second must only run if the first passed.
    """
    block = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["card"])
    for line in commands.lines:
        row = Gtk.Box(spacing=6, margin_start=SPACING, margin_end=6)
        # Not markup: the text was unescaped for the clipboard, and the
        # label shows exactly what will be copied.
        row.append(
            Gtk.Label(
                label=line,
                wrap=True,
                wrap_mode=Pango.WrapMode.WORD_CHAR,
                xalign=0,
                hexpand=True,
                selectable=True,
                css_classes=["monospace"],
            )
        )
        button = Gtk.Button(
            icon_name="edit-copy-symbolic",
            tooltip_text=t("help.copy_tooltip"),
            valign=Gtk.Align.CENTER,
            margin_top=3,
            margin_bottom=3,
            css_classes=["flat"],
        )
        button.connect("clicked", lambda _button, text=line: copy(text))
        row.append(button)
        block.append(row)
    return block
