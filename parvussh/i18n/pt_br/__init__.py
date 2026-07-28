"""Brazilian Portuguese catalog.

Split by area so no single file grows past a comfortable read. The keys are
English; only the values are translated.
"""

from __future__ import annotations

from parvussh.i18n.pt_br import guide, keywords, ui

STRINGS: dict[str, str] = {**ui.STRINGS, **keywords.STRINGS, **guide.STRINGS}

__all__ = ["STRINGS"]
