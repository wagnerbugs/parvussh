"""The help dialog, the key guide, and duplicate/delete."""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.data.guide import ABOUT_CONFIG, SECTIONS
from parvussh.data.keywords import CATALOG
from parvussh.i18n import available_locales, current_locale, set_locale

pytestmark = pytest.mark.gui

COPY_ICON = "edit-copy-symbolic"

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


def guide_bodies() -> list[tuple[str, str, str]]:
    """Every guide body in every shipped language, as `(locale, key, text)`.

    The bodies resolve through `t()` at the active locale, so a check that
    does not switch reads `pt_br` and nothing else — and the English guide is
    the same amount of hand-written markup, with the same way of breaking.
    """
    original = current_locale()
    collected: list[tuple[str, str, str]] = []
    try:
        for locale in available_locales():
            set_locale(locale)
            for section in (*SECTIONS, ABOUT_CONFIG):
                collected.append((locale, section.key, section.body))
    finally:
        set_locale(original)
    return collected


def test_the_guide_markup_is_balanced() -> None:
    """An unclosed tag makes Pango render the raw markup at the user."""
    for locale, key, body in guide_bodies():
        where = f"{locale}:{key}"
        assert body.count("<tt>") == body.count("</tt>"), where
        assert body.count("<b>") == body.count("</b>"), where


def test_the_guide_renders_as_pango_markup(gtk) -> None:
    from gi.repository import GLib, Pango

    for locale, key, body in guide_bodies():
        try:
            Pango.parse_markup(body, -1, "\0")
        except GLib.Error as error:
            # The exception alone does not say which section it came from.
            pytest.fail(f"{locale}:{key} is not valid markup: {error}")


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


# -- commands set apart, with a copy button ---------------------------------


def split(body: str):
    from parvussh.ui.help import split_body

    return split_body(body)


def commands(*lines: str):
    from parvussh.ui.help import Commands

    return Commands(lines)


def test_a_command_paragraph_becomes_a_block(gtk) -> None:
    body = "Rode na sua máquina:\n\n<tt>ssh-add ~/.ssh/id_ed25519</tt>\n\nPronto."

    assert split(body) == [
        "Rode na sua máquina:",
        commands("ssh-add ~/.ssh/id_ed25519"),
        "Pronto.",
    ]


def test_consecutive_command_lines_share_one_block(gtk) -> None:
    body = "<tt>chmod 700 ~/.ssh</tt>\n<tt>chmod 600 ~/.ssh/authorized_keys</tt>"

    assert split(body) == [
        commands("chmod 700 ~/.ssh", "chmod 600 ~/.ssh/authorized_keys")
    ]


def test_a_blank_line_starts_a_new_block(gtk) -> None:
    body = "<tt>ssh -v apelido</tt>\n\n<tt>ssh -G apelido</tt>"

    assert split(body) == [commands("ssh -v apelido"), commands("ssh -G apelido")]


def test_a_sentence_leading_into_commands_stays_prose(gtk) -> None:
    """The sshd_config lines follow their lead-in with no blank line between."""
    body = (
        "Em <tt>/etc/ssh/sshd_config</tt>, no servidor:\n"
        "<tt>PasswordAuthentication no</tt>\n"
        "<tt>PermitRootLogin prohibit-password</tt>\n\n"
        "A segunda linha libera o root apenas por chave."
    )

    assert split(body) == [
        "Em <tt>/etc/ssh/sshd_config</tt>, no servidor:",
        commands("PasswordAuthentication no", "PermitRootLogin prohibit-password"),
        "A segunda linha libera o root apenas por chave.",
    ]


def test_tt_inside_a_sentence_is_not_a_command(gtk) -> None:
    body = "O tipo <tt>ed25519</tt> é a escolha atual.\n<tt>a</tt> e <tt>b</tt>"

    assert split(body) == [body]


def test_paragraph_breaks_inside_prose_are_kept(gtk) -> None:
    body = "Um.\n\nDois.\n\n<tt>ls</tt>"

    assert split(body) == ["Um.\n\nDois.", commands("ls")]


def test_a_command_is_copied_as_typed_not_as_markup(gtk) -> None:
    """`&&` and `<` are escaped in the catalog; the terminal must get them back."""
    body = "<tt>cd /srv &amp;&amp; ls &lt;dir&gt; &quot;x&quot;</tt>"

    assert split(body) == [commands('cd /srv && ls <dir> "x"')]


def guide_parts():
    from parvussh.ui.help import split_body

    for locale, key, body in guide_bodies():
        for part in split_body(body):
            yield f"{locale}:{key}", part


def test_every_command_the_guide_shows_gets_a_block(gtk) -> None:
    from parvussh.ui.help import Commands

    lines = [
        line
        for _where, part in guide_parts()
        if isinstance(part, Commands)
        for line in part.lines
    ]

    for command in (
        'ssh-keygen -t ed25519 -C "seu-nome@notebook"',
        "ssh-copy-id -i ~/.ssh/id_ed25519.pub usuario@servidor",
        "chown -R $USER:$USER ~/.ssh",
        "sudo sshd -T | grep -i passwordauthentication",
        'ssh-keygen -t ed25519 -C "your-name@laptop"',
    ):
        assert command in lines, command


def test_no_whole_line_command_is_left_in_the_prose(gtk) -> None:
    from parvussh.ui.help import COMMAND_LINE, Commands

    for where, part in guide_parts():
        if isinstance(part, Commands):
            continue
        for line in part.split("\n"):
            assert COMMAND_LINE.fullmatch(line) is None, f"{where}: {line}"


def test_every_prose_part_is_still_valid_markup(gtk) -> None:
    """Splitting must never cut a tag in half."""
    from gi.repository import GLib, Pango

    from parvussh.ui.help import Commands

    for where, part in guide_parts():
        if isinstance(part, Commands):
            continue
        try:
            Pango.parse_markup(part, -1, "\0")
        except GLib.Error as error:
            pytest.fail(f"{where} split into invalid markup: {error}")


def copy_buttons(widget) -> list:
    from gi.repository import Gtk

    found = []
    child = widget.get_first_child()
    while child is not None:
        if isinstance(child, Gtk.Button) and child.get_icon_name() == COPY_ICON:
            found.append(child)
        found.extend(copy_buttons(child))
        child = child.get_next_sibling()
    return found


def dialog_buttons(dialog) -> list:
    return [button for page in dialog.pages for button in copy_buttons(page)]


def test_every_command_line_has_its_own_copy_button(help_dialog) -> None:
    """One per line: the second of "test, then reload" must not ride along."""
    from parvussh.ui.help import Commands

    lines = sum(
        len(part.lines)
        for part in (
            part
            for section in (*SECTIONS, ABOUT_CONFIG)
            for part in split(section.body)
        )
        if isinstance(part, Commands)
    )

    buttons = dialog_buttons(help_dialog)
    assert len(buttons) == lines
    assert all(button.get_tooltip_text() == "Copiar" for button in buttons)


def test_the_copy_button_puts_the_command_on_the_clipboard(
    help_dialog, pump, monkeypatch: pytest.MonkeyPatch
) -> None:
    said: list[str] = []
    monkeypatch.setattr(
        help_dialog, "add_toast", lambda toast: said.append(toast.get_title())
    )
    copied: list[str] = []

    dialog_buttons(help_dialog)[0].emit("clicked")

    def read(clipboard, result) -> None:
        copied.append(clipboard.read_text_finish(result))

    help_dialog.get_clipboard().read_text_async(None, read)

    pump(lambda: copied != [])
    assert copied == ['ssh-keygen -t ed25519 -C "seu-nome@notebook"']
    assert said == ["Copiado para a área de transferência"]


def test_each_button_copies_its_own_line(gtk) -> None:
    """In a block of three, the second button copies the second command."""
    from parvussh.data.guide import Section
    from parvussh.ui.help import prose_group

    copied: list[str] = []
    buttons = copy_buttons(prose_group(Section("permissions"), copied.append))

    for button in buttons:
        button.emit("clicked")

    assert copied == [
        "chmod 700 ~/.ssh",
        "chmod 600 ~/.ssh/authorized_keys",
        "chown -R $USER:$USER ~/.ssh",
    ]


def test_a_second_copy_replaces_the_first_notice(help_dialog) -> None:
    """Three quick copies must not queue three toasts one after another."""
    first, second = dialog_buttons(help_dialog)[:2]
    dismissed: list[bool] = []

    first.emit("clicked")
    help_dialog._copied.connect("dismissed", lambda _toast: dismissed.append(True))
    second.emit("clicked")

    assert dismissed == [True]


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
