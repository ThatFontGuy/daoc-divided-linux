"""The client's own art for the live packages' spells (Class-Research/codex/followup-2026-10-25, ANSWERS-D-E-CLIENT.md).

Every spell the live packages add first borrows the effect and icon of a nearby local spell. Where the client's
gamedata.mpk!spells.csv has exactly one row of the same name (case and spacing ignored), that row's ID is the client's
own effect and icon for it, and this step uses it for ClientEffect and Icon. live_spell_art_data.py lists those names;
ambiguous and unmatched names keep their borrowed art. Nothing in the client changes: these are existing client IDs.
Runs after the packages, so a reinstall re-applies it.
"""
from live_spell_art_data import ART

PACKAGES = "local-%-live-v1"


def apply(db):
    changed = 0
    for name, client_id in ART.items():
        changed += db.execute('update Spell set ClientEffect=?, Icon=? where Name=? and PackageID like ? and (ClientEffect<>? or Icon<>?)',
                              (client_id, client_id, name, PACKAGES, client_id, client_id)).rowcount
    using = db.execute(f"select count(*) from Spell where PackageID like ? and Name in ({','.join('?' * len(ART))}) and ClientEffect=Icon",
                       (PACKAGES, *ART)).fetchone()[0]
    return dict(art_names=len(ART), art_spells_using_client_art=using)
