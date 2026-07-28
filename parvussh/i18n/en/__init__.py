"""English catalog.

Same split and the same keys as `pt_br`; `tests/test_i18n.py` fails if the two
drift apart.
"""

from __future__ import annotations

from parvussh.i18n.en import guide, keywords, ui

STRINGS: dict[str, str] = {**ui.STRINGS, **keywords.STRINGS, **guide.STRINGS}

__all__ = ["STRINGS"]
