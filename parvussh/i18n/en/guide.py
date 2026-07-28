"""The key-setup guide and the "how it works" text (English).

Keys are `guide.<section>.title` and `guide.<section>.body`, matching
`parvussh/data/guide.py`. Bodies are Pango markup: `<tt>` around commands and
file names, nothing else. Any literal `&` or `<` must be escaped.

The audience is a developer who runs a couple of VPSs and has never been told
*why* any of this is the way it is. Each section says what to do, and then the
one thing that usually goes wrong.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "guide.create.title": "1. Create the key (on your own machine)",
    "guide.create.body": (
        "An SSH key is two files. The private one "
        "(<tt>~/.ssh/id_ed25519</tt>) never leaves your computer. The public "
        "one (<tt>~/.ssh/id_ed25519.pub</tt>) is what you install on servers — "
        "it can be copied around freely.\n\n"
        '<tt>ssh-keygen -t ed25519 -C "your-name@laptop"</tt>\n\n'
        "The <tt>ed25519</tt> type is the current choice: short, fast and "
        "strong. Use <tt>rsa</tt> with 4096 bits only when the server is too "
        "old to accept ed25519.\n\n"
        "Put a passphrase on the key. It protects the file if your laptop is "
        "lost, and the agent (section 5) means you type it once per session "
        "rather than once per connection."
    ),
    "guide.install.title": "2. Install the key on the server",
    "guide.install.body": (
        "<tt>ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server</tt>\n\n"
        "It asks for the account password one last time and appends your "
        "public key to <tt>~/.ssh/authorized_keys</tt> on the server.\n\n"
        "By hand it is exactly that: copy the contents of the <tt>.pub</tt> "
        "file and paste it as a new line in the server's "
        "<tt>~/.ssh/authorized_keys</tt>. One key per line."
    ),
    "guide.permissions.title": "3. Fix the permissions on the server",
    "guide.permissions.body": (
        "This is the most common reason a key does not work while nothing "
        "reports an error. sshd ignores <tt>authorized_keys</tt> silently when "
        "the permissions are too open.\n\n"
        "<tt>chmod 700 ~/.ssh</tt>\n"
        "<tt>chmod 600 ~/.ssh/authorized_keys</tt>\n"
        "<tt>chown -R $USER:$USER ~/.ssh</tt>\n\n"
        "The folder and the file must belong to the user logging in. If you "
        "created the file with <tt>sudo</tt>, it probably belongs to root."
    ),
    "guide.password.title": "4. Close the password door",
    "guide.password.body": (
        "Once the key works, turn off password logins. That is what takes your "
        "server out of range of the bots sweeping the internet for weak "
        "passwords.\n\n"
        "In <tt>/etc/ssh/sshd_config</tt>, on the server:\n"
        "<tt>PasswordAuthentication no</tt>\n"
        "<tt>PermitRootLogin prohibit-password</tt>\n\n"
        "<tt>sudo systemctl reload ssh</tt>\n\n"
        "Before closing the session you did that in, open a second one and "
        "confirm it lets you in. If something is wrong, the first session is "
        "still open for you to undo it. Closing the only session you had is "
        "like locking the door with the key still inside."
    ),
    "guide.agent.title": "5. Use the agent",
    "guide.agent.body": (
        "<tt>ssh-agent</tt> holds the unlocked key for the session, so you "
        "type its passphrase once.\n\n"
        "<tt>ssh-add ~/.ssh/id_ed25519</tt>\n\n"
        "Better still: put <tt>AddKeysToAgent yes</tt> on the connection and "
        "the key joins the agent by itself the first time it is used.\n\n"
        "On GNOME the agent already starts with your graphical session, so "
        "there is nothing else to set up."
    ),
    "guide.debug.title": "When something fails",
    "guide.debug.body": (
        "<tt>ssh -vvv alias</tt>\n\n"
        "Shows every step of the negotiation: which keys were offered, what "
        "the server accepted, and where it stopped. It is verbose on purpose — "
        "read from the bottom up, the last line before the error is usually "
        "the answer.\n\n"
        "<tt>ssh -G alias</tt>\n\n"
        "Shows the final configuration ssh will use for that alias, with "
        "everything inherited from wildcard blocks already applied. Useful "
        "when an option seems not to be taking effect: this is the value that "
        "actually counts."
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
        "instead of overriding them."
    ),
}
