# BUILD_PLAN.md

Ordered milestones. **One milestone, one commit.** At each verification gate,
actually run the commands and read the output before moving on.

Read `CLAUDE.md` for conventions and `SPEC.md` for exact behaviour. When a
milestone says "per SPEC §N", the spec is authoritative — do not improvise the
details it pins down.

Progress markers: change `[ ]` to `[x]` as you finish each milestone, and keep
the file updated in the same commit.

Decisions that changed this plan are recorded in `docs/DECISIONS.md`, and the
running narrative is in `docs/JOURNAL.md`. Read both before picking up work in
a new session.

---

## M0 — Scaffolding

- [x] `git init`, initial branch `main`
- [x] `pyproject.toml`: name `parvussh`, version `0.1.0`, `requires-python
      >=3.11`, `GPL-3.0-or-later` (**D1**, was MIT), no runtime deps, `dev`
  extra with `pytest`, `pytest-cov`, `ruff`; console script
  `parvussh = "parvussh.ui.app:main"`; ruff config with line-length 88;
  pytest config registering the `gui` marker
- [x] `.gitignore` (Python, `__pycache__`, `.venv`, `dist`, `.pytest_cache`,
  `.ruff_cache`, `*.bak-*`)
- [x] `LICENSE` — GPL-3.0-or-later (**D1**)
- [x] `Makefile` with the targets listed in CLAUDE.md §5
- [x] Package skeleton: `parvussh/__init__.py` (with `__version__`, `APP_ID`,
  `APP_NAME`), `parvussh/__main__.py`, `parvussh/core/__init__.py`,
  `parvussh/data/__init__.py`, `parvussh/ui/__init__.py`, `tests/__init__.py`
- [x] `parvussh/i18n/` with a working `t()` and the empty `pt_br` catalogs
  (**D3**)
- [x] `README.md` placeholder (filled in at M14)
- [x] `docs/DECISIONS.md` and `docs/JOURNAL.md`
- [x] `CLAUDE.md`, `BUILD_PLAN.md`, `SPEC.md` already in the repo root;
  amended for D1/D2/D3

**Gate:** `make lint` passes on an empty package.

```
chore: scaffold project layout, tooling and license
```

---

## M1 — Config model and parser

Pure Python. No GTK. Write the tests first — this is the module the whole
project's credibility rests on.

- [ ] `parvussh/core/models.py` — `Entry`, `Block` with `title`, `is_pattern`,
  `get`, `comments_for`, `subtitle`, `render` (SPEC §1, §2)
- [ ] `parvussh/core/parser.py` — `parse_text(text, source) -> list[Block]`
  (SPEC §2)
- [ ] `tests/fixtures/basic.config`, `empty.config`, `messy.config` (SPEC §9)
- [ ] `tests/test_parser.py` — every assertion listed in SPEC §9
- [ ] A parametrised round-trip test over **all** fixtures asserting byte
  equality when nothing is dirty
- [ ] `tests/test_no_gtk.py` — walk `parvussh/core` and `parvussh/data` sources and
  assert none of them contain `import gi` (CLAUDE.md §3)

**Gate:** `make test` green. Deliberately break one assertion, confirm it
fails, restore it — a test suite that cannot fail is not a test suite.

```
feat(core): parse ssh_config preserving comments and layout
```

---

## M2 — Safe writing

- [ ] `parvussh/core/writer.py` — `ConfigError`, `validate(text)`,
  `write_atomic(path, text) -> Path | None` (SPEC §3)
- [ ] `parvussh/core/store.py` — `ConfigFile`, `ConfigSet` with `load`, `hosts`,
  `file_of`, `add_host`, `remove`, `duplicate`, `save`
- [ ] Include resolution with cycle guard (SPEC §2)
- [ ] `tests/conftest.py` — a fixture that redirects `Path.home()` to
  `tmp_path` for the whole session, plus a `fake_bin` fixture that puts a
  scripted `ssh` / `ssh-keygen` shim on `PATH`
- [ ] `tests/test_writer.py`:
  - backup created with the expected name pattern
  - file mode is `0o600` after write
  - validation failure raises `ConfigError` and leaves the original file
  byte-identical on disk
  - missing `ssh` binary skips validation instead of failing
  - `save()` rewrites only dirty files and returns their paths
  - after `save()`, blocks are no longer dirty and a second `save()` is a
  no-op
- [ ] `tests/test_store.py`: Include loading, cycle guard, `add_host`,
  `duplicate`, `remove`

**Gate:** `make test` green. Manually verify the guard: point a test at a real
temp `~/.ssh`, save, and diff the untouched blocks — zero differences.

```
feat(core): write config atomically with backup and ssh -G validation
```

---

## M3 — Option catalog

- [ ] `parvussh/data/keywords.py` — `Keyword`, the 47 entries, `BY_NAME`,
  `GROUPS`, `BASIC`, `get`, `canonical`, `search` (SPEC §4, amended by D3:
  structure only, `description`/`example` are properties reading `t()`)
- [ ] `parvussh/i18n/pt_br/keywords.py` — `kw.<Name>.desc` and
  `kw.<Name>.example` for all 47, transcribed from SPEC §4
- [ ] `tests/test_i18n.py` — `t()` falls back to the key, `set_locale` rejects
  an unknown name, and every catalog entry has a non-empty description
- [ ] `tests/test_keywords.py`:
  - `search("ServerA")` ranks `ServerAliveCountMax` and
  `ServerAliveInterval` first
  - `search("chave")` returns the five auth-related options (the pt-BR
  search test — see SPEC §4)
  - `BASIC` names never appear in results
  - `exclude` removes already-used options
  - every `ENUM` has non-empty `values`; every `INT` has `lo < hi`
  - every `group` is in `GROUPS`

**Gate:** `make test` green.

```
feat(data): add ssh option catalog with pt-BR descriptions
```

---

## M4 — Key discovery and generation

- [ ] `parvussh/core/keys.py` — `SshKey`, `list_keys`, `describe`, `generate`,
  `copy_id_command` (SPEC §5)
- [ ] `tests/test_keys.py` using the fake-bin fixture:
  - `.pub` files, `known_hosts`, `config` are excluded
  - a key with a sibling `.pub` is found; a random text file is not
  - a file whose first bytes contain `PRIVATE KEY` is found without a `.pub`
  - `describe` parses `256 SHA256:xxx comment (ED25519)` into its fields
  - `describe` degrades gracefully when `ssh-keygen` fails
  - `generate` refuses an existing path with the pt-BR message
  - `generate` builds the expected argv for ed25519 and for rsa 4096

**Gate:** `make test` green.

```
feat(core): discover ssh keys and generate new ones
```

---

## M5 — Connection tester

- [ ] `parvussh/core/tester.py` — `TestResult`, `test(alias, config_text)`,
  and a separate pure `interpret(returncode, output) -> TestResult`
  (SPEC §6). Keeping `interpret` pure is what makes the table testable.
- [ ] `tests/test_tester.py` — one test per row of the interpretation table,
  named after the status (`test_interpret_permission_denied_is_success`,
  etc.). Assert `ok` is `True` for exit 0 and for permission-denied, and
  `False` everywhere else.
- [ ] Assert the temp config file is deleted even when the subprocess raises

**Gate:** `make test` green with every table row covered.

```
feat(core): run and interpret non-interactive connection tests
```

---

## M6 — Application shell

First GTK milestone. From here on, `make test-gui` matters.

- [ ] `parvussh/ui/app.py` — `ParvuSshApp(Adw.Application)`, app id from
  `parvussh.APP_ID`, `main()`, about dialog (`Gtk.License.GPL_3_0`)
- [ ] `parvussh/ui/window.py` — window, `Adw.ToastOverlay`,
  `Adw.NavigationSplitView`, both navigation pages, empty `Adw.StatusPage`
  state, window actions (`new`, `save`, `test`, `delete`, `duplicate`,
  `help`, `reload`) with accelerators
- [ ] `tests/conftest.py` — a `gui` fixture that skips cleanly when the GTK
  typelibs are missing, and builds a window against a fake `$HOME`
- [ ] `tests/test_ui_smoke.py` — `@pytest.mark.gui`: the window builds, the
  empty state is visible, every action exists

**Gate:** `make run` opens a window on the user's machine. `make test-gui`
green under `xvfb-run`.

```
feat(ui): add application shell with split-view layout
```

---

## M7 — Sidebar

- [ ] `parvussh/ui/sidebar.py` — search entry, `Gtk.ListBox` with `boxed-list`,
  one `Adw.ActionRow` per host, prefix icons, filter function (SPEC §7)
- [ ] Wire `reload()` and selection to the window
- [ ] GUI test: a fixture config with three hosts produces three rows in order;
  typing in the search box filters down to one; wildcard rows get the
  other icon

**Gate:** the sidebar shows the fixture hosts and filters as you type.

```
feat(ui): list connections in a filterable sidebar
```

---

## M8 — Editor form, basic fields

- [ ] `parvussh/ui/editor.py` — the `Conexão` group with Host / HostName / User /
  Port, the dirty-state guard, header title with `• ` prefix
- [ ] Save path: validation messages, entry rebuild with comment carry-over,
  toast, sidebar refresh keeping the selection (SPEC §7)
- [ ] Unsaved-changes `Adw.AlertDialog` on row switch
- [ ] GUI test: edit `HostName`, save, re-read the file from disk and assert
  the new value is there **and** that a sibling block is unchanged
- [ ] GUI test: empty alias refuses to save and shows the toast

**Gate:** edit, save, reopen — the change is on disk and the rest of the file
is untouched.

```
feat(ui): edit and save the core connection fields
```

---

## M9 — Typed option rows

- [ ] `parvussh/ui/rows.py` — `OptionRow` producing the right widget per kind,
  with a trash suffix button (SPEC §4 table)
- [ ] Unknown options fall back to a `STR` row and survive a save round-trip
- [ ] GUI test per kind: set a value, read it back through `value()`, and
  confirm the rendered config line
- [ ] GUI test: an option not in the catalog is loaded, displayed and saved
  unchanged

**Gate:** a `Host` with `Compression yes`, `ServerAliveInterval 60` and
`StrictHostKeyChecking accept-new` renders as a switch, a spinner and a
dropdown, and saves back identically.

```
feat(ui): render each ssh option with a widget matching its type
```

---

## M10 — Add-option popover

- [ ] `AddOptionPopover` per SPEC §7: search entry, filtered list, Enter picks
  the first match, used options excluded, focus on show
- [ ] GUI test: typing `ServerA` leaves `ServerAliveInterval` in the list;
  activating it adds the row; reopening the popover no longer offers it

**Gate:** type `ServerA`, press Enter, the row appears focused and ready.

```
feat(ui): add options through a searchable popover
```

---

## M11 — Identity picker and key creation

- [ ] Key picker popover on `IdentityFile` rows, rebuilt on every `show`
- [ ] `Gtk.FileDialog` fallback starting at `~/.ssh`, storing the `~/...` form
- [ ] `NewKeyDialog` — name, type, comment, passphrase + confirmation,
  mismatch and empty-name validation, success toast, and it fills the
  originating row
- [ ] GUI test with a fake `ssh-keygen`: creating a key calls the expected
  argv and writes the path back into the row
- [ ] GUI test: mismatched passphrases block creation

**Gate:** create a real key on the developer machine, confirm it appears in the
picker immediately afterwards without restarting the app.

```
feat(ui): pick an existing key or create a new one inline
```

---

## M12 — Test button

- [ ] Worker thread + `GLib.idle_add`, a persistent toast while running
- [ ] Result `Adw.AlertDialog` with the verdict and a collapsed expander
  holding the raw ssh output in a monospace `Gtk.TextView`
- [ ] Wildcard aliases are refused with the pt-BR message
- [ ] GUI test with a fake `ssh` that exits 255 printing `Permission denied`:
  the dialog reports success

**Gate:** point a connection at a real VPS and at a wrong port; both verdicts
read correctly and the UI never freezes.

```
feat(ui): test a connection before saving it
```

---

## M13 — Help, guide, and the remaining actions

- [ ] `parvussh/data/guide.py` — the six section keys in order and
  `ABOUT_CONFIG`; the prose itself goes in `parvussh/i18n/pt_br/guide.py`
  (SPEC §8, amended by D3)
- [ ] `HelpDialog` — `Adw.PreferencesDialog` with the three pages and search
- [ ] `Duplicar` and `Excluir` with confirmation, toasts, sidebar refresh
- [ ] GUI test: the help dialog builds and contains a row per catalog entry
- [ ] GUI test: deleting a host removes the block from the file and leaves the
  others byte-identical

**Gate:** press `?`, search `Server`, find the option and its description.

```
feat(ui): add the help dialog, key guide, duplicate and delete actions
```

---

## M14 — Packaging and documentation

- [ ] `data/io.github.wagnerbugs.ParvuSsh.desktop` — pt-BR `Name`, `Comment`,
  `Keywords`; `Categories=Network;RemoteAccess;Utility;`
- [ ] `data/io.github.wagnerbugs.ParvuSsh.metainfo.xml` — AppStream metadata,
  pt-BR summary and description, `project_license` `GPL-3.0-or-later`
- [ ] An app icon (symbolic SVG is fine for v1)
- [ ] `README.md` in **pt-BR**: what it does, screenshots, the config contract
  (CLAUDE.md §4, stated plainly for users), install instructions, the
  philosophy section, the non-goals list, and the two documented
  limitations (`ssh-keygen` passphrase in `ps`, read-only `Match` blocks)
- [ ] `CONTRIBUTING.md` in **English**: the language policy, how to add a
  catalog option in one line, how to run the tests, and the non-goals list
  restated so nobody wastes an afternoon
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md` with a checkbox: "I have read
  the non-goals list and this request is not on it"
- [ ] `CHANGELOG.md` — Keep a Changelog format, `0.1.0` entry

**Gate:** a fresh clone plus `make setup && make run` works on a clean machine.

```
docs: add readme, contributing guide, changelog and desktop metadata
```

---

## M15 — CI

- [ ] `.github/workflows/ci.yml` — Ubuntu runner, install
  `python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 xvfb openssh-client`, then
  `make lint`, `make test`, `make test-gui`
- [ ] Coverage report on `parvussh/core`, failing under 90%
- [ ] Status badges in the README

**Gate:** CI green on a pull request.

```
ci: run lint, unit tests and gui smoke tests on every push
```

---

## After v0.1.0 — candidates, not commitments

Each of these must be checked against the non-goals list before starting.

- Editable `Match` blocks
- Drag to reorder hosts (order is meaningful: OpenSSH takes the first match)
- gettext, so the interface can exist in other languages
- Flatpak packaging and a Flathub submission
- Reading `~/.ssh/known_hosts` to warn about a host key that has since changed
- A "copiar comando `ssh-copy-id`" button after creating a key

---

## Notes for the implementer

- A working prototype exists in the `REF/` folder handed over with these docs.
  Its comments and identifiers are in Portuguese, which violates the language
  policy — **port the logic, translate everything, and keep the pt-BR strings
  only where CLAUDE.md §2 allows.** Its parser and interpretation table are
  validated and match SPEC exactly; use them as the reference implementation
  rather than reinventing them.
- `REFERENCE_README.md` lists seven prototype files but only five were handed
  over. **`keywords.py`, `keys.py` and `guide.py` are missing** — M3, M4 and
  M13 build them from SPEC §4, §5 and §8 instead of porting.
- `REF/` is scaffolding for the port, not part of the product. Delete it at
  M14, once nothing is left to consult.
- The prototype's module layout is flat. The target layout in CLAUDE.md §3 is
  the one to build.
- GTK 4.14 + libadwaita 1.5 is the floor and the prototype was verified to
  import against it. Do not reach for APIs newer than that without noting the
  bumped requirement in the README.
- If anything in `SPEC.md` proves wrong during implementation, fix the spec in
  the same commit as the code and say so in the commit body.