#!/usr/bin/env bash
# sync-upstream.sh [--check] [<upstream-ref>]   bring a newer DividedRealms into this repo.
#
# Upstream's history is squashed, so ours is separate from theirs and `git merge` cannot be used. Instead:
#   1. read the upstream commit we last merged ("Merged-upstream:" in UPSTREAM.md),
#   2. take upstream's diff from that commit to <upstream-ref> (default upstream/main), minus tools/upstream-exclude.txt,
#   3. apply it with `git apply --3way`, so our own edits (marked "daoc-divided-linux:") merge in and clashes show as conflicts.
# --check only shows what would change. Run it on a new branch with a clean tree. Afterwards: resolve conflicts, hand-merge the
# two .csproj files if upstream changed them, build, run the tests, then update "Merged-upstream:" in UPSTREAM.md (the script
# prints the line). See UPSTREAM.md, "Syncing a new upstream".
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
check=false; [[ ${1:-} == --check ]] && { check=true; shift; }
ref="${1:-upstream/main}"

base=$(sed -n 's/^Merged-upstream: *\([0-9a-f]\{7,40\}\).*/\1/p' UPSTREAM.md | head -1)
[[ -n $base ]] || { echo "sync-upstream: no 'Merged-upstream: <sha>' line in UPSTREAM.md" >&2; exit 1; }
git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/rambodolphin13/DividedRealms.git
git fetch --filter=blob:none upstream main >/dev/null 2>&1 || git fetch upstream main
target=$(git rev-parse --verify "$ref^{commit}")
git cat-file -e "$base^{commit}" 2>/dev/null || { echo "sync-upstream: base $base is not in this clone; fetch it: git fetch upstream $base" >&2; exit 1; }

excl=()
while IFS= read -r line; do
  line="${line%%#*}"; line="${line//[[:space:]]/}"
  [[ -n $line ]] && excl+=(":!$line")
done < tools/upstream-exclude.txt

echo "Upstream: $base -> ${target:0:7}"
if $check; then
  git diff --stat "$base" "$target" -- . "${excl[@]}" | tail -25
  exit 0
fi

[[ -z $(git status --porcelain --untracked-files=no) ]] || { echo "sync-upstream: commit or stash your changes first" >&2; exit 1; }
[[ $(git rev-parse --abbrev-ref HEAD) != main ]] || { echo "sync-upstream: do this on a branch, not main" >&2; exit 1; }

patch="$(mktemp)"; trap 'rm -f "$patch"' EXIT
git diff --binary "$base" "$target" -- . "${excl[@]}" > "$patch"
[[ -s $patch ]] || { echo "Nothing new upstream."; exit 0; }
git apply --3way --whitespace=nowarn "$patch" || echo "(conflicts above: fix the files marked U in git status)"

echo
echo "-- Cut-out features that upstream may have wired back in (must stay empty):"
grep -rn "PassportLock\|PassportDesk\.\|OfflineDaoc\.Passport\|OfflineDaoc\.TestClient" source/server --include=*.cs --include=*.csproj || echo "   none"
echo
echo "-- Files upstream changed that we also changed (check these):"
git diff --name-only --diff-filter=U
echo
echo "Next: build + tests, then set in UPSTREAM.md:   Merged-upstream: ${target}"
