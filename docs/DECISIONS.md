# Decisions

One entry per decision that a future contributor would otherwise have to
reverse-engineer from the code. Newest last. Do not delete entries — supersede
them with a new one and link back.

Format: **context** (what forced a choice), **decision**, **consequences**
(including what it costs us).

---

## D1 — License is GPL-3.0-or-later, not MIT

**Date:** 2026-07-28 · **Supersedes:** `BUILD_PLAN.md` M0 as originally written

**Context.** The build plan handed over from the exploration phase specified
MIT. The project owner asked for "a license >= GPLv3" so that the tool stays
free for the people who receive it.

**Decision.** `GPL-3.0-or-later`. The `-or-later` clause is the ">=" the owner
described: downstream users may adopt a future GPL version.

**Consequences.**

- Derivative works must also be GPL. A company cannot ship a closed fork.
- `pyproject.toml` uses the PEP 639 SPDX form, which needs `setuptools>=77`.
- The About dialog must use `Gtk.License.GPL_3_0` (libadwaita has no
  "or later" variant; the `LICENSE` file is authoritative).
- If we ever submit to Flathub, the AppStream `project_license` field is
  `GPL-3.0-or-later`.

---

## D2 — App ID is `io.github.wagnerbugs.ParvuSsh`

**Date:** 2026-07-28

**Context.** `CLAUDE.md` §1 ships an `OWNER` placeholder and forbids committing
the literal string. Two filenames under `data/` must match the App ID exactly
or GNOME will not bind the icon to the window under Wayland.

**Decision.** `io.github.wagnerbugs.ParvuSsh`, from the owner's GitHub account.

**Consequences.** `data/io.github.wagnerbugs.ParvuSsh.desktop` and
`data/io.github.wagnerbugs.ParvuSsh.metainfo.xml` are fixed names. Renaming the
GitHub account later means renaming both files and the ID in one commit, and
existing installs get a new ID.

---

## D3 — User-visible text lives in `parvussh/i18n/`, not in `ui/`

**Date:** 2026-07-28 · **Amends:** `CLAUDE.md` §2 and §3

**Context.** `CLAUDE.md` as handed over allowed pt-BR literals inside
`parvussh/ui/**`, `data/keywords.py` and `data/guide.py`. The owner wants the
app to become multilingual later, and wants source files to stay near ~150
lines. Both pull in the same direction: text does not belong inline.

**Decision.** A `parvussh/i18n/` package owns every user-visible string.

```
parvussh/i18n/
├── __init__.py       t(key, **fmt), set_locale(), available_locales()
└── pt_br/
    ├── __init__.py   merges the three tables into STRINGS
    ├── ui.py         window, sidebar, editor, dialog copy
    ├── keywords.py   kw.<Option>.desc / kw.<Option>.example
    └── guide.py      guide.<section>.title / .body
```

Keys are English and dotted. `ui/**` and `data/**` contain no readable
literals; they call `t("editor.save")`. A new language is a sibling package
with the same keys, and `tests/test_i18n.py` fails if a key is missing.

**Consequences.**

- Adding a catalog option is now two lines, not one: the structural row in
  `data/keywords.py` plus its description in `i18n/pt_br/keywords.py`. This
  weakens the "one-line change" promise in `SPEC.md` §4, deliberately.
- `data/keywords.py` holds no `description` field; `Keyword.description` is a
  property that resolves through `t()`. `search()` keeps working unchanged
  because it reads that property.
- `data/**` may import `parvussh.i18n` (both are pure Python, no GTK). The
  no-`gi` rule from `CLAUDE.md` §3 extends to `i18n/**`.
- **`core/**` becomes translation-free**, which amends `SPEC.md` §5 and §6.
  The spec has `core/tester.py` returning pt-BR `title`/`detail` strings and
  `core/keys.generate()` returning the sentence
  *"Já existe um arquivo em {path}. Escolha outro nome."* Under D3 those are
  interface copy, so `core` returns machine-readable codes instead and the UI
  translates them:

  | Spec | Now |
  |---|---|
  | `TestResult(ok, status, title, detail, output)` | `TestResult(ok, status, output)`; UI reads `t(f"test.{status}.title")` and `t(f"test.{status}.detail")` |
  | `generate()` returns a pt-BR sentence | `generate()` raises `KeyExistsError(path)`; UI reads `t("newkey.error.exists", path=...)` |

  The interpretation table in §6 is otherwise unchanged — the ordering, the
  match strings and the `ok` column all still hold, and it is still one test
  per row. This makes the table testable without asserting on prose, which was
  the point of keeping `interpret()` pure in the first place.
- Rejected: gettext with `_("Salvar")` inline. It is the canonical GNOME path
  and we may still migrate to it before a Flathub submission, but it keeps the
  pt-BR text spread across `ui/**` and adds an `xgettext`/`msgfmt` build step
  for a benefit we do not need while there is one language. Revisit at M14.
