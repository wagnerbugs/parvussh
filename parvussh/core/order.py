"""The order the connection list shows hosts in. The file itself never moves.

Moving a block in `~/.ssh/config` would change what ssh does: for each option
it keeps the first value it finds, so a `Host *` lifted above a host hands
that host its defaults first. Sorting is a way of looking at the file, not of
rearranging it. File order stays the default because it is the order ssh
reads.
"""

from __future__ import annotations

import re

from parvussh.core.models import Block

BY_FILE = "file"
BY_NAME = "name"
ORDERS = (BY_FILE, BY_NAME)

_DIGITS = re.compile(r"(\d+)")


def arrange(blocks: list[Block], order: str) -> list[Block]:
    """`blocks` in `order`, as a new list. An order we do not know is the file's.

    Ties keep their file order, so two hosts with the same alias stay in the
    order ssh would meet them.
    """
    if order == BY_NAME:
        return sorted(blocks, key=_name_key)
    return list(blocks)


def _name_key(block: Block) -> tuple[bool, list[str | int]]:
    """Wildcards after every host; any case; `vps2` before `vps10`.

    Splitting on a capturing group puts the digit runs at the odd indices, so
    two keys compare a number with a number and a word with a word.
    """
    parts = _DIGITS.split(block.title.casefold())
    natural = [int(part) if index % 2 else part for index, part in enumerate(parts)]
    return (block.is_pattern, natural)
