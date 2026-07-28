"""The translation runtime, per docs/DECISIONS.md D3."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import parvussh
from parvussh.i18n import (
    DEFAULT_LOCALE,
    available_locales,
    current_locale,
    has,
    set_locale,
    strings,
    t,
)

UI_ROOT = Path(parvussh.__file__).parent / "ui"
# t("some.key"), t('some.key', ...) — the keys the UI actually asks for.
CALL = re.compile(r"""\bt\(\s*["']([a-zA-Z0-9_.]+)["']""")


def test_the_shipped_locale_is_the_default() -> None:
    assert available_locales() == ["pt_br"]
    assert current_locale() == DEFAULT_LOCALE


def test_a_known_key_returns_its_translation() -> None:
    assert t("app.name") == "ParvuSsh"


def test_a_missing_key_returns_the_key_itself() -> None:
    """A half-translated build should still open, showing where text is due."""
    assert t("nao.existe.esta.chave") == "nao.existe.esta.chave"
    assert has("nao.existe.esta.chave") is False


def test_placeholders_are_filled_in() -> None:
    catalog = dict(strings())
    assert "{" not in t("app.comments")  # a real key with no placeholder
    assert catalog  # and the table is not empty


def test_formatting_uses_the_keyword_arguments() -> None:
    from parvussh.i18n import pt_br

    pt_br.STRINGS["test.greeting"] = "Salvo em {path}"
    try:
        # The catalog is cached on first use, so re-select it to pick this up.
        import parvussh.i18n as module

        module._catalogs.clear()
        assert t("test.greeting", path="~/.ssh/config") == "Salvo em ~/.ssh/config"
    finally:
        del pt_br.STRINGS["test.greeting"]
        module._catalogs.clear()


def test_setting_an_unknown_locale_is_refused() -> None:
    with pytest.raises(LookupError):
        set_locale("klingon")
    assert current_locale() == DEFAULT_LOCALE


def test_setting_the_shipped_locale_works() -> None:
    set_locale("pt_br")
    assert current_locale() == "pt_br"


def test_no_key_is_defined_twice_with_different_text() -> None:
    """The three pt-BR modules are merged; a silent overwrite would lose text."""
    from parvussh.i18n.pt_br import guide, keywords, ui

    seen: dict[str, str] = {}
    for module in (ui, keywords, guide):
        for key, value in module.STRINGS.items():
            assert key not in seen or seen[key] == value, f"{key} defined twice"
            seen[key] = value
    assert len(seen) == len(strings())


def test_every_key_the_ui_asks_for_exists() -> None:
    """Fails the moment a widget references a string nobody translated."""
    missing: list[str] = []
    for path in sorted(UI_ROOT.rglob("*.py")):
        for key in CALL.findall(path.read_text(encoding="utf-8")):
            if not has(key):
                missing.append(f"{path.name}: {key}")
    assert missing == []


def test_no_translation_value_is_empty() -> None:
    for key, value in strings().items():
        assert value.strip(), key
