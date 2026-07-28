"""Key discovery and creation, per SPEC §5. Never against a real ssh-keygen."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from parvussh.core.keys import (
    KEY_MODE,
    KeyExistsError,
    KeyToolError,
    KeyToolMissing,
    SshKey,
    describe,
    generate,
    generate_command,
    list_keys,
    looks_like_a_key,
)
from tests.conftest import FakeBin

PRIVATE_HEADER = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXk=\n"
DESCRIBED = "256 SHA256:ZmFrZWZpbmdlcnByaW50 wagner@notebook (ED25519)\n"


@pytest.fixture
def ssh(fake_home: Path) -> Path:
    return fake_home / ".ssh"


def make_key(folder: Path, name: str, with_pub: bool = True) -> Path:
    path = folder / name
    path.write_text(PRIVATE_HEADER, encoding="utf-8")
    if with_pub:
        path.with_name(f"{name}.pub").write_text("ssh-ed25519 AAAA... wagner\n")
    return path


def names(keys: list[SshKey]) -> list[str]:
    return [key.name for key in keys]


# -- discovery -------------------------------------------------------------


def test_a_key_with_a_sibling_pub_is_found(ssh: Path, fake_bin: FakeBin) -> None:
    make_key(ssh, "id_ed25519")
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)

    assert names(list_keys()) == ["id_ed25519"]


def test_a_private_key_without_a_pub_is_still_found(
    ssh: Path, fake_bin: FakeBin
) -> None:
    """A key whose public half was deleted is still a key."""
    make_key(ssh, "id_orfa", with_pub=False)
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)

    assert names(list_keys()) == ["id_orfa"]


def test_a_plain_text_file_is_not_a_key(ssh: Path, fake_bin: FakeBin) -> None:
    (ssh / "anotacoes.txt").write_text("lembrar de renovar o certificado\n")
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)

    assert list_keys() == []


@pytest.mark.parametrize(
    "name",
    [
        "config",
        "known_hosts",
        "known_hosts.old",
        "authorized_keys",
        "environment",
        "rc",
        "agent.env",
        "allowed_signers",
        "id_ed25519.pub",
        "backup.bak",
        "velho.old",
        "meio.tmp",
        "algo.conf",
        "agent.sock",
        ".hidden",
        "config.d",
        "config.bak-20260728-174320",
    ],
)
def test_housekeeping_files_are_never_offered_as_keys(ssh: Path, name: str) -> None:
    path = ssh / name
    # Give each one private-key contents: the name alone must be enough.
    path.write_text(PRIVATE_HEADER, encoding="utf-8")

    assert looks_like_a_key(path) is False


def test_our_own_config_backups_are_skipped(ssh: Path, fake_bin: FakeBin) -> None:
    """The app writes config.bak-* beside the config; they are not keys."""
    (ssh / "config.bak-20260728-174320").write_text(PRIVATE_HEADER)
    make_key(ssh, "id_ed25519")
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)

    assert names(list_keys()) == ["id_ed25519"]


def test_keys_come_back_sorted_by_name(ssh: Path, fake_bin: FakeBin) -> None:
    for name in ("id_zeta", "id_alfa", "id_meio"):
        make_key(ssh, name)
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)

    assert names(list_keys()) == ["id_alfa", "id_meio", "id_zeta"]


def test_a_missing_ssh_directory_yields_nothing(fake_home: Path) -> None:
    (fake_home / ".ssh").rmdir()
    assert list_keys() == []


# -- describing ------------------------------------------------------------


def test_describe_parses_the_ssh_keygen_line(ssh: Path, fake_bin: FakeBin) -> None:
    path = make_key(ssh, "id_ed25519")
    fake_bin.install("ssh-keygen", stdout=DESCRIBED)

    key = describe(path)

    assert key.bits == 256
    assert key.fingerprint == "SHA256:ZmFrZWZpbmdlcnByaW50"
    assert key.comment == "wagner@notebook"
    assert key.kind == "ED25519"
    assert key.described is True
    assert fake_bin.args("ssh-keygen") == ["-l", "-f", str(path)]


def test_describe_handles_a_key_with_no_comment(ssh: Path, fake_bin: FakeBin) -> None:
    path = make_key(ssh, "id_rsa")
    fake_bin.install("ssh-keygen", stdout="4096 SHA256:abc no comment (RSA)\n")

    key = describe(path)

    assert key.bits == 4096
    assert key.kind == "RSA"
    assert key.comment == "no comment"


def test_describe_degrades_when_ssh_keygen_fails(ssh: Path, fake_bin: FakeBin) -> None:
    """A key we cannot describe is still a key; show the filename alone."""
    path = make_key(ssh, "id_ed25519")
    fake_bin.install("ssh-keygen", returncode=255, stderr="invalid format")

    key = describe(path)

    assert key.path == path
    assert key.fingerprint == ""
    assert key.described is False


def test_describe_degrades_when_ssh_keygen_is_missing(
    ssh: Path, fake_bin: FakeBin
) -> None:
    path = make_key(ssh, "id_ed25519")
    assert describe(path).described is False  # nothing installed on the empty PATH


def test_describe_degrades_on_unexpected_output(ssh: Path, fake_bin: FakeBin) -> None:
    path = make_key(ssh, "id_ed25519")
    fake_bin.install("ssh-keygen", stdout="something we have never seen\n")

    assert describe(path).described is False


def test_display_path_uses_the_tilde_form(fake_home: Path) -> None:
    """The value written into the config must stay portable."""
    key = SshKey(fake_home / ".ssh" / "id_ed25519")
    assert key.display_path == "~/.ssh/id_ed25519"


def test_display_path_leaves_a_key_outside_home_absolute() -> None:
    key = SshKey(Path("/etc/ssh/id_service"))
    assert key.display_path == "/etc/ssh/id_service"


# -- creating --------------------------------------------------------------


def test_generate_builds_the_expected_argv_for_ed25519(ssh: Path) -> None:
    command = generate_command(ssh / "id_ed25519", "ed25519", "segredo", "wagner@nb")

    assert command == [
        "ssh-keygen",
        "-t",
        "ed25519",
        "-f",
        str(ssh / "id_ed25519"),
        "-N",
        "segredo",
        "-C",
        "wagner@nb",
    ]


def test_generate_asks_for_4096_bits_on_rsa(ssh: Path) -> None:
    command = generate_command(ssh / "id_rsa", "rsa")

    assert "-b" in command
    assert command[command.index("-b") + 1] == "4096"


def test_generate_omits_the_comment_flag_when_there_is_no_comment(ssh: Path) -> None:
    assert "-C" not in generate_command(ssh / "id_ed25519", "ed25519")


def test_generate_runs_ssh_keygen_and_returns_the_new_key(
    ssh: Path, fake_bin: FakeBin
) -> None:
    target = ssh / "id_nova"
    fake_bin.install_sequence(
        "ssh-keygen",
        [
            # Call 1 creates the key, like the real tool. Call 2 is describe().
            {"returncode": 0, "stdout": "", "stderr": "", "creates": PRIVATE_HEADER},
            {"returncode": 0, "stdout": DESCRIBED, "stderr": "", "creates": ""},
        ],
    )

    key = generate(target, "ed25519", "", "wagner@nb")

    assert key.fingerprint == "SHA256:ZmFrZWZpbmdlcnByaW50"
    assert fake_bin.args("ssh-keygen", 0)[:4] == ["-t", "ed25519", "-f", str(target)]


def test_a_generated_key_is_private(ssh: Path, fake_bin: FakeBin) -> None:
    target = ssh / "id_nova"
    fake_bin.install("ssh-keygen", returncode=0, creates=PRIVATE_HEADER)

    generate(target)

    assert stat.S_IMODE(target.stat().st_mode) == KEY_MODE


def test_generate_refuses_an_existing_path(ssh: Path, fake_bin: FakeBin) -> None:
    """ssh-keygen would stop at an overwrite prompt the user cannot see."""
    target = make_key(ssh, "id_ed25519")
    fake_bin.install("ssh-keygen", returncode=0)

    with pytest.raises(KeyExistsError) as raised:
        generate(target)

    assert raised.value.path == target
    assert fake_bin.calls("ssh-keygen") == []  # we never even asked


def test_generate_reports_what_ssh_keygen_said(ssh: Path, fake_bin: FakeBin) -> None:
    fake_bin.install("ssh-keygen", returncode=1, stderr="unknown key type xyz")

    with pytest.raises(KeyToolError) as raised:
        generate(ssh / "id_nova")

    assert "unknown key type xyz" in str(raised.value)


def test_generate_reports_a_missing_ssh_keygen_distinctly(
    ssh: Path, fake_bin: FakeBin
) -> None:
    """The UI says "install openssh-client" for this, not "ssh-keygen said:"."""
    with pytest.raises(KeyToolMissing):
        generate(ssh / "id_nova")


def test_generate_rejects_a_key_type_we_do_not_offer(ssh: Path) -> None:
    with pytest.raises(KeyToolError):
        generate(ssh / "id_nova", "dsa")


def test_generate_creates_the_ssh_directory_when_needed(
    fake_home: Path, fake_bin: FakeBin
) -> None:
    (fake_home / ".ssh").rmdir()
    target = fake_home / ".ssh" / "id_nova"
    fake_bin.install("ssh-keygen", returncode=0, creates=PRIVATE_HEADER)

    generate(target)

    assert target.exists()
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
