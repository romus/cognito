from __future__ import annotations

import json
from pathlib import Path

from cognito.cli import main
from cognito.config import load_config
from cognito.engine import Console, run_encode


def test_cli_requires_confirmation_for_home(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({}), encoding="utf-8")

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _: "n")

    exit_code = main(["encode", "--project", str(tmp_path), "--config", str(config_path)])

    assert exit_code == 1


def test_cli_invalid_config_returns_2(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{", encoding="utf-8")

    exit_code = main(["encode", "--project", str(tmp_path), "--config", str(config_path), "--silent"])

    assert exit_code == 2


def test_cli_decode_requires_config(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    missing_config = tmp_path / "missing.json"

    exit_code = main(["decode", "--project", str(project_root), "--config", str(missing_config), "--silent"])

    assert exit_code == 2


def test_cli_decode_uses_config_reverse_mapping(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source_file = project_root / "startup1.txt"
    source_file.write_text("startup1", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "startup2"}}), encoding="utf-8")

    run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    exit_code = main(["decode", "--project", str(project_root), "--config", str(config_path), "--silent"])

    assert exit_code == 0
    assert source_file.read_text(encoding="utf-8") == "startup1"


def test_cli_init_config_creates_default_file(tmp_path):
    config_path = tmp_path / "config.json"

    exit_code = main(["init-config", "--config", str(config_path)])

    assert exit_code == 0
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["words"] == {"startup1": "startup2"}


def test_cli_init_config_requires_force_to_overwrite(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    exit_code = main(["init-config", "--config", str(config_path)])

    assert exit_code == 2
