"""The `+` popover: search the catalog, pick one, get a row ready to fill."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

CONFIG = """Host vps
    HostName 203.0.113.10
    Compression yes
"""


@pytest.fixture
def app(window, fake_home: Path):
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


@pytest.fixture
def popover(app):
    """The popover as the user meets it: rebuilt on open, like `_on_show` does."""
    popover = app.editor.add_popover
    popover.refresh()
    return popover


def names(popover) -> list[str]:
    return [row.get_title() for row in popover.rows()]


def option_names(app) -> list[str]:
    return [option.keyword.name for option in app.editor.options]


# -- searching -------------------------------------------------------------


def test_it_opens_showing_the_whole_catalog(popover) -> None:
    assert len(popover.rows()) > 40


def test_typing_narrows_the_list(popover) -> None:
    popover.search.set_text("ServerA")
    popover.refresh()

    # A name match ranks above a description match, and TCPKeepAlive's
    # description mentions ServerAlive on purpose.
    assert names(popover)[:2] == ["ServerAliveCountMax", "ServerAliveInterval"]
    assert len(names(popover)) < 5


def test_each_row_explains_what_the_option_does(popover) -> None:
    popover.search.set_text("ServerAliveInterval")
    popover.refresh()

    subtitle = popover.rows()[0].get_subtitle()
    assert "sinal de vida" in subtitle


def test_searching_in_portuguese_finds_options_by_purpose(popover) -> None:
    """The reason the catalog carries pt-BR descriptions at all."""
    popover.search.set_text("chave")
    popover.refresh()

    assert "IdentityFile" in names(popover)


def test_options_already_on_the_form_are_not_offered(popover, app) -> None:
    assert "Compression" in [o.keyword.name for o in app.editor.options]
    assert "Compression" not in names(popover)


def test_the_basic_fields_are_never_offered(popover) -> None:
    for name in ("HostName", "User", "Port"):
        assert name not in names(popover)


def test_a_query_matching_nothing_says_so(popover) -> None:
    popover.search.set_text("zzzznaoexiste")
    popover.refresh()

    assert popover.rows() == []
    assert popover.empty.get_label() == "Nenhuma opção com esse nome."


# -- picking ---------------------------------------------------------------


def test_activating_a_row_adds_the_option_to_the_form(popover, app) -> None:
    popover.search.set_text("ProxyJump")
    popover.refresh()

    popover.pick_first()

    assert "ProxyJump" in option_names(app)


def test_enter_takes_the_best_match(popover, app) -> None:
    """Type, press Enter, keep typing — adding an option never needs the mouse."""
    popover.search.set_text("ServerAlive")
    popover.refresh()

    popover.search.emit("activate")

    assert option_names(app)[-1] == "ServerAliveCountMax"


def test_enter_on_an_empty_result_does_nothing(popover, app) -> None:
    before = option_names(app)
    popover.search.set_text("zzzznaoexiste")
    popover.refresh()

    popover.search.emit("activate")

    assert option_names(app) == before


def test_adding_an_option_marks_the_form_edited(popover, app) -> None:
    assert app.editor.dirty is False

    popover.search.set_text("ProxyJump")
    popover.refresh()
    popover.pick_first()

    assert app.editor.dirty is True


def test_an_added_option_is_not_offered_again(popover, app) -> None:
    popover.search.set_text("ProxyJump")
    popover.refresh()
    popover.pick_first()

    popover.search.set_text("")
    popover.refresh()

    assert "ProxyJump" not in names(popover)


def test_removing_an_option_puts_it_back_on_offer(popover, app) -> None:
    """The used set is read fresh each time, never cached."""
    compression = next(o for o in app.editor.options if o.keyword.name == "Compression")

    app.editor.remove_option(compression)
    popover.refresh()

    assert "Compression" in names(popover)


def test_a_freshly_added_option_starts_empty(popover, app) -> None:
    popover.search.set_text("ProxyJump")
    popover.refresh()
    popover.pick_first()

    added = next(o for o in app.editor.options if o.keyword.name == "ProxyJump")
    assert added.value() == ""


def test_an_option_added_but_left_empty_never_reaches_the_file(
    popover, app, fake_home: Path
) -> None:
    popover.search.set_text("ProxyJump")
    popover.refresh()
    popover.pick_first()

    app.save_current()

    assert "ProxyJump" not in (fake_home / ".ssh" / "config").read_text()


def test_an_option_added_and_filled_in_reaches_the_file(
    popover, app, fake_home: Path
) -> None:
    popover.search.set_text("ProxyJump")
    popover.refresh()
    popover.pick_first()
    added = next(o for o in app.editor.options if o.keyword.name == "ProxyJump")
    added.row.set_text("bastion")

    app.save_current()

    assert "ProxyJump bastion" in (fake_home / ".ssh" / "config").read_text()


def test_switching_connections_rebuilds_what_is_on_offer(
    popover, app, fake_home
) -> None:
    (fake_home / ".ssh" / "config").write_text(
        CONFIG + "\nHost outro\n    ProxyJump bastion\n", encoding="utf-8"
    )
    app.reload()

    app.sidebar.listbox.select_row(app.sidebar.rows()[1])
    popover.refresh()

    assert "Compression" in names(popover)  # not used by this connection
    assert "ProxyJump" not in names(popover)  # but this one is
