"""Corrections from Codex's all-class audit (Class-Research/codex/all-classes-2026-10-26, value-checks.csv).

Codex compared every live-package spell with the corrected daoc.gg reconstruction (its rebuild_live.py fixed this
pass's earlier cache, which lost nested patch fields). Of its 300 mismatch candidates, most are representation, not
errors: a child's reuse lives on its parent, a self buff carries no range, a cast timer of 1 is the client's instant,
the Track focus and the poison buffs are modelled differently. audit_corrections_data.py keeps the real ones:
  - cast times on the rule live timer / 1000 + 2 s, where an early package used other figures (the Paladin heals'
    x0.0046 pilot calibration, the Druid cures, the Dread Lord, the Bone Phantoms);
  - snares stored as the speed left instead of the slow (Champion Decelerate, Reaver Curse of Slowness line);
  - direct damage at x0.0992 where the Reaver package used x0.1;
  - Skald Soul Bolstering Chant/Song: a 30 s realm buff with a 4 s cast, not a pulsing group chant;
  - the Bone Army absorbs' 30 s and the Enchanter enchantments' 4,000 range.
Runs after the packages and the drift step, so a reinstall re-applies it. Each row names its spell; a row whose
SpellID no longer carries that name is refused rather than applied to another spell.
"""
from audit_corrections_data import CORRECTIONS

# Not in value-checks (the chant's live duration and the pulse fields have no checked counterpart there).
EXTRA = [(74027, 'Soul Bolstering Chant', 'Duration', 30, 'live duration 30 s'),
         *[(sid, name, column, 0, 'a 30 s buff, not a pulse') for sid, name in [(74027, 'Soul Bolstering Chant'), (74028, 'Soul Bolstering Song')]
           for column in ('Pulse', 'Frequency', 'RecastDelay')]]

# The Regrowth cures (rerun audit, Class-Research/claude/full-audit-2026-10-25-after-pets): live casts the Bard's and
# Warden's in 3.2 s (timer 1200) and the Druid's in 2.4 s (400). The base Regrowth line's rows (shared by all three)
# take the Bard/Warden time; the Druid keeps 2.4 s through the stock copies in its spec line, and those copies leave
# the Bard's spec line, where they gave the Bard a faster second cure at the same level.
EXTRA += [(75153, 'Cure Poison', 'CastTime', 3.2, 'Bard/Warden live cast timer 1200 ms + 2 s'),
          (75154, 'Cure Disease', 'CastTime', 3.2, 'Bard/Warden live cast timer 1200 ms + 2 s')]
UNLINKS = [('Regrowth Bard Spec', 4983, 'Cure Poison'), ('Regrowth Bard Spec', 4869, 'Cure Disease')]


def apply(db):
    applied = 0
    for spell_id, name, column, value, _ in CORRECTIONS + EXTRA:
        row = db.execute('select Name from Spell where SpellID=?', (spell_id,)).fetchone()
        if row is None or row[0] != name:
            raise ValueError(f'Correction for {name} expects SpellID {spell_id}, which holds {row and row[0]!r}')
        db.execute(f'update Spell set "{column}"=? where SpellID=?', (value, spell_id))
        applied += 1
    for line, spell_id, name in UNLINKS:
        row = db.execute('select Name from Spell where SpellID=?', (spell_id,)).fetchone()
        if row is None or row[0] != name:
            raise ValueError(f'Unlink of {name} expects SpellID {spell_id}, which holds {row and row[0]!r}')
        db.execute('delete from LineXSpell where LineName=? and SpellID=?', (line, spell_id))
    return dict(audit_corrections=applied, audit_unlinked=len(UNLINKS))
