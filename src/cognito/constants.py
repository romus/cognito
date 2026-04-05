from __future__ import annotations

import os

_xdg_config_home = os.environ.get("XDG_CONFIG_HOME") or "~/.config"
DEFAULT_CONFIG_PATH = os.path.join(_xdg_config_home, "cognito", "config.json")
OLD_CONFIG_PATH = "~/.cognito/config.json"
STATE_DIR_NAME = ".cognito"
DEFAULT_IGNORE_DIRS = (
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "target",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    STATE_DIR_NAME,
)
