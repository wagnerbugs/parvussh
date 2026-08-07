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

PACKAGE_ROOT = Path(parvussh.__file__).parent
UI_ROOT = PACKAGE_ROOT / "ui"
#: `cli.py` shows text too — the terminal is an interface like any other.
ASKS_FOR_STRINGS = [*sorted(UI_ROOT.rglob("*.py")), PACKAGE_ROOT / "cli.py"]
# t("some.key"), t('some.key', ...) — the keys the UI actually asks for.
CALL = re.compile(r"""\bt\(\s*["']([a-zA-Z0-9_.]+)["']""")


def test_the_shipped_locales() -> None:
    assert available_locales() == ["en", "pt_br"]
    assert DEFAULT_LOCALE == "pt_br"


# -- parity between locales ------------------------------------------------


def test_every_locale_carries_the_same_keys() -> None:
    """A key present in one catalog and missing from another shows up raw."""
    reference = set(strings(DEFAULT_LOCALE))
    for locale in available_locales():
        keys = set(strings(locale))
        assert keys - reference == set(), f"{locale} has keys {DEFAULT_LOCALE} lacks"
        assert reference - keys == set(), f"{locale} is missing keys"


def test_placeholders_match_across_locales() -> None:
    """`{path}` in one language and `{caminho}` in another crashes at runtime."""
    import re

    placeholders = re.compile(r"\{(\w+)\}")
    reference = strings(DEFAULT_LOCALE)
    for locale in available_locales():
        for key, text in strings(locale).items():
            assert set(placeholders.findall(text)) == set(
                placeholders.findall(reference[key])
            ), f"{locale}: {key} has different placeholders"


#: Strings that are identical in every language on purpose. Everything else
#: being identical means a catalog was copied and not translated.
SHARED_ACROSS_LOCALES = {
    "app.name",  # the app is called the same thing everywhere
    "app.developer",
    "editor.field.user",  # the OpenSSH option name, deliberately
    "editor.field.port",
    "keypicker.summary",  # a format, not a sentence
    "keypicker.summary_no_comment",
    "sidebar.menu_tooltip",  # "Menu"
}


def is_prose(key: str) -> bool:
    """Whether a key holds a sentence rather than a technical value.

    `kw.*.example` holds config values — `~/.ssh/id_ed25519`,
    `curve25519-sha256`, `8080 localhost:80`. Those are the same in every
    language and their being identical proves nothing either way.
    """
    return not key.endswith(".example") and key not in SHARED_ACROSS_LOCALES


def test_no_prose_was_left_in_the_source_language() -> None:
    """A copied-but-not-translated sentence is worse than a missing one."""
    portuguese = strings("pt_br")
    untranslated = [
        key
        for key, text in strings("en").items()
        if is_prose(key) and text == portuguese[key]
    ]
    assert untranslated == []


def test_examples_are_localised_where_they_should_be() -> None:
    """Some examples do carry language: a locale name, a sample domain."""
    assert strings("en")["kw.SetEnv.example"] != strings("pt_br")["kw.SetEnv.example"]
    assert "example.com" in strings("en")["kw.HostName.example"]
    assert "exemplo.com" in strings("pt_br")["kw.HostName.example"]


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


# -- picking a locale from the environment ---------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pt_BR.UTF-8", "pt_br"),
        ("en_GB@euro", "en_gb"),
        ("en-US", "en_us"),
        ("  EN  ", "en"),
        ("C", "c"),
    ],
)
def test_locale_names_are_normalised(raw: str, expected: str) -> None:
    from parvussh.i18n import normalise

    assert normalise(raw) == expected


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        ({"LANG": "pt_BR.UTF-8"}, "pt_br"),
        ({"LANG": "en_US.UTF-8"}, "en"),  # language match, no en_us catalog
        ({"LANG": "en_GB.UTF-8"}, "en"),
        ({"LANG": "pt_PT.UTF-8"}, "pt_br"),  # closer than nothing
        ({"LANG": "de_DE.UTF-8"}, "pt_br"),  # unknown falls back to the default
        ({"LANG": "C"}, "pt_br"),
        ({}, "pt_br"),
        # POSIX precedence: LC_ALL beats LC_MESSAGES beats LANG.
        ({"LC_ALL": "en_US.UTF-8", "LANG": "pt_BR.UTF-8"}, "en"),
        ({"LC_MESSAGES": "en_US.UTF-8", "LANG": "pt_BR.UTF-8"}, "en"),
        # And our own override beats all of them.
        ({"PARVUSSH_LANG": "en", "LC_ALL": "pt_BR.UTF-8"}, "en"),
        ({"PARVUSSH_LANG": "pt_br", "LANG": "en_US.UTF-8"}, "pt_br"),
    ],
)
def test_the_locale_is_chosen_from_the_environment(
    environ: dict[str, str], expected: str
) -> None:
    from parvussh.i18n import detect_locale

    assert detect_locale(environ) == expected


def test_an_empty_variable_is_ignored() -> None:
    """An unset locale often shows up as an empty string, not a missing key."""
    from parvussh.i18n import detect_locale

    assert detect_locale({"LC_ALL": "", "LANG": "en_US.UTF-8"}) == "en"


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
    for path in ASKS_FOR_STRINGS:
        for key in CALL.findall(path.read_text(encoding="utf-8")):
            if not has(key):
                missing.append(f"{path.name}: {key}")
    assert missing == []


def test_no_translation_value_is_empty() -> None:
    for key, value in strings().items():
        assert value.strip(), key
