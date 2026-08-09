"""The help guide's structure: which sections exist and in what order.

The prose lives in `parvussh/i18n/pt_br/guide.py` under `guide.<key>.title` and
`guide.<key>.body`, because every user-visible string lives under
`parvussh/i18n/`. Bodies are Pango markup — `<tt>` around commands, `<b>` for
the one rule worth emphasising, and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

from parvussh.i18n import t


@dataclass(frozen=True)
class Section:
    """One part of the guide, named by key and translated on demand."""

    key: str

    @property
    def title(self) -> str:
        return t(f"guide.{self.key}.title")

    @property
    def body(self) -> str:
        return t(f"guide.{self.key}.body")


#: The path from "I have no key" to "it works", in the order someone walks it.
SECTION_KEYS: tuple[str, ...] = (
    "create",
    "install",
    "permissions",
    "password",
    "agent",
    "debug",
)

SECTIONS: tuple[Section, ...] = tuple(Section(key) for key in SECTION_KEYS)

#: How the config file itself works — the "Como funciona" page.
ABOUT_CONFIG = Section("about")
