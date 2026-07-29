# Changelog

Notable changes to ParvuSsh, in the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
format. Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **English translation.** The interface now ships in `pt_br` and `en`, chosen
  from `LC_ALL` / `LC_MESSAGES` / `LANG`, with `PARVUSSH_LANG` overriding.
  Adding a language is a sibling directory under `parvussh/i18n/` with the same
  keys — no change to `ui/` or `data/`, which was the point of the split.
- `.desktop` and AppStream metadata now follow the freedesktop convention:
  English defaults with `[pt_BR]` variants, and a `<languages>` block.

### Changed

- **New icon.** A tag with a `>` prompt, replacing the key. Naming a machine is
  what the app actually does, and a key is the symbol every password manager
  already owns. `docs/ICONS.md` has the metaphor, the GNOME HIG rules it
  follows and how to check a change.

### Fixed

- Config text is no longer parsed as Pango markup. `RemoteCommand cd /srv/app
  && bash -l` rendered as nothing at all, because every `Adw.PreferencesRow`
  treats its title and subtitle as markup by default.

## [0.1.0] — 2026-07-28

First version. Reads and writes the real `~/.ssh/config`.

### Added

- **Connection list** with a filter over alias, `HostName` and `User`.
  Wildcard blocks are marked separately, since `Host *` is meant to have no
  hostname rather than be missing one.
- **Connection form** using the real OpenSSH option names, with a pt-BR gloss,
  so what is on screen can be looked up in `man ssh_config`.
- **Catalog of 50 options**, searchable by name or by what they do. Search
  folds accents, so `sessao` finds `sessão`.
- **One widget per option kind** — switch, spinner, dropdown, text — chosen
  only when the current value actually fits it. `ConnectTimeout 99999` and
  `Compression maybe` stay as plain text rather than being silently clamped or
  rewritten on the next save.
- **Key discovery and creation.** Pick a key from `~/.ssh` or create an
  `ed25519`, `ecdsa` or `rsa` one without leaving the app. The picker rebuilds
  every time it opens, so a key made a minute ago appears without a restart.
- **Connection test before saving**, run against the form's current state on a
  worker thread. Reaching the authentication prompt counts as success: it
  proves address, port, user and network are right, which is what the person
  pressing the button wanted to know.
- **Help dialog** (`F1`) with the searchable catalog, a six-step key guide, and
  a page on how `ssh_config` resolves options — including that the **first**
  definition wins, not the last.
- **Duplicate and delete**, with confirmation. Duplicating twice never reuses
  an alias, because the second block would be dead text.
- `.desktop` file and icons, installable per user with `make install-user`.

### The config contract

Each of these is covered by a test:

- A block the user did not edit is written back byte for byte
- Comments travel with the directive below them
- Options missing from the catalog are kept, not dropped
- A dated backup before every write, never deleted by the app
- `ssh -G` validates before anything reaches disk; on refusal nothing is
  written and ssh's own message is shown
- Atomic write: temp file in the same directory, `chmod 600`, `os.replace`
- Only files that were read are ever written

### Known limitations

- The passphrase is passed to `ssh-keygen` as a command-line argument, so it is
  briefly visible in `ps` to other users of the same machine
- `Match` blocks are loaded and preserved byte for byte, but are read-only in
  the interface

[Unreleased]: https://github.com/wagnerbugs/parvussh/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/wagnerbugs/parvussh/releases/tag/v0.1.0
