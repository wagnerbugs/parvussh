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

### M1 — parser

Ported from `REF/Sshconfig.py` with three changes, all driven by round-trip
fidelity:

1. **Line splitting.** The prototype used `str.splitlines()`, which also breaks
   on form feed, vertical tab, U+0085 and U+2028. A config holding any of them
   would have been silently rewritten — half a value turning into a bogus
   keyword. `_split_lines` splits on `\n` only and drops a trailing `\r`.
2. **CRLF.** `detect_newline(text)` reports the file's convention and
   `render_blocks(blocks, newline)` writes it back. A Windows-saved config now
   round-trips byte for byte, and an edited block keeps the file's endings
   instead of introducing mixed ones.
3. **`subtitle()` returns `""`** where the spec had `"sem HostName"` — that
   sentence is interface copy and belongs to `i18n` under D3.

**The mutation gate earned its keep.** Mutation 2 (`render()` ignoring
`dirty`) failed four tests immediately. Mutation 1 (`_split_lines` →
`splitlines()`) **passed the entire suite** — the fixtures had no exotic
whitespace, so the two implementations were indistinguishable. Added
`test_only_newlines_end_a_line`; the mutation then failed five ways. Lesson
for later milestones: run the mutation, do not assume the suite would catch it.

One thing to remember when reading the tests: `fake_home` is **autouse**, so
`Path.home()` is a `tmp_path` in every test whether or not it asks. That is
deliberate — CLAUDE.md §8 forbids touching the developer's real `~/.ssh`, and
opt-in isolation is isolation someone eventually forgets.

Known, accepted normalisation: a file that does not end with a newline gains
one. Pinned by `test_a_missing_final_newline_is_added`.

`make test` → 54 passed. `make lint` → clean.

**Next session starts with.** M2 — `core/writer.py` and `core/store.py`.
Note that `ConfigFile` must carry the `newline` detected at load so `text()`
can write it back; `CLAUDE.md` §3 places `ConfigFile` in `models.py` while
`BUILD_PLAN.md` M2 places it in `store.py` — following the build plan.
