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

### M2 — writing

`ConfigFile` went in `store.py` per `BUILD_PLAN.md` M2; `CLAUDE.md` §3 said
`models.py` and has been corrected to match the code.

Five changes against `REF/Sshconfig.py` and `SPEC.md`, in rough order of how
much damage each would have done:

1. **`Path.read_text()` translates CRLF to LF.** The prototype read config
   files in text mode, so a Windows-saved config arrived already normalised:
   `detect_newline()` reported LF, and saving rewrote every line ending in the
   file. Now `read_bytes().decode(...)`, with `newline=""` on both write sites
   for symmetry. Found by `test_a_crlf_include_keeps_its_own_line_endings`,
   which was written to check the store's plumbing and caught a real bug.
2. **`SSH_DIR` and `MAIN_CONFIG` were module-level constants**, so they bound
   `Path.home()` at import time and no test redirect could reach them. They
   are now `ssh_dir()` and `main_config_path()` functions.
3. **`Block` is `@dataclass(eq=False)`.** With generated equality,
   `blocks.remove(block)` and `block in blocks` compare by value — two hosts
   with identical text would make `remove()` delete the wrong one. A block is
   a position in a document, not a value.
4. **`save()` validates every pending file before writing any of them.**
   SPEC §3 validates per file, which lets an early file land on disk and a
   later one be refused, leaving half a save. The spec is amended in the
   file itself.
5. **Backups no longer collide.** `<name>.bak-YYYYMMDD-HHMMSS` is taken twice
   if the user saves twice inside one second, and `copy2` would overwrite the
   first — losing exactly the state they might want back. `backup_path()`
   counts up.

Also: `validate()` raises `ConfigError` rather than returning a message, and
its message is ssh's own output with our temp path rewritten to the word
`config`. It may be empty when ssh says nothing; the UI supplies wording in
that case, because core carries no translated text (D3).

**Mutation gate, again the most useful ten minutes of the milestone.**
"Interleave validate with write" survived *two* rounds of hardening:

- Round 1: the shim could only give one answer, so the first validation failed
  and nothing was written either way. Added `FakeBin.install_sequence`, which
  scripts one result per call.
- Round 2: still green, because re-rendering an unedited block produces
  identical bytes — "the files are unchanged" was true even though a write had
  happened. The assertion with teeth is `list(ssh.glob("*.bak-*")) == []`: a
  backup only exists if we wrote.

Generalising: **assert on the side effect, not on the end state.** An
idempotent write is invisible to a content check.

`make test` → 96 passed. `parvussh/core` coverage 97%.

**Next session starts with.** M3 — the option catalog and the pt-BR keyword
descriptions. Two files move in step: `data/keywords.py` (structure) and
`i18n/pt_br/keywords.py` (text), with a test asserting every catalog entry has
a description so the two cannot drift.
