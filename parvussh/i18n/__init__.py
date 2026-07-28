"""Translation lookup for every user-visible string.

The app ships pt-BR only, but no module outside this package contains a
literal the user can read. Adding a language means adding a sibling package
with the same keys — never touching `ui/` or `data/`.

    from parvussh.i18n import t

    t("editor.save")                 -> "Salvar"
    t("editor.saved_toast", path=p)  -> "Salvo em ~/.ssh/config"

A missing key returns the key itself rather than raising: a half-translated
build should still open, showing `editor.save` where the label belongs.
`tests/test_i18n.py` asserts no key is missing from the shipped locales.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import MappingProxyType

DEFAULT_LOCALE = "pt_br"

_catalogs: dict[str, MappingProxyType[str, str]] = {}
_current = DEFAULT_LOCALE


def available_locales() -> list[str]:
    """Locale names shipped in this package, e.g. `["pt_br"]`."""
    return sorted(
        module.name
        for module in pkgutil.iter_modules(__path__)
        if module.ispkg and not module.name.startswith("_")
    )


def _catalog(locale: str) -> MappingProxyType[str, str]:
    """Load and cache one locale's merged string table."""
    cached = _catalogs.get(locale)
    if cached is not None:
        return cached
    module = importlib.import_module(f"{__name__}.{locale}")
    catalog = MappingProxyType(dict(module.STRINGS))
    _catalogs[locale] = catalog
    return catalog


def set_locale(locale: str) -> None:
    """Switch the active locale. Raises `LookupError` for an unknown name."""
    global _current
    if locale not in available_locales():
        raise LookupError(f"no translation catalog named {locale!r}")
    _catalog(locale)
    _current = locale


def current_locale() -> str:
    return _current


def has(key: str, locale: str | None = None) -> bool:
    return key in _catalog(locale or _current)


def strings(locale: str | None = None) -> MappingProxyType[str, str]:
    """The whole table, for tests and for the help dialog's search index."""
    return _catalog(locale or _current)


def t(key: str, **fmt: object) -> str:
    """The translated string for `key`, with `{placeholders}` filled in."""
    catalog = _catalog(_current)
    text = catalog.get(key)
    if text is None and _current != DEFAULT_LOCALE:
        text = _catalog(DEFAULT_LOCALE).get(key)
    if text is None:
        return key
    return text.format(**fmt) if fmt else text


__all__ = [
    "DEFAULT_LOCALE",
    "available_locales",
    "current_locale",
    "has",
    "set_locale",
    "strings",
    "t",
]
