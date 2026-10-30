"""Enable normal expansion-race choices in the isolated modern test only.

Preview by default; --apply backs up and updates creation settings/start locations.
Never changes player records, starts a server or enables additional classes.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import socket
import sqlite3

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO/'artifacts/modern-client-test'
DB = ROOT/'runtime/data/opendaoc.sqlite3.db'
RULES = REPO/'source/server/GameServer/gameutils/modern-races-1130.json'


def parse_ids(raw):
    result = set()
    for part in raw.split(';'):
        if not part.strip():
            continue
        pair = part.split('-')
        result.update(range(int(pair[0]), int(pair[-1])+1))
    return result


def update(database, registrations):
    database.row_factory = sqlite3.Row
    database.execute('BEGIN IMMEDIATE')
    before = dict(database.execute("SELECT Key,Value FROM ServerProperty WHERE lower(Key) IN ('disabled_races','disabled_classes','enable_modern_races')"))
    if 'disabled_races' not in before or 'disabled_classes' not in before:
        raise ValueError('Missing creation settings')
    disabled = parse_ids(before['disabled_classes'])
    inserted = []
    covered = set()
    for entry in registrations:
        career, realm = entry['Class'], entry['Realm']
        if career in disabled:
            continue
        for race in entry['Races']:
            covered.add(race)
            if database.execute('SELECT 1 FROM StartupLocation WHERE RealmID=? AND ClassID=? AND RaceID=? AND MinVersion=1130 AND ClientRegionID=0', (realm, career, race)).fetchone():
                continue
            reference = database.execute('''SELECT * FROM StartupLocation WHERE RealmID=? AND ClassID=?
                AND MinVersion<=1130 AND ClientRegionID=0 AND Region>0 AND XPos>0 AND YPos>0
                ORDER BY (Region!=?),MinVersion,StartupLoc_ID LIMIT 1''', (realm, career, {1: 1, 2: 100, 3: 200}[realm])).fetchone()
            if reference is None:
                raise ValueError(f'No safe class start for realm {realm}, class {career}')
            row = dict(reference)
            row.pop('StartupLoc_ID')
            row.update(RaceID=race, MinVersion=1130, ClientRegionID=0)
            fields = list(row)
            cursor = database.execute('INSERT INTO StartupLocation ('+','.join('"'+f+'"' for f in fields)+') VALUES ('+','.join('?' for _ in fields)+')', [row[f] for f in fields])
            inserted.append(cursor.lastrowid)
    if covered != set(range(16, 22)):
        raise ValueError('Not every expansion race has an enabled class')
    remaining = ';'.join(str(x) for x in sorted(parse_ids(before['disabled_races'])-set(range(16, 22))))
    database.execute("UPDATE ServerProperty SET Value=? WHERE lower(Key)='disabled_races'", (remaining,))
    if not database.execute("UPDATE ServerProperty SET Value='True' WHERE lower(Key)='enable_modern_races'").rowcount:
        database.execute('''INSERT INTO ServerProperty (ServerProperty_ID,Key,Value,DefaultValue,Category,Description)
            VALUES ('local-enable-modern-races','enable_modern_races','True','False','classes','Normal expansion-race creation for the private modern client test')''')
    if database.execute('PRAGMA foreign_key_check').fetchone() is not None:
        raise ValueError('Foreign-key check failed')
    if database.execute("SELECT Value FROM ServerProperty WHERE lower(Key)='disabled_classes'").fetchone()[0] != before['disabled_classes']:
        raise ValueError('Class restrictions changed unexpectedly')
    return {'PreviousProperties': before, 'DisabledRaces': remaining, 'InsertedStartupLocations': inserted,
            'ExpansionRaces': sorted(covered), 'PlayerRecordsChanged': False, 'ServerStarted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    registrations = json.loads(RULES.read_text())
    if not DB.is_file():
        raise SystemExit('Isolated test database missing')
    with socket.socket() as check:
        if check.connect_ex(('127.0.0.1', 10330)) == 0:
            raise SystemExit('Close the modern test server before updating creation settings')
    with sqlite3.connect(DB.as_uri()+'?mode=ro', uri=True) as source:
        if args.apply:
            folder = ROOT/'backups'
            folder.mkdir(exist_ok=True)
            backup = folder/('pre-modern-races-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3.db')
            with sqlite3.connect(backup) as dest:
                source.backup(dest)
        else:
            preview = sqlite3.connect(':memory:')
            source.backup(preview)
    with sqlite3.connect(DB) if args.apply else preview as database:
        report = update(database, registrations)
        database.commit()
        # A second migration must leave the starting-location count unchanged.
        repeated = update(database, registrations)
        if repeated['InsertedStartupLocations']:
            raise ValueError('Migration is not idempotent')
        database.rollback()
    report['Applied'] = args.apply
    if args.apply:
        report['Backup'] = str(backup)
        (ROOT/'modern-races-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
