"""Live (1.130a) spells missing from the casters and the Cleric, Friar, Druid, Bard, Warden, Healer and Shaman.

class_lines_data.py (made by the scratch generator gen_class_lines.py from daoc.gg's 1.130a data) holds the families in
this server's units, calibrated on the spells both sides already share:
  - Direct damage at this server's scale (x0.0992 of live's figure, the median of the shared spells); lifedrains and
    damage shields in tenths. A snare's Value is the slow (live keeps the speed left).
  - Cast time: live's timer / 1000 + 2 s, instant stays 0.
  - Durations, power, ranges, radii and recasts as live's. Damage over time keeps the local two-second-tick layout.
Each spell borrows the effect, icon, damage type and effect group of the nearest local spell of its kind, so a new buff
replaces (not stacks with) the older one. The generator keeps only spells an existing handler supports, that live gives
to every class sharing the line, and that the class doesn't already have under an older name (SKIPPED and EQUIVALENT
record the rest).

Placement:
  - The hybrid classes' lines (Smite, Rejuvenation, Enhancement, Nurture, Regrowth, Nature, Music, Mending,
    Augmentation, Pacification, Subterranean) are live hybrid
    specializations: a family goes into its existing line with a SpellGroup of its own, so the summarized list shows
    it beside the older family.
  - The list casters (the cloth casters, Animist, Valewalker) cast by line and level, the first match winning, so their
    families go into new lines "<line> (1.130)" beside the old ones (same spec, class hint and base flag), with one spell
    per level ("(1.130 II)" takes a clash).
RENAMES corrects local misspellings of live spells.
class_lines_data_v2.py (gen_class_lines_v2.py, a second pass over a world that has these families) adds kinds the first
pass had no mapping for: the Shaman's Cave and Augmentation spells (Ancestor's DDs, diseases, Break Arms, the curses,
Purifying heals and Cleanses, Clarity, Earthen Power), the casters' live diseases, Cure Sight, Shroud of Uncertainty,
the Minstrel's Crescendo and the Warden's Greater heals (the first pass dropped them as the Druid's). They come after
EXTRA_FAMILIES so the earlier IDs stay put. Not built: magic-damage and power-cost debuffs, Spirit Shell, Caustic
Carapace, the Vivification chants, Frigg's Grace, Escape Hold, Tribal Unity and the Minstrel's Spell songs (no handler
or no resist set in the data).
"""
import sqlite3
from class_lines_data import FAMILIES
from class_lines_data_v2 import FAMILIES as FAMILIES_V2
import hybrid_lines

PACKAGE = 'local-class-live-v1'
FIRST, LAST = 75000, 75887
TOOLTIP_BASE = 29112  # 29112-29999 are free; the client reads tooltip IDs as signed 16-bit
GROUP_BASE = 75000
TIMER_BASE = 75900
LINE_SUFFIX = ' (1.130)'
# (line name prefix, local name, live name, live values): misspellings, and spells live renamed (the generator's
# EQUIVALENT: same kind and level, a name live no longer has). Damage at the drift's scale; DoTs keep their tick layout.
RENAMES = [
    ('Regrowth', 'Minor Resurgance', 'Minor Resurgence', {}),
    ('Regrowth', 'Major Resurgance', 'Major Resurgence', {}),
    ('Bard Music', 'Facinating Melody', 'Fascinating Melody', {}),
    ('Bard Music', 'Facinating Hymn', 'Fascinating Hymn', {}),
    ('Pacification', 'Paralizing Gaze', 'Paralyzing Gaze', {}),
    ('Subterranean', 'Fungal  Degeneration', 'Fungal Degeneration', dict(Damage=55.0)),
    ('Terrible Hammer', 'Holy Anger', 'Divine Anger', dict(Damage=32.0, CastTime=2.8, Power=6)),
    ('Terrible Hammer', 'Holy Fury', 'Divine Fury', dict(Damage=191.3, CastTime=2.8, Range=1600)),
    ('Terrible Hammer', 'Greater Holy Fury', 'Divine Vengeance', dict(Damage=213.6, CastTime=2.8, Power=32, Range=1650)),
    ('Druid Nature Spec', 'Moldiness', 'Windburn', dict(Damage=27.0, CastTime=2.5, Power=14)),
    ('Bone Warriors', 'Cloud of Deterioration', 'Fade Bones', dict(Damage=88.0, Power=25)),
    ('Bone Army', 'Bones to Iron', 'Iron Bones', dict(Value=36.0)),
    ('Bone Army', 'Bolster Bones', 'Restore Bones', dict(Value=201.0)),
    # The Mauler's gifts carry one live name for all five ranks (the Mauler test data numbered them).
    *[(line, f'Gift of {family} {rank}', f'Gift of {family}', {})
      for line, families in [('Aura Manipulation', ('Nethuni', 'Tegashrig', 'Perizor', 'Arasthai')), ('Mauler Albion Gifts', ('Albion',)),
                             ('Mauler Midgard Gifts', ('Midgard',)), ('Mauler Hibernia Gifts', ('Hibernia',))]
      for family in families for rank in range(1, 6)],
    ('Aura Manipulation', 'Perfect Discipline of Laresh', 'Perfect Discipline of Laresh', dict(Power=17)),
    # Savage (live 1.130a): the taunts' names and values (taunts in tenths), 5% health for the Kelgor buffs and Blows,
    # the smaller live evade ranks and the Kelgor heals' costs.
    ('Savagery', 'Irreverant Gesture', 'Irreverent Gesture', dict(Value=5.2, RecastDelay=15, CastTime=0.0)),
    ('Savagery', 'Insulting Gesture', 'Insulting Gesture', dict(Value=17.1)),
    ('Savagery', 'Rude Gesture', 'Rude Gesture', dict(Value=38.7)),
    ('Savagery', 'Infurating Gesture', 'Infuriating Gesture', dict(Value=55.6, RecastDelay=15, CastTime=0.0)),
    *[('Savagery', name, name, dict(Power=-5)) for name in (
        'Nails of Kelgor', 'Hooks of Kelgor', 'Barbs of Kelgor', 'Claws of Kelgor', 'Talons of Kelgor', 'Fangs of Kelgor',
        'Passion of Kelgor', 'Drive of Kelgor', 'Mania of Kelgor', 'Fervor of Kelgor', 'Zeal of Kelgor',
        'Brutal Blows', 'Fierce Blows', 'Relentless Blows', 'Feral Blows', 'Bestial Blows', 'Savage Blows')],
    *[('Savagery', name, name, dict(Value=value, Power=-5)) for name, value in (
        ('Swiftness of Kelgor', 3), ('Alacrity of Kelgor', 5), ('Speed of Kelgor', 8), ('Fleetness of Kelgor', 12),
        ('Quickness of Kelgor', 16), ('Evasion of Kelgor', 20))],
    ("Savagery", "Kelgor's Gift", "Kelgor's Gift", dict(Power=-10)),
    ("Savagery", "Kelgor's Boon", "Kelgor's Boon", dict(Power=-15)),
    ("Savagery", "Kelgor's Reward", "Kelgor's Reward", dict(Power=-20)),
    # Hunter charms: live's level caps.
    *[('Beastcraft', name, name, dict(Value=value)) for name, value in (
        ('Minor Call of Gleipnir', 7), ('Lesser Call of Gleipnir', 13), ('Call of Gleipnir', 20), ('Greater Call of Gleipnir', 32),
        ('Superior Call of Gleipnir', 50), ('Influence Insect', 9), ('Compel Insect', 15), ('Charm Insect', 22),
        ('Control Insect', 35), ('Dominate Insect', 50))],
]

# Stock spells live took out of a line: (line, spell types). Savage: the crush, slash and thrust buffs became one.
RETIRED = [('Savagery', ('SavageCrushResistanceBuff', 'SavageSlashResistanceBuff', 'SavageThrustResistanceBuff'))]
REPTILE, INSECT, ANIMAL = 8, 3, 2


def pulsing_cures(cls, spec, hint, line):
    """Pulsing Cure Poison / Disease (live 1.81 and 1.121): a cure, then 1 (rank I) or 2 (rank II) more, 3 s apart."""
    common = dict(Target='Realm', Range=2000, Radius=0, Duration=0, RecastDelay=0, DamageType=0, EffectGroup=0)
    poison = [(14, 'Pulsing Cure Poison I', dict(common, Value=1, CastTime=3.5, Power=20, ART='Cure Poison')),
              (28, 'Pulsing Cure Poison II', dict(common, Value=2, CastTime=3.7, Power=25, ART='Cure Poison'))]
    disease = [(18, 'Pulsing Cure Disease I', dict(common, Value=1, CastTime=3.5, Power=23, ART='Cure Disease')),
               (36, 'Pulsing Cure Disease II', dict(common, Value=2, CastTime=3.7, Power=28, ART='Cure Disease'))]
    return [dict(cls=cls, list=False, spec=spec, base=0, hint=hint, lines=[line], type='PulsingCurePoison', rows=poison),
            dict(cls=cls, list=False, spec=spec, base=0, hint=hint, lines=[line], type='PulsingCureDisease', rows=disease)]


# Hand-written from the 2026-10-25 research pass (Class-Research/codex), after the generated families so their IDs stay put.
EXTRA_FAMILIES = [
    *pulsing_cures('cleric', 'Rejuvenation', 6, 'Rebirth (Cleric)'),
    *pulsing_cures('friar', 'Rejuvenation', 10, 'Rebirth'),
    *pulsing_cures('druid', 'Regrowth', 47, 'Regrowth Druid Spec'),
    *pulsing_cures('warden', 'Regrowth', 46, 'Regrowth Warden Spec'),
    *pulsing_cures('healer', 'Mending', 26, 'Healer Mending Spec'),
    # Cleric Smite reflection (1.123): Value% of all damage received returned to the attacker, 20 minutes, 10% power.
    dict(cls='cleric', list=False, spec='Smite', base=0, hint=0, lines=['Terrible Hammer'], type='DamageReflection',
         rows=[(lv, name, dict(Target='Self', Value=v, Duration=1200, CastTime=3.0, Power=-10, Range=0, Radius=0, RecastDelay=0,
                                DamageType=0, EffectGroup=0, ART='Hammer of Grace'))
               for lv, name, v in [(10, 'Virtuous Reflection', 3), (20, 'Heavenly Reflection', 5), (30, 'Rapturous Reflection', 7),
                                   (40, 'Radiant Reflection', 10)]]),
]


# Hand-written after the second pass. Mauler Superior Discipline of Laresh (Aura Manipulation 42): 29% absorb for 15
# minutes, 15 power, beside Perfect Discipline (28%, 17 power); it shares the Laresh effect group.
def charms(rows, body):
    """Hunter charms (live 1.130a Beastcraft): 4 s cast, 1,200 range, 25% power; Value is the highest level charmed."""
    return [(lv, name, dict(Target='Enemy', Value=value, Damage=82, AmnesiaChance=body, Duration=65535, CastTime=4.0, Power=-25,
                            Range=1200, Radius=0, RecastDelay=0, DamageType=0, EffectGroup=0, ART='Influence Insect'))
            for lv, name, value in rows]


def hunter_charm(rows, body):
    return dict(cls='hunter', list=False, spec='Beastcraft', base=0, hint=0, lines=['Beastcraft'], type='Charm', rows=charms(rows, body))


LATE_FAMILIES = [
    dict(cls='mauler', list=False, spec='Aura Manipulation', base=0, hint=0, lines=['Aura Manipulation'], type='ArmorAbsorptionBuff',
         rows=[(42, 'Superior Discipline of Laresh', dict(Target='Self', Value=29, Duration=900, CastTime=3.0, Power=15, Range=0, Radius=0,
                                                         RecastDelay=0, DamageType=0, EffectGroup=67010, ART='Perfect Discipline of Laresh'))]),
    # Savage Deflect..Ignore Attacks (live 1.123): 30 s self melee resist buff, 10% health, 5 s reuse.
    dict(cls='savage', list=False, spec='Savagery', base=0, hint=0, lines=['Savagery'], type='SavageMeleeResistanceBuff',
         rows=[(lv, name, dict(Target='Self', Value=v, Duration=30, CastTime=0.0, Power=-10, Range=0, Radius=0, RecastDelay=5,
                                DamageType=0, EffectGroup=0, ART='Deflect Blows'))
               for lv, name, v in [(6, 'Deflect Attacks', 5), (14, 'Bear Attacks', 9), (23, 'Withstand Attacks', 13),
                                   (31, 'Endure Attacks', 17), (40, 'Weather Attacks', 21), (47, 'Ignore Attacks', 25)]]),
    hunter_charm([(1, 'Influence Reptile', 9), (8, 'Compel Reptile', 15), (14, 'Charm Reptile', 22), (21, 'Control Reptile', 35),
                  (34, 'Dominate Reptile', 50), (45, 'Overpower Reptile', 50)], REPTILE),
    hunter_charm([(45, 'Overpower Insect', 50)], INSECT),
    hunter_charm([(45, 'Unyeilding Call of Gleipnir', 50)], ANIMAL),  # live's spelling
]


def definitions():
    """(line, level, fields, new line or None) per spell; a new line is (key, spec, hint, base)."""
    rows, spell_id, timers, taken = [], FIRST, {}, {}
    for index, fam in enumerate(FAMILIES + EXTRA_FAMILIES + FAMILIES_V2 + LATE_FAMILIES):
        list_caster = fam['list']
        for level, name, fields in fam['rows']:
            fields = dict(fields)
            timer = fields.pop('SharedTimer', None)
            if timer:
                fields['SharedTimerGroup'] = timers.setdefault(timer, TIMER_BASE + len(timers))
            new_line = None
            line = fam['lines'][0]
            if list_caster:
                suffix = 1
                while level in taken.setdefault((fam['spec'], fam['base'], fam['hint'], suffix), set()):
                    suffix += 1
                taken[(fam['spec'], fam['base'], fam['hint'], suffix)].add(level)
                line = line + LINE_SUFFIX[:-1] + (' II' if suffix == 2 else ' III' if suffix == 3 else '') + ')'
                new_line = (line, fam['spec'], fam['hint'], fam['base'])
            rows.append((line, level, dict(fields, SpellGroup=GROUP_BASE + index, Type=fam['type'], SpellID=spell_id,
                                           Spell_ID=f'{PACKAGE}-{spell_id}', PackageID=PACKAGE,
                                           TooltipId=TOOLTIP_BASE + spell_id - FIRST, Name=name,
                                           Description=f'{name} (live 1.130a {fam["spec"]}).'), new_line))
            spell_id += 1
    assert spell_id - 1 <= LAST and TIMER_BASE + len(timers) < FIRST + 1000
    return rows


def apply(db):
    db.row_factory = sqlite3.Row
    if db.execute("select 1 from Spell where (SpellID between ? and ? or TooltipId between ? and ?) and coalesce(PackageID,'')<>?",
                  (FIRST, LAST, TOOLTIP_BASE, TOOLTIP_BASE + LAST - FIRST, PACKAGE)).fetchone():
        raise ValueError('Class line spell/tooltip collision')
    rows = definitions()
    # Clear our earlier rows, then our lines.
    db.execute('delete from LineXSpell where SpellID between ? and ?', (FIRST, LAST))
    db.execute('delete from Spell where PackageID=?', (PACKAGE,))
    db.execute('delete from SpellLine where KeyName like ?', ('%' + LINE_SUFFIX[:-1] + '%',))
    lines = {}
    for line, _, _, new_line in rows:
        if new_line and line not in lines:
            if db.execute('select 1 from SpellLine where KeyName=?', (line,)).fetchone():
                raise ValueError('Spell line name clash: ' + line)
            key, spec, hint, base = new_line
            db.execute('insert into SpellLine (KeyName,Name,Spec,IsBaseLine,ClassIDHint,LastTimeRowUpdated) values (?,?,?,?,?,?)',
                       (key, key, spec, base, hint, '2000-01-01 00:00:00'))
            lines[line] = True
        elif not new_line and not db.execute('select 1 from SpellLine where KeyName=?', (line,)).fetchone():
            raise ValueError('Missing spell line ' + line)
    template = hybrid_lines.blank_spell(db)
    for line, level, fields, _ in rows:
        fields = dict(fields)
        art = fields.pop('ART')
        renamed_to = next((new for _, old, new, _ in RENAMES if old == art), art)  # a re-run finds the live name
        source = db.execute("select ClientEffect, Icon from Spell where Name in (?,?) and coalesce(PackageID,'') not in (?,?) order by SpellID limit 1",
                            (art, renamed_to, PACKAGE, hybrid_lines.PACKAGE)).fetchone()
        if source is None:
            raise ValueError('No local spell to borrow art from for ' + fields['Name'])
        row = dict(template, **fields, ClientEffect=source['ClientEffect'], Icon=source['Icon'])
        row.update(Message1=f"You are affected by {row['Name']}.", Message2=f"{{0}} is affected by {row['Name']}.",
                   Message3=f"{row['Name']} ends.", Message4=f"{row['Name']} ends on {{0}}.")
        db.execute('insert into Spell (' + ','.join(f'"{k}"' for k in row) + ') values (' + ','.join('?' * len(row)) + ')', list(row.values()))
        db.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)', (line, row['SpellID'], level, row['Spell_ID']))
    for line, types in RETIRED:
        db.execute(f"""delete from LineXSpell where LineName=? and SpellID in
                       (select SpellID from Spell where Type in ({','.join('?' * len(types))}) and coalesce(PackageID,'')<>?)""",
                   (line, *types, PACKAGE))
    in_line = 'SpellID in (select SpellID from LineXSpell where LineName like ?)'
    for line, old, new, fields in RENAMES:
        assigns = dict(fields, Name=new)
        db.execute('update Spell set ' + ','.join(f'"{k}"=?' for k in assigns) + f' where Name in (?,?) and {in_line}',
                   (*assigns.values(), old, new, line + '%'))
    renamed = sum(db.execute(f'select count(*) from Spell where Name=? and {in_line}', (new, line + '%')).fetchone()[0]
                  for line, new in {(line, new) for line, _, new, _ in RENAMES})
    return dict(class_lines_package=PACKAGE, class_line_spells=len(rows), class_lines_added=len(lines), class_line_renames=renamed)
