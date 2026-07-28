"""Descriptions and examples for the ssh option catalog (English).

Keys are `kw.<OptionName>.desc` and the optional `kw.<OptionName>.example`,
matching the structural catalog in `parvussh/data/keywords.py`.

These descriptions are the app's teaching surface. Two rules: say what the
option does in the user's words, and where an option exists to prevent a
specific frustration, name that frustration — someone who has hit "too many
authentication failures" should recognise it in `IdentitiesOnly`.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "kw.unknown.desc": "Option not in the catalog, kept exactly as it is.",
    # -- Connection -------------------------------------------------------
    "kw.HostName.desc": "The server's real address: an IP or a domain.",
    "kw.HostName.example": "203.0.113.10 or vps.example.com",
    "kw.User.desc": "The user name to log in as.",
    "kw.User.example": "deploy",
    "kw.Port.desc": "The SSH server's port.",
    "kw.Port.example": "22",
    # -- Authentication ---------------------------------------------------
    "kw.IdentityFile.desc": "The private key to use for this connection.",
    "kw.IdentityFile.example": "~/.ssh/id_ed25519",
    "kw.IdentitiesOnly.desc": (
        "Use only the key declared here, ignoring the rest in the agent. Avoids "
        "the too many authentication failures error when you have several keys."
    ),
    "kw.AddKeysToAgent.desc": (
        "Adds the key to ssh-agent once it is unlocked, so the passphrase is "
        "not asked for again."
    ),
    "kw.PubkeyAuthentication.desc": "Try to authenticate with a public key.",
    "kw.PasswordAuthentication.desc": "Allow authenticating with a password.",
    "kw.KbdInteractiveAuthentication.desc": (
        "Allow interactive authentication, such as 2FA and keyboard-interactive."
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
        "Lets the server use the keys in your agent. Only turn this on for "
        "machines you trust."
    ),
    # -- Session ----------------------------------------------------------
    "kw.ServerAliveInterval.desc": (
        "Sends a keepalive every N seconds so the session does not drop on its own."
    ),
    "kw.ServerAliveInterval.example": "60",
    "kw.ServerAliveCountMax.desc": (
        "How many unanswered keepalives before giving up on the connection."
    ),
    "kw.ServerAliveCountMax.example": "3",
    "kw.ConnectTimeout.desc": (
        "How long to wait, in seconds, for the server to answer."
    ),
    "kw.ConnectTimeout.example": "10",
    "kw.ConnectionAttempts.desc": "How many times to try before failing.",
    "kw.ConnectionAttempts.example": "2",
    "kw.Compression.desc": "Compresses the data. Helps on slow links.",
    "kw.TCPKeepAlive.desc": (
        "Lets TCP detect a dropped network. Different from ServerAlive."
    ),
    "kw.RequestTTY.desc": "Whether an interactive terminal should be allocated.",
    "kw.RemoteCommand.desc": "A command run right after logging in.",
    "kw.RemoteCommand.example": "cd /srv/app && bash -l",
    "kw.SetEnv.desc": "Sets environment variables on the server.",
    "kw.SetEnv.example": "LANG=en_GB.UTF-8",
    "kw.SendEnv.desc": "Sends local variables to the server.",
    "kw.SendEnv.example": "LANG LC_*",
    "kw.EscapeChar.desc": "The session's escape character.",
    "kw.EscapeChar.example": "~",
    # -- Host identity ----------------------------------------------------
    "kw.StrictHostKeyChecking.desc": (
        "What to do when the server's identity is new or has changed. The "
        "accept-new value accepts new hosts but still warns if a key changes."
    ),
    "kw.UserKnownHostsFile.desc": "The file known host keys are stored in.",
    "kw.UserKnownHostsFile.example": "~/.ssh/known_hosts",
    "kw.CheckHostIP.desc": "Also check the host's IP, not just its name.",
    "kw.HostKeyAlgorithms.desc": "Which host key algorithms are accepted.",
    "kw.HostKeyAlgorithms.example": "ssh-ed25519,rsa-sha2-512",
    "kw.VisualHostKey.desc": ("Draws the host key in ASCII art when connecting."),
    # -- Network ----------------------------------------------------------
    "kw.ProxyJump.desc": "Connects through another host, the bastion.",
    "kw.ProxyJump.example": "bastion or user@bastion:22",
    "kw.ProxyCommand.desc": (
        "An external command that opens the channel to the server."
    ),
    "kw.ProxyCommand.example": "cloudflared access ssh --hostname %h",
    "kw.AddressFamily.desc": "Restricts to IPv4 or IPv6.",
    "kw.BindAddress.desc": "The local address the connection comes from.",
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
    "kw.DynamicForward.desc": "Opens a SOCKS proxy on the given port.",
    "kw.DynamicForward.example": "1080",
    "kw.ExitOnForwardFailure.desc": ("Ends the connection if any forwarding fails."),
    "kw.GatewayPorts.desc": "Lets other machines use your forwarded ports.",
    "kw.ForwardX11.desc": "Forwards X11 graphical applications.",
    "kw.ForwardX11Trusted.desc": ("Gives the server full X11 access. Use with care."),
    # -- Other ------------------------------------------------------------
    "kw.LogLevel.desc": "How much ssh prints.",
    "kw.BatchMode.desc": (
        "Never asks anything. Meant for scripts, not for interactive use."
    ),
    "kw.Ciphers.desc": "Accepted ciphers, in order of preference.",
    "kw.Ciphers.example": "chacha20-poly1305@openssh.com",
    "kw.MACs.desc": "Accepted integrity algorithms.",
    "kw.MACs.example": "hmac-sha2-256-etm@openssh.com",
    "kw.KexAlgorithms.desc": "Key exchange algorithms.",
    "kw.KexAlgorithms.example": "curve25519-sha256",
    "kw.CanonicalizeHostname.desc": (
        "Completes short names with the domain before connecting."
    ),
    "kw.Include.desc": "Reads another configuration file at this point.",
    "kw.Include.example": "config.d/*.conf",
    # -- Group headings ---------------------------------------------------
    "group.connection": "Connection",
    "group.auth": "Authentication",
    "group.session": "Session",
    "group.hostkey": "Host identity",
    "group.network": "Network",
    "group.other": "Other",
}
