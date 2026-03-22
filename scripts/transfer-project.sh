#!/bin/sh

set -eu

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

require_cmd git
require_cmd cognito
require_cmd zip

printf 'Project directory path: '
IFS= read -r project_input

[ -n "$project_input" ] || fail "Project directory path is required."
[ -d "$project_input" ] || fail "Directory does not exist: $project_input"

project_dir=$(cd "$project_input" && pwd -P)
project_name=$(basename "$project_dir")
timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
branch_name="feature/cognito-transfer-$timestamp"
commit_message="chore: apply cognito transfer"
zip_name="${project_name}-transfer-${timestamp}.zip"
downloads_dir="${HOME}/Downloads"
archive_path="${downloads_dir}/${zip_name}"

[ -d "$downloads_dir" ] || fail "Downloads directory does not exist: $downloads_dir"

git -C "$project_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "Directory is not a git repository: $project_dir"

if ! git -C "$project_dir" diff --quiet || ! git -C "$project_dir" diff --cached --quiet; then
  fail "Git working tree is dirty. Commit or stash existing changes before running this script."
fi

if [ -n "$(git -C "$project_dir" status --porcelain --untracked-files=normal)" ]; then
  fail "Git working tree has untracked files. Commit, remove, or ignore them before running this script."
fi

current_branch=$(git -C "$project_dir" rev-parse --abbrev-ref HEAD)
[ "$current_branch" != "HEAD" ] || fail "Repository is in detached HEAD state."

printf 'Creating branch %s\n' "$branch_name"
git -C "$project_dir" checkout -b "$branch_name"

printf 'Running cognito in %s\n' "$project_dir"
if [ -n "${COGNITO_CONFIG:-}" ]; then
  cognito encode --project "$project_dir" --config "$COGNITO_CONFIG" --silent
else
  cognito encode --project "$project_dir" --silent
fi

git -C "$project_dir" add -A

if git -C "$project_dir" diff --cached --quiet; then
  fail "cognito did not produce any changes to commit."
fi

printf 'Creating commit\n'
git -C "$project_dir" commit -m "$commit_message"

tmp_dir=$(mktemp -d)
trap 'rm -rf "$tmp_dir"' EXIT INT TERM
tmp_archive="${tmp_dir}/${zip_name}"

printf 'Creating archive %s\n' "$tmp_archive"
(
  cd "$project_dir"
  zip -rq "$tmp_archive" . \
    -x ".git/*" \
    -x "build/*" \
    -x "build"
)

cp "$tmp_archive" "$archive_path"

printf 'Done.\n'
printf 'Branch: %s\n' "$branch_name"
printf 'Archive: %s\n' "$archive_path"
