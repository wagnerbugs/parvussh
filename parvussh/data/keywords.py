"""The ssh option catalog: which options we offer and how to render each one.

Structure only. Every readable string — the description, the example — comes
from `parvussh.i18n`, so adding a language never means touching this table.
Adding an option is one line here and one line in
`i18n/pt_br/keywords.py`; `tests/test_keywords.py` fails if you forget the
second.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from parvussh.i18n import has, t

STR, INT, BOOL, ENUM, PATH, IDENTITY = "str", "int", "bool", "enum", "path", "identity"

# Group keys, in display order. The labels are `t("group.<key>")`.
CONNECTION, AUTH, SESSION, HOSTKEY, NETWORK, OTHER = (
    "connection",
    "auth",
    "session",
    "hostkey",
    "network",
    "other",
)
GROUPS: tuple[str, ...] = (CONNECTION, AUTH, SESSION, HOSTKEY, NETWORK, OTHER)

# These already have fixed rows in the form, so the `+` search never offers them.
BASIC: tuple[str, ...] = ("HostName", "User", "Port")


@dataclass(frozen=True)
class Keyword:
    """One ssh option: its canonical spelling and the widget it deserves."""

    name: str
    kind: str
    values: tuple[str, ...] = ()  # ENUM, in preferred order
    lo: int = 0  # INT bounds
    hi: int = 65535
    group: str = OTHER
    # False for an option found in the user's file but absent from the catalog.
    catalogued: bool = True

    @property
    def description(self) -> str:
        return t(f"kw.{self.name}.desc") if self.catalogued else t("kw.unknown.desc")

    @property
    def example(self) -> str:
        """Sample value, or `""` when the option speaks for itself."""
        key = f"kw.{self.name}.example"
        return t(key) if self.catalogued and has(key) else ""


CATALOG: tuple[Keyword, ...] = (
    Keyword("HostName", STR, group=CONNECTION),
    Keyword("User", STR, group=CONNECTION),
    Keyword("Port", INT, lo=1, hi=65535, group=CONNECTION),
    Keyword("IdentityFile", IDENTITY, group=AUTH),
    Keyword("IdentitiesOnly", BOOL, group=AUTH),
    Keyword("AddKeysToAgent", ENUM, values=("yes", "no", "ask", "confirm"), group=AUTH),
    Keyword("PubkeyAuthentication", BOOL, group=AUTH),
    Keyword("PasswordAuthentication", BOOL, group=AUTH),
    Keyword("KbdInteractiveAuthentication", BOOL, group=AUTH),
    Keyword("PreferredAuthentications", STR, group=AUTH),
    Keyword("CertificateFile", PATH, group=AUTH),
    Keyword("IdentityAgent", PATH, group=AUTH),
    Keyword("ForwardAgent", BOOL, group=AUTH),
    Keyword("ServerAliveInterval", INT, lo=0, hi=86400, group=SESSION),
    Keyword("ServerAliveCountMax", INT, lo=0, hi=100, group=SESSION),
    Keyword("ConnectTimeout", INT, lo=0, hi=3600, group=SESSION),
    Keyword("ConnectionAttempts", INT, lo=1, hi=100, group=SESSION),
    Keyword("Compression", BOOL, group=SESSION),
    Keyword("TCPKeepAlive", BOOL, group=SESSION),
    Keyword("RequestTTY", ENUM, values=("auto", "no", "yes", "force"), group=SESSION),
    Keyword("RemoteCommand", STR, group=SESSION),
    Keyword("SetEnv", STR, group=SESSION),
    Keyword("SendEnv", STR, group=SESSION),
    Keyword("EscapeChar", STR, group=SESSION),
    Keyword(
        "StrictHostKeyChecking",
        ENUM,
        values=("ask", "accept-new", "yes", "no"),
        group=HOSTKEY,
    ),
    Keyword("UserKnownHostsFile", PATH, group=HOSTKEY),
    Keyword("CheckHostIP", BOOL, group=HOSTKEY),
    Keyword("HostKeyAlgorithms", STR, group=HOSTKEY),
    Keyword("VisualHostKey", BOOL, group=HOSTKEY),
    Keyword("ProxyJump", STR, group=NETWORK),
    Keyword("ProxyCommand", STR, group=NETWORK),
    Keyword("AddressFamily", ENUM, values=("any", "inet", "inet6"), group=NETWORK),
    Keyword("BindAddress", STR, group=NETWORK),
    Keyword(
        "ControlMaster",
        ENUM,
        values=("no", "auto", "yes", "ask", "autoask"),
        group=NETWORK,
    ),
    Keyword("ControlPath", PATH, group=NETWORK),
    Keyword("ControlPersist", STR, group=NETWORK),
    Keyword("LocalForward", STR, group=NETWORK),
    Keyword("RemoteForward", STR, group=NETWORK),
    Keyword("DynamicForward", STR, group=NETWORK),
    Keyword("ExitOnForwardFailure", BOOL, group=NETWORK),
    Keyword("GatewayPorts", BOOL, group=NETWORK),
    Keyword("ForwardX11", BOOL, group=NETWORK),
    Keyword("ForwardX11Trusted", BOOL, group=NETWORK),
    Keyword(
        "LogLevel",
        ENUM,
        values=(
            "QUIET",
            "FATAL",
            "ERROR",
            "INFO",
            "VERBOSE",
            "DEBUG",
            "DEBUG1",
            "DEBUG2",
            "DEBUG3",
        ),
        group=OTHER,
    ),
    Keyword("BatchMode", BOOL, group=OTHER),
    Keyword("Ciphers", STR, group=OTHER),
    Keyword("MACs", STR, group=OTHER),
    Keyword("KexAlgorithms", STR, group=OTHER),
    Keyword("CanonicalizeHostname", ENUM, values=("no", "yes", "always"), group=OTHER),
    Keyword("Include", PATH, group=OTHER),
)

BY_NAME: dict[str, Keyword] = {keyword.name.lower(): keyword for keyword in CATALOG}


def get(name: str) -> Keyword | None:
    """The catalog entry for `name`, or None if we do not know the option."""
    return BY_NAME.get(name.lower())


def for_option(name: str) -> Keyword:
    """An entry for `name`, inventing a plain text one when it is unknown.

    The config contract's third rule: an option missing from the catalog is
    still shown and still saved. It is never dropped for being unfamiliar.
    """
    return get(name) or Keyword(name, STR, group=OTHER, catalogued=False)


def canonical(name: str) -> str:
    """The catalog's spelling of `name`, or `name` unchanged when unknown."""
    keyword = get(name)
    return keyword.name if keyword else name


def _fold(text: str) -> str:
    """Lowercase and strip accents, so `sessao` finds `sessão`.

    Brazilian developers type without accents far more often than with them; a
    search that misses `conexao` would feel broken rather than strict.
    """
    stripped = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in stripped if not unicodedata.combining(char))


def search(query: str, exclude: set[str] | None = None) -> list[Keyword]:
    """Options matching `query` by name or description, best matches first.

    Rank 0 is a prefix match on the name, rank 1 is a match anywhere. Ties
    break alphabetically. An empty query returns the whole catalog.
    """
    skip = {name.lower() for name in (exclude or set())} | {
        name.lower() for name in BASIC
    }
    folded = _fold(query.strip())
    found: list[tuple[int, str, Keyword]] = []
    for keyword in CATALOG:
        if keyword.name.lower() in skip:
            continue
        name = _fold(keyword.name)
        if not folded:
            found.append((1, keyword.name, keyword))
        elif name.startswith(folded):
            found.append((0, keyword.name, keyword))
        elif folded in name or folded in _fold(keyword.description):
            found.append((1, keyword.name, keyword))
    return [keyword for _, _, keyword in sorted(found, key=lambda row: row[:2])]
