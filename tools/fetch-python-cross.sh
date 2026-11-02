#!/usr/bin/env bash
# fetch-python-cross.sh <dest> <repo-root> - cross-build-safe equivalent of fetch-python.sh.
#
# fetch-python.sh populates site-packages by *executing* the freshly-unpacked linux-x64 CPython
# binary itself ("$DEST/bin/python3" -I -m pip install ...) - that only works when the build host
# can run linux-x64 ELF binaries natively. Used by build-release.sh instead of fetch-python.sh
# when CROSS_BUILD=1 (set by `build.sh --cross`, for a host that can't run linux-x64 binaries at
# all - e.g. macOS - or simply doesn't have root to install the system tools the normal path
# needs): this does the equivalent via `pip download` (resolves + downloads wheels for the
# *target* platform/abi/python-version without ever running them, using the host's own Python as
# a pure download client) on the host's own Python, then unpacks those wheels directly into the
# bundled CPython's site-packages - never executing anything from the target platform. Produces
# the exact same final layout and trimming as fetch-python.sh; only the dependency-installation
# mechanism differs.
set -euo pipefail

DEST="${1:?usage: fetch-python-cross.sh <dest> <repo-root>}"
REPO="${2:?usage: fetch-python-cross.sh <dest> <repo-root>}"
PBS_TAG="20261026"
PY_VERSION="3.12.16"
PY_MAJMIN="3.12"
ARCHIVE="cpython-${PY_VERSION}+${PBS_TAG}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
CACHE="$REPO/.cache/python"
WHEELCACHE="$REPO/.cache/python-wheels-linux-x64"
mkdir -p "$CACHE" "$WHEELCACHE"

if [[ ! -f $CACHE/$ARCHIVE ]]; then
  echo "   downloading Python $PY_VERSION"
  curl -fsSL -o "$CACHE/$ARCHIVE.part" "https://github.com/astral-sh/python-build-standalone/releases/download/$PBS_TAG/${ARCHIVE//+/%2B}"
  mv "$CACHE/$ARCHIVE.part" "$CACHE/$ARCHIVE"
fi

rm -rf "$DEST"
mkdir -p "$DEST"
tar -xzf "$CACHE/$ARCHIVE" -C "$DEST" --strip-components=1

SITE_PACKAGES="$DEST/lib/python$PY_MAJMIN/site-packages"
mkdir -p "$SITE_PACKAGES"

download_for_target() {
  python3 -m pip download --no-cache-dir --only-binary=:all: \
    --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64 --platform manylinux1_x86_64 \
    --python-version 312 --implementation cp --abi cp312 \
    -r "$1" -d "$WHEELCACHE" >/dev/null
}

echo "   resolving dependencies for linux-x64/cp312 (host does not run the target binary)"
download_for_target "$REPO/tui/requirements.txt"
if [[ ${WITH_EDITOR_DEPS:-1} == 1 ]]; then
  download_for_target "$REPO/tui/requirements-editor.txt"
fi

echo "   unpacking wheels into bundled site-packages"
for whl in "$WHEELCACHE"/*.whl; do
  case "$(basename "$whl")" in
    pip-*|setuptools-*|wheel-*) continue ;;  # not needed at run time, same as fetch-python.sh's own pip uninstall step
  esac
  python3 -m zipfile -e "$whl" "$SITE_PACKAGES" >/dev/null
done
rm -rf "$SITE_PACKAGES"/{pip,pip-*,setuptools,setuptools-*,wheel,wheel-*,pkg_resources} 2>/dev/null || true

rm -rf "$DEST/include" "$DEST/share"
rm -rf "$SITE_PACKAGES"/{idlelib,tkinter,turtledemo,lib2to3,ensurepip,pydoc_data,test,unittest/test} \
  "$SITE_PACKAGES"/lib-dynload/_tkinter* \
  "$DEST"/lib/{libtcl,libtk,tcl,tk}* "$DEST"/lib/itcl* "$DEST"/lib/thread* "$DEST"/bin/{idle*,pydoc*,2to3*} 2>/dev/null || true
# Deliberately skipped (needs the target's own interpreter, not available on this host):
# precompiling .pyc files. Harmless - Python compiles on first import if missing.
echo "   Python $PY_VERSION (cross-bundled, deps resolved for linux-x64/cp312) -> $DEST ($(du -sh "$DEST" | cut -f1))"
