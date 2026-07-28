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

### M3 — option catalog

`REF/keywords.py` was never handed over, so this was built from SPEC §4. Two
places where the spec contradicts itself, both corrected in `SPEC.md`:

- It says "47 entries" and then lists **50**. All 50 ship.
- It says `search("chave")` must return *exactly* five options, and then
  writes descriptions putting `chave` in **nine**. Nine is the better answer —
  someone searching "chave" wants `StrictHostKeyChecking` and
  `UserKnownHostsFile` too — so the test asserts the five it names are
  present, plus that every result genuinely mentions `chave`.

The split D3 asked for: `data/keywords.py` holds `Keyword(name, kind, values,
lo, hi, group)` and nothing readable; `description` and `example` are
properties resolving `t("kw.<Name>.desc")`. `search()` needed no change,
because it reads the properties. The obvious risk is the two halves drifting —
someone adds a catalog row and forgets the text — so
`test_every_entry_has_a_description` asserts no description comes back looking
like a bare key. Deleting one description fails it, confirmed.

Group headings are keys too (`group.connection` → "Conexão"), so the six
category names are translatable rather than baked into the table.

**Added beyond spec:** `search()` folds accents through NFKD, so `sessao`
finds `sessão` and `conexao` finds `conexão`. Typing without accents is the
norm, and a search that misses them reads as broken, not strict.

`tests/test_i18n.py` carries one test worth knowing about:
`test_every_key_the_ui_asks_for_exists` greps `ui/**` for `t("...")` literals
and fails if any key is missing from the catalog. It finds nothing today
because `ui/` is empty; from M6 on it is the safety net that lets UI code use
`t()` freely.

`make test` → 135 passed.

### M4 — keys

Built from SPEC §5; `REF/keys.py` was never handed over.

Three error types instead of the spec's pt-BR sentence, per D3:
`KeyExistsError` (carries the path, so the UI can name it), `KeyToolMissing`
(no openssh-client — a different message than a failure) and `KeyToolError`
(carries whatever `ssh-keygen` printed).

Added to the skip list beyond the spec: **our own `config.bak-*` files**. They
land in `~/.ssh` right beside the keys, and the spec's suffix list only covers
`.bak`, not `.bak-20260728-174320`. They would not have survived the
`PRIVATE KEY` sniff either, but relying on that is luck rather than intent.

`generate_command()` is split out from `generate()` so the argv can be asserted
without running anything. Worth keeping that shape wherever we build a command
line.

`FakeBin` gained a `creates` field: the shim now writes a file at the path
given after `-f`/`-F`, so a fake `ssh-keygen` behaves like the real one. Before
that, "refuses to overwrite an existing key" and "did nothing at all" looked
identical from the outside, and two tests were quietly asserting the wrong
thing.

### M5 — connection tester

Ported from `REF/Tester.py`. The interpretation table moved into a `SIGNS`
tuple so the order — which is the whole contract — is one readable block
instead of a ladder of `if`s.

Two renames, both forced by pytest's collection rules and both worth having
anyway:

- `test()` → **`run()`**. A module-level `test(...)` gets collected as a test
  case wherever it is imported.
- `test_command()` → **`build_command()`**, for the same reason: pytest tried
  to inject fixtures named `alias` and `config_path`.
- `TestResult` keeps the spec's name but carries `__test__ = False`, or pytest
  warns on every run.

Kept from the prototype and *not* in the spec's table: `"line" in output and
"invalid" in output` also counts as a config error. Different ssh versions
phrase option complaints both ways. It is now covered by a named test rather
than living as an undocumented extra condition.

`TestResult` is `(status, output, returncode)` with `ok` derived from a
`SUCCESSES` set — no titles, no prose (D3). The pt-BR wording arrives at M12
as `t("test.<status>.title")`.

`make test` → 206 passed. `parvussh/core` coverage 97%. **Core is complete.**

### M6 — application shell

**This machine has a live display** (`DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0`),
so GTK tests run here without `xvfb`. `xvfb-run` itself is *not* installed;
`make test-gui` now falls back to the current display and says so, and
`make setup` installs `xvfb`. Preferring xvfb matters: without it, `make
test-gui` flashes windows onto whoever is sitting at the machine.

**How to actually see the UI without a screenshot tool.** There is no `grim`,
`gnome-screenshot` or `import` here. `scratchpad/shoot.py` presents the window,
waits 700 ms, then renders it through `Gtk.WidgetPaintable` → `Gtk.Snapshot`
→ `Gsk.CairoRenderer.render_texture()` → `save_to_png()`. That gives a real
image of the running interface to look at. Keep using it — the first render
immediately caught a bug no test would have:

> The empty state called `header.set_sensitive(False)`, following the
> prototype. An `Adw.HeaderBar` contains the **window controls**, so that also
> disabled minimise, maximise and close. Replaced with
> `action.set_enabled(False)` on the four actions that need a selection —
> every button bound via `action_name` dims by itself, and the header stays
> live. `test_the_header_bar_itself_stays_sensitive` pins it.

The general lesson: `set_sensitive` on a container is almost always too broad.
Disable the action, not the widget.

**Module layout.** `sidebar.py` and `editor.py` exist from M6 even though they
are nearly empty, so M7 and M8 fill in modules rather than carving them out of
a `window.py` that grew to 400 lines first. `window.py` is the coordinator: it
owns the `ConfigSet`, and the two pages own their widgets.

`shorten_home()` lives in `window.py` and turns `/home/x/.ssh/config` into
`~/.ssh/config`. Every path the user sees goes through it.

### M7 — sidebar

Two GTK testing facts that will keep mattering:

1. **A `Gtk.ListBox` filter is applied when the widget is mapped.** The test
   window is deliberately never presented, so every row still reports itself
   visible and asserting on widget visibility proves nothing.
   `Sidebar.visible_rows()` evaluates the predicate directly and says so in its
   docstring; a separate test proves `invalidate_filter()` really is called.
2. **`Gtk.SearchEntry` debounces `search-changed`.** It fires from a timer, so
   nothing happens unless something iterates the main context. Added a
   `pump(until, timeout)` fixture to `tests/conftest.py`. M12 will need it for
   `GLib.idle_add` from the test worker thread.

Rebuilding the list emits `row-selected` as rows come and go, which would load
blocks the user never clicked. `Sidebar._rebuilding` guards it, and
`test_rebuilding_the_list_does_not_load_blocks_nobody_clicked` pins it.

`GLib.markup_escape_text` on the row title is not cosmetic: `Adw.ActionRow`
parses its title as Pango markup, and an alias containing `&` or `<` is legal
in ssh_config.

**Departure from SPEC §1.** A wildcard row's subtitle is "Padrão curinga"
rather than "sem HostName". `Host *` is *supposed* to have no HostName, so
reporting it as missing invents a problem. Visible in `scratchpad/m7.png`.

`pyproject.toml` now filters PyGObject's own deprecation warnings, which were
burying the test output. The filters are module-scoped to `gi.*`, so warnings
from our code still surface.

### M8 — the form and the save path

**The bug the tests caught.** `Editor.apply()` set `block.dirty = True` every
time, so pressing Ctrl+S twice wrote the file twice and left *two* dated
backups. Nobody would notice until `~/.ssh` had forty copies of their config.
`apply()` now compares `patterns` and `entries` first and returns without
touching anything when they match. `save_current()` says "Nada mudou desde o
último salvamento." rather than claiming a save that did not happen.

`Block` is `eq=False` (M2) but `Entry` is a normal dataclass, so
`block.entries == entries` is the value comparison this needs. That is why the
two classes differ, and it is worth keeping that way.

**The carry-over that prevents data loss.** The M8 form shows Host, HostName,
User and Port. `apply()` rebuilds the entry list — so without care, saving a
host would have deleted its `IdentityFile`. Every entry outside `BASIC` is
copied through untouched, and `test_an_option_the_form_does_not_show_yet_survives`
pins it. M9 replaces the carry-over with real option rows; **do not delete
that test when it does** — reword it for uncatalogued options instead.

**A failed save must not strand the user.** When the unsaved-changes dialog's
"Salvar" is refused (empty alias, ssh rejects the config), the list has already
moved the selection. `Sidebar.select_silently()` puts it back without
re-reporting it as a user choice. The prototype left the user looking at a row
whose form was never loaded.

### Rendering the UI without hijacking the session

**What went wrong.** `scratchpad/shoot.py` calls `window.present()`, and on this
machine that means presenting onto the owner's live desktop. One render stole
keyboard focus mid-typing and captured the stray text in the search box —
visible in `scratchpad/m8.png`, which shows "updatre" in the filter and an
empty list because of it.

**The fix, and it needs no new packages.** `gtk4-broadwayd` ships with GTK and
is already installed:

```bash
gtk4-broadwayd :5 &            # a display that is not the user's screen
GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 python scratchpad/shoot.py out.png "$HOME"
```

Windows render into broadway instead of the session. `scratchpad/m8b.png` is
the result. Icons fall back to a different theme under broadway, so judge
layout and text there, not iconography.

The test suite never presents a window, so `make test-gui` was never affected —
this only ever applied to the screenshot script. `xvfb` is still worth
installing for CI.

### M9 — typed option rows

**The idea worth keeping: a typed widget is a promise.** Rendering
`ConnectTimeout` as a `Adw.SpinRow` bounded 0..3600 says "every value this
option can hold, this widget can hold". It is not true — someone's config may
say `99999`, and the spinner would clamp it to 3600 the next time they pressed
Salvar. Same for `Compression maybe` through a `Adw.SwitchRow`, which comes
back as `no`.

`fits_widget(keyword, value)` decides, and a row whose value does not fit falls
back to a plain `Adw.EntryRow` where anything survives. `OptionRow.typed`
records which happened, and `value()` reads whichever widget was actually
built. `ENUM` handles it differently — an unlisted value is appended to the
dropdown model, so it is selectable and never lost.

An empty value always "fits": that is a freshly added option, not something
read out of a file.

A new boolean starts **off**, matching ssh's own default for the options in the
catalog. Starting it on would silently enable something like
`ForwardX11Trusted` for anyone who added it to look at it.

`for_option()` from M3 does the rest: an option missing from the catalog gets a
text row described as "Opção não catalogada, preservada como está." and is
written back untouched.

The M8 carry-over in `Editor.apply()` is gone, replaced by the option rows as
planned. The test that guarded it was **reworded, not deleted** —
`test_an_extra_option_and_its_comment_survive_a_save`.

### M10 — the add-option popover

`ui/popovers.py` is new and M11's key picker shares it.

The `used` set is a **callable**, not a value. What is on the form changes with
every add and remove; a cached copy goes stale with no symptom until the
popover offers something the user already has.

Two of my own test assertions were wrong, both instructive. `search("ServerA")`
also matches `TCPKeepAlive`, because its description says "Diferente de
ServerAlive." on purpose — search covers descriptions, which is the entire
reason they are written in Portuguese. And the popover only rebuilds when it
opens, so a fixture has to call `refresh()` the way `_on_show` does.

### M11 — key picker and key creation

The picker rebuilds on every `show` and caches nothing, because the one case a
cache would break is exactly the one that matters: a key created a minute ago
in the same session.

Picking writes the `~/...` form. An absolute `/home/wagner/.ssh/id_ed25519`
stops working the moment the config is copied to another machine or another
user, which is a thing people do with dotfiles repositories.

The picker is attached only to a **catalogued** `IdentityFile` row. A row that
fell back to plain text under M9's rule keeps its odd value and gets no
picker — offering one would invite overwriting precisely what we preserved.

`Adw.ActionRow` emits `activated` itself. Connecting per row rather than to the
list box's `row-activated` keeps the handler reachable from a test without
synthesising a click. Worth preferring generally.

### M12 — the connection test

A worker thread runs ssh and `GLib.idle_add` delivers the verdict. The
persistent toast matters: ssh can sit for 25 seconds, and a frozen window is
indistinguishable from a crashed one.

`Editor.config_text()` builds the config from the **widgets**, not the block.
Testing what is on screen before saving is the whole feature.

`FakeBin.uninstall()` is new. The `window` fixture has to install a working
`ssh` just to load a config, so the "openssh-client is not installed" case has
to take it back off `PATH` afterwards. That is also why
`test_a_missing_ssh_is_reported` failed the first time — a good reminder that a
fixture's setup is part of the test's premises.

### M13 — help, guide, duplicate, delete

`Duplicar` no longer reuses an alias. The prototype always appended `-copia`,
so duplicating twice gave two blocks with the same alias: legal ssh_config, but
the second is dead text because the first wins every lookup. `free_alias()`
counts up to `-copia-2`.

`delete_current()` opens the confirmation; `remove_block()` does the work. The
split is what lets a test assert the deletion without driving a dialog, and it
keeps "ask" separate from "do".

The guide's markup is verified two ways: tag counts, and actually running
`Pango.parse_markup` over every section. An unclosed `<tt>` would otherwise
render as raw markup in front of the user, and no other test would notice.

`ui/help.py` is its own module rather than more of `dialogs.py`, which was
already at ~175 lines.

**The interface is complete.** M14 (packaging and docs) and M15 (CI) are what
remain, plus the two gates that need a human: pointing `Testar` at a real VPS,
and creating a real key and seeing it appear in the picker.

## 2026-07-28 — Session 2: a real bug, then packaging

### The markup bug, and why nothing caught it

Reported from an actual run: opening a connection with `RemoteCommand cd
/srv/app && bash -l` printed *"Failed to set text ... from markup"* and
rendered nothing.

**Every `Adw.PreferencesRow` parses its title and subtitle as Pango markup by
default**, and so does `Adw.PreferencesGroup`. Almost everything we put in them
is data — a host alias, a user name, an option description, an example command
— and any of those may contain `&` or `<`.

Two things worth carrying:

1. **Order matters.** `Adw.ActionRow(title=...)` parses during *construction*,
   so calling `set_use_markup(False)` afterwards is too late: the warning has
   already fired and the label is already empty. `ui/markup.py` exposes
   `text_row()`, which builds the widget, disables markup, and only then puts
   the text in. Use it for every row.
2. **The sidebar had the wrong half of the fix.** It escaped its *title* by
   hand and left the subtitle — the user's hostname and user name — exposed.
   Escaping is also the wrong tool once markup is off: it would show a literal
   `&amp;`. Rows turn markup off; only `Adw.PreferencesGroup`, which has no
   switch, gets escaped.

**Why the suite missed it.** GTK reports failed markup, missing icons and
broken widget trees on stderr and then carries on. Every gui test stayed green
while the interface was visibly broken. The `gtk` fixture now routes GLib's log
stream into a list via `GLib.log_set_writer_func` and fails any test that
provoked a WARNING, CRITICAL or ERROR. It found a second, smaller thing
immediately: the key-creation tests were closing a dialog nobody had presented.

That guard is probably the most valuable thing added this session. Any GTK
misuse now fails a test instead of scrolling past.

### M14 — packaging

- **Icon.** A key, drawn by hand: `data/icons/hicolor/scalable/apps/` for the
  app icon and `symbolic/apps/` for the 16px monochrome one. The symbolic
  version uses a *stroked* circle for the bow rather than a masked disc — at
  16px a mask leaves the hole one pixel wide and it stops reading as a key.
- **Seeing SVGs.** `Gdk.Texture.new_from_filename` refuses SVG, and so does
  `GdkPixbuf` here. `gi.repository.Rsvg` works and is installed; the render
  helper in the scratchpad uses it to lay several sizes side by side, which is
  how you check an icon actually survives being small.
- **`make install-user`** installs the launcher and icons into
  `~/.local/share` with no `sudo`, and rewrites `Exec=` to point at the
  checkout's venv. `make uninstall-user` undoes it.
- **`tools/screenshot.py`** regenerates the README images. A `Gtk.Popover`
  renders into its own surface, so a `Gtk.WidgetPaintable` of the window never
  sees it — dialogs work, popovers do not. The shots are of a dialog and two
  window states for that reason.
- **`Categories` drops `Utility`**, against the build plan:
  `desktop-file-validate` warns that `Network` and `Utility` are both main
  categories, so the app would appear twice in the menu.
- **`REF/` is gone.** Everything was ported, and git keeps the history.

### Real output from a real server, and the banner that now precedes it

The owner tested against a live VPS. **OpenSSH 10 prints a post-quantum warning
before almost every connection to a server running an older release:**

```
** WARNING: connection is not using a post-quantum key exchange algorithm.
** This session may be vulnerable to "store now, decrypt later" attacks.
** The server may need to be upgraded. See https://openssh.com/pq.html
suporte@203.0.113.10: Permission denied (publickey,password).
```

The client here is OpenSSH_10.2p1. `interpret()` handled it correctly —
`reachable`, "Servidor respondeu" — but the raw output in the expander reads
alarming, and the owner took it for a failure. The verdict wording is doing its
job; the noise in front of it is simply what ssh now says.

**No code change.** The banner is client-side commentary about the *server's*
age, not about whether the connection worked, and the promise in SPEC §6 is to
show ssh's output verbatim. Filtering it would be us deciding which of ssh's
words the user is allowed to see.

**Three tests added**, because this is the first real-world sample the suite
has:

- the exact captured output still reads as `reachable`, banner preserved
- the banner **alone** matches nothing — it contains the words "connection",
  "server" and "session", so any future needle sloppy enough to use one of
  those bare would turn a routine banner into a verdict
- the banner riding along with a genuine `hostkey` or `refused` failure does
  not change the diagnosis

Mutation confirmed: loosening the `refused` needle to a bare `"connection"`
fails three tests, two of them these.

Worth remembering: this banner only appears once crypto has been negotiated, so
its presence is itself evidence the server answered. Not encoded — but if the
interpretation table ever needs a tie-breaker, that is a real signal.

### English translation — D3 paying off

The whole point of `docs/DECISIONS.md` D3 was that a second language should
cost one directory. It did: `parvussh/i18n/en/` with the same keys, and **not
one line of `ui/` or `data/` changed**. Worth remembering the next time a
structural decision looks like over-engineering.

**Locale selection.** `current_locale()` resolves lazily from the environment
the first time a string is asked for, rather than at import. No import-time
side effect, and any entry point — including a future CLI — gets it right
without remembering to call anything. Order: `PARVUSSH_LANG`, then `LC_ALL`,
`LC_MESSAGES`, `LANG`. Exact match wins; failing that the language alone, so
`pt_PT` settles for `pt_br`; anything unknown falls back to `DEFAULT_LOCALE`.

**Four tests hold the catalogs together**, and the interesting one is
`test_no_prose_was_left_in_the_source_language`. My first version flagged 33
keys and was simply wrong: `kw.*.example` holds config *values* —
`~/.ssh/id_ed25519`, `curve25519-sha256`, `8080 localhost:80` — which are
identical in every language, and their being identical proves nothing. The test
now separates prose from values with `is_prose()`, and a second test asserts
the handful of examples that *do* carry language (`LANG=pt_BR.UTF-8` vs
`en_GB.UTF-8`, `vps.exemplo.com` vs `vps.example.com`) really differ.

Also pinned: identical `{placeholders}` across locales. A `{path}` translated
to `{caminho}` would raise `KeyError` at runtime, in front of the user.

**Packaging follows freedesktop now:** unsuffixed values are English,
`Comment[pt_BR]` and `Keywords[pt_BR]` translate them, and the metainfo gained
`<languages>`. A test asserts that block matches `available_locales()`, so
adding a language and forgetting the metadata fails.

`appstreamcli validate` leaves two notes, both fine and neither worth chasing:
`cid-contains-uppercase-letter` (GNOME app ids do use CamelCase — see
`org.gnome.TextEditor`) and `url-not-reachable` (the repository is private, so
an anonymous fetch gets a 404).

### A screenshot that lied, twice

The first English render came out with `iote` typed in the filter box and an
empty connection list — under `xvfb`, on an isolated `:99`. Two consecutive
re-runs were clean, so it was not reproducible, and the earlier `updatre`
incident on the live display had a different cause (focus stealing).

Not chased further, but `tools/screenshot.py` now clears the search box before
capturing. A README image that quietly shows a filtered, empty app is the kind
of wrong that nothing else would catch.

### Known deviation: two files are over the size guideline

`CLAUDE.md` §3 says a file past ~250 lines is usually two ideas sharing a name.
Two are over it:

| File | Lines |
|---|---|
| `ui/window.py` | 322 |
| `ui/editor.py` | 308 |

I looked for a split and did not find an honest one. `window.py` is the
coordinator plus seven action handlers, and pulling `test_current` into its own
module would move one method rather than separate two ideas. `editor.py` is one
form: its widgets, its option rows and its serialisation all reach into the
same set of entries.

Recording this rather than quietly amending the rule to fit the code. If either
file grows again during M14, split it then — the likeliest seam in `window.py`
is the group of connection commands (`new`, `duplicate`, `delete`), and in
`editor.py` the "form to config" pair (`apply` and `config_text`).
