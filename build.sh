#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Cleaning..."
rm -rf build dist

echo "Building..."
python3 setup.py py2app

echo "Fixing libffi..."
LIBFFI_SRC=$(python3 -c "import ctypes.util, os; p=ctypes.util.find_library('ffi'); print(os.path.realpath(p))")
cp "$LIBFFI_SRC" dist/ccusage-bar.app/Contents/Resources/lib/libffi.8.dylib
codesign --force --sign - dist/ccusage-bar.app/Contents/Resources/lib/libffi.8.dylib
codesign --force --sign - dist/ccusage-bar.app

echo "Done! App at dist/ccusage-bar.app"
