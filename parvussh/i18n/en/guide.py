"""The key-setup guide and the "how it works" text (English).

Keys are `guide.<section>.title` and `guide.<section>.body`, matching
`parvussh/data/guide.py`. Bodies are Pango markup: `<tt>` around commands and
file names, `<b>` for the one rule worth emphasising, nothing else. Any
literal `&` or `<` must be escaped.

The audience is a developer who runs a couple of VPSs and has never been told
*why* any of this is the way it is. Each section says what to do, and then the
one thing that usually goes wrong. Two habits come from that audience: say
which machine a command runs on, and keep the account password and the key's
passphrase clearly apart.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "guide.create.title": "1. Create the key (on your own machine)",
    "guide.create.body": (
        "An SSH key is a pair of files, created on your own computer — never "
        "on the server. The private one (<tt>~/.ssh/id_ed25519</tt>) never "
        "leaves it. The public one (<tt>~/.ssh/id_ed25519.pub</tt>) is what "
        "you install on servers — it can be copied around freely.\n\n"
        '<tt>ssh-keygen -t ed25519 -C "your-name@laptop"</tt>\n\n'
        "The <tt>ed25519</tt> type is the current choice: short, fast and "
        "strong. Use <tt>rsa</tt> with 4096 bits only when the server is too "
        "old to accept ed25519.\n\n"
        "Put a passphrase on the key. Note the word: this is the key's "
        "passphrase, it stays on your computer, and it has nothing to do with "
        "the account password on the server. It protects the file if your "
        "laptop is lost, and the agent (section 5) means you type it once per "
        "session rather than once per connection."
    ),
    "guide.install.title": "2. Install the key on the server",
    "guide.install.body": (
        "The command below runs on your own machine, not on the server — it "
        "is what carries the key over.\n\n"
        "<tt>ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server</tt>\n\n"
        "It asks for the account password one last time and appends your "
        "public key to <tt>~/.ssh/authorized_keys</tt> on the server.\n\n"
        "If the server's SSH is not on port 22, the port goes in the "
        "command:\n\n"
        "<tt>ssh-copy-id -p 2222 -i ~/.ssh/id_ed25519.pub user@server</tt>\n\n"
        "By hand it is exactly that: copy the contents of the <tt>.pub</tt> "
        "file and paste it as a new line in the server's "
        "<tt>~/.ssh/authorized_keys</tt>. One key per line, with no break in "
        "the middle — even if your editor shows the line wrapped.\n\n"
        "Before moving on, confirm it worked: open another terminal and "
        "connect. If it lets you in without asking for the account password, "
        "the key is in place."
    ),
    "guide.permissions.title": "3. Fix the permissions on the server",
    "guide.permissions.body": (
        "This is the most common reason a key does not work while nothing "
        "reports an error. sshd ignores <tt>authorized_keys</tt> silently when "
        "the permissions are too open, and all you see on this side is the "
        "password prompt coming back.\n\n"
        "<tt>chmod 700 ~/.ssh</tt>\n"
        "<tt>chmod 600 ~/.ssh/authorized_keys</tt>\n"
        "<tt>chown -R $USER:$USER ~/.ssh</tt>\n\n"
        "Run this logged in as the user who will be connecting. If you "
        "created the file with <tt>sudo</tt>, it belongs to root and the key "
        "will not work — in that case spell the name out, as in "
        "<tt>chown -R maria:maria /home/maria/.ssh</tt>.\n\n"
        "The home folder counts too: if <tt>/home/maria</tt> is writable by "
        "other users, sshd refuses for the same reason. <tt>chmod go-w ~</tt> "
        "takes away just the write bit, without opening the folder to anyone "
        "who does not need it.\n\n"
        "When nothing explains the refusal, the server does: the reason shows "
        "up in <tt>/var/log/auth.log</tt>, or in <tt>journalctl -u ssh</tt> — "
        "<tt>-u sshd</tt> on some distributions."
    ),
    "guide.password.title": "4. Close the password door",
    "guide.password.body": (
        "Once the key works, turn off password logins. That is what takes your "
        "server out of range of the bots sweeping the internet for weak "
        "passwords.\n\n"
        "Keep a copy before editing:\n\n"
        "<tt>sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak</tt>\n\n"
        "In <tt>/etc/ssh/sshd_config</tt>, on the server:\n"
        "<tt>PasswordAuthentication no</tt>\n"
        "<tt>PermitRootLogin prohibit-password</tt>\n\n"
        "The second line allows root in by key only: root still connects, and "
        "no password is accepted for that account.\n\n"
        "The VPS trap: nearly every cloud image ships files in "
        "<tt>/etc/ssh/sshd_config.d/</tt> that are read before the main file. "
        "And the <b>first</b> definition found wins, the same rule as on the "
        "client side — a <tt>PasswordAuthentication yes</tt> in there silently "
        "cancels your <tt>no</tt>. Check:\n\n"
        "<tt>sudo grep -r PasswordAuthentication /etc/ssh/sshd_config.d/</tt>"
        "\n\n"
        "Validate the syntax before reloading. If the first command reports an "
        "error, do not run the second:\n\n"
        "<tt>sudo sshd -t</tt>\n"
        "<tt>sudo systemctl reload ssh</tt>\n\n"
        "On some distributions the service is called <tt>sshd</tt> rather than "
        "<tt>ssh</tt>.\n\n"
        "Now confirm what is actually in effect, which is not always what the "
        "files say:\n\n"
        "<tt>sudo sshd -T | grep -i passwordauthentication</tt>\n\n"
        "Before closing the session you did that in, open a second one and "
        "confirm it lets you in. If something is wrong, the first session is "
        "still open for you to undo it. Closing the only session you had is "
        "like locking the door with the key still inside.\n\n"
        "On a VPS there is also the provider's panel console, which gets into "
        "the machine without going through SSH. Worth finding where it lives "
        "before you need it."
    ),
    "guide.agent.title": "5. Use the agent",
    "guide.agent.body": (
        "<tt>ssh-agent</tt> holds the unlocked key for the session, so you "
        "type its passphrase once.\n\n"
        "<tt>ssh-add ~/.ssh/id_ed25519</tt>\n\n"
        "Better still: put <tt>AddKeysToAgent yes</tt> on the connection and "
        "the key joins the agent by itself the first time it is used.\n\n"
        "On GNOME the agent already starts with your graphical session, so "
        "there is nothing else to set up.\n\n"
        "To see what the agent is already holding: <tt>ssh-add -l</tt>."
    ),
    "guide.debug.title": "When something fails",
    "guide.debug.body": (
        "<tt>ssh -v alias</tt>\n\n"
        "Shows every step of the negotiation: which keys were offered, what "
        "the server accepted, and where it stopped. If you need more detail, "
        "<tt>-vv</tt> and <tt>-vvv</tt> open it up further. Read from the "
        "bottom up — the last line before the error is usually the answer.\n\n"
        "One error that misleads: <tt>Too many authentication failures</tt>. "
        "It is not the server refusing your key. It is ssh offering every key "
        "it found, one by one, until the server cuts the connection for too "
        "many attempts — often before reaching the right one. Turn on "
        "<tt>IdentitiesOnly</tt> for the connection and it offers only the key "
        "declared there.\n\n"
        "<tt>ssh -G alias</tt>\n\n"
        "Shows the final configuration ssh will use for that alias, with "
        "everything inherited from wildcard blocks already applied. Useful "
        "when an option seems not to be taking effect: this is the value that "
        "actually counts.\n\n"
        "<tt>sudo sshd -T</tt>\n\n"
        "The same thing on the server side: sshd's effective configuration, "
        "already resolved between the main file and the ones in "
        "<tt>/etc/ssh/sshd_config.d/</tt>.\n\n"
        "And when a key is refused with no explanation, the reason is on the "
        "server, in <tt>/var/log/auth.log</tt> or in "
        "<tt>journalctl -u ssh</tt>."
    ),
    "guide.about.title": "The configuration file",
    "guide.about.body": (
        "Every connection in this list is a <tt>Host</tt> block in your "
        "<tt>~/.ssh/config</tt>. The alias you choose works everywhere that "
        "speaks SSH: <tt>ssh alias</tt>, <tt>scp file alias:/tmp</tt>, "
        "<tt>rsync</tt>, and Git when the repository uses "
        "<tt>git@alias:...</tt>.\n\n"
        "A wildcard block, such as <tt>Host *</tt> or "
        "<tt>Host *.example.com</tt>, applies to every connection matching the "
        "pattern. It is how you set defaults once.\n\n"
        "The rule that surprises people: for each option, OpenSSH uses the "
        "<b>first</b> definition it finds in the file, reading top to bottom. "
        "The last one does not win. That is why wildcard blocks usually go at "
        "the end — so they fill in what the specific blocks left blank, "
        "instead of overriding them.\n\n"
        "<tt>Match</tt> blocks are read and written back untouched, but they "
        "do not appear in this list and cannot be edited here. Edit them in "
        "your text editor — the app will not get in the way."
    ),
}
