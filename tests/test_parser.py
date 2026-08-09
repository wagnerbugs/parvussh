"""Parser and renderer, against the assertions listed in SPEC §9."""

from __future__ import annotations

import pytest

from parvussh.core.models import HOST, Block, Entry, render_blocks
from parvussh.core.parser import detect_newline, parse_text
from tests.conftest import fixture_bytes, fixture_text

FIXTURE_NAMES = ["basic.config", "empty.config", "messy.config"]


def parse_fixture(name: str) -> list[Block]:
    return parse_text(fixture_text(name))


def rendered(name: str) -> bytes:
    text = fixture_text(name)
    return render_blocks(parse_text(text), detect_newline(text)).encode("utf-8")


def hosts(blocks: list[Block]) -> list[Block]:
    return [block for block in blocks if block.kind == HOST]


def named(blocks: list[Block], alias: str) -> Block:
    return next(block for block in hosts(blocks) if alias in block.patterns)


# -- round trip ------------------------------------------------------------


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_round_trip_without_edits_is_byte_identical(name: str) -> None:
    assert rendered(name) == fixture_bytes(name)


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_round_trip_survives_a_second_pass(name: str) -> None:
    """Rendering is idempotent: parsing our own output changes nothing."""
    once = rendered(name).decode("utf-8")
    twice = render_blocks(parse_text(once), detect_newline(once))
    assert twice == once


def test_crlf_file_keeps_its_line_endings() -> None:
    assert detect_newline(fixture_text("messy.config")) == "\r\n"
    assert b"\r\n" in rendered("messy.config")


def test_empty_file_does_not_crash() -> None:
    blocks = parse_fixture("empty.config")
    assert len(blocks) == 1
    assert blocks[0].kind == "global"
    assert hosts(blocks) == []


@pytest.mark.parametrize(
    ("name", "char"),
    [
        ("form feed", "\x0c"),
        ("vertical tab", "\x0b"),
        ("file separator", "\x1c"),
        ("next line", "\x85"),
        ("line separator", "\u2028"),
    ],
)
def test_only_newlines_end_a_line(name: str, char: str) -> None:
    """`str.splitlines()` breaks on all of these; ssh does not, so nor do we.

    Reaching for `splitlines()` here would silently rewrite any config holding
    one of these bytes — turning half a value into a bogus keyword. This test
    is the reason `_split_lines` exists.
    """
    text = f"Host a\n    RemoteCommand echo{char}oi\n"
    blocks = parse_text(text)
    assert render_blocks(blocks) == text
    assert blocks[1].get("RemoteCommand") == f"echo{char}oi"


def test_a_missing_final_newline_is_added() -> None:
    """The one normalisation we allow: a text file ends with a newline."""
    assert render_blocks(parse_text("Host x")) == "Host x\n"


# -- discovery -------------------------------------------------------------


def test_host_discovery_lists_aliases_in_file_order() -> None:
    blocks = parse_fixture("basic.config")
    assert [block.title for block in hosts(blocks)] == ["vps-blog", "github.com", "*"]


def test_equals_separator_parses_like_a_space() -> None:
    block = named(parse_fixture("basic.config"), "github.com")
    assert block.get("IdentityFile") == "~/.ssh/id_github"


def test_lookup_is_case_insensitive() -> None:
    block = named(parse_fixture("basic.config"), "vps-blog")
    assert block.get("hostname") == "203.0.113.10"
    assert block.get("HOSTNAME") == "203.0.113.10"
    assert block.get("Nonexistent", "fallback") == "fallback"


def test_keyword_casing_is_preserved_as_written() -> None:
    block = named(parse_fixture("messy.config"), "crlf-host")
    assert [entry.keyword for entry in block.entries] == [
        "HostName",
        "User",
        "Compression",
        "ForwardAgent",
    ]


def test_a_bare_keyword_parses_with_an_empty_value() -> None:
    block = named(parse_fixture("messy.config"), "crlf-host")
    assert block.get("ForwardAgent") == ""


def test_wildcard_blocks_are_flagged() -> None:
    blocks = parse_fixture("basic.config")
    assert named(blocks, "*").is_pattern is True
    assert named(blocks, "vps-blog").is_pattern is False


def test_subtitle_joins_user_host_and_non_default_port() -> None:
    blocks = parse_fixture("basic.config")
    assert named(blocks, "vps-blog").subtitle() == "deploy@203.0.113.10:2222"


def test_subtitle_is_empty_without_a_hostname() -> None:
    """Core returns nothing to say; the UI decides how to say it."""
    assert named(parse_fixture("basic.config"), "github.com").subtitle() == ""


def test_subtitle_omits_the_default_port() -> None:
    block = parse_text("Host a\n    HostName h\n    Port 22\n")[1]
    assert block.subtitle() == "h"


# -- preservation ----------------------------------------------------------


def test_comments_attach_to_the_entry_below_them() -> None:
    block = named(parse_fixture("basic.config"), "vps-blog")
    assert block.comments_for("IdentityFile") == ["    # essa chave é a antiga"]
    assert block.comments_for("HostName") == []


def test_leading_comments_become_the_block_lead() -> None:
    block = named(parse_fixture("basic.config"), "vps-blog")
    assert block.lead == ["# Configuração pessoal", "# não mexer sem café", ""]


def test_a_line_matching_neither_regex_is_kept_verbatim() -> None:
    block = named(parse_fixture("messy.config"), "crlf-host")
    stray = "!!! esta linha não é ssh_config e precisa sobreviver assim mesmo"
    assert block.comments_for("User") == [stray]
    assert stray in rendered("messy.config").decode("utf-8")


def test_match_block_survives_with_its_header_intact() -> None:
    blocks = parse_fixture("basic.config")
    match = next(block for block in blocks if block.kind == "match")
    assert match.header_raw == "Match host *.interno"
    assert match.patterns == ["host *.interno"]
    assert match.get("ProxyJump") == "bastion"
    assert "Match host *.interno" in rendered("basic.config").decode("utf-8")


def test_editing_one_block_leaves_every_other_byte_alone() -> None:
    text = fixture_text("basic.config")
    blocks = parse_text(text)
    block = named(blocks, "vps-blog")
    block.entries = [
        Entry("HostName", "203.0.113.99", block.comments_for("HostName")),
        Entry("User", "deploy", block.comments_for("User")),
        Entry("IdentityFile", "~/.ssh/id_blog", block.comments_for("IdentityFile")),
    ]
    block.dirty = True

    out = render_blocks(blocks, detect_newline(text))

    assert "HostName 203.0.113.99" in out
    assert "Port 2222" not in out  # the field we dropped is gone
    for survivor in (
        "# não mexer sem café",
        "    # essa chave é a antiga",
        "IdentityFile=~/.ssh/id_github",
        "Match host *.interno",
        "    ServerAliveInterval 60",
    ):
        assert survivor in out, survivor


def test_a_new_block_is_separated_by_exactly_one_blank_line() -> None:
    blocks = parse_text("Host first\n    HostName a\n")
    blocks.append(
        Block(
            kind=HOST,
            patterns=["x"],
            entries=[Entry("HostName", "203.0.113.7")],
            lead=[""],
            dirty=True,
        )
    )
    assert render_blocks(blocks).endswith("\nHost x\n    HostName 203.0.113.7\n")


def test_a_new_block_alone_in_a_file_gains_no_leading_blank_line() -> None:
    block = Block(
        kind=HOST,
        patterns=["x"],
        entries=[Entry("HostName", "203.0.113.7")],
        lead=[""],
        dirty=True,
    )
    assert render_blocks([block]) == "Host x\n    HostName 203.0.113.7\n"


def test_an_untouched_block_renders_from_raw_not_from_entries() -> None:
    """The guarantee in one test: mangling `entries` cannot reach the file."""
    blocks = parse_fixture("basic.config")
    named(blocks, "vps-blog").entries.clear()
    assert "HostName 203.0.113.10" in render_blocks(blocks)
