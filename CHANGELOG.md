# Changelog

Notable changes to ParvuSsh, in the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
format. Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- In the help guide, every command sits in a block of its own, set apart from
  the text, with a copy button on each line. One button per line, not per
  block: in "test the config, then reload", the second command should only
  run if the first passed. What is copied is the command as typed, `&&` and
  all, and a short notice says it was copied.
- The connection list can be sorted by name, from the sidebar menu under
  **Ordenar**: case does not matter, `vps2` comes before `vps10`, and wildcard
  blocks such as `Host *` stay at the end. **Ordem do arquivo**, the order ssh
  reads, is still the default. Only the list moves — the file is never
  rewritten for this, the connection on screen stays open, and an unsaved edit
  stays unsaved. The choice is kept in `settings.ini`.
- Only the newest 3 backups of each config file stay beside it; older ones go
  to the trash, from where they can be restored, and none is ever deleted
  outright. Newest is read from the date in the name. Only names that match
  `<file>.bak-YYYYMMDD-HHMMSS`, optionally followed by `-2`, `-3` …, are
  counted: a copy made by hand under any other name is never touched. If the
  trash refuses, the save still stands and a toast says the old copies stayed.
  The number is set in Preferences, under **Cópias de segurança**, and is
  never less than one.
- The connection list follows the file. When another program writes
  `~/.ssh/config` or a file it includes, and nothing is waiting to be saved,
  the list reloads by itself and the connection on screen stays open. An
  unsaved edit is never dropped for this; the save replays it on top.
- **Acessar** opens your own terminal on `ssh <alias>`, reading the saved
  `~/.ssh/config`. The terminal is `xdg-terminal-exec` when installed — the
  one the desktop says you chose — and otherwise the first of Ptyxis, GNOME
  Terminal, Console, Konsole, Xfce Terminal, `x-terminal-emulator` and xterm.
  When ssh cannot connect, the window stays open on its message until Enter
  instead of closing with it. Unsaved edits are refused with a toast, since
  the terminal would not see them. In the Flatpak the terminal opens on the
  host, like ssh itself.
- **Preferences** (`Ctrl+,`, or the sidebar menu) choose the terminal Acessar
  opens: a path such as `/usr/bin/xterm`, or a full command such as
  `alacritty -e` for a terminal that needs an argument first. Empty keeps the
  system's own. The dialog says which terminal is in use right now — Ptyxis,
  not the `xdg-terminal-exec` that picked it — and a chosen terminal that is
  not installed is reported rather than quietly replaced. The choice lives in
  `~/.config/parvussh/settings.ini`, the only file the app keeps of its own.
- `parvussh --list` prints one line per connection — alias and
  `user@host:port` — and exits, for recalling an alias without opening the
  window. It imports no GTK, so it also works over ssh on a machine with no
  graphical stack, and it never creates or writes anything.
- `tools/check_stack.py` reports whether a machine can run ParvuSsh, and prints
  the install command for the package manager it finds — `apt`, `pacman` or
  `dnf` — when something is missing. It never runs a command itself. A GTK or
  libadwaita older than the stated minimum is now a sentence that says so
  instead of a traceback.
- `make install-user PARVUSSH_LANG=en` pins the interface language into the
  launcher, for reading the app in one language without changing the whole
  system. Without the argument it follows the system locale, as before. A
  language that is not shipped is refused, listing the ones that are.

### Changed

- Backups are always `0600`. They were made with `copy2`, which copies the
  config's own permissions, so a config readable by others left behind copies
  readable by others too. They are now created with `O_EXCL` as well: another
  program writing the same file names its copies the same way, and checking
  for a free name before copying left a gap in which one copy could overwrite
  the other.
- `make setup` no longer installs system packages and no longer calls `sudo`.
  It assumed `apt`, which made it fail on the first line on any distribution
  that does not have it. It now checks the machine and creates the venv; the
  system stack is installed with the command `tools/check_stack.py` prints.
- `PasswordAuthentication`, `KbdInteractiveAuthentication` and
  `PubkeyAuthentication` described the server's behaviour, which is what those
  same three options mean in `sshd_config`. Nothing ParvuSsh writes reaches the
  server, so the descriptions now say what the client does — turning
  `PasswordAuthentication` off makes the connection fail rather than closing
  password login on the server.
- Option descriptions across the catalog now say the default where one exists,
  and name what the option costs instead of warning to use it with care:
  `ForwardAgent` says root on the far end can use the forwarded keys,
  `EscapeChar` says `~.` ends a frozen session, and `Compression` says it hurts
  on a fast link. The `Port` example is `2222`, since the description now
  states that 22 is the default.
- The key guide now says which machine each command runs on, keeps the account
  password and the key's passphrase apart by name, and covers what a VPS
  actually does to people: the files in `/etc/ssh/sshd_config.d/` that are read
  before `sshd_config` and silently cancel a `PasswordAuthentication no`,
  `sshd -t` before reloading, `sshd -T` to see what took effect, the provider's
  panel console as the way back in, and `Too many authentication failures`
  named where someone arrives holding it. Section 2 ends by asking you to
  confirm the key works before section 4 closes the password door.

- `parvussh/core/host.py` is the one place that knows whether the app is
  running inside a sandbox. `writer.py`, `tester.py` and `keys.py` now ask it
  for the argv to run and for a temp file the host can read, which is what a
  Flatpak build will need. Outside a Flatpak nothing changes except where the
  validation and connection-test temp files live:
  `~/.ssh` instead of the system temp directory, still `0600`, and now
  dot-prefixed so a stray `Include *` cannot pick one up.

- A Flatpak manifest, `io.github.wagnerbugs.ParvuSsh.yaml`, against
  `org.gnome.Platform//51`. It is what reaches the Debian and Mint users the
  GTK 4.12 floor keeps out: the runtime travels with the app, so the host's
  GTK stops mattering. `make flatpak` builds and installs it, `make
  flatpak-run` opens it, `make flatpak-uninstall` removes it and the build
  directories. The `ssh` it runs is still the user's own, through
  `flatpak-spawn --host` — verified inside the built sandbox, where the app
  reaches OpenSSH 10.2p1 from the host while the runtime's own copy is
  10.6p1. Every permission is argued in the manifest where it is declared,
  including the two that are deliberately absent.

- A numeric row no longer prints the example the selector beside it is already
  showing. `ServerAliveInterval` read "ex.: 60" two centimetres from a spinner
  displaying 60. The example still appears where nothing on screen carries it:
  the text rows and the help page.

### Fixed

- Saving no longer undoes a change another program made to the file while
  the app was open. The loaded copy of every block used to be written back
  as it was read, so a script that moved a server to `Port 1310` lost that
  change the next time any connection was saved. The file is now read again
  before each save and, when it changed, the edit is replayed on top of it.
  When both touched the same connection, nothing is written and the app asks
  for the edit again over the file as it is now.
- The guide's markup was only ever checked in Portuguese: both tests read the
  sections through the active locale, and the suite never left `pt_br`. They
  now walk every shipped language, so an unclosed `<tt>` in the English guide
  fails the suite instead of reaching a reader as raw markup.

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
- **Portuguese and English**, picked from `LC_ALL` / `LC_MESSAGES` / `LANG`,
  with `PARVUSSH_LANG` overriding. Adding a language is a sibling directory
  under `parvussh/i18n/` with the same keys, and nothing else.
- `.desktop` file, AppStream metadata and icons, installable per user with
  `make install-user`. The icon is a tag carrying a `>` prompt — naming a
  machine is what the app does, and a key is the symbol every password manager
  already owns. See `docs/ICONS.md`.

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
