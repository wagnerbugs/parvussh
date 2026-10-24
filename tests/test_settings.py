"""The app's own preferences: where they live, and surviving a bad file."""

from __future__ import annotations

from pathlib import Path

import pytest

from parvussh.core import settings
from parvussh.core.settings import Settings


def test_the_file_follows_the_xdg_default(fake_home: Path) -> None:
    assert settings.path() == fake_home / ".config" / "parvussh" / "settings.ini"


def test_xdg_config_home_moves_it(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inside a Flatpak this is ~/.var/app/<id>/config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(fake_home / "elsewhere"))
    assert settings.path() == fake_home / "elsewhere" / "parvussh" / "settings.ini"


def test_a_relative_xdg_config_home_is_ignored(
    fake_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The spec says so: a relative value is invalid."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative/dir")
    assert settings.path().is_relative_to(fake_home / ".config")


def test_nothing_saved_reads_as_the_defaults() -> None:
    assert settings.load() == Settings()


def test_loading_creates_nothing() -> None:
    settings.load()
    assert not settings.path().parent.exists()


def test_what_is_saved_is_read_back() -> None:
    settings.save(Settings(terminal="/usr/bin/xterm"))
    assert settings.load() == Settings(terminal="/usr/bin/xterm")


def test_saving_returns_the_path_it_wrote() -> None:
    assert settings.save(Settings(terminal="xterm")) == settings.path()


def test_a_percent_sign_is_kept_as_typed() -> None:
    """Interpolation would read `%` as the start of a reference and fail."""
    settings.save(Settings(terminal="wezterm start --class 100%"))
    assert settings.load().terminal == "wezterm start --class 100%"


def test_saving_leaves_no_temp_file_behind() -> None:
    settings.save(Settings(terminal="xterm"))
    assert [item.name for item in settings.path().parent.iterdir()] == ["settings.ini"]


def test_the_file_is_one_a_person_can_read() -> None:
    settings.save(Settings(terminal="alacritty -e"))
    text = settings.path().read_text(encoding="utf-8")
    assert "[terminal]" in text
    assert "command = alacritty -e" in text


def test_a_broken_file_reads_as_the_defaults() -> None:
    """One preference is not worth refusing to open over."""
    settings.path().parent.mkdir(parents=True)
    settings.path().write_text("this is not [an ini file\n", encoding="utf-8")
    assert settings.load() == Settings()


def test_a_file_without_the_section_reads_as_the_defaults() -> None:
    settings.path().parent.mkdir(parents=True)
    settings.path().write_text("[other]\nkey = value\n", encoding="utf-8")
    assert settings.load() == Settings()


# -- how many config copies to keep -----------------------------------------


def test_three_copies_are_kept_unless_told_otherwise() -> None:
    assert settings.load().backups == 3


def test_the_number_of_copies_is_read_back() -> None:
    settings.save(Settings(backups=7))
    assert settings.load().backups == 7


def test_saving_one_setting_keeps_the_other() -> None:
    settings.save(Settings(terminal="xterm", backups=5))
    assert settings.load() == Settings(terminal="xterm", backups=5)


@pytest.mark.parametrize(("written", "read"), [("0", 1), ("-4", 1), ("dez", 3)])
def test_a_number_below_one_or_not_a_number_is_not_obeyed(
    written: str, read: int
) -> None:
    """Zero copies would leave a write with nothing to undo it by."""
    settings.path().parent.mkdir(parents=True)
    settings.path().write_text(f"[backups]\nkeep = {written}\n", encoding="utf-8")
    assert settings.load().backups == read


def test_zero_is_saved_as_one() -> None:
    settings.save(Settings(backups=0))
    assert settings.load().backups == 1
