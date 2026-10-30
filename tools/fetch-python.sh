#!/usr/bin/env bash
# fetch-python.sh <dest> - put a self-contained Python plus Textual (the admin screen) into <dest>.
#
# Uses a pinned python-build-standalone CPython (relocatable, built for glibc 2.17+), so the
# finished server folder needs no Python on the user's system. The download is cached in .cache/.
# Textual and its dependencies are pure Python, pinned in tui/requirements.txt.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:?usage: fetch-python.sh <dest>}"
PBS_TAG="20261026"
PY_VERSION="3.12.16"
ARCHIVE="cpython-${PY_VERSION}+${PBS_TAG}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
CACHE="$REPO/.cache/python"
mkdir -p "$CACHE"

if [[ ! -f $CACHE/$ARCHIVE ]]; then
  echo "   downloading Python $PY_VERSION"
  curl -fsSL -o "$CACHE/$ARCHIVE.part" "https://github.com/astral-sh/python-build-standalone/releases/download/$PBS_TAG/${ARCHIVE//+/%2B}"
  mv "$CACHE/$ARCHIVE.part" "$CACHE/$ARCHIVE"
fi

rm -rf "$DEST"
mkdir -p "$DEST"
tar -xzf "$CACHE/$ARCHIVE" -C "$DEST" --strip-components=1

# -I: ignore the user's PYTHONPATH and site-packages. Installs go into the bundled python only.
"$DEST/bin/python3" -I -m pip install --quiet --disable-pip-version-check --no-warn-script-location \
  -r "$REPO/tui/requirements.txt"
# World Workshop editor previews (Pillow, NumPy). WITH_EDITOR_DEPS=0 leaves them out (about 40 MB smaller).
if [[ ${WITH_EDITOR_DEPS:-1} == 1 ]]; then
  "$DEST/bin/python3" -I -m pip install --quiet --disable-pip-version-check --no-warn-script-location \
    -r "$REPO/tui/requirements-editor.txt"
fi
# Not needed at run time.
"$DEST/bin/python3" -I -m pip uninstall --quiet --yes pip setuptools 2>/dev/null || true
rm -rf "$DEST/include" "$DEST/share"
PYLIB="$DEST/lib/python3.12"
rm -rf "$PYLIB"/{idlelib,tkinter,turtledemo,lib2to3,ensurepip,pydoc_data,test,unittest/test} "$PYLIB"/lib-dynload/_tkinter* \
  "$DEST"/lib/{libtcl,libtk,tcl,tk}* "$DEST"/lib/itcl* "$DEST"/lib/thread* "$DEST"/bin/{idle*,pydoc*,2to3*} 2>/dev/null || true
# Pre-compile so the finished folder never has to write .pyc files.
"$DEST/bin/python3" -I -m compileall -q "$DEST/lib" || true
echo "   Python $("$DEST/bin/python3" -I -V | cut -d' ' -f2) + Textual $("$DEST/bin/python3" -I -c 'import importlib.metadata as m; print(m.version("textual"))') -> $DEST ($(du -sh "$DEST" | cut -f1))"
