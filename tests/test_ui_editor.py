"""The connection form and the save path.

The assertions that matter here are about the file on disk: an edit must land,
and every byte the user did not touch must survive.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.core import settings
from parvussh.i18n import t

pytestmark = pytest.mark.gui

CONFIG = """# não mexer sem café

Host vps-blog
    HostName 203.0.113.10
    User deploy
    Port 2222
    # essa chave é a antiga
    IdentityFile ~/.ssh/id_blog

Host github.com
    User git
    IdentityFile=~/.ssh/id_github

Host *
    ServerAliveInterval 60
"""


@pytest.fixture
def app(window, fake_home: Path):
    """A window over the fixture config, with `vps-blog` open."""
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


@pytest.fixture
def config_file(fake_home: Path) -> Path:
    return fake_home / ".ssh" / "config"


# -- loading ---------------------------------------------------------------


def test_opening_a_connection_fills_the_form(app) -> None:
    assert app.editor.host.get_text() == "vps-blog"
    assert app.editor.hostname.get_text() == "203.0.113.10"
    assert app.editor.user.get_text() == "deploy"
    assert app.editor.port.get_text() == "2222"


def test_opening_a_connection_does_not_mark_it_edited(app) -> None:
    """A programmatic set_text emits `changed` exactly like a keystroke."""
    assert app.editor.dirty is False
    assert app.editor.title_widget.get_title() == "vps-blog"


def test_switching_connections_replaces_the_form(app) -> None:
    app.sidebar.listbox.select_row(app.sidebar.rows()[1])

    assert app.editor.host.get_text() == "github.com"
    assert app.editor.hostname.get_text() == ""
    assert app.editor.dirty is False


# -- dirty state -----------------------------------------------------------


def test_typing_marks_the_connection_edited(app) -> None:
    app.editor.hostname.set_text("203.0.113.99")

    assert app.editor.dirty is True
    assert app.editor.title_widget.get_title() == "• vps-blog"


def test_saving_clears_the_edited_mark(app) -> None:
    app.editor.hostname.set_text("203.0.113.99")

    assert app.save_current() is True
    assert app.editor.dirty is False
    assert app.editor.title_widget.get_title() == "vps-blog"


# -- saving ----------------------------------------------------------------


def test_an_edit_reaches_the_file(app, config_file: Path) -> None:
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()

    assert "HostName 203.0.113.99" in config_file.read_text()


def test_saving_leaves_every_other_block_untouched(app, config_file: Path) -> None:
    """The promise the whole project rests on: an unedited block is untouched."""
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()
    text = config_file.read_text()

    for survivor in (
        "# não mexer sem café",
        "IdentityFile=~/.ssh/id_github",
        "Host *\n    ServerAliveInterval 60\n",
    ):
        assert survivor in text, survivor


def test_an_extra_option_and_its_comment_survive_a_save(app, config_file: Path) -> None:
    """Editing one field must not disturb the options around it."""
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()
    text = config_file.read_text()

    assert "IdentityFile ~/.ssh/id_blog" in text
    assert "    # essa chave é a antiga" in text


def test_clearing_a_field_removes_the_line(app, config_file: Path) -> None:
    app.editor.port.set_text("")

    app.save_current()

    assert "Port 2222" not in config_file.read_text()


def test_renaming_the_alias_rewrites_the_host_line(app, config_file: Path) -> None:
    app.editor.host.set_text("blog")

    app.save_current()
    text = config_file.read_text()

    assert "Host blog\n" in text
    assert "Host vps-blog\n" not in text


def test_saving_keeps_the_sidebar_selection(app) -> None:
    app.editor.host.set_text("blog")

    app.save_current()

    assert app.sidebar.listbox.get_selected_row().block is app.current
    assert app.sidebar.listbox.get_selected_row().get_title() == "blog"


def test_saving_backs_the_file_up_first(app, fake_home: Path) -> None:
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()

    assert len(list((fake_home / ".ssh").glob("config.bak-*"))) == 1


def test_a_second_save_with_no_edits_writes_nothing(app, fake_home: Path) -> None:
    """Otherwise every Ctrl+S drops another dated backup into ~/.ssh."""
    app.editor.hostname.set_text("203.0.113.99")
    app.save_current()

    app.save_current()

    assert len(list((fake_home / ".ssh").glob("config.bak-*"))) == 1


def test_saving_an_unchanged_form_leaves_the_block_clean(app) -> None:
    app.editor.hostname.set_text(app.editor.hostname.get_text())

    app.save_current()

    assert app.current.dirty is False


# -- refusing to save ------------------------------------------------------


def test_an_empty_alias_refuses_to_save(app, config_file: Path) -> None:
    before = config_file.read_bytes()
    app.editor.host.set_text("")

    assert app.save_current() is False
    assert config_file.read_bytes() == before


def test_a_non_numeric_port_refuses_to_save(app, config_file: Path) -> None:
    before = config_file.read_bytes()
    app.editor.port.set_text("dois mil")

    assert app.save_current() is False
    assert config_file.read_bytes() == before


def test_a_refused_save_keeps_the_edit_in_the_form(app) -> None:
    app.editor.host.set_text("")

    app.save_current()

    assert app.editor.dirty is True
    assert app.editor.host.get_text() == ""


def test_ssh_refusing_the_config_leaves_the_file_alone(
    app, config_file: Path, fake_bin
) -> None:
    before = config_file.read_bytes()
    fake_bin.install("ssh", returncode=255, stderr="%F: line 3: Bad configuration")
    app.editor.hostname.set_text("203.0.113.99")

    assert app.save_current() is False
    assert config_file.read_bytes() == before
    assert list(config_file.parent.glob("config.bak-*")) == []


# -- another program writing the same file ---------------------------------


@pytest.fixture
def shown(app, monkeypatch) -> list[tuple[str, str]]:
    """Every message dialog, as (heading, body), instead of presenting it."""
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(app, "show_message", lambda *texts: messages.append(texts))
    return messages


def test_saving_keeps_a_change_another_program_made(app, config_file: Path) -> None:
    config_file.write_text(CONFIG.replace("Interval 60", "Interval 30"))
    app.editor.hostname.set_text("203.0.113.99")

    assert app.save_current() is True

    text = config_file.read_text()
    assert "HostName 203.0.113.99" in text
    assert "ServerAliveInterval 30" in text
    assert app.sidebar.listbox.get_selected_row().block is app.current


def test_a_conflict_writes_nothing_says_so_and_reloads(
    app, config_file: Path, shown
) -> None:
    changed = CONFIG.replace("Port 2222", "Port 1310")
    config_file.write_text(changed)
    app.editor.hostname.set_text("203.0.113.99")

    assert app.save_current() is False

    assert config_file.read_text() == changed
    assert list(config_file.parent.glob("config.bak-*")) == []
    assert shown == [
        (
            t("conflict.heading", path="~/.ssh/config"),
            t("conflict.body", path="~/.ssh/config"),
        )
    ]
    # The form would only be refused again; the list shows the file as it is.
    assert app.current is None
    assert app.editor.dirty is False
    assert app.hosts[0].get("Port") == "1310"


def test_a_conflict_on_delete_keeps_the_connection(
    app, config_file: Path, shown
) -> None:
    changed = CONFIG.replace("Port 2222", "Port 1310")
    config_file.write_text(changed)

    app.remove_block(app.hosts[0])

    assert config_file.read_text() == changed
    assert [heading for heading, _ in shown] == [
        t("conflict.heading", path="~/.ssh/config")
    ]
    assert app.hosts[0].title == "vps-blog"


# -- old copies to the trash --------------------------------------------------

OLD_COPIES = [
    "config.bak-20261012-100855",
    "config.bak-20261015-142125",
    "config.bak-20261024-124225",
]


@pytest.fixture
def said(app, monkeypatch) -> list[str]:
    texts: list[str] = []
    monkeypatch.setattr(app, "toast", texts.append)
    return texts


def copies(config_file: Path) -> list[str]:
    return sorted(path.name for path in config_file.parent.glob("config.bak-*"))


def test_saving_keeps_the_newest_three_copies(
    app, config_file: Path, trash, said
) -> None:
    for name in OLD_COPIES:
        (config_file.parent / name).write_text(name)
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()

    assert trash.names == ["config.bak-20261012-100855"]
    assert len(copies(config_file)) == 3
    assert said == [t("save.done", path="~/.ssh/config")]


def test_the_number_of_copies_follows_the_preference(
    app, config_file: Path, trash
) -> None:
    settings.save(settings.Settings(backups=1))
    for name in OLD_COPIES:
        (config_file.parent / name).write_text(name)
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()

    assert trash.names == OLD_COPIES
    assert len(copies(config_file)) == 1


def test_a_trash_that_refuses_does_not_undo_the_save(
    app, config_file: Path, trash, said
) -> None:
    for name in OLD_COPIES:
        (config_file.parent / name).write_text(name)
    trash.refuse_all = True
    app.editor.hostname.set_text("203.0.113.99")

    assert app.save_current() is True

    assert "HostName 203.0.113.99" in config_file.read_text()
    assert app.editor.dirty is False
    assert len(copies(config_file)) == 4  # nothing deleted on the way
    assert said == [
        t("save.done", path="~/.ssh/config"),
        t("backups.left", folder="~/.ssh"),
    ]


def test_deleting_prunes_the_copies_too(app, config_file: Path, trash) -> None:
    for name in OLD_COPIES:
        (config_file.parent / name).write_text(name)

    app.remove_block(app.hosts[0])

    assert trash.names == ["config.bak-20261012-100855"]


# -- new connections -------------------------------------------------------


def test_new_appends_a_connection_and_selects_it(app) -> None:
    app.new_host()

    assert app.sidebar.rows()[-1].get_title() == "nova-conexao"
    assert app.current is app.hosts[-1]


def test_a_new_connection_is_not_on_disk_until_saved(app, config_file: Path) -> None:
    app.new_host()

    assert "nova-conexao" not in config_file.read_text()


def test_a_new_connection_saves_with_the_alias_the_user_typed(
    app, config_file: Path
) -> None:
    app.new_host()
    app.editor.host.set_text("vps-novo")
    app.editor.hostname.set_text("198.51.100.4")

    app.save_current()
    text = config_file.read_text()

    assert "Host vps-novo\n    HostName 198.51.100.4\n" in text
    assert text.count("Host vps-blog") == 1  # the rest is still there


# -- unsaved changes -------------------------------------------------------


def test_switching_away_while_edited_asks_first(app) -> None:
    app.editor.hostname.set_text("203.0.113.99")

    app.sidebar.listbox.select_row(app.sidebar.rows()[1])

    # The switch is held until the dialog is answered.
    assert app.current is app.hosts[0]
    assert app.editor.host.get_text() == "vps-blog"


def test_switching_away_while_clean_just_switches(app) -> None:
    app.sidebar.listbox.select_row(app.sidebar.rows()[1])

    assert app.current is app.hosts[1]


def test_reselecting_the_same_connection_does_not_ask(app) -> None:
    app.editor.hostname.set_text("203.0.113.99")

    app.sidebar.listbox.select_row(app.sidebar.rows()[0])

    assert app.current is app.hosts[0]
    assert app.editor.dirty is True
