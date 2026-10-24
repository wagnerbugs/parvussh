"""Window, sidebar, editor, dialog and command line copy (English).

Same house style as the pt-BR catalog:

- Sentence case. "Create key", never "Create Key".
- A button names the action it performs, and the confirmation echoes the same
  verb: "Save" -> "Saved to ~/.ssh/config".
- An error says what happened **and** what to do next. Never "Save failed."
- Empty states invite an action; they do not apologise.
- Field labels use the real OpenSSH option name, so the user can search the
  man page for what they see on screen.
- No exclamation marks, no "Oops!", no emoji.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    # -- application ------------------------------------------------------
    "app.name": "ParvuSsh",
    "app.comments": "Manages ~/.ssh/config without hiding ~/.ssh/config.",
    "app.developer": "wagnerbugs",
    # -- command line -----------------------------------------------------
    "cli.description": (
        "Manages the connections in ~/.ssh/config. With no arguments, opens the window."
    ),
    "cli.list_help": "list the connections in ~/.ssh/config and exit",
    "cli.no_hostname": "no HostName",
    "cli.wildcard": "wildcard pattern",
    "cli.no_config": (
        "There is no {path} yet. Open ParvuSsh to add the first connection."
    ),
    "cli.empty": "No connections in {path}. Open ParvuSsh to add the first one.",
    "cli.error.load": (
        "{path} could not be read: {detail}. Check the file's permissions."
    ),
    # -- menus ------------------------------------------------------------
    "menu.help": "Help and tips",
    "menu.reload": "Reload from disk",
    "menu.about": "About ParvuSsh",
    "menu.preferences": "Preferences",
    "menu.duplicate": "Duplicate",
    "menu.delete": "Delete",
    # -- sidebar ----------------------------------------------------------
    "sidebar.title": "Connections",
    "sidebar.new_tooltip": "New connection (Ctrl+N)",
    "sidebar.menu_tooltip": "Menu",
    "sidebar.filter_placeholder": "Filter connections…",
    "sidebar.no_hostname": "no HostName",
    "sidebar.wildcard_subtitle": "Wildcard pattern",
    "sidebar.wildcard_tooltip": (
        "Wildcard block: applies to every connection matching the pattern."
    ),
    "sidebar.empty": "No connections yet. Use + to add the first one.",
    "sidebar.no_matches": "Nothing found for “{query}”.",
    # -- editor -----------------------------------------------------------
    "editor.title": "Connection",
    "editor.save": "Save",
    "editor.test": "Test",
    "editor.test_tooltip": "Try to connect without saving",
    "editor.connect": "Connect",
    "editor.connect_tooltip": (
        "Open a terminal running ssh with this alias. Choose the terminal in "
        "Preferences."
    ),
    "editor.more_tooltip": "More actions",
    "editor.help_tooltip": "What each option does",
    "editor.empty.title": "Choose a connection",
    "editor.empty.description": "Or use + to add your first one.",
    "editor.group.connection": "Connection",
    "editor.group.connection_description": (
        "Leave out what you do not need: empty fields never reach the file."
    ),
    # Labels carry the real OpenSSH option name so the user can look it up.
    "editor.field.host": "Host — the alias you type",
    "editor.field.hostname": "HostName — the real address",
    "editor.field.user": "User",
    "editor.field.port": "Port",
    "editor.group.extras": "More options",
    "editor.group.extras_empty": "No extra options. Use + to search by name.",
    "editor.error.empty_alias": "The alias in Host cannot be empty.",
    "editor.error.port_not_a_number": "Port takes numbers only.",
    # -- saving -----------------------------------------------------------
    "new.alias": "new-connection",
    "save.done": "Saved to {path}",
    "save.nothing_changed": "Nothing has changed since the last save.",
    "save.failed.heading": "The file was not written",
    "save.failed.body": (
        "ssh refused the configuration, so nothing on disk was changed."
    ),
    "conflict.heading": "{path} changed since it was opened",
    "conflict.body": (
        "Another program changed the file in the same place you edited, so "
        "nothing was written. The list now shows {path} as it is on disk: "
        "check it and make your edit again."
    ),
    "backups.left": (
        "The old copies are still in {folder}: the trash refused them. The "
        "app tries again on the next save."
    ),
    "unsaved.heading": "Unsaved changes",
    "unsaved.body": "“{alias}” has changes that are not in the file yet.",
    "unsaved.discard": "Discard",
    # -- add-option popover -----------------------------------------------
    "addoption.tooltip": "Add option",
    "addoption.placeholder": "Type: ServerAlive…",
    "addoption.no_matches": "No option by that name.",
    # -- key picker -------------------------------------------------------
    "keypicker.tooltip": "Choose a key from ~/.ssh",
    "keypicker.empty": "No keys in ~/.ssh yet.",
    "keypicker.create": "Create key…",
    "keypicker.browse": "Browse for a file…",
    "keypicker.summary": "{kind} · {bits} bits · {comment}",
    "keypicker.summary_no_comment": "{kind} · {bits} bits",
    "keypicker.undescribed": "Could not read the details of this key.",
    "filepicker.tooltip": "Browse for a file",
    "filepicker.title": "Choose {name}",
    # -- new key dialog ---------------------------------------------------
    "newkey.title": "Create key",
    "newkey.create": "Create key",
    "newkey.default_name": "id_ed25519_new",
    "newkey.field.name": "File name",
    "newkey.field.kind": "Type",
    "newkey.field.kind_subtitle": "ed25519 is the recommended choice",
    "newkey.field.comment": "Comment",
    "newkey.field.passphrase": "Key passphrase",
    "newkey.field.confirm": "Repeat the passphrase",
    "newkey.note": (
        "The key is written to ~/.ssh. Leaving the passphrase blank creates an "
        "unprotected key."
    ),
    "newkey.created": "Key created at {path}",
    "newkey.failed.heading": "The key was not created",
    "newkey.error.empty_name": "Give the key file a name.",
    "newkey.error.mismatch": "The two passphrases do not match.",
    "newkey.error.exists": "There is already a file at {path}. Pick another name.",
    "newkey.error.no_tool": (
        "ssh-keygen was not found. Install the openssh-client package."
    ),
    # -- connection test --------------------------------------------------
    # One title/detail pair per status in parvussh/core/tester.py. Core hands
    # back a code; the wording is here.
    "test.running": "Testing {alias}…",
    "test.output_label": "ssh output",
    "test.error.no_alias": "Enter the alias before testing.",
    "test.error.wildcard": "Wildcard blocks cannot be tested directly.",
    "test.auth.title": "Connected",
    "test.auth.detail": "Logged in with the configured key. Ready to use.",
    "test.reachable.title": "The server answered",
    "test.reachable.detail": (
        "Address, port and user are valid: the server got as far as asking for "
        "authentication. Only the password or the key was missing, and the "
        "test does not send either."
    ),
    "test.dns.title": "Name not found",
    "test.dns.detail": (
        "The address in HostName could not be resolved. Check the domain for a typo."
    ),
    "test.refused.title": "Connection refused",
    "test.refused.detail": (
        "The machine answered, but nothing is listening on that port. Check the "
        "Port value and whether sshd is running."
    ),
    "test.timeout.title": "The server did not answer",
    "test.timeout.detail": (
        "No response within the time limit. Usually a firewall, the wrong IP, "
        "or a machine that is switched off."
    ),
    "test.network.title": "Network unreachable",
    "test.network.detail": (
        "There is no route to that address from here. Check your network, or "
        "whether you need a VPN."
    ),
    "test.hostkey.title": "The server's identity changed",
    "test.hostkey.detail": (
        "The host key does not match the one stored in known_hosts. It may be a "
        "reinstalled server — or somebody in the middle. Make sure before you "
        "remove the old line."
    ),
    "test.config.title": "Invalid configuration",
    "test.config.detail": (
        "ssh refused one of the options. The output below says which."
    ),
    "test.no-ssh.title": "ssh not found",
    "test.no-ssh.detail": "Install the openssh-client package to use the test.",
    "test.unknown.title": "The test could not finish",
    "test.unknown.detail": ("ssh exited with code {code}. The full output is below."),
    # -- help dialog ------------------------------------------------------
    "help.title": "Help",
    "help.page.options": "Options",
    "help.page.keys": "Keys",
    "help.page.about": "How it works",
    "help.with_example": "{description}\nExample: {example}",
    "help.with_values": "{description}\nValues: {values}",
    # -- duplicate and delete ---------------------------------------------
    "duplicate.alias": "{alias}-copy",
    "duplicate.alias_numbered": "{alias}-copy-{number}",
    "duplicate.done": "Connection duplicated. Adjust the alias and save.",
    "delete.heading": "Delete “{alias}”?",
    "delete.body": (
        "The block leaves the file as soon as you confirm. A copy of the "
        "previous config stays in the same folder, dated."
    ),
    "delete.done": "Connection deleted.",
    # -- connecting -------------------------------------------------------
    # Statuses from parvussh/core/terminal.py. `connect.notice` is printed
    # inside the terminal itself, under ssh's own message.
    "connect.running": "Opening a terminal for {alias}…",
    "connect.error.unsaved": (
        "Save before connecting: the terminal reads the file, and this change "
        "is not in it yet."
    ),
    "connect.error.wildcard": (
        "A wildcard block applies to several servers, so there is no single "
        "one to connect to."
    ),
    "connect.notice": (
        "The connection failed or dropped, and ssh said why just above. The "
        "Test button in ParvuSsh explains the error. Press Enter to close."
    ),
    "connect.no_terminal.heading": "No terminal found",
    "connect.no_terminal.body": (
        "None of these is installed: {names}. Choose yours in Preferences, or "
        "run ssh {alias} in the terminal you already use."
    ),
    "connect.failed.heading": "The terminal did not open",
    "connect.failed.body": (
        "{terminal} exited right after starting, with code {code}. If you chose "
        "it in Preferences, check whether it needs an argument before the "
        "command, such as -e. Meanwhile, run ssh {alias} in a terminal."
    ),
    "connect.missing.heading": "The chosen terminal was not found",
    "connect.missing.body": (
        "{name} is not installed, or its path changed. Fix it in Preferences, or "
        "clear the field to use the system's default terminal."
    ),
    # -- preferences ------------------------------------------------------
    "prefs.title": "Preferences",
    "prefs.terminal.title": "Terminal",
    "prefs.terminal.description": (
        "The program the Connect button opens. Leave it empty for the system "
        "default, or write the path to another: /usr/bin/xterm. If it needs an "
        "argument before the command, include it: alacritty -e."
    ),
    "prefs.terminal.command": "Terminal command",
    "prefs.terminal.in_use": "In use",
    "prefs.terminal.checking": "Looking…",
    "prefs.terminal.automatic": "{name}, the system default",
    "prefs.terminal.custom": "{name}, your choice",
    "prefs.terminal.missing": (
        "{name} was not found. Check the path, or clear the field to use the "
        "system default."
    ),
    "prefs.terminal.none": (
        "No known terminal is installed. Write the path to yours above."
    ),
    "prefs.backups.title": "Backups",
    "prefs.backups.description": (
        "Before every write, the app leaves a copy beside the file, such as "
        "config.bak-20261024-131455. The newest stay; older ones go to the "
        "trash. This also applies to files pulled in by Include. Copies other "
        "programs make under the same name pattern count together with these."
    ),
    "prefs.backups.keep": "Copies of ~/.ssh/config to keep",
    "prefs.error.save": "The preference was not written to {path}: {detail}",
    # -- option rows ------------------------------------------------------
    "rows.remove_tooltip": "Remove {name}",
    "rows.hint_with_example": "{description}  e.g. {example}",
    # -- dialogs ----------------------------------------------------------
    "dialog.understood": "Got it",
    "dialog.close": "Close",
    "dialog.cancel": "Cancel",
    # -- errors -----------------------------------------------------------
    "error.read_config": "Could not read ~/.ssh/config",
}
