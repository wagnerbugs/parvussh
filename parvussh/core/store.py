"""The main config plus everything `Include` pulls in, loaded and saved as one.

The last rule of the config contract: we only ever write files we read.
`Include`
targets are editable precisely because we loaded them, and nothing outside
`self.files` is ever touched.
"""

from __future__ import annotations

import glob
import hashlib
import shlex
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from parvussh.core.merge import ConfigConflict, rebase
from parvussh.core.models import HOST, Block, Entry, render_blocks
from parvussh.core.parser import detect_newline, parse_text
from parvussh.core.writer import ConfigError, ensure_exists, validate, write_atomic

INCLUDE = "include"


def ssh_dir() -> Path:
    """Resolved on every call — the tests redirect `Path.home()`."""
    return Path.home() / ".ssh"


def main_config_path() -> Path:
    return ssh_dir() / "config"


@dataclass
class ConfigFile:
    """One file on disk and the blocks parsed out of it."""

    path: Path
    blocks: list[Block] = field(default_factory=list)
    newline: str = "\n"
    # True when a host was added, removed or duplicated: the block list itself
    # changed, which no per-block `dirty` flag would show.
    structural: bool = False
    # The blocks as the file on disk holds them, and a hash of its bytes.
    # A save compares the hash to notice that another program wrote the file
    # since, and replays the user's edit from these onto what it wrote.
    on_disk: list[Block] = field(default_factory=list)
    digest: str = ""

    @property
    def dirty(self) -> bool:
        return self.structural or any(block.dirty for block in self.blocks)

    def text(self) -> str:
        return render_blocks(self.blocks, self.newline)


def included_paths(config: ConfigFile) -> Iterator[Path]:
    """Every existing file an `Include` in this file points at."""
    for block in config.blocks:
        for entry in block.entries:
            if entry.keyword.lower() != INCLUDE:
                continue
            for token in _tokens(entry.value):
                pattern = Path(token).expanduser()
                if not pattern.is_absolute():
                    pattern = ssh_dir() / pattern
                for hit in sorted(glob.glob(str(pattern))):
                    yield Path(hit)


def _tokens(value: str) -> list[str]:
    """Split an `Include` value. An unbalanced quote falls back to whitespace."""
    try:
        return shlex.split(value)
    except ValueError:
        return value.split()


class ConfigSet:
    """Every loaded file, and the only object allowed to write them."""

    def __init__(self, files: list[ConfigFile], main: Path) -> None:
        self.files = files
        self.main = main

    @classmethod
    def load(cls, main: Path | None = None) -> ConfigSet:
        main = (main or main_config_path()).expanduser()
        ensure_exists(main)
        main = main.resolve()
        files: list[ConfigFile] = []
        _read_into(main, files, seen=set())
        return cls(files, main)

    # -- reading -----------------------------------------------------------

    @property
    def hosts(self) -> list[Block]:
        return [b for f in self.files for b in f.blocks if b.kind == HOST]

    @property
    def main_file(self) -> ConfigFile:
        for config in self.files:
            if config.path == self.main:
                return config
        raise ConfigError("the main config file is not loaded")

    def file_of(self, block: Block) -> ConfigFile:
        for config in self.files:
            if any(candidate is block for candidate in config.blocks):
                return config
        raise ConfigError("block does not belong to any loaded file")

    # -- editing -----------------------------------------------------------

    def add_host(self, alias: str) -> Block:
        """Append a new `Host` to the main file. The alias comes from the UI."""
        target = self.main_file
        block = Block(
            kind=HOST,
            patterns=[alias],
            lead=[""],  # one blank line between it and whatever came before
            source=target.path,
            dirty=True,
        )
        target.blocks.append(block)
        target.structural = True
        return block

    def duplicate(self, block: Block, alias: str) -> Block:
        """Copy a block, entries and comments included, right below the original."""
        config = self.file_of(block)
        copy = Block(
            kind=HOST,
            patterns=[alias, *block.patterns[1:]],
            entries=[
                Entry(entry.keyword, entry.value, list(entry.comments))
                for entry in block.entries
            ],
            lead=[""],
            source=config.path,
            dirty=True,
        )
        config.blocks.insert(config.blocks.index(block) + 1, copy)
        config.structural = True
        return copy

    def remove(self, block: Block) -> None:
        config = self.file_of(block)
        config.blocks.remove(block)
        config.structural = True

    # -- writing -----------------------------------------------------------

    def save(self) -> list[Path]:
        """Write every dirty file. Returns the paths actually written.

        Each file is read again first. If another program wrote it since we
        loaded it, the edit is replayed on top of what is there now, so their
        change survives our save; `ConfigConflict` when it cannot be.

        Validation runs over *all* pending files before *any* of them is
        written. SPEC §3 validates per file, which would let an early file
        land on disk before a later one is refused — half a save is worse than
        no save.
        """
        dirty = [config for config in self.files if config.dirty]
        for config in dirty:
            _catch_up(config)

        pending = [(config, config.text()) for config in dirty]
        for _, text in pending:
            validate(text)

        for config, text in pending:
            write_atomic(config.path, text)
            for block in config.blocks:
                block.raw = block.render()  # while still dirty: renders fresh
                block.dirty = False
            config.structural = False
            config.on_disk = list(config.blocks)
            config.digest = _digest(text.encode("utf-8"))
        return [config.path for config, _ in pending]


def _catch_up(config: ConfigFile) -> None:
    """Bring `config` level with its file on disk, keeping the user's edit.

    Raises `ConfigConflict` when another program changed the same place the
    edit lands. Nothing is written then, and `config` is left as it was.
    """
    fresh = _parse(config.path)
    if fresh.digest == config.digest:
        return
    try:
        config.blocks, config.on_disk = rebase(
            config.on_disk, config.blocks, fresh.blocks
        )
    except ConfigConflict as conflict:
        conflict.path = config.path
        raise
    config.newline = fresh.newline
    config.digest = fresh.digest


def _parse(path: Path) -> ConfigFile:
    """Read and parse one file, remembering what it held.

    read_bytes, not read_text: text mode translates CRLF to LF before we ever
    see it, so detect_newline() would report the wrong ending and the file
    would come back rewritten. errors="replace" keeps a config with one stray
    byte openable instead of crashing the app on startup.
    """
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    blocks = parse_text(text, path)
    return ConfigFile(
        path,
        blocks,
        detect_newline(text),
        on_disk=list(blocks),
        digest=_digest(data),
    )


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_into(path: Path, files: list[ConfigFile], seen: set[Path]) -> None:
    """Parse `path` and follow its includes, refusing to visit a file twice."""
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return
    if resolved in seen or not resolved.is_file():
        return
    seen.add(resolved)  # the cycle guard: a -> b -> a stops here

    config = _parse(resolved)
    files.append(config)
    for target in included_paths(config):
        _read_into(target, files, seen)
