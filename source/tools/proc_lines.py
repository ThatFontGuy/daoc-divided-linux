"""Live (1.130a) class proc buffs missing here, on the existing proc handlers (OffensiveProc / DefensiveProc).

From the 2026-10-25 research pass (Class-Research/codex/2026-10-25/01-weapon-and-defensive-procs.md): the levels,
names, chances, durations, recasts and power costs are daoc.gg's 1.130a records; the fired effects are the planner's
opened child delves. Each proc is a parent buff (Value = its child's SpellID, Frequency = the chance in percent, as the
local Cleric Strength From Adversity line) and a child spell in no line.
  - Friar Protection from Fear..Heresy (Enhancement): group buff, 25% when hit, heals the struck member 15-100.
  - Friar Prophet's Penitence..Dogma (Rejuvenation): self buff, 25% on own attacks, group heal 15-100.
  - Bard Battlesong of Revival..Apotheosis (Nurture): group buff, 25% when hit, heals the struck member 15-100.
  - Warden Nature's Gift line (Regrowth): self, 15% on own attacks, group heal 15-100.
  - Warden Nature's Curator line (Nurture): self, 15% on own attacks, 25-125 heal to realm members within 250.
    (daoc.gg files it under its defensive procs, but its delve and the class library say "your attacks".)
  - Thane Dissipating..Banishing Blows (Stormcalling): self, 10% on own attacks, 6-24% Energy resist debuff, 10 s.
Follow-up (Class-Research/claude/followup-2026-10-25, from daoc.gg's client spell data):
  - Druid Vine/Leaf/Root/Lush/Fertile Skin (Nature): on a realm ally for 15 s, every melee hit roots the attacker
    5/10/20/34/48 s; 2.8 s cast, 10% power, reuse 5m/5m/60s/60s/60s (the client's; 1.123's notes said 20 s, Root 3 m).
  - Druid Touch/Clutch/Embrace/Power of Nature (Nature): on the pet for 20 minutes, 10% of its hits heal realm
    members within 1,000 for 100/150/200/250.
A rank may override its parent's fields (the Skins' reuse).
"""
import sqlite3
import hybrid_lines

PACKAGE = 'local-procs-live-v1'
FIRST, LAST = 77000, 77199
TOOLTIP_BASE = 20600  # 20600-20699 (the linked spells use 20700-20899); 23200-23999 is the Death Knight's reserved block
TOOLTIP_LAST = 20699
RESERVED_TOOLTIPS = (23200, 23999)
GROUP_BASE = 77000
PARENT_ART = 1560  # Strength From Adversity
CHILD_ART = 1563   # Strength From Adversity Proc

GROUP_BUFF = dict(Target='Group', Duration=1200, CastTime=3.0, Range=1500, RecastDelay=0)
SELF_PROC = dict(Target='Self', Duration=30, CastTime=0.0, Range=0, RecastDelay=30)

# (line, kind, chance, parent fields, child type, child fields, ranks: (level, name, power, child value))
FAMILIES = [
    ('Friar Enhancement Spec', 'DefensiveProc', 25, GROUP_BUFF, 'Heal', dict(Target='Self'),
     [(9, 'Protection from Fear', 9, 15), (19, 'Protection from Doubt', 11, 32), (29, 'Protection from Anarchy', 19, 66),
      (39, 'Protection from Idleness', 24, 83), (49, 'Protection from Heresy', 32, 100)]),
    ('Rebirth', 'OffensiveProc', 25, SELF_PROC, 'Heal', dict(Target='Group', Range=1000),
     [(8, "Prophet's Penitence", 8, 15), (16, "Prophet's Faith", 10, 30), (24, "Prophet's Piety", 13, 45),
      (32, "Prophet's Conviction", 17, 60), (40, "Prophet's Fidelity", 21, 75), (48, "Prophet's Dogma", 25, 100)]),
    ('Bard Nurture Spec', 'DefensiveProc', 25, GROUP_BUFF, 'Heal', dict(Target='Self'),
     [(8, 'Battlesong of Revival', 9, 15), (16, 'Battlesong of Regeneration', 11, 32), (24, 'Battlesong of Regrowth', 15, 49),
      (32, 'Battlesong of Restoration', 19, 66), (40, 'Battlesong of Renascence', 24, 83), (48, 'Battlesong of Apotheosis', 32, 100)]),
    ('Regrowth Warden Spec', 'OffensiveProc', 15, SELF_PROC, 'Heal', dict(Target='Group', Range=1000),
     [(8, "Lesser Nature's Gift", 8, 15), (16, "Lesser Nature's Favor", 10, 30), (24, "Lesser Nature's Token", 13, 45),
      (32, "Nature's Gift", 17, 60), (40, "Nature's Favor", 21, 75), (48, "Nature's Token", 25, 100)]),
    ('Nurture Warden Spec', 'OffensiveProc', 15, SELF_PROC, 'Heal', dict(Target='Realm', Range=0, Radius=250),
     [(10, "Nature's Curator", 5, 25), (20, "Nature's Deacon", 12, 50), (30, "Nature's Keeper", 17, 75),
      (40, "Nature's Steward", 21, 100), (50, "Nature's Sentinel", 25, 125)]),
    ('Stormcalling', 'OffensiveProc', 10, dict(Target='Self', Duration=1200, CastTime=3.0, Range=0, RecastDelay=0),
     'EnergyResistDebuff', dict(Target='Enemy', Range=500, Duration=10, DamageType=12),
     [(17, 'Dissipating Blows', 12, 6), (23, 'Routing Blows', 16, 12), (36, 'Sundering Blows', 25, 18), (47, 'Banishing Blows', 32, 24)]),
    ('Druid Nature Spec', 'DefensiveProc', 100, dict(Target='Realm', Duration=15, CastTime=2.8, Range=1500),
     'SpeedDecrease', dict(Target='Enemy', Value=99, DamageType=15),
     [(8, 'Vine Skin', -10, 5, dict(RecastDelay=300)), (18, 'Leaf Skin', -10, 10, dict(RecastDelay=300)),
      (28, 'Root Skin', -10, 20, dict(RecastDelay=60)), (38, 'Lush Skin', -10, 34, dict(RecastDelay=60)),
      (48, 'Fertile Skin', -10, 48, dict(RecastDelay=60))]),
    ('Druid Nature Spec', 'OffensiveProc', 10, dict(Target='Pet', Duration=1200, CastTime=3.0, Range=1500, RecastDelay=0),
     'Heal', dict(Target='Realm', Range=0, Radius=1000),
     [(15, 'Touch of Nature', 15, 100), (25, 'Clutch of Nature', 22, 150), (35, 'Embrace of Nature', 29, 200), (45, 'Power of Nature', 36, 250)]),
]


def definitions():
    """(line or None, level, fields): each rank's child (no line) then its parent."""
    rows, spell_id = [], FIRST
    for index, (line, kind, chance, parent, child_type, child, ranks) in enumerate(FAMILIES):
        for level, name, power, value, *override in ranks:
            child_id, parent_id = spell_id, spell_id + 1
            # A root's or heal's amount is its Value, except a root, whose amount is its Duration.
            amount = dict(Duration=value) if child_type == 'SpeedDecrease' else dict(Value=value)
            rows.append((None, level, dict(dict(child, **amount), Type=child_type, Name=name, SpellID=child_id, ART=CHILD_ART,
                                           Description=f'{name}: the proc (live 1.130a).')))
            rows.append((line, level, dict(dict(parent, **(override[0] if override else {})), Type=kind, Name=name, Value=child_id,
                                           Frequency=chance, Power=power,
                                           SpellGroup=GROUP_BASE + index, EffectGroup=GROUP_BASE + index, SpellID=parent_id,
                                           ART=PARENT_ART, Description=f'{name} (live 1.130a {line}).')))
            spell_id += 2
    assert spell_id - 1 <= LAST and TOOLTIP_BASE + spell_id - 1 - FIRST <= TOOLTIP_LAST
    for _, _, fields in rows:
        fields.update(Spell_ID=f"{PACKAGE}-{fields['SpellID']}", PackageID=PACKAGE, TooltipId=TOOLTIP_BASE + fields['SpellID'] - FIRST)
    return rows


def apply(db):
    db.row_factory = sqlite3.Row
    if db.execute("select 1 from Spell where (SpellID between ? and ? or TooltipId between ? and ?) and coalesce(PackageID,'')<>?",
                  (FIRST, LAST, TOOLTIP_BASE, TOOLTIP_LAST, PACKAGE)).fetchone():
        raise ValueError('Proc spell/tooltip collision')
    rows = definitions()
    if any(RESERVED_TOOLTIPS[0] <= fields['TooltipId'] <= RESERVED_TOOLTIPS[1] for _, _, fields in rows):
        raise ValueError("Proc tooltips would enter the Death Knight's reserved block")
    for line, _, fields in rows:
        if line and not db.execute('select 1 from SpellLine where KeyName=?', (line,)).fetchone():
            raise ValueError('Missing spell line ' + line)
        if line and db.execute("""select 1 from LineXSpell l join Spell s on s.SpellID=l.SpellID where l.LineName=? and s.Name=?
                                  and coalesce(s.PackageID,'')<>?""", (line, fields['Name'], PACKAGE)).fetchone():
            raise ValueError(f"{line} already has {fields['Name']}")
    db.execute('delete from LineXSpell where SpellID between ? and ?', (FIRST, LAST))
    db.execute('delete from Spell where PackageID=?', (PACKAGE,))
    template = hybrid_lines.blank_spell(db)
    for line, level, fields in rows:
        fields = dict(fields)
        art = db.execute('select ClientEffect, Icon from Spell where SpellID=?', (fields.pop('ART'),)).fetchone()
        row = dict(template, **fields, ClientEffect=art['ClientEffect'], Icon=art['Icon'])
        row.update(Message1=f"You are affected by {row['Name']}.", Message2=f"{{0}} is affected by {row['Name']}.",
                   Message3=f"{row['Name']} ends.", Message4=f"{row['Name']} ends on {{0}}.")
        db.execute('insert into Spell (' + ','.join(f'"{k}"' for k in row) + ') values (' + ','.join('?' * len(row)) + ')', list(row.values()))
        if line:
            db.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)', (line, row['SpellID'], level, row['Spell_ID']))
    return dict(proc_package=PACKAGE, proc_buffs=sum(1 for line, _, _ in rows if line), proc_children=sum(1 for line, _, _ in rows if not line))
