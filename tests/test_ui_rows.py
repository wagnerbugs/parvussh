"""One widget per option kind, and the values each one must not mangle."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

CONFIG = """Host vps
    HostName 203.0.113.10
    Compression yes
    ServerAliveInterval 60
    StrictHostKeyChecking accept-new
    IdentityFile ~/.ssh/id_blog
    GSSAPIAuthentication no
"""


@pytest.fixture
def rows(gtk):
    from parvussh.ui import rows as module

    return module


@pytest.fixture
def app(window, fake_home: Path):
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


def option(app, name: str):
    return next(o for o in app.editor.options if o.keyword.name == name)


# -- one widget per kind ---------------------------------------------------


def test_a_boolean_becomes_a_switch(rows, app) -> None:
    from gi.repository import Adw

    compression = option(app, "Compression")
    assert isinstance(compression.row, Adw.SwitchRow)
    assert compression.row.get_active() is True
    assert compression.value() == "yes"


def test_a_switch_writes_yes_or_no(rows, app) -> None:
    compression = option(app, "Compression")

    compression.row.set_active(False)

    assert compression.value() == "no"
    assert compression.config_line() == "    Compression no"


def test_an_integer_becomes_a_spinner(rows, app) -> None:
    from gi.repository import Adw

    interval = option(app, "ServerAliveInterval")
    assert isinstance(interval.row, Adw.SpinRow)
    assert interval.value() == "60"


def test_a_spinner_respects_the_catalog_bounds(rows, app) -> None:
    interval = option(app, "ServerAliveInterval")
    assert interval.row.get_adjustment().get_lower() == 0
    assert interval.row.get_adjustment().get_upper() == 86400


def test_a_spinner_does_not_print_the_example_it_is_already_showing(app) -> None:
    """A number in the subtitle beside a selector displaying one reads as noise."""
    interval = option(app, "ServerAliveInterval")

    assert interval.row.get_subtitle() == interval.keyword.description
    assert interval.keyword.example  # the catalog has one; the row just skips it
    assert interval.keyword.example not in interval.row.get_subtitle()


def test_a_text_row_still_offers_the_example(app) -> None:
    """The other half of the rule: nothing on screen shows it there."""
    identity = option(app, "IdentityFile")

    assert identity.keyword.example in identity.row.get_tooltip_text()


def test_an_enum_becomes_a_dropdown(rows, app) -> None:
    from gi.repository import Adw

    strict = option(app, "StrictHostKeyChecking")
    assert isinstance(strict.row, Adw.ComboRow)
    assert strict.value() == "accept-new"


def test_a_dropdown_writes_the_selected_value(rows, app) -> None:
    strict = option(app, "StrictHostKeyChecking")

    strict.row.set_selected(0)  # "ask", first in the catalog order

    assert strict.value() == "ask"


def test_a_path_or_identity_becomes_a_text_entry(rows, app) -> None:
    from gi.repository import Adw

    identity = option(app, "IdentityFile")
    assert isinstance(identity.row, Adw.EntryRow)
    assert identity.value() == "~/.ssh/id_blog"


def test_an_uncatalogued_option_becomes_a_text_entry(rows, app) -> None:
    from gi.repository import Adw

    unknown = option(app, "GSSAPIAuthentication")
    assert isinstance(unknown.row, Adw.EntryRow)
    assert unknown.keyword.catalogued is False
    assert unknown.value() == "no"


def test_the_basic_fields_do_not_get_a_second_row(app) -> None:
    assert "HostName" not in [o.keyword.name for o in app.editor.options]


# -- values a typed widget cannot hold -------------------------------------


def test_a_boolean_value_ssh_does_not_accept_falls_back_to_text(rows, gtk) -> None:
    """`Compression maybe` is not ours to reinterpret as `no`."""
    from parvussh.data.keywords import get

    row = rows.OptionRow(get("Compression"), "maybe")

    assert row.typed is False
    assert row.value() == "maybe"


def test_an_integer_outside_the_catalog_range_falls_back_to_text(rows, gtk) -> None:
    """A SpinRow bounded 0..3600 would silently clamp 99999 on the next save."""
    from parvussh.data.keywords import get

    row = rows.OptionRow(get("ConnectTimeout"), "99999")

    assert row.typed is False
    assert row.value() == "99999"


def test_a_non_numeric_integer_falls_back_to_text(rows, gtk) -> None:
    from parvussh.data.keywords import get

    row = rows.OptionRow(get("ServerAliveInterval"), "%h")

    assert row.typed is False
    assert row.value() == "%h"


def test_an_unlisted_enum_value_is_kept_in_the_dropdown(rows, gtk) -> None:
    from parvussh.data.keywords import get

    row = rows.OptionRow(get("AddKeysToAgent"), "1h")

    assert row.typed is True
    assert row.value() == "1h"


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("Compression", "yes", True),
        ("Compression", "no", True),
        ("Compression", "YES", True),
        ("Compression", "true", False),
        ("Compression", "", True),
        ("ConnectTimeout", "10", True),
        ("ConnectTimeout", "0", True),
        ("ConnectTimeout", "3600", True),
        ("ConnectTimeout", "3601", False),
        ("ConnectTimeout", "-1", False),
        ("IdentityFile", "qualquer coisa", True),
    ],
)
def test_the_fallback_rule(rows, gtk, name: str, value: str, expected: bool) -> None:
    from parvussh.data.keywords import get

    assert rows.fits_widget(get(name), value) is expected


# -- through a save --------------------------------------------------------


def test_every_option_survives_a_save_round_trip(app, fake_home: Path) -> None:
    before = (fake_home / ".ssh" / "config").read_text()
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()
    after = (fake_home / ".ssh" / "config").read_text()

    for line in (
        "Compression yes",
        "ServerAliveInterval 60",
        "StrictHostKeyChecking accept-new",
        "IdentityFile ~/.ssh/id_blog",
        "GSSAPIAuthentication no",
    ):
        assert line in after, f"{line} was lost\n{before}\n---\n{after}"


def test_an_uncatalogued_option_is_never_dropped(app, fake_home: Path) -> None:
    """Contract rule 3, end to end: unknown in, unknown out."""
    app.editor.hostname.set_text("203.0.113.99")

    app.save_current()

    assert "GSSAPIAuthentication no" in (fake_home / ".ssh" / "config").read_text()


def test_toggling_a_switch_reaches_the_file(app, fake_home: Path) -> None:
    option(app, "Compression").row.set_active(False)

    app.save_current()

    assert "Compression no" in (fake_home / ".ssh" / "config").read_text()


def test_removing_an_option_removes_the_line(app, fake_home: Path) -> None:
    app.editor.remove_option(option(app, "Compression"))

    app.save_current()

    assert "Compression" not in (fake_home / ".ssh" / "config").read_text()


def test_removing_an_option_marks_the_form_edited(app) -> None:
    app.editor.remove_option(option(app, "Compression"))
    assert app.editor.dirty is True


def test_an_option_with_no_value_is_left_out_of_the_file(app, fake_home: Path) -> None:
    option(app, "IdentityFile").row.set_text("")

    app.save_current()

    assert "IdentityFile" not in (fake_home / ".ssh" / "config").read_text()


def test_comments_above_an_option_travel_with_it(window, fake_home: Path) -> None:
    (fake_home / ".ssh" / "config").write_text(
        "Host vps\n"
        "    HostName 203.0.113.10\n"
        "    # essa chave é a antiga\n"
        "    IdentityFile ~/.ssh/id_blog\n",
        encoding="utf-8",
    )
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])

    window.editor.hostname.set_text("203.0.113.99")
    window.save_current()

    assert (
        "    # essa chave é a antiga\n" in (fake_home / ".ssh" / "config").read_text()
    )


# -- the empty state -------------------------------------------------------


def test_a_connection_with_no_extras_invites_using_the_plus(
    window, fake_home: Path
) -> None:
    (fake_home / ".ssh" / "config").write_text("Host vps\n    User dev\n")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])

    assert window.editor.options == []
    assert window.editor.empty_extras.get_visible() is True


def test_the_invitation_hides_once_there_are_options(app) -> None:
    assert app.editor.options != []
    assert app.editor.empty_extras.get_visible() is False
