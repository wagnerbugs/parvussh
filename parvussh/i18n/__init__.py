"""Translation lookup for every user-visible string.

No module outside this package contains a literal the user can read. Adding a
language means adding a sibling package with the same keys — never touching
`ui/` or `data/`.

    from parvussh.i18n import t

    t("editor.save")              -> "Salvar"
    t("save.done", path="~/.ssh") -> "Salvo em ~/.ssh"

The active locale comes from the environment on first use, so any entry point
gets it right without remembering to ask. `PARVUSSH_LANG=en` overrides, which
is how you read the interface in the other language without changing your
system settings.

A missing key returns the key itself rather than raising: a half-translated
build should still open, showing `editor.save` where the label belongs, and
`tests/test_i18n.py` fails if any locale is missing one.
"""

from __future__ import annotations

import importlib
import os
import pkgutil
from collections.abc import Mapping
from types import MappingProxyType

#: The project's home language, and the fallback for a key a locale is missing.
DEFAULT_LOCALE = "pt_br"

#: Checked first, so the interface can be switched without touching the system
#: locale: `PARVUSSH_LANG=en make run`.
LANG_OVERRIDE = "PARVUSSH_LANG"
#: POSIX order of precedence for the rest.
LANG_VARIABLES = ("LC_ALL", "LC_MESSAGES", "LANG")

_catalogs: dict[str, Mapping[str, str]] = {}
_current: str | None = None


def available_locales() -> list[str]:
    """Locale names shipped in this package, e.g. `["en", "pt_br"]`."""
    return sorted(
        module.name
        for module in pkgutil.iter_modules(__path__)
        if module.ispkg and not module.name.startswith("_")
    )


def normalise(name: str) -> str:
    """`pt_BR.UTF-8` -> `pt_br`, `en-GB@euro` -> `en_gb`."""
    for separator in (".", "@"):
        name = name.split(separator)[0]
    return name.strip().lower().replace("-", "_")


def detect_locale(environ: Mapping[str, str] | None = None) -> str:
    """The shipped locale that best matches the environment.

    An exact match wins; failing that, the language alone (`pt_PT` settles for
    `pt_br`, since sharing a language beats sharing nothing). Anything else
    falls back to `DEFAULT_LOCALE`.
    """
    environ = os.environ if environ is None else environ
    shipped = available_locales()
    for variable in (LANG_OVERRIDE, *LANG_VARIABLES):
        raw = environ.get(variable)
        if not raw:
            continue
        wanted = normalise(raw)
        if wanted in shipped:
            return wanted
        language = wanted.split("_")[0]
        near = next((s for s in shipped if s.split("_")[0] == language), None)
        if near is not None:
            return near
    return DEFAULT_LOCALE


def current_locale() -> str:
    """The active locale, chosen from the environment the first time it is asked."""
    global _current
    if _current is None:
        _current = detect_locale()
    return _current


def set_locale(locale: str) -> None:
    """Switch the active locale. Raises `LookupError` for an unknown name."""
    global _current
    if locale not in available_locales():
        raise LookupError(f"no translation catalog named {locale!r}")
    _catalog(locale)
    _current = locale


def _catalog(locale: str) -> Mapping[str, str]:
    """Load and cache one locale's merged string table."""
    cached = _catalogs.get(locale)
    if cached is not None:
        return cached
    module = importlib.import_module(f"{__name__}.{locale}")
    catalog = MappingProxyType(dict(module.STRINGS))
    _catalogs[locale] = catalog
    return catalog


def has(key: str, locale: str | None = None) -> bool:
    return key in _catalog(locale or current_locale())


def strings(locale: str | None = None) -> Mapping[str, str]:
    """The whole table, for tests and for the help dialog's search index."""
    return _catalog(locale or current_locale())


def t(key: str, **fmt: object) -> str:
    """The translated string for `key`, with `{placeholders}` filled in."""
    locale = current_locale()
    text = _catalog(locale).get(key)
    if text is None and locale != DEFAULT_LOCALE:
        text = _catalog(DEFAULT_LOCALE).get(key)
    if text is None:
        return key
    return text.format(**fmt) if fmt else text


__all__ = [
    "DEFAULT_LOCALE",
    "available_locales",
    "current_locale",
    "detect_locale",
    "has",
    "normalise",
    "set_locale",
    "strings",
    "t",
]
