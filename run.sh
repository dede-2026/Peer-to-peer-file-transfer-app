#!/usr/bin/env bash
# SimpleShare launcher for Linux / macOS
set -e

# Move to the folder this script lives in
cd "$(dirname "$0")"

# Check Python 3 is available
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "❌  Python 3 not found. Please install it from https://python.org"
    exit 1
fi

VER=$($PY -c "import sys; print(sys.version_info.major)")
if [ "$VER" -lt 3 ]; then
    echo "❌  Python 3 is required (found Python $VER)"
    exit 1
fi

echo "✅  Using $($PY --version)"
exec $PY simpleshare.py "$@"
