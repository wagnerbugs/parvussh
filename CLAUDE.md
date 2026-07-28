# CLAUDE.md

Working agreement for this repository. Read this before touching anything.

---

## 1. What we are building

**ParvuSsh** — a GTK4/libadwaita desktop app that manages SSH connections by
reading and writing the user's real `~/.ssh/config`. No parallel database, no
proprietary format, no import step.

Two-column layout: connection cards on the left, connection form on the right.

Target user: a developer who runs a handful of VPSs and is tired of opening the
config in a text editor to remember which alias they used. **Not** an infra
specialist. The app teaches the real OpenSSH option names while making them
easy to discover.

Target platform: Ubuntu 26.04, GNOME 50, Wayland, Python 3.14.
Minimum supported: GTK 4.12, libadwaita 1.5, Python 3.11.

### The name, spelled canonically

From *parvus* — small, in Latin. The etymology is the non-goals list in one
word; the README tagline may lean on that.

The joined `u`+`Ssh` is easy to get wrong. These spellings are the only correct
ones, and there are no others:

| Context | Spelling |
|---|---|
| Python package, module paths, imports | `parvussh` |
| Console command, repository name, Makefile targets | `parvussh` |
| Display name — window title, About dialog, README heading, `.desktop` `Name` | `ParvuSsh` |
| Class prefixes | `ParvuSshWindow`, `ParvuSshApp` |
| App ID | `io.github.wagnerbugs.ParvuSsh` |

Never `ParvuSSH`, `Parvussh`, `parvuSsh`, or `Parvu SSH`.

The App ID is settled (`docs/DECISIONS.md` D2). The literal string `OWNER` must
never appear in the tree.

Two file names must match the app ID **exactly**, or GNOME will not bind the
icon to the window under Wayland and a future Flathub submission gets rejected:

```
data/io.github.wagnerbugs.ParvuSsh.desktop
data/io.github.wagnerbugs.ParvuSsh.metainfo.xml
```

The canonical constants live in `parvussh/__init__.py` as `APP_ID` and
`APP_NAME`. Import them; do not retype the strings.

---

## 2. Language policy (strict — do not deviate)

| What | Language |
|---|---|
| Identifiers, function/class/variable names | English |
| Docstrings and code comments | English |
| Commit messages, branch names, PR titles | English |
| `CONTRIBUTING.md`, `docs/**`, code review notes | English |
| Test names and test docstrings | English |
| **Every string the user can see in the app** | **`parvussh/i18n/<locale>/` only** |
| `README.md` (public project page) | Portuguese (pt-BR) |
| `.desktop` / `.metainfo.xml` default values | English, with `[pt_BR]` variants |

Readable text is allowed **only** in:

- `parvussh/i18n/<locale>/**` — every string the interface can show
- `README.md`, `data/*.desktop`, `data/*.metainfo.xml`

That is the whole list. In particular, `parvussh/ui/**` and `parvussh/data/**`
contain **no** readable literals — they call `t("editor.save")`. If you find
yourself typing a sentence anywhere else, the string is in the wrong module.
Move it.

Rationale: contributors from anywhere can read the code; users are Brazilian
developers who deserve their own language in the interface; and a language the
app does not speak yet should cost one new directory, not a refactor.
See `docs/DECISIONS.md` D3.

### Shipped locales

`pt_br` and `en`. `pt_br` is `DEFAULT_LOCALE`: the project's home language, and
the fallback for any key a locale is missing.

The active locale is chosen from the environment the first time a string is
asked for — `LC_ALL`, then `LC_MESSAGES`, then `LANG`, with `PARVUSSH_LANG`
overriding all three. An exact match wins; failing that, the language alone
(`pt_PT` settles for `pt_br`); anything unknown falls back to the default.

```bash
PARVUSSH_LANG=en make run      # read the interface in the other language
```

Adding a language is a sibling directory with the same keys. Four tests hold
the catalogs together: identical key sets, identical `{placeholders}`, no
sentence left in the source language, and every `t("…")` literal in `ui/**`
resolving.

### Using `t()`

```python
from parvussh.i18n import t

t("editor.save")                     # -> "Salvar" / "Save"
t("save.done", path="~/.ssh/config") # -> "Salvo em ~/.ssh/config"
```

Keys are English, dotted, and named after where the string appears
(`sidebar.`, `editor.`, `dialog.`, `test.`, `kw.<Option>.`, `guide.`). A
missing key returns the key itself, so a half-translated build still opens.

---

## 3. Architecture

```
parvussh/
├── core/            pure Python, zero GTK imports — fully unit tested
│   ├── models.py      Entry and Block dataclasses, render_blocks
│   ├── parser.py      text  -> blocks, newline detection
│   ├── writer.py      validation, dated backup, atomic write
│   ├── store.py       ConfigFile + ConfigSet: main config + Include files
│   ├── keys.py        discover keys in ~/.ssh, generate new ones
│   └── tester.py      run ssh non-interactively, interpret the outcome
├── data/            static tables, no logic, no readable text
│   ├── keywords.py    SSH option catalog: name, kind, values, bounds, group
│   └── guide.py       guide section order and icons
├── i18n/            every user-visible string
│   ├── __init__.py    t(), set_locale(), available_locales()
│   └── pt_br/         ui.py, keywords.py, guide.py — the pt-BR catalog
└── ui/              GTK4 + libadwaita only
    ├── app.py         Adw.Application entry point
    ├── window.py      main window, split view, actions, wiring
    ├── sidebar.py     connection list
    ├── editor.py      the form
    ├── rows.py        one widget per option kind
    ├── popovers.py    add-option search, key picker
    ├── dialogs.py     new key, test result
    └── help.py        the help dialog and the guide pages
```

**Hard rule:** `parvussh/core/**`, `parvussh/data/**` and `parvussh/i18n/**`
must never `import gi`. A test enforces this. It keeps the logic testable
without a display and keeps the door open for a future CLI or TUI.

`parvussh/ui/**` must never parse or write config text by hand. It talks to
`core` only through the public API.

Import direction, and nothing against it: `ui → core, data, i18n`;
`data → i18n`; `core → nothing of ours`. `core` stays translation-free —
it returns status codes and raw ssh output, and the UI decides what to say
about them.

### File size

Aim for ~150 lines per module. It is a guideline, not a gate: a coherent
200-line module beats two artificial 100-line halves. But a file that has
grown past ~250 lines is usually two ideas sharing a name — split it.

---

## 4. The `~/.ssh/config` contract

This is the part that earns or destroys the user's trust. Every one of these is
covered by a test; do not weaken any of them to make a feature easier.

1. **A block the user did not edit is written back byte for byte.** Only the
   edited `Host` block is re-rendered.
2. **Comments survive.** Each comment line belongs to the directive immediately
   below it and travels with it.
3. **Unknown directives survive.** An option missing from our catalog is kept
   as a plain text field, never dropped.
4. **Backup before every write** to `<config>.bak-YYYYMMDD-HHMMSS`.
5. **Validate before writing.** Render to a temp file, run
   `ssh -F <temp> -G parvussh-validation.invalid`. On non-zero exit, abort and
   surface the message. Nothing reaches disk.
6. **Atomic write** — temp file in the same directory, `chmod 600`,
   `os.replace`.
7. **Never touch a file we did not read.** `Include` targets are editable only
   because we loaded them; nothing else is written.

---

## 5. Commands

```bash
make setup      # apt deps + venv with --system-site-packages
make test       # pytest, core suite (no display needed)
make test-gui   # pytest -m gui under xvfb-run
make lint       # ruff check + ruff format --check
make run        # python -m parvussh
make check      # lint + test + test-gui — run before every commit
```

System dependencies (documented in README, installed by `make setup`):

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                 openssh-client
```

There are no PyPI runtime dependencies. PyGObject comes from the distro on
purpose — it is the path that works without build pain on a modern GTK stack.
Dev dependencies (`pytest`, `pytest-cov`, `ruff`) live in the `dev` extra.

---

## 6. Code style

- `ruff` for lint and format. Line length 88. Config in `pyproject.toml`.
- Type hints on every public function. `from __future__ import annotations`
  at the top of each module.
- `pathlib.Path` everywhere; no `os.path` string juggling.
- Dataclasses for data, plain functions for transformations, classes only when
  there is real state.
- No `except Exception: pass`. Catch the specific error and either handle it or
  surface it to the user with a sentence that says what to do next.
- Docstrings: one summary line, then the non-obvious detail. Skip the docstring
  when the signature already says everything.

---

## 7. UI copy rules

The interface text is part of the design, not decoration.

- Sentence case, never Title Case. "Criar chave", not "Criar Chave".
- A button says exactly what happens: "Salvar", "Testar", "Criar chave".
  The confirmation echoes the same verb: "Salvo em ~/.ssh/config".
- Errors explain what happened **and** what to do. Never "Erro ao salvar."
  Prefer "O arquivo não foi gravado. O ssh recusou a opção X, então nada foi
  alterado no disco."
- Empty states invite an action, they do not apologize.
- Field labels use the exact OpenSSH option name, with a short gloss when it
  helps: `HostName — endereço real`. The user should be able to search the
  OpenSSH man page for what they see on screen.
- No exclamation marks, no "Ops!", no emoji in the interface.

---

## 8. Testing rules

- `core` is covered first and heavily. New logic in `core` arrives with its
  tests in the same commit.
- Parser tests use golden files in `tests/fixtures/`. A round-trip test asserts
  byte equality for every fixture.
- Anything that touches the real filesystem uses `tmp_path`. **No test may ever
  read or write the developer's actual `~/.ssh`.** A session fixture patches
  `Path.home()`; a test asserts the fixture is active.
- Anything that shells out to `ssh` / `ssh-keygen` is tested with a fake
  binary placed on `PATH` by a fixture, never against a real server.
- GUI tests are marked `@pytest.mark.gui`, run under `xvfb-run`, and are
  skipped with a clear reason when GTK typelibs are missing.
- Target: 90%+ on `parvussh/core`, and every branch of the ssh-output interpreter
  covered by name.

---

## 9. Commits

Conventional Commits, imperative mood, English.

```
feat(core): parse ssh_config preserving comments and layout
fix(ui): keep the sidebar selection after saving a renamed host
test(core): cover connection test interpretation branches
docs: describe the config write contract
chore: configure ruff and pytest
```

One logical change per commit. The test suite passes at every commit — a
reviewer must be able to check out any SHA and run `make check` successfully.
No `WIP`, no `misc fixes`, no commit that only says "update".

---

## 10. Non-goals — the point of the project

Feature requests matching this list get closed with thanks. Keeping the list
short is what keeps the app small.

- Embedded terminal
- Tunnel/port-forward orchestration UI (the options exist in the form; managing
  live sessions is a different product)
- Password vault (that is `ssh-agent` and the system keyring)
- Cloud sync, accounts, telemetry
- SFTP browsing, remote file editing
- A proprietary config format — the format is `ssh_config`, always
- Abstracting SSH away — field labels use real OpenSSH option names on purpose

---

## 11. Working style for this repo

- Follow `BUILD_PLAN.md` milestone by milestone. One milestone, one commit.
- Read `SPEC.md` for the exact behaviour of parser, tester and catalog before
  implementing them. Those specs are precise on purpose.
- Stop at each milestone's verification gate and actually run the commands
  before moving on. Do not batch three milestones into one commit.
- If a spec detail turns out to be wrong or impossible, say so and propose the
  fix instead of silently improvising.