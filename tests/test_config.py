from __future__ import annotations

import json

import pytest

from cognito.config import ConfigError, create_default_config, load_config, resolve_config_path


def test_load_config_defaults(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "startup2"}}), encoding="utf-8")

    config = load_config(str(config_path))

    assert config.words == {"startup1": "startup2"}
    assert config.directory == {}
    assert ".git" in config.ignore_dirs


def test_load_config_invalid_schema(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": []}), encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(str(config_path))


def test_create_default_config(tmp_path):
    config_path = tmp_path / "nested" / "config.json"

    created_path = create_default_config(str(config_path))

    payload = json.loads(created_path.read_text(encoding="utf-8"))
    assert created_path == config_path.resolve()
    assert payload["words"] == {"startup1": "startup2"}
    assert payload["directory"] == {"com/startup1": "dev/startup2"}


def test_create_default_config_refuses_overwrite(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ConfigError):
        create_default_config(str(config_path))


def test_resolve_config_path_respects_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr("cognito.constants._xdg_config_home", str(tmp_path))
    monkeypatch.setattr(
        "cognito.constants.DEFAULT_CONFIG_PATH",
        str(tmp_path / "cognito" / "config.json"),
    )
    # Re-import to pick up patched constant
    import cognito.config

    monkeypatch.setattr(
        cognito.config, "DEFAULT_CONFIG_PATH", str(tmp_path / "cognito" / "config.json")
    )
    result = resolve_config_path(None)
    assert result == (tmp_path / "cognito" / "config.json").resolve()


def test_resolve_config_path_warns_old_location(tmp_path, monkeypatch, capsys):
    old_config = tmp_path / ".cognito" / "config.json"
    old_config.parent.mkdir(parents=True)
    old_config.write_text("{}", encoding="utf-8")

    import cognito.config

    monkeypatch.setattr(cognito.config, "OLD_CONFIG_PATH", str(old_config))
    monkeypatch.setattr(
        cognito.config, "DEFAULT_CONFIG_PATH", str(tmp_path / ".config" / "cognito" / "config.json")
    )
    resolve_config_path(None)
    captured = capsys.readouterr()
    assert "old location" in captured.err
