# cognito

`cognito` is a Python CLI for encoding and decoding project-specific content so code can be moved between different startup projects with less manual cleanup.

The tool can:
- replace words inside text files using case-insensitive substring matching
- rename directories and files anywhere inside a project tree
- save an `encode` manifest in `.cognito/` inside the target project
- restore changes later with `decode`
- run in `dry-run` mode without changing files

## Why this exists

If you regularly bootstrap new products from previous internal projects, you often need to:
- replace project names in source files
- rename package paths such as `com/startup1` to `dev/startup2`
- keep enough metadata to reverse the transformation later

`cognito` is designed for that workflow.


## Requirements

- Python 3.14+
- `make`

## Installation

### Local development install

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install --upgrade pip setuptools
make install
```

After that:

```bash
.venv/bin/cognito --help
```

### Editable install details

`make install` does the following:
- creates or reuses `.venv`
- can be run after `source .venv/bin/activate`
- upgrades `pip`
- installs the project in editable mode
- installs development dependencies from `.[dev]`

## CLI usage

```bash
cognito encode [--project PATH] [--config PATH] [--silent] [--dry-run]
cognito decode [--project PATH] [--config PATH] [--silent] [--dry-run]
cognito init-config [--config PATH] [--force]
```

### Commands

`encode`
- loads the config
- scans the project recursively
- replaces configured words in text files
- renames matching directories and files
- writes an `encode-<timestamp>.json` manifest into `.cognito/`

`decode`
- loads the latest `encode-*.json` manifest from `.cognito/`
- reverses renames in reverse order
- reverses text replacements using the saved manifest
- writes `decode-<timestamp>.log`

`init-config`
- creates a default JSON config template
- writes to `~/.cognito/config.json` by default
- can write to a custom path with `--config`
- refuses to overwrite an existing file unless `--force` is passed

## Options

### `--project`

Project root to process.

Default:
```bash
.
```

If omitted, the current directory is used.

If the target directory resolves to the current user's home directory or filesystem root, the CLI asks for confirmation unless `--silent` is set.

### `--config`

Path to the JSON config file.

Default:
```bash
~/.cognito/config.json
```

Notes:
- `encode` requires a valid config
- `decode` does not require the config file because it restores from the saved manifest
- `init-config` uses this path as the output target for the generated template

### `--force`

Available for `init-config`.

Overwrites the target config file if it already exists.

### `--silent`

Skips the dangerous-path confirmation prompt.

This is useful for automation, CI, or scripted runs.

### `--dry-run`

Prints what would change without mutating the project.

In `dry-run` mode:
- files are not rewritten
- paths are not renamed
- manifests and decode logs are not created

## Config format

Example:

```json
{
  "directory": {
    "com/startup1": "dev/startup2",
    "startup1.txt": "startup2.txt"
  },
  "words": {
    "startup1": "startup2"
  },
  "ignore_dirs": [
    ".git",
    "build"
  ]
}
```

Generate this template automatically:

```bash
.venv/bin/cognito init-config
```

### `words`

Map of source string to target string.

Behavior:
- substring matching
- case-insensitive search
- replacement uses the exact target string from config
- case is not preserved

Example:
- `startup1` matches `startup1`, `Startup1`, `STARTUP1`
- all of them become `startup2`

### `directory`

Map of path fragments to replacement path fragments.

Behavior:
- matching is done against path parts, not file contents
- fragments can target nested paths such as `com/startup1`
- matches can happen at any level inside the project
- both directories and file names can be renamed

### `ignore_dirs`

Optional list of directory names to skip during traversal.

If omitted, built-in defaults are used, including:
- `.git`
- `.hg`
- `.svn`
- `.idea`
- `.venv`
- `venv`
- `node_modules`
- `build`
- `dist`
- `target`
- `__pycache__`
- `.mypy_cache`
- `.pytest_cache`
- `.cognito`

## How encode works

1. Load config.
2. Walk the project recursively, skipping ignored directories.
3. Detect text files by reading file content.
4. Apply case-insensitive substring replacements from `words`.
5. Apply path-based renames from `directory`.
6. Save the actual successful operations to `.cognito/encode-<timestamp>.json`.

Important implementation details:
- binary files are skipped
- only successfully applied operations are recorded in the manifest
- if a write or rename fails, the error is logged and the process continues

## How decode works

1. Read the latest manifest from `.cognito/`.
2. Reverse renames in reverse order.
3. Reverse text replacements from the manifest.
4. Write `.cognito/decode-<timestamp>.log`.

Important behavior:
- `decode` trusts the manifest and does not require the original config
- missing files or paths are logged as warnings
- filesystem errors are logged as errors
- conflicting reverse mappings are treated as decode errors

## Manifest and logs

### Manifest

`encode` writes:

```text
.cognito/encode-YYYYMMDDTHHMMSSZ.json
```

The manifest stores:
- operation id
- timestamp
- project root
- config snapshot
- successful file replacements
- successful rename operations
- warnings
- errors

### Decode log

`decode` writes:

```text
.cognito/decode-YYYYMMDDTHHMMSSZ.log
```

The log contains:
- source manifest name
- timestamp
- warning count
- error count
- warning lines
- error lines

## Exit codes

- `0` successful run with no errors
- `1` runtime errors or partial failures occurred
- `2` invalid CLI usage or invalid config

## Examples

### Encode a project

```bash
.venv/bin/cognito encode \
  --project /path/to/project \
  --config ~/.cognito/config.json \
  --silent
```

### Create the default config template

```bash
.venv/bin/cognito init-config
```

### Overwrite an existing config template

```bash
.venv/bin/cognito init-config --force
```

### Preview changes only

```bash
.venv/bin/cognito encode \
  --project /path/to/project \
  --config ~/.cognito/config.json \
  --silent \
  --dry-run
```

### Decode the latest manifest

```bash
.venv/bin/cognito decode \
  --project /path/to/project \
  --silent
```

## Development

### Common commands

```bash
make venv
make install
make test
make run-help
```

### Run tests directly

```bash
.venv/bin/pytest -q
```

## Project layout

```text
src/cognito/
  cli.py
  config.py
  constants.py
  engine.py
  fs.py
  models.py
  text.py
tests/
docs/
```

## Limitations

- only JSON config is supported
- text detection is heuristic-based
- replacement matching is case-insensitive but not word-boundary-aware
- replacement target casing is not auto-adjusted
- ambiguous reverse mappings cannot be decoded safely

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).
