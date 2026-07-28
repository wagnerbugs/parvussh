"""Choosing an existing key, and creating a new one from the form."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.gui

CONFIG = """Host vps
    HostName 203.0.113.10
    IdentityFile ~/.ssh/id_blog
    ControlPath ~/.ssh/cm-%r@%h:%p
"""
PRIVATE = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXk=\n"
DESCRIBED = "256 SHA256:ZmFrZWZpbmdlcnByaW50 wagner@notebook (ED25519)\n"


@pytest.fixture
def app(window, fake_home: Path, fake_bin):
    (fake_home / ".ssh" / "config").write_text(CONFIG, encoding="utf-8")
    window.reload()
    window.sidebar.listbox.select_row(window.sidebar.rows()[0])
    return window


def option(app, name: str):
    return next(o for o in app.editor.options if o.keyword.name == name)


def make_key(home: Path, name: str) -> Path:
    path = home / ".ssh" / name
    path.write_text(PRIVATE, encoding="utf-8")
    path.with_name(f"{name}.pub").write_text("ssh-ed25519 AAAA... wagner\n")
    return path


# -- the picker ------------------------------------------------------------


def test_an_identity_row_offers_a_key_picker(app) -> None:
    assert hasattr(option(app, "IdentityFile"), "key_popover")


def test_a_path_row_offers_a_file_button_not_a_key_picker(app) -> None:
    assert not hasattr(option(app, "ControlPath"), "key_popover")


def test_the_picker_lists_the_keys_in_the_ssh_directory(
    app, fake_home: Path, fake_bin
) -> None:
    make_key(fake_home, "id_ed25519")
    make_key(fake_home, "id_rsa")
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)
    picker = option(app, "IdentityFile").key_popover

    picker.refresh()

    assert [row.get_title() for row in picker.rows()] == ["id_ed25519", "id_rsa"]


def test_a_key_row_shows_its_type_and_fingerprint_comment(
    app, fake_home: Path, fake_bin
) -> None:
    make_key(fake_home, "id_ed25519")
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)
    picker = option(app, "IdentityFile").key_popover

    picker.refresh()

    assert picker.rows()[0].get_subtitle() == "ED25519 · 256 bits · wagner@notebook"


def test_a_key_we_cannot_describe_still_appears(app, fake_home: Path, fake_bin) -> None:
    make_key(fake_home, "id_estranha")
    fake_bin.install("ssh-keygen", returncode=255, stderr="invalid format")
    picker = option(app, "IdentityFile").key_popover

    picker.refresh()

    assert [row.get_title() for row in picker.rows()] == ["id_estranha"]


def test_an_empty_ssh_directory_says_so(app) -> None:
    picker = option(app, "IdentityFile").key_popover

    picker.refresh()

    assert picker.rows() == []


def test_picking_a_key_writes_the_portable_tilde_form(
    app, fake_home: Path, fake_bin
) -> None:
    """An absolute /home/wagner/... path would break on another machine."""
    make_key(fake_home, "id_ed25519")
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)
    row = option(app, "IdentityFile")
    row.key_popover.refresh()

    row.key_popover.rows()[0].emit("activated")

    assert row.value() == "~/.ssh/id_ed25519"


def test_the_picker_is_rebuilt_every_time_it_opens(
    app, fake_home: Path, fake_bin
) -> None:
    """A key made a minute ago must show up without restarting the app."""
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)
    picker = option(app, "IdentityFile").key_popover
    picker.refresh()
    assert picker.rows() == []

    make_key(fake_home, "id_nova")
    picker.emit("show")

    assert [row.get_title() for row in picker.rows()] == ["id_nova"]


# -- creating a key --------------------------------------------------------


@pytest.fixture
def new_key(window, fake_home: Path, fake_bin):
    """A NewKeyDialog presented on a window, the way the app opens it.

    Presented rather than merely built: `create()` closes the dialog on
    success, and `Adw.Dialog.close()` is a no-op plus a critical when nothing
    ever presented it.
    """
    from parvussh.ui.dialogs import NewKeyDialog

    def build(on_created=None, toast=None):
        dialog = NewKeyDialog(on_created=on_created, toast=toast)
        dialog.present(window)
        return dialog

    return build


def test_creating_a_key_calls_ssh_keygen_with_the_expected_argv(
    new_key, fake_home: Path, fake_bin
) -> None:
    fake_bin.install("ssh-keygen", returncode=0, creates=PRIVATE)
    dialog = new_key()
    dialog.name.set_text("id_nova")
    dialog.comment.set_text("wagner@nb")
    dialog.passphrase.set_text("segredo")
    dialog.confirm.set_text("segredo")

    assert dialog.create() is True

    argv = fake_bin.args("ssh-keygen", 0)
    assert argv[:2] == ["-t", "ed25519"]
    assert argv[argv.index("-f") + 1] == str(fake_home / ".ssh" / "id_nova")
    assert argv[argv.index("-N") + 1] == "segredo"
    assert argv[argv.index("-C") + 1] == "wagner@nb"


def test_a_created_key_fills_the_row_that_asked_for_it(
    new_key, fake_home: Path, fake_bin
) -> None:
    fake_bin.install_sequence(
        "ssh-keygen",
        [
            {"returncode": 0, "stdout": "", "stderr": "", "creates": PRIVATE},
            {"returncode": 0, "stdout": DESCRIBED, "stderr": "", "creates": ""},
        ],
    )
    filled: list[str] = []
    dialog = new_key(on_created=filled.append)
    dialog.name.set_text("id_nova")

    dialog.create()

    assert filled == ["~/.ssh/id_nova"]


def test_a_created_key_is_announced(new_key, fake_bin) -> None:
    fake_bin.install("ssh-keygen", returncode=0, creates=PRIVATE)
    said: list[str] = []
    dialog = new_key(toast=said.append)
    dialog.name.set_text("id_nova")

    dialog.create()

    assert said == ["Chave criada em ~/.ssh/id_nova"]


def test_mismatched_passphrases_block_creation(new_key, fake_bin) -> None:
    fake_bin.install("ssh-keygen", returncode=0, creates=PRIVATE)
    dialog = new_key()
    dialog.name.set_text("id_nova")
    dialog.passphrase.set_text("segredo")
    dialog.confirm.set_text("outra")

    assert dialog.create() is False
    assert fake_bin.calls("ssh-keygen") == []  # we never even asked


def test_an_empty_name_blocks_creation(new_key, fake_bin) -> None:
    fake_bin.install("ssh-keygen", returncode=0, creates=PRIVATE)
    dialog = new_key()
    dialog.name.set_text("   ")

    assert dialog.create() is False
    assert fake_bin.calls("ssh-keygen") == []


def test_an_existing_file_blocks_creation(new_key, fake_home: Path, fake_bin) -> None:
    """ssh-keygen would stop at an overwrite prompt nobody can see."""
    make_key(fake_home, "id_ed25519")
    fake_bin.install("ssh-keygen", returncode=0, creates=PRIVATE)
    dialog = new_key()
    dialog.name.set_text("id_ed25519")

    assert dialog.create() is False
    assert (fake_home / ".ssh" / "id_ed25519").read_text() == PRIVATE


def test_a_missing_ssh_keygen_is_reported(new_key, fake_bin) -> None:
    dialog = new_key()  # nothing installed on the empty PATH
    dialog.name.set_text("id_nova")

    assert dialog.create() is False


def test_ssh_keygen_failing_is_reported(new_key, fake_bin) -> None:
    fake_bin.install("ssh-keygen", returncode=1, stderr="unknown key type")
    dialog = new_key()
    dialog.name.set_text("id_nova")

    assert dialog.create() is False


def test_the_offered_key_types_come_from_core(new_key) -> None:
    from parvussh.core.keys import KEY_TYPES

    dialog = new_key()
    model = dialog.kind.get_model()
    assert [model.get_string(i) for i in range(model.get_n_items())] == list(KEY_TYPES)


def test_ed25519_is_the_default_choice(new_key) -> None:
    dialog = new_key()
    assert dialog.kind.get_selected() == 0
    assert dialog.kind.get_model().get_string(0) == "ed25519"
