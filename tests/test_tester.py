"""The connection test, one test per row of the SPEC §6 interpretation table."""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.core.tester import (
    AUTH,
    CONFIG,
    DNS,
    HOSTKEY,
    NETWORK,
    NO_SSH,
    REACHABLE,
    REFUSED,
    TIMEOUT_STATUS,
    UNKNOWN,
    TestResult,
    build_command,
    interpret,
    run,
)
from tests.conftest import FakeBin

CONFIG_TEXT = "Host vps\n    HostName 203.0.113.10\n    User deploy\n"


# -- the table, row by row -------------------------------------------------


def test_interpret_exit_zero_is_authenticated() -> None:
    result = interpret(0, "")
    assert result.status == AUTH
    assert result.ok is True


def test_interpret_permission_denied_is_success() -> None:
    """The central insight: being asked for a credential proves the rest works."""
    result = interpret(255, "vps: Permission denied (publickey).")
    assert result.status == REACHABLE
    assert result.ok is True


def test_interpret_no_supported_authentication_is_success() -> None:
    result = interpret(255, "No supported authentication methods available")
    assert result.status == REACHABLE
    assert result.ok is True


def test_interpret_could_not_resolve_is_dns() -> None:
    result = interpret(255, "ssh: Could not resolve hostname vps.exemplo: ...")
    assert result.status == DNS
    assert result.ok is False


def test_interpret_name_or_service_not_known_is_dns() -> None:
    assert interpret(255, "Name or service not known").status == DNS


def test_interpret_connection_refused_is_refused() -> None:
    result = interpret(
        255, "ssh: connect to host 203.0.113.10 port 22: Connection refused"
    )
    assert result.status == REFUSED
    assert result.ok is False


def test_interpret_timed_out_is_timeout() -> None:
    result = interpret(255, "ssh: connect to host ... : Connection timed out")
    assert result.status == TIMEOUT_STATUS
    assert result.ok is False


def test_interpret_the_word_timeout_is_timeout() -> None:
    assert interpret(255, "Operation timeout").status == TIMEOUT_STATUS


def test_interpret_no_route_to_host_is_network() -> None:
    result = interpret(255, "ssh: connect to host ...: No route to host")
    assert result.status == NETWORK
    assert result.ok is False


def test_interpret_network_is_unreachable_is_network() -> None:
    assert interpret(255, "Network is unreachable").status == NETWORK


def test_interpret_host_key_verification_failed_is_hostkey() -> None:
    result = interpret(255, "Host key verification failed.")
    assert result.status == HOSTKEY
    assert result.ok is False


def test_interpret_remote_host_identification_is_hostkey() -> None:
    message = "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!"
    assert interpret(255, message).status == HOSTKEY


def test_interpret_bad_configuration_is_config() -> None:
    result = interpret(255, "/tmp/x: line 3: Bad configuration option: Nonsense")
    assert result.status == CONFIG
    assert result.ok is False


def test_interpret_an_invalid_line_is_also_config() -> None:
    """Older ssh phrases option complaints this way instead."""
    assert interpret(255, "config: line 4: invalid port number").status == CONFIG


def test_interpret_anything_else_is_unknown() -> None:
    result = interpret(3, "algo que nunca vimos antes")
    assert result.status == UNKNOWN
    assert result.ok is False
    assert result.returncode == 3


def test_interpret_keeps_the_raw_output_for_the_dialog() -> None:
    noise = "debug1: Reading configuration data\nPermission denied (publickey)."
    assert interpret(255, noise).output == noise


def test_interpret_is_case_insensitive() -> None:
    assert interpret(255, "PERMISSION DENIED").status == REACHABLE
    assert interpret(255, "permission denied").status == REACHABLE


def test_only_auth_and_reachable_count_as_success() -> None:
    failures = [DNS, REFUSED, TIMEOUT_STATUS, NETWORK, HOSTKEY, CONFIG, NO_SSH, UNKNOWN]
    for status in failures:
        assert TestResult(status).ok is False, status
    for status in (AUTH, REACHABLE):
        assert TestResult(status).ok is True, status


def test_a_refusal_wins_over_a_message_that_also_says_timeout() -> None:
    """Order matters: the specific diagnosis beats the vague one."""
    both = "Connection refused after connect timeout"
    assert interpret(255, both).status == REFUSED


# -- output captured from real servers -------------------------------------

#: OpenSSH 10 prints this before almost every connection to a server running an
#: older release. It is client-side noise about the *server's* age, not about
#: whether the connection worked, and it will be in front of nearly every
#: verdict from now on.
POST_QUANTUM_WARNING = (
    "** WARNING: connection is not using a post-quantum key exchange algorithm.\n"
    '** This session may be vulnerable to "store now, decrypt later" attacks.\n'
    "** The server may need to be upgraded. See https://openssh.com/pq.html"
)


def test_the_post_quantum_warning_alone_matches_nothing() -> None:
    """The banner is inert: it must never be mistaken for a diagnosis.

    Fails if a future needle collides with one of its words — "connection",
    "server" and "session" are all in there, and any of them would turn a
    routine banner into a verdict.
    """
    assert interpret(255, POST_QUANTUM_WARNING).status == UNKNOWN


def test_a_real_openssh_10_refusal_still_reads_as_reachable() -> None:
    """Captured from an actual run against a VPS, OpenSSH 10.2 client.

    Three lines of banner, then the line that matters. Reaching the
    authentication prompt is the success we care about, and the noise in front
    of it must not change that.

    The address is the only edit: a real one from the capture, swapped for a
    documentation address (RFC 5737). A test fixture is a public document.
    """
    real = (
        f"{POST_QUANTUM_WARNING}\n"
        "deploy@203.0.113.24: Permission denied (publickey,password)."
    )

    result = interpret(255, real)

    assert result.status == REACHABLE
    assert result.ok is True
    # And the banner survives into the expander, unedited.
    assert "post-quantum" in result.output


def test_the_banner_does_not_disturb_a_genuine_failure() -> None:
    """It only appears once crypto was negotiated, so it rides along with
    late-stage failures too."""
    for tail, expected in (
        ("Host key verification failed.", HOSTKEY),
        ("ssh: connect to host x port 22: Connection refused", REFUSED),
    ):
        assert interpret(255, f"{POST_QUANTUM_WARNING}\n{tail}").status == expected


# -- running it ------------------------------------------------------------


def test_the_command_is_fully_non_interactive() -> None:
    command = build_command("vps", "/tmp/x.sshconfig")

    assert command[:3] == ["ssh", "-F", "/tmp/x.sshconfig"]
    assert command[-2:] == ["vps", "true"]
    for option in (
        "BatchMode=yes",
        "ConnectTimeout=8",
        "NumberOfPasswordPrompts=0",
        "StrictHostKeyChecking=accept-new",
    ):
        assert option in command, option


def test_run_passes_the_unsaved_config_to_ssh(fake_bin: FakeBin) -> None:
    """The point of the feature: test before committing anything to disk."""
    fake_bin.install("ssh", returncode=0)

    assert run("vps", CONFIG_TEXT).status == AUTH
    assert fake_bin.args("ssh")[:2] == ["-F", fake_bin.args("ssh")[1]]
    assert fake_bin.args("ssh")[-2:] == ["vps", "true"]


def test_run_reads_both_streams(fake_bin: FakeBin) -> None:
    fake_bin.install("ssh", returncode=255, stderr="Permission denied (publickey).")

    result = run("vps", CONFIG_TEXT)

    assert result.status == REACHABLE
    assert "Permission denied" in result.output


def test_run_reports_a_missing_ssh(fake_bin: FakeBin) -> None:
    result = run("vps", CONFIG_TEXT)  # nothing installed on the empty PATH
    assert result.status == NO_SSH
    assert result.ok is False


def test_run_reports_its_own_timeout(fake_bin: FakeBin, monkeypatch) -> None:
    import subprocess

    def slow(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="ssh", timeout=25)

    monkeypatch.setattr(subprocess, "run", slow)

    assert run("vps", CONFIG_TEXT).status == TIMEOUT_STATUS


def test_run_deletes_the_temp_config(fake_bin: FakeBin) -> None:
    fake_bin.install("ssh", returncode=0)

    run("vps", CONFIG_TEXT)

    assert not Path(fake_bin.args("ssh")[1]).exists()


def test_run_deletes_the_temp_config_even_when_ssh_explodes(monkeypatch) -> None:
    """A leaked temp file holds the user's config at 0600 in /tmp forever."""
    import subprocess

    seen: list[str] = []

    def explode(command: list[str], **kwargs: object) -> None:
        seen.append(command[command.index("-F") + 1])
        raise RuntimeError("boom")

    monkeypatch.setattr(subprocess, "run", explode)

    with pytest.raises(RuntimeError):
        run("vps", CONFIG_TEXT)

    assert seen and not Path(seen[0]).exists()


def test_the_temp_config_is_somewhere_the_host_can_read(
    fake_bin: FakeBin, fake_home: Path
) -> None:
    """The system temp directory is private to a Flatpak sandbox.

    A config written there is invisible to the host `ssh` we hand the path to,
    so it goes in `~/.ssh` — dot-prefixed, because a glob does not match a
    dotfile and the user may well have an `Include *`.
    """
    fake_bin.install("ssh", returncode=0, stdout="%F")

    result = run("vps", CONFIG_TEXT)

    # The shim echoed its own -F path back at us.
    passed = Path(result.output)
    assert passed.suffix == ".sshconfig"
    assert passed.name.startswith(".parvussh-")
    assert passed.parent == fake_home / ".ssh"
