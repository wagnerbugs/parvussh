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

- [x] `parvussh/core/models.py` — `Entry`, `Block` with `title`, `is_pattern`,
  `get`, `comments_for`, `subtitle`, `render` (SPEC §1, §2), plus
  `render_blocks(blocks, newline)`
- [x] `parvussh/core/parser.py` — `parse_text(text, source) -> list[Block]`
  and `detect_newline(text)` (SPEC §2)
- [x] `tests/fixtures/basic.config`, `empty.config`, `messy.config` (SPEC §9),
  pinned to their exact bytes by `.gitattributes`
- [x] `tests/test_parser.py` — every assertion listed in SPEC §9
- [x] A parametrised round-trip test over **all** fixtures asserting byte
  equality when nothing is dirty
- [x] `tests/test_no_gtk.py` — walk `parvussh/core`, `parvussh/data` and
  `parvussh/i18n` sources and assert none of them import `gi` (CLAUDE.md §3).
  Parses the AST rather than grepping.
- [x] `tests/conftest.py` — an **autouse** `fake_home` fixture, so no test can
  reach the real `~/.ssh` even by accident, plus `tests/test_safety.py`
  asserting the redirect is live (CLAUDE.md §8; pulled forward from M2)

**Gate:** `make test` green. Deliberately break one assertion, confirm it
fails, restore it — a test suite that cannot fail is not a test suite.

**Gate result.** Two mutations were run. The second (`render()` ignoring
`dirty`) was caught by four tests. **The first was not caught**: swapping
`_split_lines` for `str.splitlines()` left every test green, because
`splitlines()` also breaks on form feed, vertical tab, U+0085 and U+2028 —
bytes no fixture contained. `test_only_newlines_end_a_line` was added to close
the hole, and the mutation then failed five ways. Keep this in mind for the
later milestones: the gate is only worth the mutation you actually run.

```
feat(core): parse ssh_config preserving comments and layout
```

---

## M2 — Safe writing

- [x] `parvussh/core/writer.py` — `ConfigError`, `validate(text)` (raises),
  `ensure_exists(path)`, `backup_path(path)`,
  `write_atomic(path, text) -> Path | None` (SPEC §3)
- [x] `parvussh/core/store.py` — `ConfigFile`, `ConfigSet` with `load`, `hosts`,
  `main_file`, `file_of`, `add_host`, `remove`, `duplicate`, `save`
- [x] Include resolution with cycle guard (SPEC §2)
- [x] `tests/conftest.py` — `fake_bin`, which empties `PATH` and installs
  scripted `ssh` / `ssh-keygen` shims that record their argv and can answer
  differently per call (`install_sequence`). The `Path.home()` redirect landed
  at M1 and is autouse.
- [x] `tests/test_writer.py`:
  - backup created with the expected name pattern
  - file mode is `0o600` after write
  - validation failure raises `ConfigError` and leaves the original file
  byte-identical on disk
  - missing `ssh` binary skips validation instead of failing
  - `save()` rewrites only dirty files and returns their paths
  - after `save()`, blocks are no longer dirty and a second `save()` is a
  no-op
- [x] `tests/test_store.py`: Include loading, cycle guard, `add_host`,
  `duplicate`, `remove`

**Gate:** `make test` green. Manually verify the guard: point a test at a real
temp `~/.ssh`, save, and diff the untouched blocks — zero differences.

**Gate result.** 96 passed, `parvussh/core` at 97%. The guard is pinned by
`test_saving_an_edit_leaves_every_other_block_byte_identical` and
`test_save_writes_only_dirty_files`.

Two mutations, and the first was again not caught on the first try:

- *Interleave validate with write* (SPEC §3 as literally written) passed the
  suite twice over. First because the shim could only give one answer, so the
  very first validation failed and nothing was written either way — fixed by
  adding `install_sequence`. Then **again**, because re-rendering an unchanged
  block produces identical bytes, so "the files are untouched" was true even
  after a write. The assertion that actually bites is "no backup file exists":
  a backup only appears if we wrote.
- *Skip the backup* failed three tests immediately.

```
feat(core): write config atomically with backup and ssh -G validation
```

---

## M3 — Option catalog

- [x] `parvussh/data/keywords.py` — `Keyword`, the **50** entries (SPEC said
  47; its own list holds 50), `BY_NAME`, `GROUPS`, `BASIC`, `get`,
  `for_option`, `canonical`, `search` (SPEC §4, amended by D3: structure only,
  `description`/`example` are properties reading `t()`)
- [x] `parvussh/i18n/pt_br/keywords.py` — `kw.<Name>.desc`, the optional
  `kw.<Name>.example`, and the six `group.<key>` headings
- [x] `tests/test_i18n.py` — `t()` falls back to the key, `set_locale` rejects
  an unknown name, no key is defined twice across the three pt-BR modules, and
  every `t("...")` literal in `ui/**` resolves
- [x] `tests/test_keywords.py`:
  - `search("ServerA")` ranks `ServerAliveCountMax` and
  `ServerAliveInterval` first
  - `search("chave")` finds the five auth-related options SPEC §4 names, and
  every result really does mention `chave` (see the correction below)
  - `BASIC` names never appear in results
  - `exclude` removes already-used options, whatever casing was typed
  - every `ENUM` has non-empty `values`; every `INT` has `lo < hi`
  - every `group` is in `GROUPS`, and every group has entries
  - every catalog entry has a pt-BR description — the guard that stops the
  structural and text catalogs from drifting apart

**Gate:** `make test` green — 135 passed.

**Two corrections to SPEC §4, made in the spec itself:**

1. It said "47 entries" and then listed 50. All 50 ship; the count is pinned
   by a test.
2. It said `search("chave")` must return *exactly* five options. Its own
   descriptions put `chave` in nine — `StrictHostKeyChecking`,
   `UserKnownHostsFile`, `VisualHostKey` and `KexAlgorithms` too. Nine is the
   better answer, so the test asserts the five are present rather than alone.

**Added beyond spec:** search folds accents, so `sessao` finds `sessão`.

**Mutation:** deleting one description from the pt-BR catalog — the exact
mistake D3's two-file split makes possible — failed two tests.

```
feat(data): add ssh option catalog with pt-BR descriptions
```

---

## M4 — Key discovery and generation

- [x] `parvussh/core/keys.py` — `SshKey`, `looks_like_a_key`, `list_keys`,
  `describe`, `generate_command`, `generate`, `copy_id_command`, and the
  `KeyToolError` / `KeyExistsError` / `KeyToolMissing` hierarchy (SPEC §5)
- [x] `tests/test_keys.py` using the fake-bin fixture:
  - `.pub` files, `known_hosts`, `config` are excluded
  - a key with a sibling `.pub` is found; a random text file is not
  - a file whose first bytes contain `PRIVATE KEY` is found without a `.pub`
  - `describe` parses `256 SHA256:xxx comment (ED25519)` into its fields
  - `describe` degrades gracefully when `ssh-keygen` fails, is missing, or
  prints something we have never seen
  - `generate` refuses an existing path — raising `KeyExistsError`, not
  returning a pt-BR sentence (D3)
  - `generate` builds the expected argv for ed25519 and for rsa 4096

**Gate:** `make test` green — 177 passed.

**Added beyond spec:** our own `config.bak-*` files are skipped by name. They
sit right next to the keys and the spec's suffix list does not cover them.

`FakeBin` grew a `creates` field so a fake `ssh-keygen` leaves a key behind
like the real one; without it, "refuses to overwrite" could not be told apart
from "did nothing".

**Mutation:** removing the overwrite guard failed
`test_generate_refuses_an_existing_path`.

```
feat(core): discover ssh keys and generate new ones
```

---

## M5 — Connection tester

- [x] `parvussh/core/tester.py` — `TestResult`, **`run(alias, config_text)`**
  (renamed from `test()`, which pytest collects as a test case wherever it is
  imported), `build_command()`, and a separate pure
  `interpret(returncode, output) -> TestResult` (SPEC §6). Keeping `interpret`
  pure is what makes the table testable.
- [x] `tests/test_tester.py` — one test per row of the interpretation table,
  named after the status (`test_interpret_permission_denied_is_success`,
  etc.). Assert `ok` is `True` for exit 0 and for permission-denied, and
  `False` everywhere else.
- [x] Assert the temp config file is deleted even when the subprocess raises

**Gate:** `make test` green with every table row covered — 206 passed,
`parvussh/core/tester.py` at 100%.

**Kept from the prototype, absent from the spec's table:** `"line"` plus
`"invalid"` in the output also counts as a config error. Different ssh versions
phrase option complaints both ways. Now covered by a named test instead of
living as an undocumented extra condition.

```
feat(core): run and interpret non-interactive connection tests
```

---

## M6 — Application shell

First GTK milestone. From here on, `make test-gui` matters.

- [x] `parvussh/ui/app.py` — `ParvuSshApp(Adw.Application)`, app id from
  `parvussh.APP_ID`, `main()`, about dialog (`Gtk.License.GPL_3_0`)
- [x] `parvussh/ui/window.py` — window, `Adw.ToastOverlay`,
  `Adw.NavigationSplitView`, both navigation pages, empty `Adw.StatusPage`
  state, window actions (`new`, `save`, `test`, `delete`, `duplicate`,
  `help`, `reload`) with accelerators
- [x] `parvussh/ui/sidebar.py` and `parvussh/ui/editor.py` — the two pages as
  their own modules from the start, so M7 and M8 fill them in rather than
  carving them out of a grown `window.py`
- [x] `tests/conftest.py` — a `gtk` fixture that skips cleanly when the
  typelibs or the display are missing, and a `window` fixture building against
  a fake `$HOME`
- [x] `tests/test_ui_smoke.py` — `@pytest.mark.gui`: the window builds, the
  empty state is visible, every action exists

**Gate:** `make run` opens a window on the user's machine. `make test-gui`
green under `xvfb-run`.

**Gate result.** `python -m parvussh` runs until killed, no output. 23 gui
tests pass, 206 headless tests still green.

`xvfb-run` is not installed on this machine, so `make test-gui` now falls back
to the running display instead of failing, and says so. `make setup` installs
`xvfb`.

**Caught by looking at a render of the window:** the empty state disabled the
whole `Adw.HeaderBar`, which also disables minimise, maximise and close. Now
the four actions needing a selection (`save`, `test`, `delete`, `duplicate`)
are disabled instead; every button bound with `action_name` dims by itself and
the window controls keep working.

```
feat(ui): add application shell with split-view layout
```

---

## M7 — Sidebar

- [x] `parvussh/ui/sidebar.py` — search entry, `Gtk.ListBox` with `boxed-list`,
  one `Adw.ActionRow` per host, prefix icons, filter function (SPEC §7)
- [x] Wire `reload()` and selection to the window
- [x] GUI test: a fixture config with three hosts produces three rows in order;
  typing in the search box filters down to one; wildcard rows get the
  other icon

**Gate:** the sidebar shows the fixture hosts and filters as you type — 44 gui
tests pass, and the render in `scratchpad/m7.png` shows all three rows with
their subtitles and icons.

**Two testing facts worth carrying forward:**

1. **GTK applies a list box filter only once the widget is mapped.** The test
   window is never presented, so every row reports itself visible.
   `Sidebar.visible_rows()` therefore evaluates the predicate directly, and a
   separate test proves `invalidate_filter` is actually called.
2. **`Gtk.SearchEntry` debounces `search-changed` behind a timer.** Nothing
   fires unless something iterates the main context. `tests/conftest.py` gained
   a `pump(until, timeout)` fixture for this; M12 needs the same thing for
   `GLib.idle_add`.

**Departure from SPEC §1:** a wildcard row's subtitle is "Padrão curinga", not
"sem HostName". `Host *` is *meant* to have no HostName — reporting it as
missing describes a problem that does not exist.

```
feat(ui): list connections in a filterable sidebar
```

---

## M8 — Editor form, basic fields

- [x] `parvussh/ui/editor.py` — the `Conexão` group with Host / HostName / User /
  Port, the dirty-state guard, header title with `• ` prefix
- [x] Save path: validation messages, entry rebuild with comment carry-over,
  toast, sidebar refresh keeping the selection (SPEC §7)
- [x] Unsaved-changes `Adw.AlertDialog` on row switch, with the selection put
  back when the save is refused
- [x] GUI test: edit `HostName`, save, re-read the file from disk and assert
  the new value is there **and** that a sibling block is unchanged
- [x] GUI test: empty alias refuses to save and shows the toast

**Gate:** edit, save, reopen — the change is on disk and the rest of the file
is untouched. 68 gui tests pass, 206 headless tests green.

**Bug the tests caught:** `Editor.apply()` marked the block dirty unconditionally,
so pressing Ctrl+S twice wrote the file twice and left **two** dated backups.
Over a session that quietly fills `~/.ssh` with copies. `apply()` now compares
patterns and entries first and does nothing when they match; the toast says
"Nada mudou desde o último salvamento."

**Carried over deliberately:** options the form does not render yet
(`IdentityFile` and friends) are copied through untouched by `apply()`.
Rebuilding entries from the visible fields alone would have deleted a host's
key on the first save. M9 replaces that carry-over with real option rows.

```
feat(ui): edit and save the core connection fields
```

---

## M9 — Typed option rows

- [x] `parvussh/ui/rows.py` — `OptionRow` producing the right widget per kind,
  with a trash suffix button (SPEC §4 table)
- [x] Unknown options fall back to a `STR` row and survive a save round-trip
- [x] GUI test per kind: set a value, read it back through `value()`, and
  confirm the rendered config line
- [x] GUI test: an option not in the catalog is loaded, displayed and saved
  unchanged

**Gate:** a `Host` with `Compression yes`, `ServerAliveInterval 60` and
`StrictHostKeyChecking accept-new` renders as a switch, a spinner and a
dropdown, and saves back identically — confirmed in `scratchpad/m9.png`.
101 gui tests pass.

**Added beyond spec, and it matters:** a typed widget is only used when the
*current value fits it*. `fits_widget()` sends `Compression maybe` and
`ConnectTimeout 99999` to a plain text row instead. A `Adw.SpinRow` bounded
0..3600 would have clamped that timeout to 3600 on the next save, and a
`Adw.SwitchRow` would have rewritten `maybe` as `no` — both silently, both in
a file the app promises not to mangle. `ENUM` keeps an unlisted value by
appending it to the dropdown model.

```
feat(ui): render each ssh option with a widget matching its type
```

---

## M10 — Add-option popover

- [x] `AddOptionPopover` per SPEC §7: search entry, filtered list, Enter picks
  the first match, used options excluded, focus on show
- [x] GUI test: typing `ServerA` leaves `ServerAliveInterval` in the list;
  activating it adds the row; reopening the popover no longer offers it

**Gate:** type `ServerA`, press Enter, the row appears focused and ready.

It lives in the new `parvussh/ui/popovers.py`, which M11's key picker shares.
The `used` set is passed as a **callable**: what is on the form changes with
every add and remove, and a cached copy goes stale with no symptom until the
popover offers an option the user already has.

```
feat(ui): add options through a searchable popover
```

---

## M11 — Identity picker and key creation

- [x] Key picker popover on `IdentityFile` rows, rebuilt on every `show`
- [x] `Gtk.FileDialog` fallback starting at `~/.ssh`, storing the `~/...` form
- [x] `NewKeyDialog` — name, type, comment, passphrase + confirmation,
  mismatch and empty-name validation, success toast, and it fills the
  originating row
- [x] GUI test with a fake `ssh-keygen`: creating a key calls the expected
  argv and writes the path back into the row
- [x] GUI test: mismatched passphrases block creation

**Gate:** create a real key on the developer machine, confirm it appears in the
picker immediately afterwards without restarting the app. Covered by
`test_the_picker_is_rebuilt_every_time_it_opens`, which adds a key after the
first open and asserts it appears on the second — **still worth doing by hand
once**, since the test fakes `ssh-keygen`.

The picker is only attached to a *catalogued* `IdentityFile` row. A row that
fell back to plain text (M9) keeps its odd value and gets no picker; offering
one would invite overwriting exactly what we went out of our way to preserve.

```
feat(ui): pick an existing key or create a new one inline
```

---

## M12 — Test button

- [x] Worker thread + `GLib.idle_add`, a persistent toast while running
- [x] Result `Adw.AlertDialog` with the verdict and a collapsed expander
  holding the raw ssh output in a monospace `Gtk.TextView`
- [x] Wildcard aliases are refused with the pt-BR message
- [x] GUI test with a fake `ssh` that exits 255 printing `Permission denied`:
  the dialog reports success

**Gate:** point a connection at a real VPS and at a wrong port; both verdicts
read correctly and the UI never freezes. **Still to be done by hand** — the
suite covers the interpretation and the threading, not a real network.

The config handed to ssh is built from the *widgets*, not from the block, so
what gets tested is what is on screen. Testing before committing anything to
disk is the entire point of the feature.

```
feat(ui): test a connection before saving it
```

---

## M13 — Help, guide, and the remaining actions

- [x] `parvussh/data/guide.py` — the six section keys in order and
  `ABOUT_CONFIG`; the prose itself goes in `parvussh/i18n/pt_br/guide.py`
  (SPEC §8, amended by D3)
- [x] `HelpDialog` — `Adw.PreferencesDialog` with the three pages and search,
  in its own `parvussh/ui/help.py`
- [x] `Duplicar` and `Excluir` with confirmation, toasts, sidebar refresh
- [x] GUI test: the help dialog builds and contains a row per catalog entry
- [x] GUI test: deleting a host removes the block from the file and leaves the
  others byte-identical

**Gate:** press `?`, search `Server`, find the option and its description —
the render in `scratchpad/m13-help.png` shows the three pages with search
enabled. 185 gui tests pass.

**Added beyond spec:** `Duplicar` never reuses an alias. The prototype always
appended `-copia`, so duplicating twice produced two identical aliases — legal
ssh_config, but the second is dead text since the first wins every lookup.
`free_alias()` counts up to `-copia-2`.

The guide's markup is checked twice: balanced tags by string count, and by
actually running `Pango.parse_markup` over every section. An unclosed `<tt>`
would otherwise show raw markup to the user.

```
feat(ui): add the help dialog, key guide, duplicate and delete actions
```

---

## M14 — Packaging and documentation

- [x] `data/io.github.wagnerbugs.ParvuSsh.desktop` — pt-BR `Comment` and
  `Keywords`; `Categories=Network;RemoteAccess;`
- [x] `data/io.github.wagnerbugs.ParvuSsh.metainfo.xml` — AppStream metadata,
  pt-BR summary and description, `project_license` `GPL-3.0-or-later`
- [x] An app icon — a key, in `scalable/` and `symbolic/`. `ui/app.py` adds the
  source tree to the icon search path, so a clone shows the right icon without
  being installed.
- [x] `README.md` in **pt-BR**: what it does, screenshots, the config contract
  (CLAUDE.md §4, stated plainly for users), install instructions, the
  philosophy section, the non-goals list, and the two documented
  limitations (`ssh-keygen` passphrase in `ps`, read-only `Match` blocks)
- [x] `CONTRIBUTING.md` in **English**: the language policy, how to add a
  catalog option, how to run the tests, and the non-goals list restated so
  nobody wastes an afternoon
- [x] `.github/ISSUE_TEMPLATE/feature_request.md` with a checkbox: "I have read
  the non-goals list and this request is not on it"
- [x] `CHANGELOG.md` — Keep a Changelog format, `0.1.0` entry
- [x] `make install-user` / `uninstall-user` — puts the launcher and icons in
  `~/.local/share` with no `sudo`, rewriting `Exec=` to point at the checkout
- [x] `tools/screenshot.py` and `make screenshots`, so the README images can be
  regenerated instead of going stale
- [x] `tests/test_packaging.py` — filenames match `APP_ID`, the metainfo `id`
  and release version agree with the package, the icons parse, and the literal
  `OWNER` appears nowhere
- [x] `REF/` and `REFERENCE_README.md` deleted; everything was ported and git
  keeps the history

**Gate:** a fresh clone plus `make setup && make run` works on a clean machine.
Still to be confirmed on a *second* machine — this one has the toolchain
already.

**Departure from the plan:** `Categories` drops `Utility`.
`desktop-file-validate` warns that `Network` and `Utility` are both main
categories, so the app would appear twice in the menu. `RemoteAccess` is a
subcategory of `Network`, which is the accurate placement.

`appstreamcli validate` passes apart from three `url-not-reachable` warnings —
the GitHub repository does not exist yet. They clear once it does.

```
docs: add readme, contributing guide, changelog and desktop metadata
```

---

## M15 — CI

**Deferred by the owner on 2026-07-28.** Not done, and deliberately not ticked:
the project is for personal use for the next few months, and `make check` runs
locally before every commit. Revisit when someone other than the owner starts
sending changes.

- [ ] `.github/workflows/ci.yml` — Ubuntu runner, install
  `python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 xvfb openssh-client`, then
  `make lint`, `make test`, `make test-gui`
- [ ] Coverage report on `parvussh/core`, failing under 90%
- [ ] Status badges in the README

**Gate:** CI green on a pull request.

Whoever picks this up: everything it needs already exists. `make check` is the
whole pipeline, `make test-gui` falls back gracefully when `xvfb-run` is
missing, and `tests/conftest.py` skips the gui suite cleanly when the typelibs
are absent — so a runner without the gir packages reports skips, not failures.

```
ci: run lint, unit tests and gui smoke tests on every push
```

---

## M16 — `parvussh --list`

**Asked for by the owner on 2026-08-06.** Not in the original plan; checked
against the non-goals list first, and it is on none of them — the format is
still `ssh_config`, nothing is abstracted away, and the flag prints the same
two columns the sidebar shows. The reason it earns its place: as the number of
servers grows, the thing you need most often is to remember the alias, and
opening a window to read five lines is the slow way to do it.

- [x] `parvussh/cli.py` — `argparse`, `--list`/`-l`, `--version`; unrecognised
  arguments are forwarded to GTK, which used to receive `sys.argv` whole
- [x] GTK imported lazily, inside `main`, so the listing runs on a machine with
  no graphical stack. `tests/test_no_gtk.py` forbids the import statically;
  `tests/test_cli.py` proves it in a fresh interpreter via `sys.modules`
- [x] Console script moved to `parvussh.cli:main`; `__main__.py` follows
- [x] `ui/app.py:main` takes an optional `argv`
- [x] `cli.*` keys in both catalogs; the terminal is an interface like any
  other, so no sentence lives in `cli.py` (CLAUDE.md §2)
- [x] A source column, shown only when `Include` brought in more than one file
- [x] `tests/test_cli.py` — columns, wildcard wording, `Match` excluded, the
  empty and missing-config invitations, the unreadable-file error, argument
  forwarding, and that a read never creates the config
- [x] `tests/test_i18n.py` scans `cli.py` for `t("…")` keys too

**Gate:** `make check` green, and `parvussh --list` prints the real config.

```
feat(cli): list the configured connections without opening the window
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