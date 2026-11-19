#!/usr/bin/env bash
# FramePilot - one-click start for Mac and Linux.
# First run: checks Python and sets up a private Python folder (.venv) and desktop packages.
# Every run opens FramePilot in its own desktop window.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

say()  { printf "  %s\n" "$1"; }
fail() { printf "\n  \033[31m%s\033[0m\n\n" "$1"; exit 1; }
echo; say "=== FramePilot ==="; echo

if [ "$(uname)" = "Darwin" ] && [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
if [ "$(uname)" = "Darwin" ] && [ -x /usr/local/bin/brew ]; then eval "$(/usr/local/bin/brew shellenv)"; fi

find_python() {
  for p in python3.12 python3.11 python3.13 python3.10 python3; do
    if command -v "$p" >/dev/null 2>&1 &&
       "$p" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] < (3,14) else 1)' 2>/dev/null; then
      echo "$p"; return
    fi
  done
}

PY="$(find_python)"
if [ -z "$PY" ]; then
  if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    say "Python 3.10+ not found. Installing Python 3.12 with Homebrew..."
    brew install python@3.12
    PY="$(find_python)"
  fi
  [ -n "$PY" ] || {
    if [ "$(uname)" = "Darwin" ]; then
      open "https://www.python.org/downloads/release/python-3129/" 2>/dev/null || true
      fail "Install Python 3.12 from the page that just opened, then run this again."
    else
      fail "Python 3.10+ is needed. Install it (for example: sudo apt install python3 python3-venv), then run this again."
    fi
  }
fi
say "Python: $($PY --version)"

if [ ! -x .venv/bin/python ]; then
  say "Setting up (one time)..."
  "$PY" -m venv .venv || fail "Could not create the Python environment (on Linux: sudo apt install python3-venv)."
fi
HASH="$("$PY" -c 'import hashlib,sys; print(hashlib.sha256(open("requirements-desktop.txt","rb").read()).hexdigest())')"
if [ ! -f .venv/requirements.sha ] || [ "$(cat .venv/requirements.sha)" != "$HASH" ]; then
  say "Installing packages (one time, a few minutes)..."
  .venv/bin/python -m pip install --upgrade pip --disable-pip-version-check -q
  .venv/bin/python -m pip install -r requirements-desktop.txt --disable-pip-version-check || fail "Installing packages failed. Check your internet connection and run this again."
  if [ "$(uname)" != "Darwin" ]; then
    .venv/bin/python -m pip install PyGObject --disable-pip-version-check || fail "Install the Linux GTK and WebKit development libraries, then run FramePilot again."
  fi
  echo "$HASH" > .venv/requirements.sha
fi

echo
say "Opening FramePilot. The first start downloads the speech model (about 480 MB, once)."
say "Close the FramePilot window when you are finished."
echo
export PYTHONWARNINGS="ignore::DeprecationWarning"
exec .venv/bin/python -m studio.desktop
