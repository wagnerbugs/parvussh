"""The option catalog and its search, per SPEC §4."""

from __future__ import annotations

import pytest

from parvussh.data.keywords import (
    BASIC,
    BY_NAME,
    CATALOG,
    ENUM,
    GROUPS,
    INT,
    STR,
    Keyword,
    canonical,
    for_option,
    get,
    search,
)


def names(found: list[Keyword]) -> list[str]:
    return [keyword.name for keyword in found]


# -- shape of the table ----------------------------------------------------


def test_the_catalog_holds_every_option_the_spec_lists() -> None:
    assert len(CATALOG) == 50
    assert len(BY_NAME) == len(CATALOG), "two entries share a name"


def test_every_entry_belongs_to_a_known_group() -> None:
    for keyword in CATALOG:
        assert keyword.group in GROUPS, keyword.name


def test_every_group_has_at_least_one_entry() -> None:
    used = {keyword.group for keyword in CATALOG}
    assert used == set(GROUPS)


def test_every_enum_offers_values() -> None:
    for keyword in CATALOG:
        if keyword.kind == ENUM:
            assert keyword.values, keyword.name


def test_only_enums_carry_values() -> None:
    for keyword in CATALOG:
        if keyword.kind != ENUM:
            assert keyword.values == (), keyword.name


def test_every_int_has_a_usable_range() -> None:
    for keyword in CATALOG:
        if keyword.kind == INT:
            assert keyword.lo < keyword.hi, keyword.name


def test_the_basic_fields_are_in_the_catalog() -> None:
    """The form renders them by hand, but help still describes them."""
    for name in BASIC:
        assert get(name) is not None


# -- the text half ---------------------------------------------------------


def test_every_entry_has_a_description() -> None:
    """Catches a catalog row added without its pt-BR text."""
    for keyword in CATALOG:
        assert keyword.description, keyword.name
        assert not keyword.description.startswith("kw."), (
            f"{keyword.name} has no description in the pt-BR catalog"
        )


def test_every_group_has_a_heading() -> None:
    from parvussh.i18n import t

    for group in GROUPS:
        assert not t(f"group.{group}").startswith("group."), group


def test_descriptions_are_sentences_not_labels() -> None:
    for keyword in CATALOG:
        assert keyword.description[0].isupper(), keyword.name
        assert keyword.description.endswith("."), keyword.name


# -- lookup ----------------------------------------------------------------


def test_lookup_is_case_insensitive() -> None:
    assert get("hostname") is get("HostName") is get("HOSTNAME")


def test_canonical_fixes_the_users_casing() -> None:
    assert canonical("identityfile") == "IdentityFile"
    assert canonical("serveraliveinterval") == "ServerAliveInterval"


def test_canonical_leaves_an_unknown_option_alone() -> None:
    assert canonical("GSSAPIAuthentication") == "GSSAPIAuthentication"


def test_an_unknown_option_becomes_a_plain_text_row() -> None:
    """Contract rule 3: we show and keep what we do not recognise."""
    keyword = for_option("GSSAPIAuthentication")

    assert keyword.name == "GSSAPIAuthentication"
    assert keyword.kind == STR
    assert keyword.catalogued is False
    assert keyword.description == "Opção não catalogada, preservada como está."
    assert keyword.example == ""


def test_a_known_option_comes_back_from_the_catalog() -> None:
    assert for_option("compression") is get("Compression")


# -- search ----------------------------------------------------------------


def test_an_empty_query_returns_the_whole_catalog_minus_the_basics() -> None:
    found = search("")
    assert len(found) == len(CATALOG) - len(BASIC)
    assert names(found) == sorted(names(found))


def test_basic_fields_never_appear_in_search() -> None:
    for name in BASIC:
        assert name not in names(search(name))


def test_a_prefix_match_on_the_name_ranks_first() -> None:
    found = names(search("ServerA"))
    assert found[:2] == ["ServerAliveCountMax", "ServerAliveInterval"]


def test_search_is_case_insensitive() -> None:
    assert names(search("serveralive")) == names(search("ServerAlive"))


def test_exclude_removes_options_already_on_the_form() -> None:
    assert "Compression" in names(search("compress"))
    assert "Compression" not in names(search("compress", exclude={"Compression"}))


def test_exclude_ignores_the_casing_the_user_typed() -> None:
    assert "Compression" not in names(search("compress", exclude={"compression"}))


def test_searching_in_portuguese_finds_the_key_related_options() -> None:
    """The feature that makes the app feel like it speaks the user's language.

    SPEC §4 predicts exactly five results here. It is wrong: `chave` also
    appears in the descriptions of StrictHostKeyChecking, UserKnownHostsFile,
    VisualHostKey and KexAlgorithms, and returning those is *better* — someone
    searching "chave" wants all of them. So we assert the five the spec names
    are present, and that nothing unrelated slipped in.
    """
    found = names(search("chave"))

    for expected in (
        "IdentityFile",
        "AddKeysToAgent",
        "IdentitiesOnly",
        "HostKeyAlgorithms",
        "ForwardAgent",
    ):
        assert expected in found, expected

    for keyword in search("chave"):
        haystack = f"{keyword.name} {keyword.description}".lower()
        assert "chave" in haystack, keyword.name


def test_search_ignores_accents_so_sessao_finds_sessao() -> None:
    """Brazilian developers type without accents more often than with them."""
    assert names(search("conexao")) == names(search("conexão"))
    assert "IdentityFile" in names(search("conexao"))
    assert names(search("sessao")) == names(search("sessão"))
    assert "ServerAliveInterval" in names(search("sessao"))


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("proxy", "ProxyJump"),
        ("bastion", "ProxyJump"),  # found through the description
        ("socks", "DynamicForward"),
        ("firewall", None),  # honest miss: nothing claims to fix firewalls
    ],
)
def test_search_finds_options_by_what_they_do(query: str, expected: str | None) -> None:
    found = names(search(query))
    if expected is None:
        assert found == []
    else:
        assert expected in found
