"""Live (1.130a) assassin poisons: the Envenom spell line of the Infiltrator, Shadowblade and Nightshade.

From daoc.gg's client spell data (PLAYER_POISONS, the same 32 spells for all three classes) and the dated patches
through 1.130a, checked against the official notes (1.125: poisons became Envenom proc buffs; 1.126 and 1.128c reuse
timers; 1.128 snare durations):
  - Each poison is an instant self buff (PoisonCoating) whose poison fires on melee hits (100%); landing it leaves the
    buff active (official 1.121). One poison buff at a time: they share an effect group, so a new one replaces the old.
    All coatings share one reuse (the client's use_timer 5): 10 s for ranks below 20, 9 s for 20-29, 8 s for 30-39,
    7 s for 40+, and 7 s for Crippling Toxin (1.125). Tranquilizing Gas and Miasma have their own (150 s and 120 s since 1.128c).
  - How long the buff lasts isn't in any source found (Codex 2026-10-25): here it's 60 minutes.
  - Lethal Poison/Venom, Lifebane: Body DoT every 3.9 s for 20 s, 9 to 82 a tick.
  - Essence of Lethargy, Swordbreaker: melee damage -3/5/7/10/15% for 20 s.
  - Widow Sting/Toxin/Venom: a 15 s disease (the server's disease: slow, strength and healing cut); Widow Venom also
    cuts melee resists 5% for 15 s (1.126).
  - Weakening/Inhibiting/Enervating/Unnerving Poison, Touch of Death: weaponskill -5/8/10/14/21% for 30 s.
  - Crippling Toxin, Snaring Toxin, Shadowbind: 15/35/60% snares for 3/5/7 s (1.128) that last through damage and
    ignore snare immunity.
  - Tranquilizing Gas / Miasma: mez within 350 / 700 of the target for 5 / 8 s. (The client's 1 s disarm link isn't
    built: it ends inside the mez.)
  - Consume Venom (Envenom 50): removes the assassin's own DoTs, 5 min reuse.
The Envenom spec becomes a hybrid spec (only the best rank of each poison shows). The lines are class-hinted so the
item poisons' Mundane Poisons line (also Envenom, no class hint) stays out of the spell list.

Live Stealth-line spells on existing handlers, in class-hinted Stealth lines (Stealth is already a hybrid spec):
  - Nightshade Eventide Resonance..Reflection (10-50): a 20-minute self damage shield, 1/2/3/4/5 a hit (live's tenths),
    3 s cast.
  - Nightshade Clouded Agony/Distress/Pain/Destruction (15-46): an instant DoT, 4/8/14/22 a tick, 500 range, 30 s reuse
    (the caster DoTs' doubled timing: 48 s, every 8 s).
  - Shadowblade Bludgeon (10): for 30 s melee hits deal crush damage, 3 min reuse.
  - Caltrops (Stealth 35, all three): spikes at the assassin's feet for 20 minutes; every second enemies within 350 are
    snared 25% for 30 s (snare immunity applies); 10 min reuse.
  - Heightened Awareness (Stealth 45; the Hunter's, Scout's and Ranger's at 30): a group pulse (every 5.5 s, 1,500 range) of +10% stealth
    detection that, unlike Track, survives moving; 3 s cast.
  - Blur (Stealth 40, all three): teleports to a player within 1,000, usable while rooted (1.121); 90 s reuse.
Not built: Overshadow (temporary stealth for an ally).
"""
import math
import sqlite3
import hybrid_lines

PACKAGE = 'local-envenom-live-v1'
FIRST, LAST = 77400, 77499
TOOLTIP_BASE = 20900  # 20900-20999 are unused; 23200-23999 is the Death Knight's reserved block
RESERVED_TOOLTIPS = (23200, 23999)
GROUP_BASE = 77400
COATING_TIMER, MEZ_TIMER = 77498, 77499
HYBRID = 'DOL.GS.LiveSpellHybridSpecialization'
LINES = [('Infiltrator Envenom', 9), ('Shadowblade Envenom', 23), ('Nightshade Envenom', 49)]
BODY, SPIRIT = 10, 15
COATING_DURATION = 3600
COATING_EFFECT_GROUP = 77497  # one poison buff at a time


def reuse(level):
    return 7 if level >= 40 else 8 if level >= 30 else 9 if level >= 20 else 10


def weaponskill(percent):
    """WeaponSkillPercentCalculator divides a weaponskill debuff by 5.4."""
    return math.ceil(percent * 5.4) + 1


# (family, art SpellID, child fields, ranks: (level, name, child values[, parent overrides]))
FAMILIES = [
    ('Lethal', 30000, dict(Type='DamageOverTime', Duration=20, Frequency=39, DamageType=BODY, Range=1500),
     [(lv, name, dict(Damage=d)) for lv, name, d in [
         (1, 'Minor Lethal Poison', 9), (5, 'Lesser Lethal Poison', 15), (10, 'Lethal Poison', 22), (15, 'Major Lethal Poison', 29),
         (20, 'Greater Lethal Poison', 36), (25, 'Minor Lethal Venom', 36), (30, 'Lesser Lethal Venom', 38), (35, 'Major Lethal Venom', 42),
         (40, 'Greater Lethal Venom', 50), (45, 'Insidious Lethal Venom', 68), (50, 'Lifebane', 82)]]),
    ('Lethargy', 8101, dict(Type='MeleeDamageDebuff', Duration=20, DamageType=BODY, Range=1500),
     [(lv, name, dict(Value=v)) for lv, name, v in [
         (3, 'Minor Essence of Lethargy', 3), (13, 'Weak Essence of Lethargy', 5), (23, 'Essence of Lethargy', 7),
         (33, 'Major Essence of Lethargy', 10), (43, 'Swordbreaker', 15)]]),
    ('Widow', 30003, dict(Type='Disease', Duration=15, DamageType=BODY, Range=1500),
     [(lv, name, dict(Value=v)) for lv, name, v in [
         (4, 'Minor Widow Sting', 5), (16, 'Widow Sting', 10), (26, 'Widow Toxin', 15), (38, 'Major Widow Toxin', 20)]] +
     [(48, 'Widow Venom', dict(Value=25, Extra=dict(Type='CrushSlashThrustDebuff', Name="Widow's Bite", Target='Enemy', Value=5,
                                                    Duration=15, Range=1500, DamageType=BODY)))]),
    ('Weakening', 30001, dict(Type='WeaponSkillDebuff', Duration=30, DamageType=BODY, Range=1500),
     [(lv, name, dict(Value=weaponskill(p))) for lv, name, p in [
         (7, 'Weakening Poison', 5), (17, 'Inhibiting Poison', 8), (27, 'Enervating Poison', 10), (37, 'Unnerving Poison', 14),
         (47, 'Touch of Death', 21)]]),
    ('Snare', 30022, dict(Type='PoisonSnare', DamageType=BODY, Range=1500),
     [(9, 'Crippling Toxin', dict(Value=15, Duration=3), dict(RecastDelay=7)), (29, 'Snaring Toxin', dict(Value=35, Duration=5)),
      (49, 'Shadowbind', dict(Value=60, Duration=7))]),
    ('Tranquilize', 40013, dict(Type='Mesmerize', DamageType=SPIRIT, Range=350),
     [(18, 'Tranquilizing Gas', dict(Radius=350, Duration=5), dict(RecastDelay=150, SharedTimerGroup=MEZ_TIMER)),
      (46, 'Tranquilizing Miasma', dict(Radius=700, Duration=8), dict(RecastDelay=120, SharedTimerGroup=MEZ_TIMER))]),
]

STEALTH_LINES = [('Nightshade Stealth', 49), ('Shadowblade Stealth', 23), ('Infiltrator Stealth', 9), ('Hunter Stealth', 25),
                 ('Scout Stealth', 3), ('Ranger Stealth', 50)]
ASSASSIN_STEALTH = ('Infiltrator Stealth', 'Shadowblade Stealth', 'Nightshade Stealth')
FEET = 2  # TimedPulseAreaSpellHandler.FEET
CRUSH = 1
# (line, art SpellID, fields, ranks: (level, name, rank fields))
STEALTH = [
    ('Nightshade Stealth', 2874, dict(Type='DamageShield', Target='Self', Duration=1200, CastTime=3.0, Range=0, Power=0, DamageType=SPIRIT),
     [(10, 'Eventide Resonance', dict(Damage=1.0)), (20, 'Eventide Redirection', dict(Damage=2.0)), (30, 'Eventide Reverberation', dict(Damage=3.0)),
      (40, 'Eventide Repercussion', dict(Damage=4.0)), (50, 'Eventide Reflection', dict(Damage=5.0))]),
    ('Nightshade Stealth', 30000, dict(Type='DamageOverTime', Target='Enemy', Duration=48, Frequency=80, CastTime=0, Range=500, RecastDelay=30,
                                       Power=0, DamageType=BODY),
     [(15, 'Clouded Agony', dict(Damage=4)), (25, 'Clouded Distress', dict(Damage=8)), (36, 'Clouded Pain', dict(Damage=14)),
      (46, 'Clouded Destruction', dict(Damage=22))]),
    ('Shadowblade Stealth', 30000, dict(Type='MeleeDamageTypeAura', Target='Self', Duration=30, CastTime=0, Range=0, Radius=0, RecastDelay=180,
                                        Power=0, DamageType=CRUSH),
     [(10, 'Bludgeon', {})]),
    *[(line, 30022, dict(Type='TimedPulseArea', Target='Self', LifeDrainReturn=FEET, Duration=1200, Frequency=10, Radius=350, Value=0,
                         CastTime=0, Range=0, RecastDelay=600, Power=0,
                         Child=dict(Type='SpeedDecrease', Name='Caltrops', Target='Enemy', Value=25, Duration=30, Range=0, DamageType=BODY)),
       [(35, 'Caltrops', {})]) for line in ASSASSIN_STEALTH],
    *[(line, 2874, dict(Type='StealthDetectionAura', Target='Group', Value=10, Pulse=1, Frequency=55, Duration=6, CastTime=3.0,
                        Range=1500, Power=0, PulsePower=0, RecastDelay=0),
       [(level, 'Heightened Awareness', {})]) for line, level in [*[(line, 45) for line in ASSASSIN_STEALTH], ('Hunter Stealth', 30),
                                                               ('Scout Stealth', 30), ('Ranger Stealth', 30)]],
    *[(line, 30022, dict(Type='ShadowStep', Target='Enemy', Range=1000, CastTime=0, RecastDelay=90, Power=0), [(40, 'Blur', {})])
      for line in ASSASSIN_STEALTH],
]

CONSUME_VENOM = dict(Name='Consume Venom', Type='ConsumeVenom', Target='Self', Range=0, CastTime=0, RecastDelay=300, Power=0,
                     Description='Consume Venom (live 1.130a Envenom): removes your own damage-over-time effects; grants no immunity.')


def definitions():
    """(level or None, fields, art SpellID) per row: each rank's child (no level: it is in no line), then its coating."""
    rows, spell_id, extras = [], FIRST, []
    for index, (family, art, child, ranks) in enumerate(FAMILIES):
        group = GROUP_BASE + index
        for level, name, values, *override in ranks:
            values = dict(values)
            extra = values.pop('Extra', None)  # a second effect the poison lays (its SubSpellID), after the coating
            child_id, parent_id = spell_id, spell_id + 1
            rows.append((None, dict(child, **values, Name=name, Target='Enemy', SpellID=child_id,
                                    Description=f'{name}: the poison (live 1.130a Envenom).'), art))
            parent = dict(Type='PoisonCoating', Target='Self', Name=name, Value=child_id, Frequency=100, Duration=COATING_DURATION,
                          CastTime=0, RecastDelay=reuse(level), SharedTimerGroup=COATING_TIMER, Power=0, Range=0,
                          SpellGroup=group, EffectGroup=COATING_EFFECT_GROUP, SpellID=parent_id,
                          Description=f'{name} (live 1.130a Envenom): your melee hits deliver it.')
            rows.append((level, dict(parent, **(override[0] if override else {})), art))
            spell_id += 2
            if extra:
                extras.append((rows[-2][1], extra, name, art))
    rows.append((50, dict(CONSUME_VENOM, SpellID=spell_id, SpellGroup=GROUP_BASE + len(FAMILIES)), 30049))
    spell_id += 1
    for index, (line, art, common, ranks) in enumerate(STEALTH):
        group = GROUP_BASE + len(FAMILIES) + 1 + index
        for level, name, values in ranks:
            fields = dict(common, **values)
            child = fields.pop('Child', None)
            parent_id = spell_id + (1 if child else 0)
            if child:
                rows.append((None, dict(child, SpellID=spell_id, Description=f"{child['Name']}: part of {name}."), art))
                fields['SubSpellID'] = spell_id
            rows.append((level, dict(fields, Name=name, SpellID=parent_id, SpellGroup=group, Line=line,
                                     Description=f'{name} (live 1.130a Stealth).'), art))
            spell_id = parent_id + 1
    for poison, extra, name, art in extras:  # last, so the earlier IDs stay put
        poison['SubSpellID'] = spell_id
        rows.append((None, dict(extra, SpellID=spell_id, Description=f"{extra['Name']}: part of {name}."), art))
        spell_id += 1
    assert spell_id - 1 < COATING_TIMER
    for _, fields, _ in rows:
        fields.update(Spell_ID=f"{PACKAGE}-{fields['SpellID']}", PackageID=PACKAGE, TooltipId=TOOLTIP_BASE + fields['SpellID'] - FIRST)
    return rows


def apply(db):
    db.row_factory = sqlite3.Row
    rows = definitions()
    if any(RESERVED_TOOLTIPS[0] <= f['TooltipId'] <= RESERVED_TOOLTIPS[1] for _, f, _ in rows):
        raise ValueError("Envenom tooltips would enter the Death Knight's reserved block")
    if db.execute("select 1 from Spell where (SpellID between ? and ? or TooltipId between ? and ?) and coalesce(PackageID,'')<>?",
                  (FIRST, LAST, TOOLTIP_BASE, TOOLTIP_BASE + LAST - FIRST, PACKAGE)).fetchone():
        raise ValueError('Envenom spell/tooltip collision')
    if not db.execute("select 1 from Specialization where KeyName='Envenom'").fetchone():
        raise ValueError('Missing Envenom specialization')
    db.execute('delete from LineXSpell where SpellID between ? and ?', (FIRST, LAST))
    db.execute('delete from Spell where PackageID=?', (PACKAGE,))
    if db.execute(f"select 1 from SpellLine where Spec='Stealth' and KeyName not in ({','.join('?' * len(STEALTH_LINES))})",
                  tuple(k for k, _ in STEALTH_LINES)).fetchone():
        raise ValueError('Another Stealth spell line exists; class-hinted lines would hide it')
    for (key, hint), spec in [(line, 'Envenom') for line in LINES] + [(line, 'Stealth') for line in STEALTH_LINES]:
        db.execute('delete from SpellLine where KeyName=?', (key,))
        db.execute('insert into SpellLine (KeyName,Name,Spec,IsBaseLine,ClassIDHint,LastTimeRowUpdated) values (?,?,?,?,?,?)',
                   (key, spec, spec, 0, hint, '2000-01-01 00:00:00'))
    db.execute('update Specialization set Implementation=? where KeyName=?', (HYBRID, 'Envenom'))
    template = hybrid_lines.blank_spell(db)
    for level, fields, art in rows:
        fields = dict(fields)
        line = fields.pop('Line', None)
        source = db.execute('select ClientEffect, Icon from Spell where Name=? and SpellID between 30000 and 30049', (fields['Name'],)).fetchone() \
            or db.execute('select ClientEffect, Icon from Spell where SpellID=?', (art,)).fetchone()
        if source is None:
            raise ValueError(f'No stock spell {art} to borrow art from')
        row = dict(template, **fields, ClientEffect=source['ClientEffect'], Icon=source['Icon'])
        row.update(Message1=f"You are affected by {row['Name']}.", Message2=f"{{0}} is affected by {row['Name']}.",
                   Message3=f"{row['Name']} ends.", Message4=f"{row['Name']} ends on {{0}}.")
        db.execute('insert into Spell (' + ','.join(f'"{k}"' for k in row) + ') values (' + ','.join('?' * len(row)) + ')', list(row.values()))
        if line:
            db.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)', (line, row['SpellID'], level, row['Spell_ID']))
        elif level is not None:
            for key, _ in LINES:
                db.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)',
                           (key, row['SpellID'], level, f"{row['Spell_ID']}-{key}"))
    stealth = sum(1 for r in rows if 'Line' in r[1])
    return dict(envenom_package=PACKAGE, envenom_spells=sum(1 for r in rows if r[0] is not None) - stealth,
                envenom_children=sum(1 for r in rows if r[0] is None), envenom_lines=len(LINES), stealth_spells=stealth)
