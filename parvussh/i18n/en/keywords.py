"""Descriptions and examples for the ssh option catalog (English).

Keys are `kw.<OptionName>.desc` and the optional `kw.<OptionName>.example`,
matching the structural catalog in `parvussh/data/keywords.py`.

These descriptions are the app's teaching surface. Two rules: say what the
option does in the user's words, and where an option exists to prevent a
specific frustration, name that frustration — someone who has hit "too many
authentication failures" should recognise it in `IdentitiesOnly`.

Three of these options exist in `sshd_config` too, with a different meaning:
`PasswordAuthentication`, `KbdInteractiveAuthentication` and
`PubkeyAuthentication`. Nothing here touches the server, and the wording says
so — a reader coming from a hardening tutorial must not think otherwise.

Voice: third person indicative, matching the pt-BR catalog. Noun phrases are
fine where the option names a thing rather than a behaviour.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "kw.unknown.desc": "Option not in the catalog, kept exactly as it is.",
    # -- Connection -------------------------------------------------------
    "kw.HostName.desc": "The server's real address: an IP or a domain.",
    "kw.HostName.example": "203.0.113.10 or vps.example.com",
    "kw.User.desc": (
        "The user name to log in as. Without it, ssh uses your local user name."
    ),
    "kw.User.example": "deploy",
    "kw.Port.desc": (
        "The SSH server's port. Defaults to 22 — set it only if yours listens "
        "elsewhere."
    ),
    "kw.Port.example": "2222",
    # -- Authentication ---------------------------------------------------
    "kw.IdentityFile.desc": "The private key to use for this connection.",
    "kw.IdentityFile.example": "~/.ssh/id_ed25519",
    "kw.IdentitiesOnly.desc": (
        "Uses only the key declared here, ignoring the rest in the agent. Avoids "
        "the too many authentication failures error when you have several keys."
    ),
    "kw.AddKeysToAgent.desc": (
        "Adds the key to ssh-agent once it is unlocked, so the passphrase is "
        "not asked for again."
    ),
    "kw.PubkeyAuthentication.desc": (
        "Tries to authenticate with a key. Turn it off only to force another "
        "method in a test."
    ),
    "kw.PasswordAuthentication.desc": (
        "Offers a password to the server if the key fails. When off, the "
        "connection fails instead of prompting."
    ),
    "kw.KbdInteractiveAuthentication.desc": (
        "Answers questions from the server, such as 2FA codes. Applies to this "
        "connection only."
    ),
    "kw.PreferredAuthentications.desc": (
        "The order authentication methods are tried in."
    ),
    "kw.PreferredAuthentications.example": "publickey,password",
    "kw.CertificateFile.desc": "A user certificate signed by a CA.",
    "kw.CertificateFile.example": "~/.ssh/id_ed25519-cert.pub",
    "kw.IdentityAgent.desc": (
        "The agent socket to talk to. Use none to ignore the agent."
    ),
    "kw.IdentityAgent.example": "~/.1password/agent.sock",
    "kw.ForwardAgent.desc": (
        "Lets the server use the keys in your agent. Anyone with root there can "
        "use them too."
    ),
    # -- Session ----------------------------------------------------------
    "kw.ServerAliveInterval.desc": (
        "Sends a keepalive every N seconds so the session does not drop on its own."
    ),
    "kw.ServerAliveInterval.example": "60",
    "kw.ServerAliveCountMax.desc": (
        "How many unanswered keepalives before giving up. Multiply by the "
        "interval for the total."
    ),
    "kw.ServerAliveCountMax.example": "3",
    "kw.ConnectTimeout.desc": (
        "How long to wait, in seconds, for the server to answer."
    ),
    "kw.ConnectTimeout.example": "10",
    "kw.ConnectionAttempts.desc": "How many times to try before failing.",
    "kw.ConnectionAttempts.example": "2",
    "kw.Compression.desc": (
        "Compresses the data. Helps on slow links, hurts on fast ones."
    ),
    "kw.TCPKeepAlive.desc": (
        "Lets TCP detect a dropped network. Works outside the encrypted channel, "
        "unlike ServerAlive."
    ),
    "kw.RequestTTY.desc": (
        "Forces or skips the interactive terminal. Use force when a remote "
        "command needs one."
    ),
    "kw.RemoteCommand.desc": "A command run right after logging in.",
    "kw.RemoteCommand.example": "cd /srv/app && bash -l",
    "kw.SetEnv.desc": "Sets environment variables on the server.",
    "kw.SetEnv.example": "LANG=en_GB.UTF-8",
    "kw.SendEnv.desc": (
        "Sends local variables to the server, which only accepts them if configured to."
    ),
    "kw.SendEnv.example": "LANG LC_*",
    "kw.EscapeChar.desc": (
        "The character that opens session commands. With the default, ~. at the "
        "start of a line kills a frozen connection."
    ),
    "kw.EscapeChar.example": "~",
    # -- Host identity ----------------------------------------------------
    "kw.StrictHostKeyChecking.desc": (
        "What to do when the server's identity is new or has changed. The "
        "accept-new value accepts new hosts but still warns if a key changes."
    ),
    "kw.UserKnownHostsFile.desc": "The file known host keys are stored in.",
    "kw.UserKnownHostsFile.example": "~/.ssh/known_hosts",
    "kw.CheckHostIP.desc": (
        "Also checks the IP, not just the name. Warns when DNS starts pointing "
        "somewhere else."
    ),
    "kw.HostKeyAlgorithms.desc": "Which host key algorithms are accepted.",
    "kw.HostKeyAlgorithms.example": "ssh-ed25519,rsa-sha2-512",
    "kw.VisualHostKey.desc": (
        "Draws the host key as ASCII art when connecting. A change is easy to spot."
    ),
    # -- Network ----------------------------------------------------------
    "kw.ProxyJump.desc": (
        "Connects through another host, the bastion. It can be the alias of "
        "another connection here."
    ),
    "kw.ProxyJump.example": "bastion or user@bastion:22",
    "kw.ProxyCommand.desc": (
        "An external command that opens the channel to the server."
    ),
    "kw.ProxyCommand.example": "cloudflared access ssh --hostname %h",
    "kw.AddressFamily.desc": (
        "Restricts to IPv4 or IPv6. Useful when one of the two is broken on your "
        "network."
    ),
    "kw.BindAddress.desc": (
        "The local address the connection comes from. Useful on machines with "
        "several NICs."
    ),
    "kw.BindAddress.example": "192.168.0.10",
    "kw.ControlMaster.desc": (
        "Reuses an already open connection for the next ones. Makes everything "
        "noticeably faster."
    ),
    "kw.ControlPath.desc": "Where the shared connection's socket lives.",
    "kw.ControlPath.example": "~/.ssh/cm-%r@%h:%p",
    "kw.ControlPersist.desc": (
        "How long the master connection stays alive after you close it."
    ),
    "kw.ControlPersist.example": "10m",
    "kw.LocalForward.desc": "Forwards a local port to the server.",
    "kw.LocalForward.example": "8080 localhost:80",
    "kw.RemoteForward.desc": "Forwards a port on the server back to you.",
    "kw.RemoteForward.example": "9000 localhost:9000",
    "kw.DynamicForward.desc": (
        "Opens a SOCKS proxy on the given port, so the browser can go out "
        "through the server."
    ),
    "kw.DynamicForward.example": "1080",
    "kw.ExitOnForwardFailure.desc": (
        "Ends the connection if any forwarding fails, instead of connecting without it."
    ),
    "kw.GatewayPorts.desc": (
        "Lets other machines on the network use your forwarded ports. Off by default."
    ),
    "kw.ForwardX11.desc": "Forwards X11 graphical applications.",
    "kw.ForwardX11Trusted.desc": (
        "Gives the server full X11 access, including your keystrokes."
    ),
    # -- Other ------------------------------------------------------------
    "kw.LogLevel.desc": (
        "How much ssh prints. Use DEBUG to find out why a connection fails."
    ),
    "kw.BatchMode.desc": (
        "Never asks anything. Meant for scripts, not for interactive use."
    ),
    "kw.Ciphers.desc": (
        "Accepted ciphers, in order of preference. Leave empty unless the server "
        "demands otherwise."
    ),
    "kw.Ciphers.example": "chacha20-poly1305@openssh.com",
    "kw.MACs.desc": (
        "Accepted integrity algorithms. Only set this to talk to older servers."
    ),
    "kw.MACs.example": "hmac-sha2-256-etm@openssh.com",
    "kw.KexAlgorithms.desc": (
        "Key exchange algorithms. Changing this can stop the connection from completing."
    ),
    "kw.KexAlgorithms.example": "curve25519-sha256",
    "kw.CanonicalizeHostname.desc": (
        "Completes short names with the domain before connecting."
    ),
    "kw.Include.desc": (
        "Reads another configuration file at this point. The first definition "
        "found always wins, not the last."
    ),
    "kw.Include.example": "config.d/*.conf",
    # -- Group headings ---------------------------------------------------
    "group.connection": "Connection",
    "group.auth": "Authentication",
    "group.session": "Session",
    "group.hostkey": "Host identity",
    "group.network": "Network",
    "group.other": "Other",
}
