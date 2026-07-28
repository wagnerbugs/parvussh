"""The window builds, the empty state shows, and every action exists."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

ACTIONS = ("help", "reload", "new", "save", "test", "delete", "duplicate")


def test_the_window_builds(window) -> None:
    from parvussh import APP_NAME

    assert window.get_title() == APP_NAME
    assert window.get_default_size() == (1020, 700)


def test_the_split_view_has_both_pages(window) -> None:
    assert window.split.get_sidebar() is window.sidebar
    assert window.split.get_content() is window.editor


def test_the_empty_state_is_showing(window) -> None:
    assert window.editor.stack.get_visible_child_name() == "empty"
    assert window.editor.placeholder.get_title() == "Escolha uma conexão"


@pytest.mark.parametrize("name", ("save", "test", "delete", "duplicate"))
def test_actions_needing_a_selection_start_disabled(window, name: str) -> None:
    """A live Salvar button with nothing to save is a lie about the state."""
    assert window.lookup_action(name).get_enabled() is False


@pytest.mark.parametrize("name", ("help", "reload", "new"))
def test_actions_that_always_apply_stay_enabled(window, name: str) -> None:
    assert window.lookup_action(name).get_enabled() is True


def test_the_header_bar_itself_stays_sensitive(window) -> None:
    """Disabling the header would disable minimise, maximise and close."""
    assert window.editor.header.get_sensitive() is True


@pytest.mark.parametrize("name", ACTIONS)
def test_every_window_action_exists(window, name: str) -> None:
    assert window.lookup_action(name) is not None


def test_loading_an_empty_config_selects_nothing(window) -> None:
    assert window.config is not None
    assert window.hosts == []
    assert window.current is None


def test_the_config_file_is_created_on_first_run(window, fake_home: Path) -> None:
    assert (fake_home / ".ssh" / "config").exists()


def test_reload_reads_a_config_written_after_startup(window, fake_home: Path) -> None:
    (fake_home / ".ssh" / "config").write_text(
        "Host vps\n    HostName 203.0.113.10\n", encoding="utf-8"
    )

    window.reload()

    assert [block.title for block in window.hosts] == ["vps"]


def test_a_toast_can_be_shown(window) -> None:
    window.toast("Salvo em ~/.ssh/config")  # must not raise


def test_shorten_home_writes_paths_the_way_the_user_knows_them(
    fake_home: Path,
) -> None:
    from parvussh.ui.window import shorten_home

    assert shorten_home(fake_home / ".ssh" / "config") == "~/.ssh/config"
    assert shorten_home(Path("/etc/ssh/ssh_config")) == "/etc/ssh/ssh_config"
