"""Turn ssh_config text into blocks, losing nothing on the way.

Every byte of the input lands in exactly one place: an entry's value, an
entry's attached comments, a block's `lead` or `tail`, or a header line. A line
this parser does not understand is kept verbatim rather than dropped — we do
not get to decide that part of someone's config was a mistake.
"""

from __future__ import annotations

import re
from pathlib import Path

from parvussh.core.models import GLOBAL, HOST, MATCH, Block, Entry

# OpenSSH accepts both `Key value` and `Key=value`; both must parse.
PAIR = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_-]*)\s*(?:=\s*|\s+)(.*?)\s*$")
BARE = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_-]*)\s*$")

SECTION_KEYWORDS = ("host", "match")


def detect_newline(text: str) -> str:
    """The line ending the file already uses, so writing back keeps it."""
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf > lf else "\n"


def _split_lines(text: str) -> list[str]:
    """Split on newlines and drop the CR, so CRLF and LF files parse alike.

    Deliberately not `str.splitlines()`, which also breaks on form feed and
    U+2028 and would silently rewrite a file containing either.
    """
    return [line.removesuffix("\r") for line in text.split("\n")]


def parse_text(text: str, source: Path | None = None) -> list[Block]:
    """Parse config text into blocks. The first block is always the preamble."""
    blocks: list[Block] = []
    pending: list[str] = []
    current = Block(kind=GLOBAL, source=source)

    for line in _split_lines(text):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            pending.append(line)
            continue

        match = PAIR.match(line) or BARE.match(line)
        if match is None:
            pending.append(line)  # not ours to understand; keep the bytes
            continue

        keyword = match.group(2)
        value = match.group(3).strip() if match.re is PAIR else ""

        if keyword.lower() in SECTION_KEYWORDS:
            blocks.append(current)
            current = _open_block(keyword, value, line, pending, source)
        else:
            current.entries.append(Entry(keyword, value, list(pending)))
            current.raw.extend([*pending, line])
        pending = []

    current.tail = pending
    current.raw.extend(pending)
    blocks.append(current)
    return blocks


def _open_block(
    keyword: str,
    value: str,
    line: str,
    lead: list[str],
    source: Path | None,
) -> Block:
    """Start a new `Host` or `Match` block, adopting the pending comments."""
    is_host = keyword.lower() == "host"
    return Block(
        kind=HOST if is_host else MATCH,
        # `Host a b` matches several aliases; `Match` takes one expression.
        patterns=value.split() if is_host else [value],
        lead=list(lead),
        header_raw=line,
        raw=[*lead, line],
        source=source,
    )
