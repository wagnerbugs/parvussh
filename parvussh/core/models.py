"""Dataclasses describing one parsed ssh_config file.

A `Block` keeps every original line it was built from, so a block the user did
not edit is written back byte for byte. Only blocks marked `dirty` are ever
re-rendered — that is the first rule of the config contract, and everything
else in this module exists to keep it true.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

GLOBAL = "global"
HOST = "host"
MATCH = "match"

INDENT = "    "
WILDCARD_CHARS = "*?!"
DEFAULT_PORT = "22"


@dataclass
class Entry:
    """One `Keyword value` line, plus the comment lines sitting above it."""

    keyword: str  # original spelling; comparison is always .lower()
    value: str
    comments: list[str] = field(default_factory=list)


@dataclass(eq=False)
class Block:
    """The global preamble, a `Host` block or a `Match` block.

    `eq=False` on purpose: a block is a position in a document, not a value.
    Two `Host` blocks can hold identical text and still be different blocks, so
    `list.remove(block)` and `block in blocks` must compare by identity — with
    the generated `__eq__` they would silently act on the wrong one.
    """

    kind: str  # GLOBAL | HOST | MATCH
    patterns: list[str] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)
    lead: list[str] = field(default_factory=list)  # lines above the header
    tail: list[str] = field(default_factory=list)  # leftovers at the end
    header_raw: str = ""
    raw: list[str] = field(default_factory=list)  # every original line
    source: Path | None = None
    dirty: bool = False

    @property
    def title(self) -> str:
        return " ".join(self.patterns) if self.patterns else "(global)"

    @property
    def is_pattern(self) -> bool:
        """True for wildcard blocks such as `Host *`, which match many hosts."""
        return any(
            char in pattern for pattern in self.patterns for char in WILDCARD_CHARS
        )

    def get(self, keyword: str, default: str = "") -> str:
        """The first value for `keyword`, compared case-insensitively."""
        wanted = keyword.lower()
        for entry in self.entries:
            if entry.keyword.lower() == wanted:
                return entry.value
        return default

    def comments_for(self, keyword: str) -> list[str]:
        """Comments attached to `keyword`, so an edit can carry them over."""
        wanted = keyword.lower()
        for entry in self.entries:
            if entry.keyword.lower() == wanted:
                return list(entry.comments)
        return []

    def subtitle(self) -> str:
        """The sidebar's second line: `user@hostname`, plus `:port` when set.

        Empty when there is no HostName. The UI supplies the wording for that
        case; `core` holds no translated text.
        """
        hostname = self.get("HostName")
        if not hostname:
            return ""
        user = self.get("User")
        port = self.get("Port")
        text = f"{user}@{hostname}" if user else hostname
        return f"{text}:{port}" if port and port != DEFAULT_PORT else text

    def render(self) -> list[str]:
        """This block's lines. An untouched block returns its original bytes."""
        if not self.dirty:
            return list(self.raw)
        indent = "" if self.kind == GLOBAL else INDENT
        out = list(self.lead)
        if self.kind == HOST:
            out.append("Host " + " ".join(self.patterns))
        elif self.kind == MATCH:
            out.append(self.header_raw.rstrip())
        for entry in self.entries:
            out.extend(entry.comments)
            out.append(f"{indent}{entry.keyword} {entry.value}".rstrip())
        out.extend(self.tail)
        return out


def render_blocks(blocks: list[Block], newline: str = "\n") -> str:
    """Join every block into file text, ending with exactly one newline.

    Leading and trailing blank lines are dropped, which is what lets a newly
    created block carry `lead=[""]` — one blank line before it — without
    opening the file with an empty line.
    """
    lines: list[str] = []
    for block in blocks:
        lines.extend(block.render())
    body = newline.join(lines).strip("\r\n")
    return body + newline if body else ""
