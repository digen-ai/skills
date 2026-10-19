#!/bin/bash
# Install the Digen CLI (which includes `digen skill`) via npm.

set -e

if ! command -v node &> /dev/null; then
    echo "Error: node not found. Install Node.js >=20 first: https://nodejs.org/"
    exit 1
fi

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 20 ]; then
    echo "Error: Node.js >=20 is required (found $(node -v))"
    exit 1
fi

if command -v digen &> /dev/null; then
    echo "==> digen is already installed: $(command -v digen)"
else
    echo "==> Installing digen-cli"
    if [ -n "${DIGEN_CLI_DIR:-}" ]; then
        npm install -g "$DIGEN_CLI_DIR"
    else
        npm install -g digen-cli
    fi
fi

echo ""
echo "✓ Install complete"
echo ""
echo "Verify:  digen skill --help"
echo "Config:  digen login && digen config show"
echo "Upgrade: npm install -g digen-cli@latest"
echo "Remove:  npm uninstall -g digen-cli"
