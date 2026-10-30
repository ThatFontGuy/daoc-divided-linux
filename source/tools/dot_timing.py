"""Live (1.130a) damage-over-time timing for the class lines (owner: "convert all damage-over-time spells to live's
duration and tick timing, same total damage").

This server's class DoTs ran twice live's duration with ticks half as often (Corrosive Mist: 20 s every 5 s here,
10 s every 2.5 s on live; the class library and the client data agree on live's). The tick count and the damage per
tick are the same either way, so the total is unchanged; live's just lands in half the time.
  - A DoT whose name has a live record (dot_timing_data.py, Codex's corrected reconstruction) takes live's duration and
    tick interval. Most are exactly half; a few live records also change the tick count, and those follow live.
  - An older rank with no live record keeps its ticks and damage at live's pace: the doubled layouts 24 s / 4 s and
    20 s / 5 s become 12 s / 2 s and 10 s / 2.5 s. Other layouts are left alone.
Left alone: item poisons (Mundane Poisons, already at live's 20 s / 3.9 s), item and style procs, the classic
Necromancer, the Death Knight session's classes and kits (hint 33/34/39/58/66, packages *-test-v1), and NPC spells.
A spell changes only while it is in an old layout or differs from live, so re-applying is stable.
"""
from dot_timing_data import LIVE

HALVE = {(24, 40): (12, 20), (20, 50): (10, 25)}
SKIP_LINES = ('Mundane Poisons', 'Item Effects', 'Combat Style Effects')
SKIP_HINTS = (12, 33, 34, 39, 58, 66)
NECROMANCER_SPECS = ('Deathsight', 'Painworking', 'Death Servant')


def spells(db):
    return db.execute(f"""select distinct s.SpellID, s.Name, s.Duration, s.Frequency from Spell s
        join LineXSpell l on l.SpellID=s.SpellID join SpellLine sl on sl.KeyName=l.LineName
        where s.Type='DamageOverTime' and coalesce(s.PackageID,'') not like '%-test-v1'
          and s.SpellID not in (select l2.SpellID from LineXSpell l2 join SpellLine sl2 on sl2.KeyName=l2.LineName
                                where l2.LineName in ({','.join('?' * len(SKIP_LINES))})
                                   or sl2.ClassIDHint in ({','.join('?' * len(SKIP_HINTS))})
                                   or (sl2.Spec in ({','.join('?' * len(NECROMANCER_SPECS))}) and sl2.ClassIDHint in (0, 12)))""",
                      (*SKIP_LINES, *SKIP_HINTS, *NECROMANCER_SPECS)).fetchall()


def apply(db):
    live = halved = already = left = 0
    for spell_id, name, duration, frequency in spells(db):
        target = LIVE.get(name) or HALVE.get((duration, frequency))
        if target is None:
            left += 1
            continue
        if (duration, frequency) == tuple(target) or (name not in LIVE and (duration, frequency) in HALVE.values()):
            already += 1
            continue
        db.execute('update Spell set Duration=?, Frequency=? where SpellID=?', (*target, spell_id))
        if name in LIVE:
            live += 1
        else:
            halved += 1
    return dict(dot_timing_live=live, dot_timing_halved=halved, dot_timing_already=already, dot_timing_left=left)
