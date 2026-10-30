#!/usr/bin/env bash
# world-editor.sh - open the World Workshop editor (DividedRealms) on this server's world, in your browser.
#
#   ./world-editor.sh [--client <DAoC 1.130 client folder>] [--port N] [--no-browser]
#
# The editor reads the client's art for its 3D views, so it needs your client folder (the one with game.dll). It is remembered in
# config/client.json (the admin screen's Client tab uses the same file). Stop the server first: the editor saves into the world
# database. Editor state (backups of every save, caches) is kept in editor-data/ inside this folder.
# The editor's collision-floor feature needs a Windows tool and is not available here.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAOC_HOME="${DAOC_HOME:-$HERE}"
die() { echo "world-editor: $*" >&2; exit 1; }

PY="$DAOC_HOME/python/bin/python3"
EDITOR="$DAOC_HOME/editor/source/tools/world_editor/editor.py"
[[ -x $PY && -f $EDITOR ]] || die "the editor is not part of this folder (editor/ is missing); rebuild with ./build.sh"
DB="$DAOC_HOME/data/opendaoc.sqlite3.db"
[[ -f $DB ]] || die "no world yet (data/opendaoc.sqlite3.db): start the server once first"

pid=$(cat "$DAOC_HOME/run/server.pid" 2>/dev/null || true)
[[ $pid =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null && die "the server is running (pid $pid). Stop it first: ./daoc-server.sh stop"

client=""; rest=()
while (($#)); do
  case "$1" in
    --client) client="${2:?--client needs a folder}"; shift 2 ;;
    *) rest+=("$1"); shift ;;
  esac
done
if [[ -z $client && -f $DAOC_HOME/config/client.json ]]; then
  client=$("$PY" -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("client",""))' "$DAOC_HOME/config/client.json" 2>/dev/null || true)
fi
[[ -n $client ]] || die "tell me where your client is: ./world-editor.sh --client \"/path/to/Dark Age of Camelot\" (or set it on the admin screen's Client tab)"
[[ -f $client/game.dll ]] || die "$client has no game.dll; it is not a DAoC client folder"

mkdir -p "$DAOC_HOME/editor-data"
export PYTHONDONTWRITEBYTECODE=1
exec "$PY" -I "$EDITOR" --db "$DB" --client "$client" --state "$DAOC_HOME/editor-data" ${rest[@]+"${rest[@]}"}
