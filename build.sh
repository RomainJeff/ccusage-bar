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

echo "Copying OpenSSL libraries..."
OPENSSL_PREFIX=$(brew --prefix openssl@3 2>/dev/null || echo "/opt/homebrew/opt/openssl@3")
if [ -f "$OPENSSL_PREFIX/lib/libssl.3.dylib" ]; then
    cp "$OPENSSL_PREFIX/lib/libssl.3.dylib" dist/ccusage-bar.app/Contents/Frameworks/
    cp "$OPENSSL_PREFIX/lib/libcrypto.3.dylib" dist/ccusage-bar.app/Contents/Frameworks/
    codesign --force --sign - dist/ccusage-bar.app/Contents/Frameworks/libssl.3.dylib
    codesign --force --sign - dist/ccusage-bar.app/Contents/Frameworks/libcrypto.3.dylib
    echo "OpenSSL libraries copied and signed"
else
    echo "Warning: OpenSSL 3 not found at $OPENSSL_PREFIX"
fi

codesign --force --sign - dist/ccusage-bar.app

echo "Done! App at dist/ccusage-bar.app"
