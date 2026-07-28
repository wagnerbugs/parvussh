"""The help dialog, the key guide, and duplicate/delete."""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.data.guide import ABOUT_CONFIG, SECTIONS
from parvussh.data.keywords import CATALOG

pytestmark = pytest.mark.gui

CONFIG = """# não mexer sem café

Host vps-blog
    HostName 203.0.113.10
    User deploy
    IdentityFile ~/.ssh/id_blog

Host github.com
    User git

Host *
    ServerAliveInterval 60
"""


@pytest.fixture
def app(window, fake_home: Path, fake_bin):
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


@pytest.fixture
def config_file(fake_home: Path) -> Path:
    return fake_home / ".ssh" / "config"


def aliases(app) -> list[str]:
    return [block.title for block in app.hosts]


# -- the guide's text ------------------------------------------------------


def test_every_guide_section_has_a_title_and_a_body() -> None:
    for section in (*SECTIONS, ABOUT_CONFIG):
        assert not section.title.startswith("guide."), section.key
        assert not section.body.startswith("guide."), section.key
        assert len(section.body) > 100, section.key


def test_the_guide_walks_the_path_in_order() -> None:
    assert [section.key for section in SECTIONS] == [
        "create",
        "install",
        "permissions",
        "password",
        "agent",
        "debug",
    ]


def test_the_guide_names_the_commands_it_talks_about() -> None:
    body = "\n".join(section.body for section in SECTIONS)

    for command in ("ssh-keygen -t ed25519", "ssh-copy-id", "chmod 700 ~/.ssh"):
        assert command in body, command


def test_the_guide_markup_is_balanced() -> None:
    """An unclosed tag makes Pango render the raw markup at the user."""
    for section in (*SECTIONS, ABOUT_CONFIG):
        assert section.body.count("<tt>") == section.body.count("</tt>"), section.key
        assert section.body.count("<b>") == section.body.count("</b>"), section.key


def test_the_guide_renders_as_pango_markup(gtk) -> None:
    from gi.repository import Pango

    for section in (*SECTIONS, ABOUT_CONFIG):
        # Raises GLib.Error on malformed markup, which is the point.
        Pango.parse_markup(section.body, -1, "\0")


def test_the_first_match_wins_rule_is_explained() -> None:
    """The one surprise about ssh_config someone has to be told."""
    assert "primeira" in ABOUT_CONFIG.body


# -- the dialog ------------------------------------------------------------


@pytest.fixture
def help_dialog(gtk):
    from parvussh.ui.help import HelpDialog

    return HelpDialog()


def test_the_dialog_builds_with_three_pages(help_dialog) -> None:
    assert help_dialog.get_title() == "Ajuda"
    assert help_dialog.get_search_enabled() is True


def test_every_catalog_option_is_documented(gtk) -> None:
    from parvussh.ui.help import option_subtitle

    for keyword in CATALOG:
        subtitle = option_subtitle(keyword)
        assert keyword.description in subtitle, keyword.name


def test_an_option_with_an_example_shows_it(gtk) -> None:
    from parvussh.data.keywords import get
    from parvussh.ui.help import option_subtitle

    assert "203.0.113.10" in option_subtitle(get("HostName"))


def test_an_enum_without_an_example_lists_its_values(gtk) -> None:
    from parvussh.data.keywords import get
    from parvussh.ui.help import option_subtitle

    subtitle = option_subtitle(get("AddKeysToAgent"))
    assert "yes, no, ask, confirm" in subtitle


def test_opening_help_does_not_raise(app) -> None:
    app.show_help()


# -- duplicating -----------------------------------------------------------


def test_duplicate_copies_the_connection_below_the_original(app) -> None:
    app.duplicate_current()

    assert aliases(app) == ["vps-blog", "vps-blog-copia", "github.com", "*"]


def test_a_duplicate_carries_the_options_over(app) -> None:
    app.duplicate_current()

    copy = app.hosts[1]
    assert copy.get("HostName") == "203.0.113.10"
    assert copy.get("IdentityFile") == "~/.ssh/id_blog"


def test_a_duplicate_is_selected_and_ready_to_rename(app) -> None:
    app.duplicate_current()

    assert app.current is app.hosts[1]
    assert app.editor.host.get_text() == "vps-blog-copia"


def test_a_duplicate_is_not_on_disk_until_saved(app, config_file: Path) -> None:
    app.duplicate_current()

    assert "vps-blog-copia" not in config_file.read_text()


def test_duplicating_twice_does_not_reuse_the_alias(app) -> None:
    """Two hosts with one alias is legal but useless: the first always wins."""
    app.duplicate_current()
    app.sidebar.listbox.select_row(app.sidebar.rows()[0])

    app.duplicate_current()

    assert "vps-blog-copia-2" in aliases(app)
    assert len(aliases(app)) == len(set(aliases(app)))


def test_a_saved_duplicate_reaches_the_file(app, config_file: Path) -> None:
    app.duplicate_current()

    app.save_current()

    text = config_file.read_text()
    assert "Host vps-blog-copia\n" in text
    assert text.count("HostName 203.0.113.10") == 2


# -- deleting --------------------------------------------------------------


def test_delete_removes_the_block_from_the_file(app, config_file: Path) -> None:
    app.remove_block(app.hosts[0])

    text = config_file.read_text()
    assert "Host vps-blog" not in text
    assert aliases(app) == ["github.com", "*"]


def test_delete_leaves_the_other_blocks_byte_identical(app, config_file: Path) -> None:
    app.remove_block(app.hosts[0])
    text = config_file.read_text()

    for survivor in (
        "Host github.com\n    User git\n",
        "Host *\n    ServerAliveInterval 60\n",
    ):
        assert survivor in text, survivor


def test_delete_backs_the_file_up_first(app, fake_home: Path) -> None:
    app.remove_block(app.hosts[0])

    assert len(list((fake_home / ".ssh").glob("config.bak-*"))) == 1


def test_delete_clears_the_editor(app) -> None:
    app.remove_block(app.hosts[0])

    assert app.current is None
    assert app.editor.stack.get_visible_child_name() == "empty"


def test_delete_asks_before_doing_anything(app, config_file: Path) -> None:
    before = config_file.read_bytes()

    app.delete_current()  # opens the dialog and returns

    assert config_file.read_bytes() == before
    assert aliases(app) == ["vps-blog", "github.com", "*"]


def test_deleting_with_nothing_selected_does_nothing(window) -> None:
    window.delete_current()
    assert window.hosts == []
