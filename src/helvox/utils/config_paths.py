"""config.json lives either next to the app (helvox/) or in the OS user config dir."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_config_path

from helvox.utils.platform import portable_base_dir


def user_config_file() -> Path:
    return Path(user_config_path(appname="helvox", appauthor="noxenum")) / "config.json"


def portable_config_file() -> Path:
    return portable_base_dir() / "helvox" / "config.json"


def portable_path_anchor() -> Path:
    """Base directory used for portable path serialization."""
    return portable_base_dir().resolve()


def encode_portable_path(path_value: str | Path) -> str:
    """Store paths relative to the portable app base when possible."""
    raw = str(path_value).strip()
    if not raw:
        return ""

    path = Path(raw).expanduser()
    try:
        absolute = path.resolve()
    except OSError:
        absolute = path.absolute()

    anchor = portable_path_anchor()
    try:
        rel = os.path.relpath(absolute, anchor)
    except ValueError:
        # Windows: different drives cannot be represented as relative paths.
        return str(absolute)

    return rel


def decode_portable_path(path_value: str | Path) -> Path:
    """Resolve stored portable paths against the app base."""
    raw = str(path_value).strip()
    if not raw:
        return portable_path_anchor()

    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()

    return (portable_path_anchor() / path).resolve()


def resolve_startup_settings_path() -> tuple[Path, bool | None]:
    """(path passed to load_settings, hint if JSON lacks config_portable)."""
    p, u = portable_config_file(), user_config_file()
    if p.exists():
        return p, True
    if u.exists():
        return u, False
    if u.with_suffix(".ini").exists() and not u.exists():
        return u, False
    if p.with_suffix(".ini").exists() and not p.exists():
        return p, True
    return u, None


def has_any_config_file() -> bool:
    p, u = portable_config_file(), user_config_file()
    return (
        p.exists()
        or u.exists()
        or p.with_suffix(".ini").exists()
        or u.with_suffix(".ini").exists()
    )


def prune_other_config(keep: Path) -> None:
    keep = keep.resolve()
    for c in (portable_config_file(), user_config_file()):
        if c.resolve() != keep and c.exists():
            try:
                c.unlink()
            except OSError:
                pass
