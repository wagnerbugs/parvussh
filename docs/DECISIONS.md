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

---

## D4 — Look native, invest the effort in polish, ship no custom CSS

**Date:** 2026-07-28

**Context.** The owner ranked presentation above performance and asked for
"um ambiente bonito". That could mean a distinctive visual identity or a
faithful, well-finished GNOME app.

**Decision.** Follow `SPEC.md` §7 exactly for structure, and spend the effort
on finish: consistent spacing, the right symbolic icons, empty states that
invite an action, tooltips on every icon-only button. **No custom stylesheet.**

**Consequences.**

- Light and dark themes, the user's accent colour, high-contrast mode and
  font scaling all work for free and keep working. A hand-rolled palette
  breaks the moment someone switches theme, and would be ours to maintain.
- Existing style classes carry the visual weight: `boxed-list`, `flat`,
  `circular`, `suggested-action`, `destructive-action`, `dim-label`, `card`.
  If something needs styling that these cannot express, that is a signal the
  layout is wrong, not that we need CSS.
- Colour never carries meaning alone — the connection test says what happened
  in words, since `SUCCESSES` is two statuses out of ten and a green dot would
  not explain the other eight.
- Revisit only if a specific screen proves genuinely unbuildable within
  libadwaita's vocabulary. Record it here if so.

---

## D5 — In the Flatpak, run the host's `ssh` and take `--filesystem=home`

**Date:** 2026-08-08 · **Answers:** `BUILD_PLAN.md` M17, question 2

**Context.** The Flatpak exists for one reason: the GTK 4.12 floor keeps
Debian stable and Mint users out, and a Flatpak carries its own runtime. It is
a way to reach them, not a way to contain the app.

The app shells out in three places — `writer.validate()` (`ssh -G`),
`tester.run()` (`ssh`), and `keys.py` (`ssh-keygen -l` and `-t`). Two paths
were on the table: bundle `openssh-client` as a manifest module, or reach the
host's binaries through `flatpak-spawn --host`.

**Correction, measured 2026-08-08 and worth having in writing.** This entry
first said there is no openssh inside the sandbox. There is:
`org.gnome.Platform//50` ships `/usr/bin/ssh` and `/usr/bin/ssh-keygen`, at
OpenSSH 10.4p1 against the host's 10.2p1. So there is a third path, and it is
the one you fall into by writing no code at all — the app finds a plausible
`ssh`, everything appears to work, and it is quietly the wrong program. That
makes the seam more necessary rather than less: a bundled module was never
required to reproduce the bundled-module failure modes below.

**Decision.** `flatpak-spawn --host`, with `--talk-name=org.freedesktop.Flatpak`
and **`--filesystem=home`** rather than `--filesystem=~/.ssh`. The sandbox is
a delivery mechanism here, not a security boundary, and the manifest and the
Flathub submission say so in those words rather than implying otherwise.

**Why not bundle openssh.** It is not merely a version-skew risk. Three things
in our own catalog stop working, and none of them fails loudly:

| Catalog option | What a sandboxed `ssh` does |
|---|---|
| `ProxyCommand` (example: `cloudflared access ssh --hostname %h`) | Cannot execute a host binary. The connection test dies for anyone behind a proxy command. |
| `IdentityAgent` (example: `~/.1password/agent.sock`) | An arbitrary socket path is not reachable from inside. |
| `UserKnownHostsFile` outside `~/.ssh` | Not readable. |

The connection test is the feature that proves the app told the truth. A test
that cannot run the user's real `ssh` is worse than no test.

`validate()` is the one place bundling would have been defensible, and it is
worth recording why: **`ssh -F <file> -G <host>` ignores `/etc/ssh/ssh_config`
entirely.** Verified on OpenSSH 10.2p1 — with `-F`, `gssapiauthentication`
flips from `yes` to `no`, `hashknownhosts` from `yes` to `no`, and the system
`SendEnv` entries disappear. So validation is hermetic with respect to the
system config, and a bundled `ssh` would differ from the user's only by
version. That was not enough to carry the other three rows.

**Why `--filesystem=home` and not `--filesystem=~/.ssh`.** Two features break
under the narrower permission, and the second breaks silently:

- `store.included_paths()` honours an absolute `Include` target, so
  `Include ~/work/ssh.conf` works today. Under `~/.ssh` only, the app cannot
  see the file — and would then write the main config as if it did not exist.
- The `IdentityFile` picker writes whatever path the file dialog returns
  (`ui/dialogs.py`, `display_path`). Under a narrow permission, choosing a key
  outside `~/.ssh` goes through the document portal, which returns
  `/run/user/1000/doc/<id>/<name>`. That path works for us and **not for the
  user's `ssh`**, so we would write a line into `~/.ssh/config` that only
  ParvuSsh can read. That is contract rule 1 broken quietly, which is the
  worst way to break it.

The wider permission is not a real widening. Once
`--talk-name=org.freedesktop.Flatpak` is granted, arbitrary host commands can
be run; arguing about `~/.ssh` versus `home` after that protects nothing.
Taking the narrower one would cost two features and buy an appearance.

**Consequences.**

- **Two changes in `core/` before the manifest, or the app opens and fails on
  the first click.** `writer.validate()` and `tester.try_alias()` build their
  temp file with `tempfile.mkstemp()`, which lands in `/tmp` — private to the
  sandbox and invisible to a host `ssh`. They need a directory both sides see:
  `$XDG_RUNTIME_DIR/app/io.github.wagnerbugs.ParvuSsh/`, or `~/.ssh` itself,
  where `write_atomic()` already puts its own temp file.
- `tester.interpret()` decides everything from `ssh`'s exit code.
  `flatpak-spawn` forwards the child's status but has failure codes of its own
  when the portal does not answer. That needs a branch and a test; the
  `fake_bin` fixture already covers this shape.
- **The agent needs no permission at all** — measured 2026-08-08, flatpak
  1.16.6 on `org.gnome.Platform//50`. `SSH_AUTH_SOCK` is passed into the
  sandbox unchanged (`/run/user/1000/gcr/ssh`), and because the command runs
  on the host that path is valid where it is used.
  `flatpak-spawn --host ssh-add -l` listed every key, exit 0, with no
  `--socket=ssh-auth` and no `--env=`. **Do not add `--socket=ssh-auth`**: it
  would bind the agent at a sandbox path and hand the host a path that only
  exists inside, which is the failure this bullet was written to look for.
- **`flatpak-spawn` exits 1 when it cannot start the command**, and forwards
  the child's own status otherwise — 42 comes back 42, 255 comes back 255.
  That matters because `tester.interpret()` reads a status as ssh's verdict.
  1 is safe to claim, because the real `ssh` never returns it in either shape
  we run: `ssh -F … -G host` gives 0 or 255 (a bad option, a missing config
  file and a failed lookup are all 255), and the connection test runs `true`
  on the far side. `host.spawn_failed()` carries this, so a host without
  openssh reads as `NO_SSH` rather than as ssh rejecting the config — which
  would otherwise mean the user could never save.
- `parvussh --list` survives untouched: `parvussh/cli.py` imports no GTK, and
  `pip install` puts the console script in `/app/bin` with no manifest line and
  no permission of its own. What changes is how it is called, so the README
  documents the alias in the Flatpak install section:
  `alias parvussh='flatpak run --command=parvussh io.github.wagnerbugs.ParvuSsh'`
- The Flathub submission needs the justification written before it is asked
  for: this is a configurator for a host tool, in the same category as Builder
  and Boxes, and a copy of `ssh` the user never runs would be configuring
  something that does not exist on their machine.
- No feature of the app is given up. What is given up is the claim of running
  confined — which was never true for a front-end to the host's OpenSSH.
- Revisit if Flatpak ever grows a narrower way to run one named host binary.
  That would let us drop `--talk-name=org.freedesktop.Flatpak` and revisit
  `--filesystem=home` in the same commit, since the argument above for the
  wider path stops holding the moment the wider permission goes.
