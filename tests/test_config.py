from __future__ import annotations

import json

import pytest

from cognito.config import ConfigError, create_default_config, load_config


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
