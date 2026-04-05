from __future__ import annotations

import json
import sys
from pathlib import Path

from .constants import DEFAULT_CONFIG_PATH, DEFAULT_IGNORE_DIRS, OLD_CONFIG_PATH
from .models import Config

DEFAULT_CONFIG_TEMPLATE = {
    "directory": {
        "com/startup1": "dev/startup2",
    },
    "words": {
        "startup1": "startup2",
    },
    "ignore_dirs": [
        ".git",
        "build",
    ],
}


class ConfigError(ValueError):
    """Raised when config loading or validation fails."""


def resolve_config_path(config_path: str | None) -> Path:
    if config_path is None:
        old_path = Path(OLD_CONFIG_PATH).expanduser().resolve()
        if old_path.exists():
            print(
                f"Warning: found config at {old_path} (old location).\n"
                f"cognito now reads from {Path(DEFAULT_CONFIG_PATH).expanduser().resolve()} by default.\n"
                "Move your config or pass --config explicitly.",
                file=sys.stderr,
            )
    raw_path = config_path or DEFAULT_CONFIG_PATH
    return Path(raw_path).expanduser().resolve()


def load_config(config_path: str | None) -> Config:
    path = resolve_config_path(config_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigError("Config root must be a JSON object.")

    words = _load_mapping(payload, "words")
    directory = _load_mapping(payload, "directory")
    ignore_dirs = _load_ignore_dirs(payload)
    return Config(words=words, directory=directory, ignore_dirs=ignore_dirs)


def create_default_config(config_path: str | None, force: bool = False) -> Path:
    path = resolve_config_path(config_path)
    if path.exists() and not force:
        raise ConfigError(f"Config file already exists: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_CONFIG_TEMPLATE, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return path


def _load_mapping(payload: dict[str, object], key: str) -> dict[str, str]:
    raw = payload.get(key, {})
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"Config field '{key}' must be an object.")

    result: dict[str, str] = {}
    for source, target in raw.items():
        if not isinstance(source, str) or not isinstance(target, str):
            raise ConfigError(f"Config field '{key}' must map strings to strings.")
        if not source:
            raise ConfigError(f"Config field '{key}' cannot contain an empty key.")
        result[source] = target
    return result


def _load_ignore_dirs(payload: dict[str, object]) -> tuple[str, ...]:
    raw = payload.get("ignore_dirs")
    if raw is None:
        return DEFAULT_IGNORE_DIRS
    if not isinstance(raw, list) or any(not isinstance(item, str) or not item for item in raw):
        raise ConfigError("Config field 'ignore_dirs' must be a list of non-empty strings.")
    merged = dict.fromkeys([*DEFAULT_IGNORE_DIRS, *raw])
    return tuple(merged)
