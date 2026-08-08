"""Test a connection without saving the config first.

Write the block being edited to a temp file, run ssh non-interactively, and
read the reason it stopped. The central insight (SPEC §6): reaching the
authentication prompt is a **success**. It proves the address, the port, the
network and the user are all right — which is exactly what the person clicking
"Testar" wanted to know. Only the credential is missing, and the test never
sends one.

`interpret()` is a pure function on purpose: the table below is the part worth
testing, and it should be testable without a subprocess.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from parvussh.core import host

TIMEOUT = 25
CONNECT_TIMEOUT = 8

# Status codes, not sentences. The UI turns each into t("test.<status>.title")
# and t("test.<status>.detail") — core carries no translated text (D3).
AUTH = "auth"
REACHABLE = "reachable"
DNS = "dns"
REFUSED = "refused"
TIMEOUT_STATUS = "timeout"
NETWORK = "network"
HOSTKEY = "hostkey"
CONFIG = "config"
NO_SSH = "no-ssh"
UNKNOWN = "unknown"

#: Ordered: the first match wins, so the specific cases come before the vague
#: ones. `timed out` sits after `connection refused` because a refusal is the
#: more precise diagnosis when a message somehow mentions both.
SIGNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (REACHABLE, ("permission denied", "no supported authentication")),
    (DNS, ("could not resolve", "name or service not known")),
    (REFUSED, ("connection refused",)),
    (TIMEOUT_STATUS, ("timed out", "timeout")),
    (NETWORK, ("no route to host", "network is unreachable")),
    (HOSTKEY, ("host key verification failed", "remote host identification")),
    (CONFIG, ("bad configuration",)),
)

#: Statuses the user should read as good news.
SUCCESSES = frozenset({AUTH, REACHABLE})


@dataclass(frozen=True)
class TestResult:
    """What happened, in a form the UI can put words to."""

    # Not a pytest test class, despite the name SPEC §6 gave it.
    __test__ = False

    status: str
    output: str = ""
    returncode: int = 0

    @property
    def ok(self) -> bool:
        return self.status in SUCCESSES


def interpret(returncode: int, output: str) -> TestResult:
    """Classify one ssh run. Pure: no files, no subprocess, no clock."""
    if returncode == 0:
        return TestResult(AUTH, output, returncode)
    low = output.lower()
    for status, needles in SIGNS:
        if any(needle in low for needle in needles):
            return TestResult(status, output, returncode)
    # The prototype also treated "line ... invalid" as a config error. Keeping
    # it: ssh phrases option complaints both ways depending on the version.
    if "line" in low and "invalid" in low:
        return TestResult(CONFIG, output, returncode)
    return TestResult(UNKNOWN, output, returncode)


def build_command(alias: str, config_path: str) -> list[str]:
    """The argv we run. Split out so a test can assert on it.

    Inside a Flatpak this comes back wrapped in `flatpak-spawn --host`, so the
    ssh that answers is the user's own — the one that can reach their agent and
    run their `ProxyCommand` (D5).
    """
    return host.command(
        [
            "ssh",
            "-F",
            config_path,
            "-o",
            "BatchMode=yes",  # never prompt: a hung prompt is an invisible freeze
            "-o",
            f"ConnectTimeout={CONNECT_TIMEOUT}",
            "-o",
            "NumberOfPasswordPrompts=0",
            "-o",
            "StrictHostKeyChecking=accept-new",
            alias,
            "true",  # the cheapest possible remote command
        ]
    )


def run(alias: str, config_text: str, timeout: int = TIMEOUT) -> TestResult:
    """Try `alias` against `config_text`, which need not be saved anywhere."""
    with host.temp_config(config_text) as temp:
        try:
            result = subprocess.run(
                build_command(alias, temp),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return TestResult(NO_SSH)
        except subprocess.TimeoutExpired:
            return TestResult(TIMEOUT_STATUS)
        output = (result.stdout + result.stderr).strip()
        return interpret(result.returncode, output)
