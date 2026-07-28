"""Leitura e escrita do ~/.ssh/config.

Regras de ouro deste módulo:

1. Bloco que você não editou é reescrito byte a byte, do jeito que estava.
2. Comentários acompanham a linha que vem logo abaixo deles.
3. Antes de gravar, faz backup e valida o arquivo com `ssh -G`. Se a
   validação falhar, nada é gravado.
"""

from __future__ import annotations

import glob
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

SSH_DIR = Path.home() / ".ssh"
MAIN_CONFIG = SSH_DIR / "config"

_PAIR = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_-]*)\s*(?:=\s*|\s+)(.*?)\s*$")
_BARE = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9_-]*)\s*$")


class ConfigError(Exception):
    """Erro que impede a gravação do arquivo."""


@dataclass
class Entry:
    keyword: str
    value: str
    comments: list[str] = field(default_factory=list)


@dataclass
class Block:
    """Um trecho do arquivo: o topo global, um `Host` ou um `Match`."""

    kind: str  # "global" | "host" | "match"
    patterns: list[str] = field(default_factory=list)
    entries: list[Entry] = field(default_factory=list)
    lead: list[str] = field(default_factory=list)  # comentários antes do Host
    tail: list[str] = field(default_factory=list)  # sobras no fim do bloco
    header_raw: str = ""
    raw: list[str] = field(default_factory=list)
    source: Path | None = None
    dirty: bool = False

    # -- consulta ----------------------------------------------------------
    @property
    def title(self) -> str:
        return " ".join(self.patterns) if self.patterns else "(global)"

    @property
    def is_pattern(self) -> bool:
        """True para blocos curinga como `Host *`, que valem para todos."""
        return any(c in p for p in self.patterns for c in "*?!")

    def get(self, keyword: str, default: str = "") -> str:
        low = keyword.lower()
        for e in self.entries:
            if e.keyword.lower() == low:
                return e.value
        return default

    def comments_for(self, keyword: str) -> list[str]:
        low = keyword.lower()
        for e in self.entries:
            if e.keyword.lower() == low:
                return list(e.comments)
        return []

    def subtitle(self) -> str:
        """Linha de apoio do card: user@hostname:porta."""
        host = self.get("HostName")
        user = self.get("User")
        port = self.get("Port")
        if not host:
            return "sem HostName" if self.kind == "host" else ""
        text = f"{user}@{host}" if user else host
        return f"{text}:{port}" if port and port != "22" else text

    # -- escrita -----------------------------------------------------------
    def render(self) -> list[str]:
        if not self.dirty:
            return list(self.raw)
        indent = "" if self.kind == "global" else "    "
        out = list(self.lead)
        if self.kind == "host":
            out.append("Host " + " ".join(self.patterns))
        elif self.kind == "match":
            out.append(self.header_raw.rstrip())
        for e in self.entries:
            out.extend(e.comments)
            out.append(f"{indent}{e.keyword} {e.value}".rstrip())
        out.extend(self.tail)
        return out


def parse_text(text: str, source: Path) -> list[Block]:
    blocks: list[Block] = []
    pending: list[str] = []
    cur = Block(kind="global", source=source)

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            pending.append(line.rstrip("\n"))
            continue

        m = _PAIR.match(line) or _BARE.match(line)
        if not m:  # linha que não entendemos: preserva como está
            pending.append(line.rstrip("\n"))
            continue

        keyword = m.group(2)
        value = m.group(3).strip() if m.re is _PAIR else ""
        low = keyword.lower()

        if low in ("host", "match"):
            blocks.append(cur)
            cur = Block(
                kind="host" if low == "host" else "match",
                patterns=value.split() if low == "host" else [value],
                header_raw=line.rstrip("\n"),
                lead=pending,
                source=source,
            )
            cur.raw = list(pending) + [line.rstrip("\n")]
            pending = []
        else:
            entry = Entry(keyword, value, pending)
            cur.entries.append(entry)
            cur.raw.extend(pending + [line.rstrip("\n")])
            pending = []

    cur.tail = pending
    cur.raw.extend(pending)
    blocks.append(cur)
    return blocks


@dataclass
class ConfigFile:
    path: Path
    blocks: list[Block]
    removed: bool = False  # marca alteração estrutural (host novo/apagado)

    @property
    def dirty(self) -> bool:
        return self.removed or any(b.dirty for b in self.blocks)

    def text(self) -> str:
        lines: list[str] = []
        for b in self.blocks:
            lines.extend(b.render())
        body = "\n".join(lines).strip("\n")
        return body + "\n" if body else ""


class ConfigSet:
    """O config principal mais os arquivos trazidos por `Include`."""

    def __init__(self, files: list[ConfigFile], main: Path):
        self.files = files
        self.main = main

    # -- carga -------------------------------------------------------------
    @classmethod
    def load(cls, main: Path = MAIN_CONFIG) -> "ConfigSet":
        files: list[ConfigFile] = []
        seen: set[Path] = set()

        def read(path: Path) -> None:
            path = path.expanduser().resolve()
            if path in seen or not path.is_file():
                return
            seen.add(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            cf = ConfigFile(path=path, blocks=parse_text(text, path))
            files.append(cf)
            for inc in _included_paths(cf):
                read(inc)

        if not main.exists():
            SSH_DIR.mkdir(mode=0o700, exist_ok=True)
            main.touch(mode=0o600)
        read(main)
        return cls(files, main.expanduser().resolve())

    # -- consulta ----------------------------------------------------------
    @property
    def hosts(self) -> list[Block]:
        return [b for f in self.files for b in f.blocks if b.kind == "host"]

    def file_of(self, block: Block) -> ConfigFile:
        for f in self.files:
            if block in f.blocks:
                return f
        raise ConfigError("bloco não pertence a nenhum arquivo carregado")

    # -- edição ------------------------------------------------------------
    def add_host(self, alias: str = "nova-conexao") -> Block:
        main_file = next(f for f in self.files if f.path == self.main)
        block = Block(
            kind="host",
            patterns=[alias],
            lead=[""],
            source=main_file.path,
            dirty=True,
        )
        main_file.blocks.append(block)
        main_file.removed = True
        return block

    def remove(self, block: Block) -> None:
        cf = self.file_of(block)
        cf.blocks.remove(block)
        cf.removed = True

    def duplicate(self, block: Block) -> Block:
        cf = self.file_of(block)
        copy = Block(
            kind="host",
            patterns=[f"{block.patterns[0]}-copia"] + block.patterns[1:],
            entries=[Entry(e.keyword, e.value, list(e.comments))
                     for e in block.entries],
            lead=[""],
            source=cf.path,
            dirty=True,
        )
        cf.blocks.insert(cf.blocks.index(block) + 1, copy)
        cf.removed = True
        return copy

    # -- gravação ----------------------------------------------------------
    def save(self) -> list[Path]:
        saved = []
        for cf in self.files:
            if not cf.dirty:
                continue
            text = cf.text()
            problem = validate(text)
            if problem:
                raise ConfigError(problem)
            write_atomic(cf.path, text)
            for b in cf.blocks:
                b.raw = b.render()
                b.dirty = False
            cf.removed = False
            saved.append(cf.path)
        return saved


def _included_paths(cf: ConfigFile):
    for block in cf.blocks:
        for entry in block.entries:
            if entry.keyword.lower() != "include":
                continue
            for token in shlex.split(entry.value):
                p = Path(token).expanduser()
                if not p.is_absolute():
                    p = SSH_DIR / p
                for hit in sorted(glob.glob(str(p))):
                    yield Path(hit)


def validate(text: str) -> str | None:
    """Roda `ssh -G` no conteúdo. Devolve a mensagem de erro, ou None."""
    fd, tmp = tempfile.mkstemp(suffix=".sshconfig")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        os.chmod(tmp, 0o600)
        proc = subprocess.run(
            ["ssh", "-F", tmp, "-G", "parvussh-validacao.invalid"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout).strip()
            return msg.replace(tmp, "config") or "o ssh recusou o arquivo"
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None  # sem ssh instalado: segue sem validar
    finally:
        os.unlink(tmp)


def write_atomic(path: Path, text: str) -> Path | None:
    """Faz backup, grava em arquivo temporário e troca. Devolve o backup."""
    backup = None
    if path.exists():
        backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".parvussh-")
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return backup