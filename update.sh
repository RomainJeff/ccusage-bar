#!/bin/bash
# Manual update script for ccusage-bar
# This script pulls the latest code, rebuilds the app, and reinstalls it

cd "$(dirname "$0")"

echo "Checking for updates..."
git fetch origin main

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "Already up to date."
    exit 0
fi

echo "Update available! Pulling changes..."
git pull origin main

echo "Rebuilding app..."
./build.sh

echo "Quitting old app..."
osascript -e 'quit app "ccusage-bar"' 2>/dev/null || true
sleep 2

echo "Installing to /Applications..."
cp -r dist/ccusage-bar.app /Applications/

echo "Relaunching app..."
open /Applications/ccusage-bar.app

echo "✓ Update complete!"
