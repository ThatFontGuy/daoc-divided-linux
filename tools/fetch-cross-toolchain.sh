#!/usr/bin/env bash
# fetch-cross-toolchain.sh <cache-dir> - a complete, no-root build toolchain for linux-x64, for any
# host that can't (or shouldn't need to) install system compilers: cmake, ninja and a zig-based
# C/C++ cross-compiler targeting glibc 2.34 (this project's own documented minimum), all via pip
# wheels - no sudo, no Homebrew/apt/dnf, no system g++/make. Works equally on macOS (which has no
# native way to produce linux-x64 binaries at all) and on a Linux host that simply has no root
# access to install build-essential (confirmed need: the very box this project's own server runs
# on can be exactly such a host).
#
# Used by build-release.sh when CROSS_BUILD=1 (set by `build.sh --cross`) instead of requiring a
# system cmake/g++. Safe to re-run; only fetches what is missing. Prints
# "<cmake-binary>|<ninja-binary>|<toolchain-file>" on its last line for the caller to use.
set -euo pipefail

DEST="${1:?usage: fetch-cross-toolchain.sh <cache-dir>}"
mkdir -p "$DEST"
PY="$(command -v python3)"

if [[ ! -e $DEST/.installed ]]; then
  echo "   installing cmake, ninja, zig (pip wheels, no root needed)" >&2
  "$PY" -m pip install --quiet --disable-pip-version-check --target "$DEST/pylibs" cmake ninja ziglang
  touch "$DEST/.installed"
fi

# The "cmake"/"ninja" console-script shims pip writes to pylibs/bin need their own package on
# PYTHONPATH to run at all (they're thin Python wrappers, not the real binaries) - cmake's real
# native binary lives one level deeper (its wheel bundles a full separate install tree); ninja's
# own pip wheel happens to *be* the real native binary already, directly executable.
CMAKE_BIN="$(find "$DEST/pylibs/cmake" -type f -name cmake -perm -u+x | head -1)"
NINJA_BIN="$DEST/pylibs/bin/ninja"
[[ -x $CMAKE_BIN && -x $NINJA_BIN ]] || { echo "fetch-cross-toolchain: could not locate cmake/ninja after install" >&2; exit 1; }

# ziglang ships only its own compiler driver, no bundled interpreter - `-m ziglang` always runs
# under whatever python3 invokes it, so the wrapper needs PYTHONPATH pointed at pylibs (pip
# --target never puts a package on the default search path by itself, unlike a real site-packages
# install) and the host's own real python3 binary path baked in.
mkdir -p "$DEST/bin"
for pair in "cc:x86_64-linux-gnu-cc" "c++:x86_64-linux-gnu-c++"; do
  mode="${pair%%:*}"; name="${pair##*:}"
  cat > "$DEST/bin/$name" << EOF
#!/bin/sh
PYTHONPATH="$DEST/pylibs\${PYTHONPATH:+:\$PYTHONPATH}" exec "$PY" -m ziglang $mode -target x86_64-linux-gnu.2.34 "\$@"
EOF
  chmod +x "$DEST/bin/$name"
done

cat > "$DEST/toolchain-linux-x64.cmake" << EOF
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR x86_64)
set(CMAKE_C_COMPILER $DEST/bin/x86_64-linux-gnu-cc)
set(CMAKE_CXX_COMPILER $DEST/bin/x86_64-linux-gnu-c++)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
EOF

echo "$CMAKE_BIN|$NINJA_BIN|$DEST/toolchain-linux-x64.cmake"
