"""The connection list and its filter."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

CONFIG = """# pessoal

Host vps-blog
    HostName 203.0.113.10
    User deploy
    Port 2222

Host github.com
    User git

Host *
    ServerAliveInterval 60
"""


@pytest.fixture
def listed(window, fake_home: Path):
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    return window


def titles(window) -> list[str]:
    return [row.get_title() for row in window.sidebar.rows()]


def visible_titles(window) -> list[str]:
    return [row.get_title() for row in window.sidebar.visible_rows()]


# -- filling ---------------------------------------------------------------


def test_every_host_gets_a_row_in_file_order(listed) -> None:
    assert titles(listed) == ["vps-blog", "github.com", "*"]


def test_a_row_carries_the_block_it_shows(listed) -> None:
    assert listed.sidebar.rows()[0].block is listed.hosts[0]


def test_the_subtitle_summarises_the_connection(listed) -> None:
    assert listed.sidebar.rows()[0].get_subtitle() == "deploy@203.0.113.10:2222"


def test_a_host_without_a_hostname_says_so(listed) -> None:
    """core returns "" here; the sidebar supplies the wording (D3)."""
    assert listed.sidebar.rows()[1].get_subtitle() == "sem HostName"


def test_a_wildcard_row_is_marked_differently(listed) -> None:
    wildcard = listed.sidebar.rows()[2]
    assert wildcard.block.is_pattern is True
    assert wildcard.get_tooltip_text() is not None
    assert listed.sidebar.rows()[0].get_tooltip_text() is None


def test_a_wildcard_row_does_not_claim_a_missing_hostname(listed) -> None:
    """`Host *` is meant to have no HostName; saying so reads as an error."""
    assert listed.sidebar.rows()[2].get_subtitle() == "Padrão curinga"


def test_an_alias_with_markup_characters_is_escaped(window, fake_home: Path) -> None:
    """`Adw.ActionRow` parses its title as markup; an alias is plain text."""
    (fake_home / ".ssh" / "config").write_text("Host a<b>&c\n", encoding="utf-8")

    window.reload()

    assert window.sidebar.rows()[0].get_title() == "a&lt;b&gt;&amp;c"


def test_reloading_replaces_the_rows_rather_than_appending(listed) -> None:
    listed.reload()
    assert titles(listed) == ["vps-blog", "github.com", "*"]


# -- filtering -------------------------------------------------------------


def test_an_empty_filter_shows_everything(listed) -> None:
    assert visible_titles(listed) == ["vps-blog", "github.com", "*"]


def test_filtering_by_alias(listed) -> None:
    listed.sidebar.search.set_text("blog")
    assert visible_titles(listed) == ["vps-blog"]


def test_filtering_by_hostname(listed) -> None:
    listed.sidebar.search.set_text("203.0.113")
    assert visible_titles(listed) == ["vps-blog"]


def test_filtering_by_user(listed) -> None:
    listed.sidebar.search.set_text("git")
    assert visible_titles(listed) == ["github.com"]


def test_filtering_ignores_case(listed) -> None:
    listed.sidebar.search.set_text("VPS")
    assert visible_titles(listed) == ["vps-blog"]


def test_a_filter_matching_nothing_says_what_was_searched(listed, pump) -> None:
    listed.sidebar.search.set_text("nao-existe")

    assert visible_titles(listed) == []
    # Gtk.SearchEntry debounces search-changed behind a timer.
    pump(lambda: "nao-existe" in listed.sidebar.placeholder.get_text())


def test_an_empty_config_invites_the_first_connection(window) -> None:
    assert window.sidebar.rows() == []
    assert "Use o +" in window.sidebar.placeholder.get_text()


# -- selection -------------------------------------------------------------


def test_typing_asks_the_list_to_re_filter(listed, pump) -> None:
    """Our half of filtering: the predicate is right and GTK is told to re-run it.

    GTK applies the filter itself only once the widget is mapped, and the test
    window is never presented, so the invalidation is what we can observe.
    """
    calls: list[int] = []
    listed.sidebar.listbox.invalidate_filter = lambda: calls.append(1)

    listed.sidebar.search.set_text("blog")

    pump(lambda: calls != [])


def test_selecting_a_row_shows_that_block(listed) -> None:
    listed.sidebar.listbox.select_row(listed.sidebar.rows()[0])

    assert listed.current is listed.hosts[0]
    assert listed.editor.title_widget.get_title() == "vps-blog"


def test_selecting_a_row_names_the_file_it_came_from(listed) -> None:
    listed.sidebar.listbox.select_row(listed.sidebar.rows()[0])
    assert listed.editor.title_widget.get_subtitle() == "~/.ssh/config"


def test_selecting_enables_the_actions_that_need_a_selection(listed) -> None:
    listed.sidebar.listbox.select_row(listed.sidebar.rows()[0])

    for name in ("save", "test", "delete", "duplicate"):
        assert listed.lookup_action(name).get_enabled() is True, name


def test_rebuilding_the_list_does_not_load_blocks_nobody_clicked(listed) -> None:
    """GTK emits row-selected as rows are removed; that is not a user action."""
    listed.sidebar.listbox.select_row(listed.sidebar.rows()[0])

    listed.refresh_list(select=listed.hosts[1])

    assert listed.current is listed.hosts[1]


def test_refreshing_keeps_the_selection_it_was_given(listed) -> None:
    listed.refresh_list(select=listed.hosts[2])

    assert listed.sidebar.listbox.get_selected_row().block is listed.hosts[2]
    assert listed.current is listed.hosts[2]
