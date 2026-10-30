"""Live (1.130a) values for existing stock spells. spell_drift_data.py is made by two scratch generators:
  - gen_drift.py: power, range, radius, duration and recast, where both sides use the same unit. It left out damage
    over time and pulsing or concentration durations, flat vs percentage power, a zero local range/radius/duration,
    durations more than 4x apart and permanent effects.
  - gen_drift2.py: from daoc.gg's raw records matched by name per class, direct damage at the median scale of all the
    shared spells (DD_SCALE, tenths), lifedrains and damage shields in tenths, damage over time and heal/regen values
    1:1, cast times (live's timer + 2 s, instant 0; the data's 1 ms placeholder is unknown) and line levels (LEVELS; a
    list line's level only when it is free). Damage changes beyond 0.5-2x and value changes beyond 0.6-1.6x are a
    different model and were left out.
  - gen_drift3.py (DRIFT_V3, applied after DRIFT): the same damage, heal and cast rules on Codex's corrected
    reconstruction (Class-Research/codex/all-classes-2026-10-26; the earlier cache lost nested patch fields, so
    e.g. Major Constricting Blast missed 1.129b), plus armor-factor, stat, absorb and resist buff values, debuff values,
    haste values and snares (the slow = 100 - live's speed left), live bonus 1:1 within 0.4-2.5x. The classic
    Necromancer and the Death Knight session's classes (Bainshee, Vampiir, Heretic, Valkyrie) are left out.
All skip pet, summon, proc and storm spells, the custom classes' rows and shared spells the classes disagree on. A
value changes only while the world still holds the old local one, so a later edit of that spell is left alone.
"""
from spell_drift_data import DRIFT, DRIFT_V3, LEVELS
from audit_corrections import UNLINKS

# Level moves for links the audit corrections retire (they run after this step, so a reinstall finds the link gone).
RETIRED = {(spell_id, line) for line, spell_id, _ in UNLINKS}

COLUMNS = {'Power', 'Range', 'Radius', 'Duration', 'RecastDelay', 'Damage', 'Value', 'CastTime'}


def apply(db):
    live = kept = 0
    for spell_id, column, old, new in DRIFT + DRIFT_V3:
        if column not in COLUMNS:
            raise ValueError('Unexpected column ' + column)
        row = db.execute(f'select "{column}" from Spell where SpellID=?', (spell_id,)).fetchone()
        if row is None:
            kept += 1
            continue
        if row[0] == old:
            db.execute(f'update Spell set "{column}"=? where SpellID=?', (new, spell_id))
            live += 1
        elif row[0] == new:
            live += 1
        else:
            kept += 1
    levels = levels_kept = 0
    for spell_id, line, old, new in LEVELS:
        if (spell_id, line) in RETIRED:
            continue
        row = db.execute('select Level from LineXSpell where SpellID=? and LineName=?', (spell_id, line)).fetchone()
        if row is not None and row[0] == old:
            db.execute('update LineXSpell set Level=? where SpellID=? and LineName=?', (new, spell_id, line))
            levels += 1
        elif row is not None and row[0] == new:
            levels += 1
        else:
            levels_kept += 1
    return dict(drift_values_live=live, drift_values_left=kept, drift_levels_live=levels, drift_levels_left=levels_kept)
