# Contributing

Thanks for looking. This document is short on purpose; the two things worth
reading before you write code are the **language policy** and the **non-goals**.

## Before anything: the non-goals

These will not be added. A pull request implementing one gets closed with
thanks, and it is fairer to say so here than after you have spent an evening on
it.

- Embedded terminal
- Tunnel / port-forward orchestration UI (the options exist in the form;
  managing live sessions is a different product)
- Password vault — that is `ssh-agent` and the system keyring
- Cloud sync, accounts, telemetry
- SFTP browsing, remote file editing
- A proprietary config format — the format is `ssh_config`, always
- Abstracting SSH away: field labels use real OpenSSH option names on purpose

The Latin *parvus* means small. Keeping this list short is what keeps the app
small.

## Language policy

This trips people up, so it is stated plainly:

| What | Language |
|---|---|
| Identifiers, functions, classes, variables | English |
| Docstrings and code comments | English |
| Commit messages, branch names, PR titles | English |
| This file, `docs/**`, code review | English |
| Test names and test docstrings | English |
| **Every string the user can see** | **Portuguese (pt-BR)** |
| `README.md` | Portuguese (pt-BR) |

Portuguese is allowed in exactly two places:

- `parvussh/i18n/pt_br/**`
- `README.md`, `data/*.desktop`, `data/*.metainfo.xml`

Nowhere else. `parvussh/ui/**` and `parvussh/data/**` contain **no** readable
literals — they call `t("editor.save")`. If you find yourself typing Portuguese
into a widget, the string is in the wrong file.

The reasoning: contributors from anywhere can read the code, and users are
Brazilian developers who deserve their own language in the interface. A second
language should cost one new directory under `parvussh/i18n/`, not a refactor.

## Getting set up

```bash
make setup      # apt packages + a venv with --system-site-packages
make check      # lint + unit tests + gui tests. Run this before every commit.
```

`make check` must pass at **every** commit. A reviewer should be able to check
out any SHA and get a green suite.

## Adding an option to the catalog

Two lines, in two files. Structure here:

```python
# parvussh/data/keywords.py
Keyword("ExitOnForwardFailure", BOOL, group=NETWORK),
```

Text here:

```python
# parvussh/i18n/pt_br/keywords.py
"kw.ExitOnForwardFailure.desc": "Encerra a conexão se algum encaminhamento falhar.",
"kw.ExitOnForwardFailure.example": "",   # omit the key entirely if there is none
```

`tests/test_keywords.py` fails if you add the first without the second. Write
the description in the user's words, and where an option exists to prevent a
specific frustration, name that frustration — someone who has hit "too many
authentication failures" should recognise it in `IdentitiesOnly`.

## Architecture, in one rule each

```
parvussh/
├── core/    pure Python. Never imports gi. Never returns a translated string.
├── data/    static tables. No logic, no readable text.
├── i18n/    every user-visible string.
└── ui/      GTK only. Never parses or writes config text by hand.
```

Import direction, and nothing against it: `ui → core, data, i18n`;
`data → i18n`; `core → nothing of ours`. `tests/test_no_gtk.py` enforces the
`gi` half by parsing the AST.

`core` returning status codes rather than sentences is deliberate: the
connection tester hands back `status="reachable"` and the UI decides what to
say. That is what makes the interpretation table testable without asserting on
prose.

## The config contract

`README.md` states it for users; it is also seven tests. Do not weaken any of
them to make a feature easier:

1. A block the user did not edit is written back byte for byte
2. Comments travel with the directive below them
3. Unknown directives survive
4. Backup before every write
5. Validate with `ssh -G` before writing; on refusal nothing reaches disk
6. Atomic write
7. Never write a file we did not read

## Testing rules

- New logic in `core` arrives with its tests in the same commit
- **No test may read or write the developer's real `~/.ssh`.** The `fake_home`
  fixture is autouse, so isolation is the default rather than something you
  have to remember
- Anything shelling out to `ssh` or `ssh-keygen` uses the `fake_bin` fixture,
  never a real binary and never a real server
- GUI tests are marked `@pytest.mark.gui` and skip cleanly when the typelibs
  or a display are missing
- The `gtk` fixture fails a test if GTK logged a WARNING or CRITICAL. GTK
  reports real bugs on stderr and carries on, so without that a test passes
  while the interface is visibly broken — which is exactly how a Pango markup
  bug shipped once
- Target: 90%+ on `parvussh/core`

**Run the mutation.** When you add a guarantee, break it deliberately and
confirm a test fails. Three times during this project a mutation passed a suite
that looked thorough. A test suite that cannot fail is not a test suite.

## Code style

- `ruff` for lint and format, line length 88, configured in `pyproject.toml`
- Type hints on every public function
- `from __future__ import annotations` at the top of each module
- `pathlib.Path`, not `os.path` string juggling
- No `except Exception: pass`. Catch the specific error and either handle it or
  surface it with a sentence that says what to do next
- Aim for ~150 lines per module. It is a guideline: a coherent 200-line module
  beats two artificial halves. Past ~250 lines, look for the seam

## UI copy

The interface text is design, not decoration.

- Sentence case. "Criar chave", never "Criar Chave"
- A button names what happens, and the confirmation echoes the same verb:
  "Salvar" → "Salvo em ~/.ssh/config"
- An error says what happened **and** what to do. Never "Erro ao salvar."
- Empty states invite an action; they do not apologise
- No exclamation marks, no "Ops!", no emoji

## Commits

Conventional Commits, imperative mood, English. One logical change per commit.

```
feat(core): parse ssh_config preserving comments and layout
fix(ui): keep the sidebar selection after saving a renamed host
test(core): cover connection test interpretation branches
docs: describe the config write contract
```

The body is where the reasoning goes — especially when you departed from the
spec, and why.
