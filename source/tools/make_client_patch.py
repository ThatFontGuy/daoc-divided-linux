"""Make the modern client patch that players apply to their own 1.130 client (no retail file ships).

    python make_client_patch.py <pristine 1.130 client folder> <client-patch.json>

Runs the hash-guarded class-slot patch (classslots/patch_class_slots.py: game.dll's native class slots 63-67 and
the creation screen's extra class buttons in pregame/character_creation.xml) on the pristine files, then records
only the edits (our hooks, section and added buttons, not Broadsword's bytes) with each file's input and output
SHA256. The launcher's client setup (OfflineDaoc.Launcher/ModernClientSetup.cs) copies the player's client and applies
these edits in order; it refuses any input that isn't the pristine 1.130 file. These two files and the splash below are
the only client files the modern test changes (a full hash comparison of the test client with a pristine 1.130 client,
2026-10-25, before the splash).

The loading screen, pregame/splash.mpk, is replaced whole by the Divided Realms splash (our own art,
OfflineDaoc.Launcher/Assets/divided-realms-client-splash.mpk): one edit that removes the stock archive and inserts ours,
guarded by the stock file's SHA256 like the others.
"""
import argparse
import base64
import difflib
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'classslots'))
import patch_class_slots  # noqa: E402

FORMAT = 1
CLIENT_VERSION = '1.130'
MERGE_GAP = 32  # in-place changes this close together are kept in one edit
SPLASH = Path(__file__).resolve().parent / 'OfflineDaoc.Launcher/Assets/divided-realms-client-splash.mpk'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def edits(original: bytes, patched: bytes):
    """(at, remove, insert): at an offset of the original, drop `remove` bytes and put `insert` there. Same-size files
    (game.dll grows only by its appended section) are compared in place; the layout's added buttons are an insertion,
    so it is compared by sequence and only the inserted text is kept."""
    if len(patched) >= len(original) and len(original) > 1 << 20:
        out, start, last = [], None, None
        for offset in range(len(original)):
            if original[offset] == patched[offset]:
                continue
            if start is not None and offset - last <= MERGE_GAP:
                last = offset
                continue
            if start is not None:
                out.append((start, last + 1 - start, patched[start:last + 1]))
            start = last = offset
        if start is not None:
            out.append((start, last + 1 - start, patched[start:last + 1]))
        if len(patched) > len(original):
            out.append((len(original), 0, patched[len(original):]))
        return out
    matcher = difflib.SequenceMatcher(None, original, patched, autojunk=False)
    return [(i1, i2 - i1, patched[j1:j2]) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != 'equal']


def apply(original: bytes, entry: dict) -> bytes:
    """The launcher's algorithm, for the tests: check the input, rebuild the output, check it."""
    if sha(original) != entry['InputSha256']:
        raise ValueError(f"{entry['Path']}: not the pristine {CLIENT_VERSION} file")
    out, position = bytearray(), 0
    for edit in entry['Edits']:
        out += original[position:edit['At']]
        out += base64.b64decode(edit['Insert'])
        position = edit['At'] + edit['Remove']
    out += original[position:]
    if len(out) != entry['OutputSize'] or sha(bytes(out)) != entry['OutputSha256']:
        raise ValueError(f"{entry['Path']}: the patched file doesn't match")
    return bytes(out)


def replace_whole(original: bytes, replacement: bytes):
    """One edit that swaps the whole file (the splash archive shares no bytes worth diffing with the stock one)."""
    return [(0, len(original), replacement)]


def build(client: Path, splash: Path = SPLASH) -> dict:
    game = (client / 'game.dll').read_bytes()
    layout = (client / 'pregame/character_creation.xml').read_bytes()
    stock_splash = (client / 'pregame/splash.mpk').read_bytes()
    patched_game, _ = patch_class_slots.patch(game)
    patched_layout = patch_class_slots.patch_layout(layout)
    our_splash = splash.read_bytes()
    files = []
    for path, original, patched, changes in [
            ('game.dll', game, patched_game, edits),
            ('pregame/character_creation.xml', layout, patched_layout, edits),
            ('pregame/splash.mpk', stock_splash, our_splash, replace_whole)]:
        entry = dict(Path=path, InputSha256=sha(original), OutputSha256=sha(patched), OutputSize=len(patched),
                     Edits=[dict(At=at, Remove=remove, Insert=base64.b64encode(block).decode('ascii')) for at, remove, block in changes(original, patched)])
        assert apply(original, entry) == patched
        files.append(entry)
    return dict(Format=FORMAT, ClientVersion=CLIENT_VERSION, Files=files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('client', type=Path, help='pristine 1.130 client folder (only read)')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    patch = build(args.client)
    args.output.write_text(json.dumps(patch, indent=1), encoding='utf-8')
    for entry in patch['Files']:
        print(entry['Path'], entry['InputSha256'][:12], '->', entry['OutputSha256'][:12],
              len(entry['Edits']), 'edits,', sum(len(base64.b64decode(e['Insert'])) for e in entry['Edits']), 'bytes')
