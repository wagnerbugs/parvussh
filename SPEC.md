# SPEC.md

Precise behaviour specs for the parts that are easy to get subtly wrong.
Where this document shows code, treat it as the intended implementation, not a
suggestion — it has been validated against a working prototype.

---

## 1. Config model

```python
@dataclass
class Entry:
    keyword: str            # original spelling, e.g. "IdentityFile"
    value: str              # everything after the separator, stripped
    comments: list[str]     # raw comment/blank lines directly above this entry


@dataclass
class Block:
    kind: str               # "global" | "host" | "match"
    patterns: list[str]     # ["web1", "web1.local"] for Host; [expr] for Match
    entries: list[Entry]
    lead: list[str]         # raw lines above the "Host" header
    tail: list[str]         # trailing comment/blank lines at the end of a block
    header_raw: str         # the original "Host ..." / "Match ..." line
    raw: list[str]          # every original line of this block, in order
    source: Path
    dirty: bool = False
```

The first block of every file is always `kind="global"` and holds directives
that appear before any `Host` (commonly `Include`). It may be empty.

### Derived properties on `Block`

- `title` → `" ".join(patterns)`, or `"(global)"` when there are no patterns.
- `is_pattern` → `True` when any pattern contains `*`, `?` or `!`. Used to give
  wildcard blocks a different icon and to block the connection test.
- `get(keyword, default="")` → first matching value, case-insensitive.
- `comments_for(keyword)` → the comment lines attached to that entry, so an
  edit can carry them over.
- `subtitle()` → the sidebar's second line:
    - no `HostName` → `"sem HostName"` for host blocks, `""` otherwise
    - `user@hostname` when `User` is set, else `hostname`
    - append `:port` when `Port` is set and is not `22`

---

## 2. Parser

### Recognised line shapes

```python
PAIR = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_-]*)\s*(?:=\s*|\s+)(.*?)\s*$")
BARE = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_-]*)\s*$")
```

OpenSSH accepts both `Key value` and `Key=value`. Both must parse. A line that
matches neither regex is preserved verbatim in the pending-comment buffer — we
never discard bytes we do not understand.

### Algorithm

Walk the file line by line with a `pending: list[str]` buffer.

1. Blank line or line starting with `#` → append to `pending`, continue.
2. Line matching neither regex → append to `pending`, continue.
3. Keyword is `Host` or `Match` (case-insensitive) → close the current block,
   start a new one. `pending` becomes the new block's `lead`. The new block's
   `raw` starts as `lead + [header_line]`.
4. Any other keyword → create `Entry(keyword, value, comments=pending)`, append
   it to the current block, extend `raw` with `pending + [line]`, clear
   `pending`.
5. End of file → whatever is left in `pending` becomes the last block's `tail`.

Keyword casing is preserved exactly as the user wrote it. Comparison is always
`.lower()`.

### Rendering

```python
def render(self) -> list[str]:
    if not self.dirty:
        return list(self.raw)          # untouched blocks are byte-identical
    indent = "" if self.kind == "global" else "    "
    out = list(self.lead)
    if self.kind == "host":
        out.append("Host " + " ".join(self.patterns))
    elif self.kind == "match":
        out.append(self.header_raw.rstrip())
    for entry in self.entries:
        out.extend(entry.comments)
        out.append(f"{indent}{entry.keyword} {entry.value}".rstrip())
    out.extend(self.tail)
    return out
```

A file's text is every block's `render()` joined with `\n`, stripped of leading
and trailing blank lines, plus one final `\n`. An empty file renders as `""`.

A newly created block sets `lead=[""]` so it is separated from the previous
block by exactly one blank line.

### Include resolution

Walk every entry with keyword `Include`. Split the value with `shlex.split`.
For each token: `expanduser()`, resolve relative paths against `~/.ssh`, then
`glob`. Parse each match into its own `ConfigFile`, recursively, guarding
against cycles with a set of resolved paths already seen. `Match` blocks are
loaded and preserved but are read-only in the UI for v1.

---

## 3. Writing

```
render all blocks
  → validate(text)          ssh -F <temp> -G parvussh-validation.invalid
      non-zero exit         → raise ConfigError(stderr, with the temp path
                              replaced by "config"); nothing is written
      ssh not installed     → skip validation, proceed
  → backup                  copy2 to <path>.bak-YYYYMMDD-HHMMSS
  → atomic write            mkstemp in the same dir, chmod 600, os.replace
  → reset state             every block: raw = render(), dirty = False
```

Only files with at least one dirty block, or a structural change (host added,
removed or duplicated), are rewritten. `ConfigSet.save()` returns the list of
paths it actually wrote.

If `~/.ssh/config` does not exist at startup, create `~/.ssh` with mode `700`
and an empty `config` with mode `600`.

---

## 4. Option catalog

> **Amended by `docs/DECISIONS.md` D3.** `description` and `example` are no
> longer literal fields on `Keyword`; they are properties resolving
> `t("kw.<Name>.desc")` and `t("kw.<Name>.example")` against
> `i18n/pt_br/keywords.py`. `search()` is unchanged because it reads the
> properties. Adding an option is therefore two lines — the structural row
> here, the description there.

`parvussh/data/keywords.py`. Adding an option must stay a near-trivial change.

```python
STR, INT, BOOL, ENUM, PATH, IDENTITY = "str", "int", "bool", "enum", "path", "identity"

@dataclass(frozen=True)
class Keyword:
    name: str          # canonical OpenSSH spelling
    kind: str          # decides which widget is rendered
    description: str   # pt-BR, one or two sentences, shown in search and help
    example: str = ""
    values: tuple = () # for ENUM, in preferred order
    lo: int = 0        # INT bounds
    hi: int = 65535
    group: str = "Conexão"
```

`kind` → widget mapping:

| kind | widget | stored value |
|---|---|---|
| `STR` | `Adw.EntryRow` | text as typed |
| `INT` | `Adw.SpinRow` bounded by `lo`/`hi` | integer as string |
| `BOOL` | `Adw.SwitchRow` | `"yes"` / `"no"` |
| `ENUM` | `Adw.ComboRow` over `values` | selected string |
| `PATH` | `Adw.EntryRow` + file picker button | text |
| `IDENTITY` | `Adw.EntryRow` + key picker button | text |

Groups, in display order: `Conexão`, `Autenticação`, `Sessão`,
`Identidade do host`, `Rede`, `Outras`.

`BASIC = ("HostName", "User", "Port")` — these already have fixed rows in the
form and are excluded from the `+` search.

### Search function

```python
def search(query: str, exclude: set[str] | None = None) -> list[Keyword]:
    """Filter by name or description. Prefix matches rank first."""
```

- Skip anything in `exclude` (already added to the current host) and anything
  in `BASIC`.
- Rank 0: `name.lower().startswith(query)`. Rank 1: query appears in the name
  or in the description.
- Sort by `(rank, name)`. Empty query returns the whole catalog, rank 1.

Because descriptions are in Portuguese, typing `chave` must return
`IdentityFile`, `AddKeysToAgent`, `IdentitiesOnly`, `HostKeyAlgorithms`,
`ForwardAgent`. Write a test asserting exactly this — it is the feature that
makes the app feel like it speaks the user's language.

### Initial catalog

Ship these 47 entries. Descriptions are pt-BR and user-visible.

```
Conexão
  HostName            STR   Endereço real do servidor: IP ou domínio.               ex: 203.0.113.10 ou vps.exemplo.com
  User                STR   Usuário usado no login remoto.                          ex: deploy
  Port                INT   Porta do servidor SSH.                                  1..65535, ex: 22

Autenticação
  IdentityFile        IDENT Chave privada usada nesta conexão.                      ex: ~/.ssh/id_ed25519
  IdentitiesOnly      BOOL  Usa só a chave declarada aqui, ignorando as demais do agente. Evita o erro de "muitas tentativas" quando você tem várias chaves.
  AddKeysToAgent      ENUM  Adiciona a chave ao ssh-agent depois de destravá-la, para não pedir a senha de novo.   yes|no|ask|confirm
  PubkeyAuthentication        BOOL  Tenta autenticar por chave pública.
  PasswordAuthentication      BOOL  Permite autenticar por senha.
  KbdInteractiveAuthentication BOOL Permite autenticação interativa (2FA, teclado-interativo).
  PreferredAuthentications    STR   Ordem em que os métodos de autenticação são tentados.   ex: publickey,password
  CertificateFile     PATH  Certificado de usuário assinado por uma CA.             ex: ~/.ssh/id_ed25519-cert.pub
  IdentityAgent       PATH  Socket do agente a consultar. Use 'none' para ignorar o agente.   ex: ~/.1password/agent.sock
  ForwardAgent        BOOL  Deixa o servidor usar as chaves do seu agente. Só ative em máquinas de confiança.

Sessão
  ServerAliveInterval STR→INT  Envia um sinal de vida a cada N segundos para a sessão não cair sozinha.   0..86400, ex: 60
  ServerAliveCountMax INT   Quantos sinais sem resposta antes de desistir da conexão.   0..100, ex: 3
  ConnectTimeout      INT   Tempo máximo, em segundos, esperando o servidor responder.  0..3600, ex: 10
  ConnectionAttempts  INT   Quantas vezes tentar antes de falhar.                   1..100, ex: 2
  Compression         BOOL  Comprime os dados. Ajuda em links lentos.
  TCPKeepAlive        BOOL  Deixa o TCP detectar quedas de rede. Diferente de ServerAlive*.
  RequestTTY          ENUM  Se um terminal interativo deve ser alocado.             auto|no|yes|force
  RemoteCommand       STR   Comando executado logo após o login.                    ex: cd /srv/app && bash -l
  SetEnv              STR   Define variáveis de ambiente no servidor.               ex: LANG=pt_BR.UTF-8
  SendEnv             STR   Envia variáveis locais para o servidor.                 ex: LANG LC_*
  EscapeChar          STR   Caractere de escape da sessão.                          ex: ~

Identidade do host
  StrictHostKeyChecking  ENUM  O que fazer quando a identidade do servidor é nova ou mudou. 'accept-new' aceita hosts novos, mas ainda alerta se a chave mudar.   ask|accept-new|yes|no
  UserKnownHostsFile  PATH  Arquivo onde as chaves de host conhecidas são guardadas.  ex: ~/.ssh/known_hosts
  CheckHostIP         BOOL  Confere também o IP do host, além do nome.
  HostKeyAlgorithms   STR   Algoritmos de chave de host aceitos.                    ex: ssh-ed25519,rsa-sha2-512
  VisualHostKey       BOOL  Mostra um desenho ASCII da chave do host ao conectar.

Rede
  ProxyJump           STR   Conecta passando por outro host (bastion).              ex: bastion ou user@bastion:22
  ProxyCommand        STR   Comando externo que cria o canal até o servidor.        ex: cloudflared access ssh --hostname %h
  AddressFamily       ENUM  Restringe a IPv4 ou IPv6.                               any|inet|inet6
  BindAddress         STR   Endereço local de origem da conexão.                    ex: 192.168.0.10
  ControlMaster       ENUM  Reaproveita uma conexão já aberta para as próximas. Deixa tudo bem mais rápido.   no|auto|yes|ask|autoask
  ControlPath         PATH  Onde o socket da conexão compartilhada fica.            ex: ~/.ssh/cm-%r@%h:%p
  ControlPersist      STR   Por quanto tempo a conexão mestre continua viva depois de fechar.   ex: 10m
  LocalForward        STR   Encaminha uma porta local para o servidor.              ex: 8080 localhost:80
  RemoteForward       STR   Encaminha uma porta do servidor para você.              ex: 9000 localhost:9000
  DynamicForward      STR   Abre um proxy SOCKS na porta indicada.                  ex: 1080
  ExitOnForwardFailure BOOL Encerra a conexão se algum encaminhamento falhar.
  GatewayPorts        BOOL  Deixa outras máquinas usarem suas portas encaminhadas.
  ForwardX11          BOOL  Encaminha aplicações gráficas X11.
  ForwardX11Trusted   BOOL  Dá acesso total do X11 ao servidor. Use com cautela.

Outras
  LogLevel            ENUM  Quanta informação o ssh imprime.   QUIET|FATAL|ERROR|INFO|VERBOSE|DEBUG|DEBUG1|DEBUG2|DEBUG3
  BatchMode           BOOL  Nunca pergunta nada. Serve para scripts, não para uso interativo.
  Ciphers             STR   Cifras aceitas, em ordem de preferência.                ex: chacha20-poly1305@openssh.com
  MACs                STR   Algoritmos de integridade aceitos.                      ex: hmac-sha2-256-etm@openssh.com
  KexAlgorithms       STR   Algoritmos de troca de chaves.                          ex: curve25519-sha256
  CanonicalizeHostname ENUM Completa nomes curtos com o domínio antes de conectar.  no|yes|always
  Include             PATH  Lê outro arquivo de configuração neste ponto.           ex: config.d/*.conf
```

`ServerAliveInterval` is `INT` with `lo=0, hi=86400`.

An option present in the user's file but absent from the catalog is rendered as
a plain `STR` row with the description
`"Opção não catalogada, preservada como está."` and is never dropped on save.

---

## 5. Key discovery and creation

> **Amended by `docs/DECISIONS.md` D3.** `core/` returns no translated text.
> Where this section shows a pt-BR sentence coming out of `core/keys.py`, the
> function raises a typed error instead and the UI supplies the wording.

### Discovery — `core/keys.py`

Scan `~/.ssh` for regular files, skipping:

- names: `config`, `known_hosts`, `known_hosts.old`, `authorized_keys`,
  `environment`, `rc`, `agent.env`, `allowed_signers`
- suffixes: `.pub`, `.bak`, `.old`, `.tmp`, `.conf`, `.sock`
- dotfiles and anything under a `config.d` prefix

Keep a file when a sibling `<name>.pub` exists **or** its first 200 bytes
contain `PRIVATE KEY`.

Describe each key with `ssh-keygen -l -f <path>`, which reads the public half
and never prompts for a passphrase. Output looks like:

```
256 SHA256:abc123... user@laptop (ED25519)
```

Parse into `bits`, `fingerprint`, `comment`, `kind`. A failure to describe is
not fatal — show the filename alone.

`SshKey.display_path` returns `~/...` when the key is under `$HOME`, so the
value written into the config stays portable.

### Creation

```
ssh-keygen -t <kind> -f <path> -N <passphrase> [-b 4096 if rsa] [-C <comment>]
```

Refuse when the target already exists — return
`"Já existe um arquivo em {path}. Escolha outro nome."` rather than letting
`ssh-keygen` prompt. `chmod 600` afterwards. Types offered:
`ed25519` (default), `ecdsa`, `rsa` (4096).

**Known limitation, document it in the README:** the passphrase is passed as a
command-line argument, so it is briefly visible in `ps` to other users of the
same machine. Acceptable on a personal desktop; mention the terminal
alternative for anyone who cares.

---

## 6. Connection test

> **Amended by `docs/DECISIONS.md` D3.** `TestResult` carries
> `(ok, status, output)` only. The Heading and Body columns below are the
> pt-BR copy for `t("test.<status>.title")` and `t("test.<status>.detail")`,
> which live in `i18n/pt_br/ui.py`. Every other column — the ordering, the
> match strings, the `status` names and the `ok` values — is normative and
> unchanged.

Runs against the **form's current state**, not the saved file, so the user can
test before committing anything.

Write the block being edited to a temp file (`chmod 600`) and run:

```
ssh -F <temp>
    -o BatchMode=yes
    -o ConnectTimeout=8
    -o NumberOfPasswordPrompts=0
    -o StrictHostKeyChecking=accept-new
    <alias> true
```

Subprocess timeout: 25s. Run on a worker thread; deliver the result to GTK via
`GLib.idle_add`. Delete the temp file in a `finally`.

Wildcard aliases cannot be tested — show
`"Blocos com curinga não podem ser testados direto."` and stop.

### Interpretation table

Match against the lowercased combined stdout+stderr, **in this order**:

| Condition | status | `ok` | Heading (pt-BR) | Body (pt-BR) |
|---|---|---|---|---|
| exit code 0 | `auth` | ✅ | Conectado | Login concluído com a chave configurada. Está pronto para usar. |
| `permission denied` or `no supported authentication` | `reachable` | ✅ | Servidor respondeu | Endereço, porta e usuário estão válidos: o servidor chegou a pedir autenticação. Faltou só a senha ou a chave, que o teste não envia. |
| `could not resolve` or `name or service not known` | `dns` | ❌ | Nome não encontrado | O endereço em HostName não foi resolvido. Confira se não há erro de digitação no domínio. |
| `connection refused` | `refused` | ❌ | Conexão recusada | A máquina respondeu, mas nada está escutando nessa porta. Confira o valor de Port e se o sshd está no ar. |
| `timed out` or `timeout` | `timeout` | ❌ | O servidor não respondeu | Sem resposta dentro do tempo limite. Costuma ser firewall, IP errado ou máquina desligada. |
| `no route to host` or `network is unreachable` | `network` | ❌ | Rede inacessível | Não há caminho até esse endereço a partir daqui. Verifique sua rede ou a necessidade de VPN. |
| `host key verification failed` or `remote host identification` | `hostkey` | ❌ | A identidade do servidor mudou | A chave do host não bate com a guardada em known_hosts. Pode ser reinstalação do servidor — ou alguém no meio do caminho. Confirme antes de remover a linha antiga. |
| `bad configuration` | `config` | ❌ | Configuração inválida | O ssh recusou uma das opções. A saída abaixo indica qual. |
| `FileNotFoundError` | `no-ssh` | ❌ | ssh não encontrado | Instale o pacote openssh-client para usar o teste. |
| `subprocess.TimeoutExpired` | `timeout` | ❌ | O servidor não respondeu | Passou de 25s sem resposta. Verifique o endereço, a porta e se há firewall no caminho. |
| anything else | `unknown` | ❌ | Não deu para concluir o teste | O ssh terminou com código N. A saída completa está abaixo. |

The `reachable` case being a **success** is the central insight: reaching the
authentication prompt proves host, port and network are correct, which is
exactly what the user wanted to verify.

Always return the raw ssh output alongside the verdict; the dialog shows it in
a collapsed expander.

---

## 7. UI

### Window

`Adw.ApplicationWindow` 1020×700, containing `Adw.ToastOverlay` →
`Adw.NavigationSplitView` (sidebar 280–360px). Window title is `ParvuSsh`;
the editor header replaces it with the selected alias.

### Sidebar — `Adw.NavigationPage` "Conexões"

- Header: `+` button (`win.new`, tooltip "Nova conexão (Ctrl+N)") on the left;
  hamburger menu on the right with "Ajuda e dicas" and "Recarregar do disco".
- `Gtk.SearchEntry`, placeholder `Filtrar conexões…`, filters on alias,
  `HostName` and `User` via `set_filter_func` + `invalidate_filter`.
- `Gtk.ListBox` with `boxed-list` style, one `Adw.ActionRow` per host block:
  title = alias (escape with `GLib.markup_escape_text`), subtitle =
  `block.subtitle()`, prefix icon `network-server-symbolic`, or
  `emblem-system-symbolic` when `is_pattern`.
- Each row carries `row.block`, the `Block` it represents.

### Editor — `Adw.NavigationPage` "Conexão"

Header bar: `Adw.WindowTitle` showing the alias plus the source file path
(`~/.ssh/config`) as subtitle; buttons `Testar` and `Salvar`
(`suggested-action`); overflow menu with `Duplicar` and `Excluir`.

`Gtk.Stack` with two children:

- `empty` — `Adw.StatusPage`, icon `network-server-symbolic`,
  title "Escolha uma conexão", description "Ou use o + para cadastrar a
  primeira." Header bar is insensitive in this state.
- `form` — `Adw.PreferencesPage` with two groups:
    - **Conexão** — description "Deixe em branco o que não usar: campos vazios
      não vão para o arquivo." Rows: `Host — o apelido que você digita`,
      `HostName — endereço real`, `User`, `Port` (input purpose DIGITS).
    - **Opções adicionais** — header suffix is a box with a `?` button
      (`help-about-symbolic`, opens the help dialog) and a `+` `Gtk.MenuButton`.
      When empty, shows a dim label: "Nenhuma opção extra. Use o + para procurar
      pelo nome."

### Add-option popover

`Gtk.Popover`, 420px wide: `Gtk.SearchEntry` (placeholder
`Digite: ServerAlive…`) over a 320px-tall scrolled `Gtk.ListBox`. Rows are
`Adw.ActionRow` with the option name as title and the pt-BR description as
subtitle (`subtitle_lines=2`), activatable.

- On show: clear the entry, rebuild the list, focus the entry.
- On `search-changed`: rebuild from `keywords.search(text, used)`.
- On `activate` (Enter): pick the first row.
- On row activation: close and add the option to the form, focused.

Already-used options are excluded from the list.

### Identity picker

Suffix button (`dialog-password-symbolic`) on `IdentityFile` rows. Its popover
is filled on `show` — never cached, so a key created a minute ago appears
immediately. Contents: a boxed list of `Adw.ActionRow`s (title = filename,
subtitle = `ED25519 · 256 bits · comment`), then `Criar chave…`, then
`Procurar arquivo…` (`Gtk.FileDialog` starting at `~/.ssh`). No keys found →
"Nenhuma chave em ~/.ssh ainda."

Selecting a key writes the `~/...` form of the path into the entry.

### Dirty state

Any widget change sets `dirty` and prefixes the header title with `• `. Loading
a block sets a `_loading` guard first so programmatic `set_text` calls do not
mark it dirty.

Switching rows while dirty opens an `Adw.AlertDialog`: "Alterações não salvas"
/ "“{alias}” tem mudanças que ainda não foram gravadas no arquivo." with
`Descartar` and `Salvar` (suggested, default). A failed save cancels the
switch; the selection stays put.

### Saving

Validate first: empty alias → toast "O apelido em Host não pode ficar vazio.";
non-numeric port → toast "Port aceita apenas números."

Rebuild the block's entries in this order: non-empty `HostName`, `User`,
`Port`, then every non-empty extra option in form order. Carry over each
entry's original comments by keyword. Empty fields are simply absent from the
file. Then `ConfigSet.save()`, refresh the sidebar keeping the selection, and
toast "Salvo em ~/.ssh/config".

On `ConfigError`, show: "O arquivo não foi gravado" / "O ssh recusou a
configuração, então nada foi alterado no disco." plus the ssh message.

### Help dialog

`Adw.PreferencesDialog` with `search_enabled=True` and three pages:

1. **Opções** (`view-list-symbolic`) — every catalog entry as an
   `Adw.ActionRow` grouped by category, subtitle = description + example or
   allowed values.
2. **Chaves** (`dialog-password-symbolic`) — the six-step guide from
   `data/guide.py`, rendered as wrapped, selectable, markup-enabled labels.
3. **Como funciona** (`help-about-symbolic`) — how `Host` blocks map to the
   `ssh` command, and the first-match-wins rule for wildcards.

### Keyboard

`Ctrl+S` save, `Ctrl+N` new connection, `F1` help.

---

## 8. Help guide content (pt-BR, `data/guide.py`)

Six sections, each a `(title, markup_text)` pair. `<tt>` for commands.

1. **1. Criar a chave (na sua máquina)** — a key is a pair of files; the
   private one never leaves; `ssh-keygen -t ed25519 -C "seu-nome@notebook"`;
   ed25519 is the current choice, rsa 4096 only for old servers; use a
   passphrase, the agent stops it from being annoying.
2. **2. Instalar a chave no servidor** —
   `ssh-copy-id -i ~/.ssh/id_ed25519.pub usuario@servidor`; the manual
   equivalent is appending the `.pub` to the remote `~/.ssh/authorized_keys`.
3. **3. Ajustar as permissões no servidor** — `chmod 700 ~/.ssh`,
   `chmod 600 ~/.ssh/authorized_keys`, correct ownership. Frame it as the most
   common cause of silent failure.
4. **4. Fechar a porta da senha** — `PasswordAuthentication no`,
   `PermitRootLogin prohibit-password`, `sudo systemctl reload ssh`, and the
   warning to open a second session to verify before closing the first.
5. **5. Usar o agente** — `ssh-add`, `AddKeysToAgent yes`, GNOME starts the
   agent with the session.
6. **Quando algo falha** — `ssh -vvv apelido` shows every negotiation step;
   `ssh -G apelido` shows the effective config including wildcard inheritance.

Plus `ABOUT_CONFIG`: each connection is a `Host` block; the alias works with
`scp`, `rsync`, Git and anything that speaks SSH; wildcard blocks apply to
several hosts and OpenSSH takes the **first** definition it finds for each
option, which is why wildcard blocks usually go at the end of the file.

---

## 9. Test fixtures

`tests/fixtures/basic.config` must contain, at minimum:

```
# Configuração pessoal
# não mexer sem café

Host vps-blog
    HostName 203.0.113.10
    User deploy
    Port 2222
    # essa chave é a antiga
    IdentityFile ~/.ssh/id_blog

Host github.com
    User git
    IdentityFile=~/.ssh/id_github
    IdentitiesOnly yes

Match host *.interno
    ProxyJump bastion

Host *
    ServerAliveInterval 60
    AddKeysToAgent yes
```

It exercises: leading comments, an inline comment inside a block, `=` as
separator, a `Match` block, and a wildcard block. Add at least two more
fixtures: one empty file, and one with CRLF line endings plus a malformed line.

Required assertions (these all pass in the reference prototype):

- round-trip with no edits is byte-identical, for every fixture
- host discovery returns `["vps-blog", "github.com", "*"]`
- `IdentityFile=~/.ssh/id_github` parses to `~/.ssh/id_github`
- the `Match` block survives rendering with its header intact
- editing `vps-blog` changes only that block; `# não mexer sem café`,
  `    # essa chave é a antiga` and `IdentityFile=~/.ssh/id_github` all survive
- a new block renders as `\nHost x\n    HostName ...\n`
- `Host *` reports `is_pattern`, `vps-blog` does not
- `subtitle()` for `vps-blog` is `deploy@203.0.113.10:2222`
- an empty file does not crash
- a line matching neither regex is preserved verbatim