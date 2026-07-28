# Journal

Running log of what happened, in order, so a session can be picked up cold.
One heading per working session. Record what was built, what was verified, what
surprised us, and what the next session should do first.

The authoritative checklist is `BUILD_PLAN.md`; this file is the "why it went
that way" beside it.

---

## 2026-07-28 — Session 1: kickoff and M0

**Starting state.** A repository with `CLAUDE.md`, `SPEC.md`, `BUILD_PLAN.md`,
`REFERENCE_README.md` and a `REF/` folder of prototype code, on a `master`
branch with zero commits.

**Environment measured on this machine** (higher than the documented floor of
GTK 4.12 / libadwaita 1.5 / Python 3.11 — the floor stays as documented, so do
not reach for newer APIs without saying so):

| Component | Version here |
|---|---|
| Python | 3.14.4 |
| GTK | 4.22.4 |
| libadwaita | 1.9.1 |
| `ssh`, `ssh-keygen` | present at `/bin` |
| `xvfb-run` | **missing** — `make setup` now installs `xvfb` |

**Decisions taken.** D1 (GPL-3.0-or-later), D2 (App ID `io.github.wagnerbugs.ParvuSsh`)
and D3 (the `parvussh/i18n/` package). See `docs/DECISIONS.md`.

**Note on `REF/`.** `REFERENCE_README.md` lists seven prototype files. Only five
are present: `Sshconfig.py`, `Tester.py`, `Window.py`, `App.py` and
`Test sshconfig.py`. **`keywords.py`, `keys.py` and `guide.py` were never
handed over** — M3, M4 and M13 build them from `SPEC.md` §4, §5 and §8 rather
than porting. The spec is detailed enough for that; the catalog's 47 entries
are transcribed from §4.

**Reference code read so far.** `REF/Sshconfig.py` matches `SPEC.md` §1–§3
almost exactly and is the basis for M1/M2. `REF/Tester.py` matches §6 with one
difference worth keeping an eye on: its `bad configuration` branch also fires
on `"line" in low and "invalid" in low`, which the spec table omits. Keeping
the prototype's wider condition, and noting it here rather than silently
dropping a case the prototype found useful.

**Built.** M0 scaffolding: `pyproject.toml`, `.gitignore`, `LICENSE` (GPL-3
text copied from `/usr/share/common-licenses/GPL-3`), `Makefile`, the
`core`/`data`/`i18n`/`ui` package skeleton with a working `i18n.t()`, a pt-BR
README placeholder, and this file.

**Next session starts with.** M1 — `core/models.py` and `core/parser.py`, tests
first, fixtures per `SPEC.md` §9.
