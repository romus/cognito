from __future__ import annotations

import json
from pathlib import Path

from cognito.config import load_config
from cognito.engine import Console, run_decode, run_encode


def test_encode_decode_round_trip(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    nested_dir = project_root / "src" / "com" / "startup1"
    nested_dir.mkdir(parents=True)
    code_file = nested_dir / "startup1.txt"
    code_file.write_text("Hello startup1\nHELLO STARTUP1\n", encoding="utf-8")
    binary_file = project_root / "src" / "blob.bin"
    binary_file.parent.mkdir(exist_ok=True)
    binary_file.write_bytes(b"\x00\x01startup1")

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "directory": {
                    "com/startup1": "dev/startup2",
                    "startup1.txt": "startup2.txt",
                },
                "words": {"startup1": "startup2"},
            }
        ),
        encoding="utf-8",
    )
    config = load_config(str(config_path))

    encode_report = run_encode(project_root, config, dry_run=False, console=Console())

    assert encode_report.exit_code == 0
    encoded_file = project_root / "src" / "dev" / "startup2" / "startup2.txt"
    assert encoded_file.read_text(encoding="utf-8") == "Hello startup2\nHELLO startup2\n"
    assert binary_file.read_bytes() == b"\x00\x01startup1"

    decode_report = run_decode(project_root, config, dry_run=False, console=Console())

    assert decode_report.exit_code == 0
    restored_file = project_root / "src" / "com" / "startup1" / "startup1.txt"
    assert restored_file.read_text(encoding="utf-8") == "Hello startup1\nHELLO startup1\n"
    assert not (project_root / ".cognito").exists()


def test_decode_uses_config_without_manifest(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source_file = project_root / "startup2.txt"
    source_file.write_text("startup2", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"directory": {"startup1.txt": "startup2.txt"}, "words": {"startup1": "startup2"}}),
        encoding="utf-8",
    )
    config = load_config(str(config_path))

    report = run_decode(project_root, config, dry_run=False, console=Console())

    assert report.exit_code == 0
    restored_file = project_root / "startup1.txt"
    assert restored_file.read_text(encoding="utf-8") == "startup1"
    assert not (project_root / ".cognito").exists()


def test_failed_text_write_does_not_create_state(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "startup1.txt"
    target_file.write_text("startup1", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "startup2"}}), encoding="utf-8")

    original_write_text = Path.write_text

    def flaky_write_text(self, data, *args, **kwargs):
        if self == target_file:
            raise OSError("boom")
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)

    report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert report.exit_code == 1
    assert not (project_root / ".cognito").exists()


def test_failed_rename_does_not_create_state(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source_file = project_root / "startup1.txt"
    source_file.write_text("startup1", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"directory": {"startup1.txt": "startup2.txt"}}), encoding="utf-8")

    original_rename = Path.rename

    def flaky_rename(self, target):
        if self == source_file:
            raise OSError("boom")
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)

    report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert report.exit_code == 1
    assert not (project_root / ".cognito").exists()


def test_decode_reports_ambiguous_reverse_mapping(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "encoded.txt"
    target_file.write_text("x", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "x", "startup2": "x"}}), encoding="utf-8")

    report = run_decode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert report.exit_code == 1
    assert target_file.read_text(encoding="utf-8") == "x"
    assert any("ambiguous reverse mapping" in error for error in report.errors)


def test_decode_reports_empty_reverse_source_without_mutating(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "encoded.txt"
    target_file.write_text("x", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": ""}}), encoding="utf-8")

    report = run_decode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert report.exit_code == 1
    assert target_file.read_text(encoding="utf-8") == "x"
    assert any("empty value" in error for error in report.errors)


def test_decode_dry_run_reports_reverse_changes_without_mutating(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / "startup2.txt"
    target_file.write_text("startup2", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"directory": {"startup1.txt": "startup2.txt"}, "words": {"startup1": "startup2"}}),
        encoding="utf-8",
    )

    report = run_decode(project_root, load_config(str(config_path)), dry_run=True, console=Console())

    assert report.exit_code == 0
    assert target_file.read_text(encoding="utf-8") == "startup2"
    assert target_file.exists()
    assert not (project_root / "startup1.txt").exists()
    assert report.file_replacements
    assert report.renames


def test_directory_rename_prunes_empty_source_parents(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source_dir = project_root / "src" / "com" / "example"
    source_dir.mkdir(parents=True)
    (source_dir / "App.java").write_text("package com.example;", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"directory": {"com/example": "dev/service"}}),
        encoding="utf-8",
    )

    report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert report.exit_code == 0
    assert (project_root / "src" / "dev" / "service" / "App.java").exists()
    assert not (project_root / "src" / "com").exists()

    decode_report = run_decode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert decode_report.exit_code == 0
    assert (project_root / "src" / "com" / "example" / "App.java").exists()
    assert not (project_root / "src" / "dev").exists()


def test_text_replacements_apply_longest_match_first_and_decode_symmetrically(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source_file = project_root / "Main.java"
    source_file.write_text("package com.system1;\nimport com.system1.Service;\n", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "words": {
                    "com.system1": "dev.service",
                    "system1": "service1",
                }
            }
        ),
        encoding="utf-8",
    )

    encode_report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert encode_report.exit_code == 0
    assert source_file.read_text(encoding="utf-8") == "package dev.service;\nimport dev.service.Service;\n"

    decode_report = run_decode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert decode_report.exit_code == 0
    assert source_file.read_text(encoding="utf-8") == "package com.system1;\nimport com.system1.Service;\n"


def test_patch_file_with_utf8_content_is_processed(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    patch_file = project_root / "some-git-patch.patch"
    patch_file.write_text("--- a/startup1.txt\n+++ b/startup1.txt\n+startup1\n", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "startup2"}}), encoding="utf-8")

    encode_report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert encode_report.exit_code == 0
    assert patch_file.read_text(encoding="utf-8") == "--- a/startup2.txt\n+++ b/startup2.txt\n+startup2\n"


def test_patch_file_with_non_utf8_bytes_is_processed_with_warning_and_decodes(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    patch_file = project_root / "some-git-patch.patch"
    patch_file.write_bytes(b"--- a/startup1.txt\n+++ b/startup1.txt\n+startup1\x80\n")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "startup2"}}), encoding="utf-8")

    encode_report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert encode_report.exit_code == 0
    assert patch_file.read_bytes() == b"--- a/startup2.txt\n+++ b/startup2.txt\n+startup2\x80\n"
    assert any("Processing patch-like file with non-UTF-8 bytes" in warning for warning in encode_report.warnings)

    decode_report = run_decode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert decode_report.exit_code == 0
    assert patch_file.read_bytes() == b"--- a/startup1.txt\n+++ b/startup1.txt\n+startup1\x80\n"
    assert any("Processing patch-like file with non-UTF-8 bytes" in warning for warning in decode_report.warnings)


def test_patch_file_with_nul_byte_is_skipped_as_binary(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    patch_file = project_root / "some-git-patch.patch"
    patch_file.write_bytes(b"--- a/startup1.txt\n\x00+++ b/startup1.txt\n+startup1\n")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "startup2"}}), encoding="utf-8")

    encode_report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert encode_report.exit_code == 0
    assert patch_file.read_bytes() == b"--- a/startup1.txt\n\x00+++ b/startup1.txt\n+startup1\n"
    assert encode_report.file_replacements == []


def test_non_patch_file_with_invalid_utf8_after_sample_reports_error(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source_file = project_root / "startup1.txt"
    source_file.write_bytes((b"a" * 8192) + b"startup1\x80")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"words": {"startup1": "startup2"}}), encoding="utf-8")

    encode_report = run_encode(project_root, load_config(str(config_path)), dry_run=False, console=Console())

    assert encode_report.exit_code == 1
    assert source_file.read_bytes() == (b"a" * 8192) + b"startup1\x80"
    assert any("Failed to read startup1.txt" in error for error in encode_report.errors)
