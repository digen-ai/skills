#!/bin/bash
# Install the user-side skill CLI (digenskill) via uv tool install

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# skills/skill-creator/scripts -> repo root
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLI_DIR="$REPO_ROOT/cli"

echo "==> Installing digen-skill-cli (digenskill)"
echo "CLI directory: $CLI_DIR"

if [ ! -f "$CLI_DIR/pyproject.toml" ]; then
    echo "Error: $CLI_DIR/pyproject.toml not found"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: uv command not found"
    echo "Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

uv tool install --force --editable "$CLI_DIR"

echo ""
echo "✓ Install complete"
echo ""
echo "Verify:  digenskill --help"
echo "Config:  digenskill config set-api https://api.digen.ai && digenskill login"
echo "Upgrade: uv tool upgrade digen-skill-cli"
echo "Remove:  uv tool uninstall digen-skill-cli"
