"""Shared fixtures.

Safety rule from CLAUDE.md §8: no test may read or write the developer's real
`~/.ssh`. Everything that touches a home directory goes through `fake_home`.
"""

from __future__ import annotations

import json
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# A shim that records how it was called and replays a scripted result. The
# shebang is the absolute interpreter: `fake_bin` empties PATH, so `env` would
# have nothing to look `python3` up in.
SHIM = """#!{interpreter}
import json, pathlib, sys

results = json.loads(pathlib.Path({spec!r}).read_text())
log_path = pathlib.Path({log!r})
argv = sys.argv[1:]

# The call index picks the scripted result, so a test can say "succeed once,
# then fail" and catch code that acts on the first answer before asking twice.
done = log_path.read_text().splitlines() if log_path.exists() else []
seen = len([line for line in done if line])
with log_path.open("a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv) + "\\n")
result = results[seen] if seen < len(results) else results[-1]

# The file argument: -F for ssh, -f for ssh-keygen.
flag = "-F" if "-F" in argv else ("-f" if "-f" in argv else "")
target = argv[argv.index(flag) + 1] if flag else ""

# A real ssh-keygen leaves a key behind, so a shim standing in for it must
# too — otherwise "refuse to overwrite" cannot be told from "did nothing".
if result.get("creates") and target:
    pathlib.Path(target).write_text(result["creates"], encoding="utf-8")

# %F in a scripted stream expands to that same path, so a test can script a
# message quoting the temp file the caller just invented.
sys.stdout.write(result["stdout"].replace("%F", target))
sys.stderr.write(result["stderr"].replace("%F", target))
sys.exit(result["returncode"])
"""


def fixture_bytes(name: str) -> bytes:
    """Raw bytes of a fixture — the round-trip test compares these exactly."""
    return (FIXTURES / name).read_bytes()


def fixture_text(name: str) -> str:
    return fixture_bytes(name).decode("utf-8")


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture(autouse=True)
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A throwaway `$HOME` with an empty `.ssh`, patched into `Path.home()`.

    Autouse on purpose: the developer's real `~/.ssh` must be unreachable from
    the suite even by accident, so isolation is the default rather than
    something a test has to remember to ask for.
    """
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


@dataclass
class FakeBin:
    """A PATH holding only the shims a test installs, and a log of their argv.

    CLAUDE.md §8: nothing in the suite may shell out to a real `ssh` or
    `ssh-keygen`. PATH is emptied, so a command the test did not install
    raises `FileNotFoundError` — which is exactly the "openssh-client is not
    installed" case we need to cover anyway.
    """

    bindir: Path

    def install(
        self,
        name: str,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        creates: str = "",
    ) -> None:
        """Script one answer, replayed for every call.

        `creates` is content the shim writes to the file named after `-f`/`-F`,
        so a fake `ssh-keygen` can leave a key behind like the real one does.
        """
        self.install_sequence(
            name,
            [
                {
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "creates": creates,
                }
            ],
        )

    def install_sequence(self, name: str, results: list[dict[str, object]]) -> None:
        """Script one answer per call; the last one repeats after that.

        `%F` inside `stdout`/`stderr` expands to the argument after `-F`.
        """
        spec = self.bindir / f"{name}.spec.json"
        spec.write_text(json.dumps(results), encoding="utf-8")
        # Re-scripting starts a fresh recording, so call indices always line up
        # with the sequence just installed.
        self._log(name).unlink(missing_ok=True)
        script = self.bindir / name
        script.write_text(
            SHIM.format(
                interpreter=sys.executable,
                spec=str(spec),
                log=str(self._log(name)),
            ),
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IXUSR)

    def calls(self, name: str) -> list[list[str]]:
        """Every invocation's argv, in order. `argv[0]` is the shim's path."""
        log = self._log(name)
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line]

    def args(self, name: str, index: int = 0) -> list[str]:
        """Just the arguments of one call, without argv[0]."""
        return self.calls(name)[index][1:]

    def _log(self, name: str) -> Path:
        return self.bindir / f"{name}.calls.jsonl"


@pytest.fixture
def fake_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeBin:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    monkeypatch.setenv("PATH", str(bindir))
    return FakeBin(bindir)
