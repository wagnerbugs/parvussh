"""Re-apply the user's edit on top of a file another program changed.

The app can sit open for hours, and other programs edit `~/.ssh/config` too —
a provisioning script that moves a server from `Port 22` to `Port 1310`, or
the user in a text editor. Writing our copy of every block back would undo
their change. So when the file on disk is no longer the one we read, the
edit is replayed on top of what is there now, block by block:

- an edited block replaces the block it was read from;
- a removed block is removed;
- a new block (Novo, Duplicar) goes after the same neighbour, or at the end.

Each block is found by the text it had when we read it. When that text is
gone or is no longer unique, the change on disk touched the very place the
edit lands, and guessing would lose one of the two edits. `ConfigConflict`
is raised instead, before anything is written or mutated.
"""

from __future__ import annotations

from pathlib import Path

from parvussh.core.models import GLOBAL, Block


class ConfigConflict(Exception):
    """The file changed on disk where the edit lands; nothing was written.

    The message names the block, for logs and tests. `path` is filled in by
    the caller, which knows which file it was saving.
    """

    def __init__(self, title: str, path: Path | None = None) -> None:
        super().__init__(title)
        self.path = path


def rebase(
    on_disk: list[Block], ours: list[Block], theirs: list[Block]
) -> tuple[list[Block], list[Block]]:
    """`ours` replayed onto `theirs`. Returns the new blocks and new `on_disk`.

    `on_disk` is what the file held when we read it, `ours` is that list as
    the user has edited it, and `theirs` is the file parsed again just now.
    Blocks are told apart by identity: a block in `on_disk` and not in `ours`
    was removed, one in `ours` and not in `on_disk` is new. The returned
    `on_disk` is `theirs` with each edited block standing in for the one it
    replaced, so a second rebase still recognises it.
    """
    base = {id(block) for block in on_disk}
    kept = {id(block) for block in ours}
    removed = [block for block in on_disk if id(block) not in kept]
    edited = [block for block in ours if id(block) in base and block.dirty]
    anchors = [
        anchor
        for anchor in _anchors(ours, base)
        if id(anchor) in base and not anchor.dirty
    ]

    # Every lookup first, so a conflict leaves `ours` exactly as it was.
    match = {id(block): _find(block, on_disk, theirs) for block in removed + edited}
    for anchor in anchors:
        match.setdefault(id(anchor), _find(anchor, on_disk, theirs))

    gone = {id(match[id(block)]) for block in removed}
    standing_in = {id(match[id(block)]): block for block in edited}
    for block in edited:
        source = match[id(block)]
        # Lead and tail are blank lines and comments around the block, which
        # the form never edits. Taking theirs keeps the spacing the other
        # program left, instead of doubling a blank line it moved.
        block.lead, block.tail, block.raw = (
            list(source.lead),
            list(source.tail),
            list(source.raw),
        )

    result = [
        standing_in.get(id(block), block) for block in theirs if id(block) not in gone
    ]
    for index, block in enumerate(ours):
        if id(block) in base:
            continue
        if all(id(later) not in base for later in ours[index + 1 :]):
            result.append(block)  # it was at the end, so it stays at the end
            continue
        # Index 0 is always the preamble, which is never new. The anchor is
        # in `result` as itself when it is new or edited, and as its match
        # when it was left alone.
        anchor = ours[index - 1]
        untouched = id(anchor) in base and not anchor.dirty
        target = match[id(anchor)] if untouched else anchor
        position = next(i for i, candidate in enumerate(result) if candidate is target)
        result.insert(position + 1, block)

    new_on_disk = [standing_in.get(id(block), block) for block in theirs]
    return result, new_on_disk


def _anchors(ours: list[Block], base: set[int]) -> list[Block]:
    """The block right above each new block that is not at the end."""
    found = []
    for index, block in enumerate(ours):
        if id(block) in base:
            continue
        if any(id(later) in base for later in ours[index + 1 :]):
            found.append(ours[index - 1])
    return found


def _find(block: Block, on_disk: list[Block], theirs: list[Block]) -> Block:
    """The block in `theirs` that `block` was read as, or `ConfigConflict`.

    Unique on both sides, or nothing: with two identical blocks there is no
    telling which one the other program changed.
    """
    if block.kind == GLOBAL and not block.dirty:
        return theirs[0]  # the preamble only ever matters as a position
    key = _key(block)
    before = [candidate for candidate in on_disk if _key(candidate) == key]
    now = [candidate for candidate in theirs if _key(candidate) == key]
    if len(before) != 1 or len(now) != 1:
        raise ConfigConflict(block.title)
    return now[0]


def _key(block: Block) -> tuple[str, ...]:
    """The block's original lines, without the blank lines that end it.

    A blank line before a `Host` belongs to the block above it when the file
    ends there, and to the new block once something is appended. Without the
    trim, appending a host would make the last block look changed.
    """
    lines = list(block.raw)
    while lines and not lines[-1].strip():
        lines.pop()
    return tuple(lines)
