"""The order the connection list shows: the file's, or by name."""

from __future__ import annotations

from parvussh.core.models import HOST, Block
from parvussh.core.order import BY_FILE, BY_NAME, ORDERS, arrange


def hosts(*aliases: str) -> list[Block]:
    return [Block(kind=HOST, patterns=alias.split()) for alias in aliases]


def titles(blocks: list[Block]) -> list[str]:
    return [block.title for block in blocks]


def test_the_two_orders_and_file_first() -> None:
    assert ORDERS == (BY_FILE, BY_NAME)


def test_file_order_is_the_order_ssh_reads() -> None:
    blocks = hosts("vps-blog", "github.com", "*")
    assert arrange(blocks, BY_FILE) == blocks


def test_by_name_is_alphabetical() -> None:
    blocks = hosts("lexi", "contabo", "home")
    assert titles(arrange(blocks, BY_NAME)) == ["contabo", "home", "lexi"]


def test_by_name_ignores_case() -> None:
    """Plain text order puts every capital before every lower-case letter."""
    blocks = hosts("beta", "Gamma", "alpha")
    assert titles(arrange(blocks, BY_NAME)) == ["alpha", "beta", "Gamma"]


def test_numbers_are_compared_as_numbers() -> None:
    """Plain text order would put `vps10` before `vps2`."""
    blocks = hosts("vps10", "vps2", "contabo3", "contabo", "contabo2")
    assert titles(arrange(blocks, BY_NAME)) == [
        "contabo",
        "contabo2",
        "contabo3",
        "vps2",
        "vps10",
    ]


def test_a_number_and_a_word_in_the_same_place_do_not_clash() -> None:
    """`2fa` starts with digits and `a2` with a letter; both must still sort."""
    blocks = hosts("a2", "2fa", "b")
    assert titles(arrange(blocks, BY_NAME)) == ["2fa", "a2", "b"]


def test_wildcards_come_after_every_host() -> None:
    blocks = hosts("*", "zeta", "*.internal", "alpha")
    assert titles(arrange(blocks, BY_NAME)) == ["alpha", "zeta", "*", "*.internal"]


def test_a_block_with_several_patterns_sorts_by_its_first() -> None:
    blocks = hosts("web db", "api")
    assert titles(arrange(blocks, BY_NAME)) == ["api", "web db"]


def test_equal_names_keep_their_file_order() -> None:
    """Two blocks with one alias are legal; ssh meets the first one first."""
    first, other, second = hosts("twin", "alpha", "twin")
    arranged = arrange([first, other, second], BY_NAME)
    assert arranged[1] is first
    assert arranged[2] is second


def test_an_unknown_order_falls_back_to_the_file() -> None:
    blocks = hosts("b", "a")
    assert arrange(blocks, "recent") == blocks


def test_arranging_leaves_the_list_it_was_given_alone() -> None:
    """The caller's list is the file order, and the sidebar still needs it."""
    blocks = hosts("b", "a")
    before = list(blocks)

    for order in ORDERS:
        arranged = arrange(blocks, order)
        assert arranged is not blocks

    assert blocks == before
