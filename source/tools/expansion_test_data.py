"""Modern-live test kits for the last three classes: Bainshee (39), Vampiir (58) and Heretic (33).

Each kit starts from the complete pre-1.121 spell ranks in the Eve of Darkness database (pinned donor copy) and applies
the live changes from 1.121 through 1.129b on top; the official class library supplies newer damage values where it
has them. Every change and its source is listed in docs/EXPANSION-CLASSES-MODERN-TEST.md. Definition-only migration;
the caller owns the transaction. Saved progress is never touched.
"""
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EOD = REPO / 'artifacts/sovereign-validation/database-donors/Eve-of-Darkness-db-public'

# Spell and tooltip ranges. Tooltip indexes must stay below 32768: the client reads them as signed 16-bit values.
KITS = {
    39: dict(name='Bainshee', package='local-bainshee-test-v1', spells=68000, tooltips=17600, realm=3, baseline='Spectral Force',
             lines=('Spectral Force', 'Spectral Guard', 'Ethereal Shriek', 'Phantasmal Wail'), property='enable_bainshee_test'),
    58: dict(name='Vampiir', package='local-vampiir-test-v1', spells=69000, tooltips=18400, realm=3, styles=5800,
             lines=('Dementia', 'Shadow Mastery', 'Vampiiric Embrace'), property='enable_vampiir_test', career='VampiirCareer'),
    33: dict(name='Heretic', package='local-heretic-test-v1', spells=70000, tooltips=19200, realm=1, styles=3300, baseline='Heretic Enhancement',
             lines=('Heretic Rejuvenation Spec', 'Heretic Enhancement Spec', 'Heretic Enhancement'), property='enable_heretic_test',
             career='HereticCareer'),
    66: dict(name='Death Knight', package='local-deathknight-test-v1', spells=71000, tooltips=23200, realm=1, styles=6600,
             lines=('Death Knight Deathsight', 'Death Knight Deathsight Spec', 'Death Knight Painworking', 'Death Knight Painworking Spec',
                    'Death Knight Death Servant', 'Death Knight Death Servant Spec'),
             property='enable_death_knight_test', career='DeathKnightCareer'),
}
SPAN = 800  # spells per kit; also keeps each tooltip block inside its 800-wide reservation
STYLE_SPAN = 100

# Career abilities (armor, weapons, class abilities) from the EoD SpecXAbility rows; this world has none for these careers.
CAREER = {
    'VampiirCareer': [(1, 'HibArmor', 2), (1, 'Weaponry: Piercing', 0), (10, 'Safe Fall', 1), (20, 'Safe Fall', 2), (25, 'Climb Walls', 0),
                      (40, 'Safe Fall', 3), (45, 'Safe Fall', 4), (6, 'Vampiir Constitution', 0), (6, 'Vampiir Dexterity', 0),
                      (6, 'Vampiir Quickness', 0), (6, 'Vampiir Strength', 0)]
                     + [(lv, 'Vampiir Bolt', i) for i, lv in enumerate([1, 10, 20, 30, 35, 40, 45, 50])],
    'DeathKnightCareer': [(1, 'Weaponry: Two Handed', 0), (8, 'Parry', 1)],  # Chthonic Form's parry; the armor and staff come from AlbClothCasterCareer
    'HereticCareer': [(1, 'AlbArmor', 1), (1, 'Shield', 1), (1, 'Weaponry: Flexible', 0), (1, 'Weaponry: Staves', 0),
                      (1, 'Weaponry: Crushing', 0)],
}
# Live realm-ability access added after the EoD lists this world carries.
LIVE_RAS = {
    33: (('AtlasOF_StaticTempest', '1.125: Static Tempest replaced the Ichor that 1.121 had added'),),
    58: (('Mastery of Focus', '1.114b'), ('AtlasOF_MasteryOfMagery', '1.123'), ('Dual Threat', '1.123')),
}
REMOVED_RAS = {33: ('AtlasOF_Ichor',)}

# Abilities the server implements but this world's Ability table lacks: (key, internal id, implementation, description).
NEW_ABILITIES = [
    ('Vampiir Constitution', 3101, 'DOL.GS.SkillHandler.VampiirConstitution', 'The Vampiir gains 3 constitution every level from 6.'),
    ('Vampiir Dexterity', 3102, 'DOL.GS.SkillHandler.VampiirDexterity', 'The Vampiir gains 3 dexterity every level from 6.'),
    ('Vampiir Quickness', 3103, 'DOL.GS.SkillHandler.VampiirQuickness', 'The Vampiir gains 2 quickness every level from 6.'),
    ('Vampiir Strength', 3104, 'DOL.GS.SkillHandler.VampiirStrength', 'The Vampiir gains 3 strength every level from 6.'),
]

_eod_cache = {}

def eod(table='Spell', key='SpellID'):
    if table not in _eod_cache:
        _eod_cache[table] = {s[key]: s for s in json.loads((EOD / f'{table}.json').read_text(encoding='utf-8'))}
    return _eod_cache[table]


class Kit:
    """Collects (line, level, row) definitions with stable private IDs in manifest order."""

    def __init__(self, cls):
        self.cls = cls
        self.info = KITS[cls]
        self.rows = []
        self.next = self.info['spells']
        self.imported = {}
        self.styles = []  # (row, [(proc spell id, chance)])
        self.style_ids = {}  # name -> client style ID, for follow-up requirements

    def _id(self):
        sid = self.next
        self.next += 1
        if sid >= self.info['spells'] + SPAN:
            raise ValueError('Kit spell range exhausted')
        return sid

    def _finish(self, row, sid):
        if row.get('Type') == 'ArmorFactorBuff':
            row['Type'] = 'BaseArmorFactorBuff'  # baseline; specialization rows are switched in _place
        row.update(SpellID=sid, Spell_ID=f"{self.info['package']}-{sid}", PackageID=self.info['package'],
                   TooltipId=self.info['tooltips'] + sid - self.info['spells'])
        return row

    def eod(self, line, level, source, **kw):
        """Import one EoD spell (by ID), remapping its sub-spell into the kit as well."""
        row = dict(eod()[source])
        sid = self._id()
        row = self._finish(row, sid)
        sub = row.get('SubSpellID') or 0
        if sub and 'SubSpellID' not in kw:
            kw['SubSpellID'] = self.imported.get(sub) or self.eod(None, level, sub)
        row.update(kw)
        self.imported[source] = sid
        self.rows.append((line, level, self._place(line, row)))
        return sid

    def _place(self, line, row):
        # EoD's ArmorFactorBuff has no concrete handler here: baseline AF is base AF, specialization AF is spec AF.
        if row.get('Type') == 'BaseArmorFactorBuff' and line and line != self.info.get('baseline'):
            row['Type'] = 'SpecArmorFactorBuff'
        return row

    def new(self, line, level, name, icon, **kw):
        row = dict(Name=name, Description='', Type='DirectDamage', Target='Enemy', Range=1500, Radius=0, CastTime=3.0,
                   Damage=0, Value=0, Duration=0, Frequency=0, Pulse=0, PulsePower=0, Power=0, RecastDelay=0,
                   DamageType=10, Icon=icon, ClientEffect=icon, EffectGroup=0, SubSpellID=0, LifeDrainReturn=0,
                   Message1='', Message2='', Message3='', Message4='')
        row.update(kw)
        sid = self._id()
        self.rows.append((line, level, self._place(line, self._finish(row, sid))))
        return sid

    def proc(self, name, kind, value=0, damage=0, duration=0, icon=0, effect=0, damage_type=10, **kw):
        """A style proc spell (no line); icon 0 like the stock style procs."""
        return self.new(None, 0, name, icon, Type=kind, Value=value, Damage=damage, Duration=duration, ClientEffect=effect,
                        DamageType=damage_type, CastTime=0, Range=0, **kw)

    def style(self, spec, level, client_id, source, follows=None, procs=(), **kw):
        """Copy one EoD style row onto a client style ID; follows names an earlier style of this kit."""
        base = self.info['styles']
        row = dict(eod('Style', 'StyleID')[source])
        row.update(StyleID=base + len(self.styles), ID=client_id, Icon=client_id, TwoHandAnimation=client_id, ClassId=self.cls,
                   SpecKeyName=spec, SpecLevelRequirement=level)
        if follows:
            row.update(OpeningRequirementType=0, OpeningRequirementValue=self.style_ids[follows], AttackResultRequirement=7)
        row.update(getattr(self, 'style_defaults', {}))
        row.update(kw)
        if len(self.styles) >= STYLE_SPAN:
            raise ValueError('Kit style range exhausted')
        self.style_ids[row['Name']] = client_id
        self.styles.append((row, list(procs)))
        return client_id


# Live 1.130a names and values (daoc.gg spell data) for Bainshee spells the kit carried under older names: the Ethereal
# Shriek area nukes run one rank ahead of the pre-1.121 rows, the Dex/Qui debuffs became stronger targeted area debuffs,
# the Body debuffs last 8 s, and the Thunderous bolts were renamed. Keyed by the kit's old name.
BAINSHEE_LIVE = {
    'Minor Concussion': dict(Name='Roaring Concussion', Damage=38, Power=4),
    'Roaring Concussion': dict(Name='Resonant Concussion', Damage=73, Power=8),
    'Resonant Concussion': dict(Name='Clangorous Burst', Damage=114, Power=14),
    'Clangorous Burst': dict(Name='Resonant Explosion', Damage=157, Power=23),
    'Resonant Explosion': dict(Name='Deafening Explosion', Damage=174, Power=27),
    'Diminishing Yell': dict(Name='Diminishing Screech', Value=24, Power=5),
    'Diminishing Wail': dict(Value=32, Power=8),
    'Diminishing Cadence': dict(Name='Diminishing Bellow', Value=49, Power=13),
    'Diminishing Shriek': dict(Value=60, Power=17),
    'Diminishing Scream': dict(Value=70, Power=20),
    'Reverberating Yell': dict(Name='Reverberating Wail', Duration=8, Power=10),
    'Reverberating Shriek': dict(Duration=8, Power=16),
    'Reverberating Scream': dict(Duration=8, Power=23),
    'Thunderous Burst (Minor)': dict(Name='Thunderous Blast (Minor)'),
    'Thunderous Burst': dict(Name='Thunderous Blast'),
    'Thunderous Burst (Major)': dict(Name='Thunderous Blast (Major)'),
}
for _name in ('Diminishing Yell', 'Diminishing Wail', 'Diminishing Cadence', 'Diminishing Shriek', 'Diminishing Scream'):
    BAINSHEE_LIVE[_name].update(Target='Enemy', Range=1500, Duration=45, RecastDelay=7)


def bainshee():
    k = Kit(39)
    BASE, SPEC, ES, PW = KITS[39]['lines']
    # Spectral Force baseline: AF, absorb, bladeturn and the Pain nuke are unchanged.
    for sid, lv in zip(range(13501, 13511), [1, 3, 5, 9, 13, 18, 24, 31, 40, 50]):
        k.eod(BASE, lv, sid)
    for sid, lv, icon in [(13518, 30, 12037), (13519, 41, 12040)]:
        k.eod(BASE, lv, sid, Icon=icon)  # EoD's absorb icons are not in this client
    k.eod(BASE, 19, 13520)
    for sid, lv in zip(range(13524, 13534), [4, 7, 10, 15, 20, 25, 29, 36, 42, 48]):
        k.eod(BASE, lv, sid)
    # 1.128: a new baseline root.
    for i, (lv, n, dur, pw) in enumerate([(8, 'Spectral Cords', 16, 4), (14, 'Spectral Bonds', 23, 7), (21, 'Spectral Ropes', 31, 11),
                                          (27, 'Spectral Restraints', 41, 14), (32, 'Spectral Bindings', 48, 16),
                                          (39, 'Spectral Chains', 61, 20), (49, 'Spectral Shackles', 73, 25)]):
        k.new(BASE, lv, n, 13534 + i, Type='SpeedDecrease', Value=99, Duration=dur, CastTime=2.5, Power=pw)
    # 1.121 added the mez cure to Ethereal Shriek; 1.129 moved it to the baseline at 26.
    k.new(BASE, 26, 'Alarming Screech', 13612, Type='CureMezz', Target='Realm', CastTime=3.0, Power=-6, DamageType=0)

    # Spectral Guard specialization.
    for sid, lv in zip(range(13585, 13589), [3, 16, 28, 43]):
        k.eod(SPEC, lv, sid)
    for sid, lv in zip(range(13551, 13554), [20, 30, 40]):  # 1.121 moved the ablative chant to 20/30/40
        k.eod(SPEC, lv, sid)
    for sid, lv, dmg in zip(range(13555, 13564), [1, 8, 14, 22, 29, 34, 39, 44, 49], [4, 31, 54, 85, 112, 131, 151, 170, 189]):
        k.eod(SPEC, lv, sid, Damage=dmg)  # class library values
    for sid, lv in zip(range(13565, 13572), [5, 13, 21, 26, 33, 41, 46]):  # 1.122b moved the level 47 cone root to 46
        k.eod(SPEC, lv, sid)
    for sid, lv, dmg in zip(range(13575, 13583), [6, 12, 18, 24, 31, 36, 42, 48], [43, 80, 117, 153, 195, 226, 263, 299]):
        k.eod(SPEC, lv, sid, Damage=dmg)  # class library values
    # 1.121 moved the single-target root from the baseline into the specialization at the same levels.
    for sid, lv in zip(range(13534, 13541), [6, 12, 21, 28, 35, 43, 49]):
        k.eod(SPEC, lv, sid)
    # 1.126: Bawler's Obliteration, a cone nuke with a snare that breaks on damage.
    k.new(SPEC, 50, "Bawler's Obliteration", 13563, Type='DamageSpeedDecrease', Target='Cone', Range=500, Radius=100,
          Damage=189, Value=35, Duration=15, CastTime=3.0, Power=48)

    # Ethereal Shriek specialization, consolidated in 1.122b; nukes and bolts became Cold in 1.121.
    for sid, lv in [(13651, 1), (13653, 11), (13655, 21), (13657, 31), (13659, 41)]:
        k.eod(ES, lv, sid, DamageType=11)
    for sid, lv, rng, rad, pw, pp in [(13680, 2, 1800, 200, 4, 2), (13681, 12, 1850, 250, 7, 5), (13682, 22, 1900, 300, 12, 7),
                                      (13683, 32, 1950, 350, 16, 9), (13684, 42, 2000, 400, 20, 12)]:
        k.eod(ES, lv, sid, Range=rng, Radius=rad, Power=pw, PulsePower=pp, Duration=3, Pulse=1, Frequency=30)  # 1.121b
    for sid, lv in [(13625, 3), (13627, 13), (13628, 23), (13630, 33), (13631, 43)]:
        k.eod(ES, lv, sid)
    for sid, lv, dmg in [(13670, 5, None), (13672, 15, None), (13673, 25, None), (13674, 35, None), (13676, 45, 315)]:
        kw = dict(DamageType=11)
        if dmg:
            kw['Damage'] = dmg
        k.eod(ES, lv, sid, **kw)
    for i, (lv, n, dmg, pw) in enumerate([(7, 'Frosty Torment', 34, 4), (17, 'Bleak Torment', 68, 9), (27, 'Chilled Torment', 122, 17),
                                          (37, 'Icy Torment', 153, 22), (47, 'Frigid Torment', 199, 29)]):
        k.new(ES, lv, n, [13527, 13529, 13531, 13532, 13533][i], Damage=dmg, DamageType=11, CastTime=2.8, Power=pw)
    # 1.127 Body debuffs (1.128c raised 38/48 to 30/50%); the top rank also applies 40% Energy and Spirit debuffs for 12 s.
    spirit = k.new(None, 48, 'Reverberating Scream Spirit', 4458, Type='SpiritResistDebuff', Value=40, Duration=12, CastTime=0)
    energy = k.new(None, 48, 'Reverberating Scream Energy', 4458, Type='EnergyResistDebuff', Value=40, Duration=12, CastTime=0,
                   SubSpellID=spirit)
    for lv, n, v, pw, icon, sub in [(28, 'Reverberating Yell', 10, 10, 4457, 0), (38, 'Reverberating Shriek', 30, 15, 4458, 0),
                                    (48, 'Reverberating Scream', 50, 20, 4458, energy)]:
        k.new(ES, lv, n, icon, Type='BodyResistDebuff', Value=v, Duration=15, CastTime=2.0, Power=pw, SubSpellID=sub)
    # 1.121 level 50 PBAoE pet scare, as changed by 1.123: 2000 radius, 3 s cast, 60 s, 5-minute reuse.
    k.new(ES, 50, 'Ethereal Shriek', 15201, Type='PetScareArea', Range=0, Radius=2000, Duration=60, CastTime=3.0,
          RecastDelay=300, Power=-20)

    # Phantasmal Wail specialization.
    # 1.121: the single-target Dex/Qui debuff nuke became an AoE Body nuke with a 10% Body debuff.
    for lv, n, dmg, dur, pw in [(3, 'Restricting Yelp', 3, 10, 3), (7, 'Restricting Cry', 25, 10, 4), (13, 'Restricting Screech', 44, 10, 8),
                                (19, 'Restricting Shout', 64, 10, 10), (27, 'Restricting Blare', 89, 15, 13), (35, 'Restricting Bellow', 110, 15, 17),
                                (43, 'Restricting Shriek', 120, 15, 23), (48, 'Restricting Scream', 141, 15, 30)]:
        k.new(PW, lv, n, 13702, Type='DirectDamageWithDebuff', Radius=350, Damage=dmg, Value=10, Duration=dur, Power=pw)
    # Pulsing PBAoE damage chant: class library damage, radius and costs; 2.5 s pulses.
    for sid, lv, dmg, rad, pw, pp in [(13601, 1, 15, 300, 6, 1), (13602, 8, 66, 300, 13, 4), (13607, 14, 110, 300, 19, 7),
                                      (13603, 21, 161, 300, 26, 10), (13604, 32, 241, 300, 37, 15), (13605, 41, 307, 350, 46, 19),
                                      (13606, 46, 343, 350, 51, 21)]:
        k.eod(PW, lv, sid, Damage=dmg, Radius=rad, Power=pw, PulsePower=pp, CastTime=3.0, Pulse=1, Frequency=25)
    for sid, lv in zip(range(13610, 13616), [6, 12, 18, 25, 31, 42]):
        k.eod(PW, lv, sid)
    # Pet fear: added to Ethereal Shriek in 1.122b, moved here in 1.127, durations 1.123b, 3.5 s cast and levels per 1.129.
    for i, (lv, n, dur, pw) in enumerate([(9, 'Fear Minion', 5, 6), (19, 'Expel Minion', 9, 15), (29, 'Intimidate Minion', 15, 26),
                                          (39, 'Daunt Minion', 22, 35), (49, 'Terrify Minion', 30, 43)]):
        k.new(PW, lv, n, 15197 + i, Type='WarlockPetFear', Duration=dur, CastTime=3.5, Power=pw, DamageType=0)
    # 1.126 Resounding Aura with the 2020-02-12 hotfix: 375 Body damage, no snare, realm targets only.
    k.new(PW, 50, 'Resounding Aura', 13605, Type='BainsheeRealmPulse', Range=0, Radius=350, Damage=375, CastTime=3.0,
          Pulse=1, Frequency=25, Power=51, PulsePower=21)
    # Sound Vortex (live 1.130a, Bainshee specialization 50): a ground vortex that hits up to 8 enemies within 1500 units for
    # 300 every 4 s for 30 s; 10 s cast, 25% power, 10 minute reuse. Live also has Bawler's Obliteration at 50 in this line
    # and the client casts one spell per level, so spread_levels moves the vortex to the nearest free level.
    wave = k.new(None, 50, 'Sound Vortex Wave', 1145, Damage=300, CastTime=0, Range=3000, DamageType=10)
    k.new(SPEC, 50, 'Sound Vortex', 1145, Type='DeathKnightGround', Target='Area', Range=1500, Radius=1500, Duration=30, CastTime=10.0,
          Power=-25, RecastDelay=600, Damage=300, SubSpellID=wave, DamageType=10,
          _params=dict(GroundKind=2, GroundPulse=4000, GroundTargets=8))
    for _, _, row in k.rows:
        row.update(BAINSHEE_LIVE.get(row['Name'], {}))
    return k


def vampiir():
    k = Kit(58)
    DEM, SM, VE = KITS[58]['lines']
    # Vampiir Bolt class ability ranks first: VampiirBoltAbilityHandler casts kit base + ability level.
    # 1.123: castable in combat (handler change), range stays 1875, reuse 30 s -> 45 s.
    for sid in range(13200, 13208):
        k.eod(None, 0, sid, RecastDelay=45, Range=1875)

    def claws(line, ids, levels, powers):
        # 1.121c raised the level 48 claws to 36 power, 1.122b lowered them to 28, 1.127 raised every claw by 33%.
        for sid, lv, pw in zip(ids, levels, powers):
            k.eod(line, lv, sid, Power=round(pw * 1.33))

    # Dementia.
    claws(DEM, range(13170, 13179), [3, 10, 15, 20, 24, 27, 34, 41, 48], [2, 5, 7, 9, 12, 13, 17, 20, 28])
    for sid, lv in zip(range(13121, 13126), [8, 13, 23, 33, 43]):
        k.eod(DEM, lv, sid, RecastDelay=45)  # 1.129
    for sid, lv in zip(range(13130, 13135), [11, 18, 25, 35, 44]):
        k.eod(DEM, lv, sid, RecastDelay=45)  # 1.129
    for sid, lv in zip(range(13135, 13140), [5, 16, 28, 37, 49]):
        k.eod(DEM, lv, sid)
    for sid, lv in zip(range(13145, 13148), [30, 40, 50]):
        k.eod(DEM, lv, sid)
    # 1.121 removed the +skill and effectiveness debuffs; 1.121c returned them (Impress Confusion at 36).
    for sid, lv in zip(range(13150, 13154), [14, 26, 36, 46]):
        k.eod(DEM, lv, sid, RecastDelay=10)
    for sid, lv in zip(range(13155, 13161), [1, 9, 19, 29, 39, 47]):
        k.eod(DEM, lv, sid)
    k.eod(DEM, 45, 13165)
    # The 1.121 Night's Servant pet and its sacrifice were removed again in 1.125.

    # Shadow Mastery.
    for sid, lv in [(13001, 1), (13002, 5), (13011, 8), (13003, 13), (13004, 17), (13005, 22), (13006, 28), (13008, 37),
                    (13009, 43), (13010, 48)]:
        k.eod(SM, lv, sid)  # 1.121 removed Enervating Embrace (32)
    for sid, lv in [(13015, 4), (13016, 15), (13017, 20), (13099, 26), (13018, 38), (13019, 46)]:
        k.eod(SM, lv, sid)  # 1.121 moved Renewal from 21 to 20
    # 1.123 Flight spells: stay up in combat, 45 s, 15% power, stand-still cast (1.124b).
    for sid, lv, name in [(13020, 2, 'Flight of the Bat'), (13021, 10, 'Flight of the Marrach'), (13022, 19, 'Flight of the Gargoyle'),
                          (13023, 33, 'Flight of Shadow'), (13024, 44, 'Flight of Darkness')]:
        k.eod(SM, lv, sid, Name=name, Type='VampiirFlight', Duration=45, Power=-15, MoveCast=0, Uninterruptible=0)
    claws(SM, range(13025, 13034), [3, 9, 14, 18, 24, 29, 34, 40, 49], [2, 4, 7, 9, 12, 14, 17, 20, 28])  # Flaring Claw 19 -> 18
    for sid, lv in zip(range(13035, 13042), [7, 12, 16, 23, 31, 42, 50]):
        k.eod(SM, lv, sid)
    for sid, lv in [(13055, 30), (13056, 47)]:
        k.eod(SM, lv, sid)
    # Fumble moved here in 1.121; 60 s reuse (1.114b); 1.128 values 10/20/30%.
    for sid, lv, value, pw in [(13080, 11, 10, 6), (13081, 21, 20, 11), (13082, 32, 30, 16)]:
        k.eod(SM, lv, sid, Value=value, RecastDelay=60, Power=pw)

    # Vampiiric Embrace.
    for sid, lv in zip(range(13085, 13095), [1, 8, 14, 18, 22, 26, 30, 35, 42, 49]):
        k.eod(VE, lv, sid, Range=750)  # Blaze 36 -> 35 (1.121), Inferno 47 -> 49 (1.128), range 750 (1.129b)
    # Haste moved here in 1.121 and shares a reuse timer with the weaponskill and evade buffs.
    for sid, lv in zip(range(13061, 13066), [4, 10, 20, 33, 46]):
        k.eod(VE, lv, sid, SharedTimerGroup=71)
    for sid, lv in zip(range(13070, 13077), [6, 12, 17, 24, 31, 40, 50]):
        k.eod(VE, lv, sid, SharedTimerGroup=71)
    for sid, lv in zip(range(13045, 13050), [11, 16, 29, 36, 45]):
        k.eod(VE, lv, sid, SharedTimerGroup=71)
    claws(VE, range(13100, 13109), [3, 9, 15, 19, 25, 27, 34, 41, 48], [2, 5, 7, 9, 12, 13, 17, 20, 28])  # library costs
    for sid, lv in zip(range(13110, 13113), [13, 28, 38]):
        k.eod(VE, lv, sid)
    # 1.121 removed the NPC dismissal (Suppress/Subdue/Neutralize).
    # 1.128 self Determination (crowd-control duration reduction), 180 s. Costs are not published; estimated.
    for lv, name, value, pw in [(21, "Shadow's Will", 8, 10), (32, "Shadow's Endurance", 17, 15),
                                (39, "Shadow's Perserverence", 30, 20), (47, "Shadow's Spite", 46, 25)]:
        k.new(VE, lv, name, 7214, Type='VampiirDetermination', Target='Self', Range=0, Value=value, Duration=180,
              CastTime=3.0, Power=pw, DamageType=0)

    # Piercing styles: the EoD rows on the Vampiir client style IDs, with the class library effects as procs
    # (this world has no piercing style procs at all).
    def bleed(name, damage):
        return k.proc(name, 'StyleBleeding', damage=damage, duration=20, effect=2130, Frequency=40)

    def asd(name, value):
        return k.proc(name, 'StyleCombatSpeedDebuff', value=value, duration=20, effect=2140)

    def snare(name, duration):
        return k.proc(name, 'StyleSpeedDecrease', value=40, duration=duration, effect=2135)

    P = 'Piercing'
    k.style(P, 1, 418, 1529)
    k.style(P, 4, 419, 1544, procs=[(bleed("Wasp's Sting Effect", 8), 100)])
    k.style(P, 6, 420, 1542, procs=[(k.proc("Vampiir's Sting Effect", 'StyleTaunt', value=17, effect=7353, damage_type=0), 100)])
    k.style(P, 8, 421, 1533, follows="Wasp's Sting", procs=[(asd("Hornet's Sting Effect", 18), 100)])
    k.style(P, 10, 422, 1537, procs=[(k.proc('Scorpion Effect', 'StyleTaunt', value=-19, effect=7354, damage_type=0), 100)])
    k.style(P, 11, 423, 1532)
    k.style(P, 12, 425, 1525, procs=[(snare('Black Widow Effect', 12), 100)])
    k.style(P, 12, 424, 1540)
    k.style(P, 13, 426, 1535)
    k.style(P, 15, 427, 1539, procs=[(bleed('Tarantula Effect', 14), 100)])
    k.style(P, 18, 428, 1538, follows='Black Widow', procs=[(asd('Sidewinder Effect', 21), 100)])
    k.style(P, 21, 429, 1527, procs=[(snare('Copperhead Effect', 15), 100)])
    k.style(P, 25, 430, 1528, procs=[(bleed('Diamondback Effect', 20), 100)])
    k.style(P, 29, 431, 1543, follows='Tarantula', procs=[(asd("Viper's Bite Effect", 26), 100)])
    k.style(P, 34, 432, 1524)
    k.style(P, 39, 434, 1526, follows='Copperhead', procs=[(bleed("Cobra's Bite Effect", 26), 100)])
    # 1.123: Vampiiric Feint raises spell crit to 25% for 10 s; Eye Shot, Lung Shot and Knee Cap became front, side
    # and back positionals, which the client carries as separate styles.
    feint = k.new(None, 0, 'Vampiiric Feint Effect', 15347, Type='VampiirFeint', Target='Self', Range=0, Value=25,
                  Duration=10, CastTime=0, DamageType=0)
    k.style(P, 41, 433, 1541, procs=[(feint, 100)])
    k.style(P, 43, 577, 1531, OpeningRequirementType=2, OpeningRequirementValue=2, AttackResultRequirement=0)
    stun = k.proc('Dragonspider Effect', 'StyleStun', duration=8, effect=2132, damage_type=0)
    k.style(P, 44, 436, 1530, follows='Diamondback', procs=[(stun, 100)])
    k.style(P, 44, 578, 1536, OpeningRequirementType=2, OpeningRequirementValue=1, AttackResultRequirement=0)
    k.style(P, 45, 579, 1534, OpeningRequirementType=2, OpeningRequirementValue=0, AttackResultRequirement=0)
    k.style(P, 50, 439, 1545, follows="Asp's Bite", procs=[(asd("Wyvern's Bite Effect", 34), 100)])
    return k


def heretic():
    k = Kit(33)
    RS, ES, BASE = KITS[33]['lines']
    HEAT, MATTER = 13, 14

    # Rejuvenation specialization (the Rejuvenation baseline is the shared Albion line and is left alone).
    for sid, lv in zip(range(14044, 14053), [1, 4, 9, 15, 21, 26, 31, 37, 47]):
        # 1.125: interruptible focus DD range 1650. Arawn's Singe art is not in this client.
        k.eod(RS, lv, sid, Range=1650, **({'Icon': 14045} if sid == 14044 else {}))
    for sid, lv in [(14065, 3), (14066, 6), (14064, 10), (14067, 13), (14068, 20), (14069, 29), (14070, 38), (14071, 49)]:
        k.eod(RS, lv, sid, Value=50)  # class library: 50% snare
    for sid, lv in zip(range(14055, 14062), [9, 14, 19, 25, 32, 40, 50]):
        k.eod(RS, lv, sid, Range=1650, Value=40)  # 1.121 1750, 1.126 1650; 1.128 snare 60% -> 40%; 3 s snare (1.125b)
    for sid, lv in [(14080, 36), (14081, 42), (14082, 48)]:
        # The uninterruptible focus DDs stay at 1600 range (1.125). 2020 hotfix: Torrential Blaze 2.5 s.
        k.eod(RS, lv, sid, Range=1600, **({'CastTime': 2.5} if sid == 14082 else {}))
    for sid, lv in zip(range(1351, 1359), [5, 8, 11, 14, 18, 25, 33, 43]):
        k.eod(RS, lv, sid)
    # 1.123: the instant Embers DoT became an instant direct-damage shout (Bursting Embers 39 -> 38).
    for icon, lv, name, dmg, pw in [(14036, 5, 'Flickering Embers', 19, 3), (14037, 10, 'Smoldering Embers', 34, 6),
                                    (14038, 16, 'Heated Embers', 48, 10), (14039, 23, 'Molten Embers', 76, 13),
                                    (14040, 30, 'Flaming Embers', 96, 19), (14041, 38, 'Bursting Embers', 129, 25),
                                    (14042, 48, 'Incinerating Embers', 160, 32)]:
        k.new(RS, lv, name, icon, Damage=dmg, DamageType=HEAT, CastTime=0, Power=pw, RecastDelay=15, SharedTimerGroup=30)
    # Fiery Grasp instant snare: 1.123 range 1000; reuse 30 s (1.126, after 1.125 had lowered it to 20 s); class library 50%.
    for sid, lv in zip(range(14085, 14091), [6, 12, 20, 28, 37, 46]):
        k.eod(RS, lv, sid, Range=1000, RecastDelay=30, Value=50)
    # 1.125: the focused snare/attack-speed debuff became the Cocoon line: a 3 s normal cast that puts an all-damage
    # ablative on the enemy with ramping combat effectiveness and swing speed debuffs (HereticCocoon handler).
    # Power costs are not published; these keep the old focus spells' opening costs.
    for icon, lv, name, ablative, start, step, cap, pw in [
            (14095, 7, 'Afflicting Cocoon', 10, 5, 1, 10, 1), (14096, 11, 'Aggravating Cocoon', 25, 8, 2, 16, 3),
            (14097, 21, 'Hindering Cocoon', 50, 12, 3, 24, 11), (14098, 27, 'Lacerating Cocoon', 75, 16, 4, 32, 17),
            (14099, 33, 'Agonizing Cocoon', 100, 20, 5, 40, 22), (14100, 41, 'Tormenting Cocoon', 150, 22, 5, 44, 26),
            (14101, 49, 'Destructive Cocoon', 200, 25, 5, 50, 31)]:
        k.new(RS, lv, name, icon, Type='HereticCocoon', Range=1500, CastTime=3.0, Duration=60, Value=ablative, Damage=100,
              Power=pw, DamageType=HEAT, _params=dict(CocoonStart=start, CocoonStep=step, CocoonMax=cap))
    # 1.121: single-target Matter nuke.
    for icon, lv, name, dmg, pw in [(81, 2, 'Dark Ashes', 13, 4), (82, 17, 'Dark Obsidian', 67, 9), (83, 24, 'Dark Slag', 89, 14),
                                    (84, 35, 'Dark Basalt', 146, 28), (3494, 45, 'Dark Magma', 184, 44)]:
        k.new(RS, lv, name, icon, Damage=dmg, DamageType=MATTER, CastTime=2.6, Power=pw)
    k.eod(RS, 41, 14076)  # Reanimate Corpse; the 1.121 rework is not modelled (see docs)
    for _, _, row in k.rows:
        if row['Name'] == 'Monster Disease':
            row.update(Icon=14075, ClientEffect=14075)  # EoD art 14078 is not in this client

    # Enhancement specialization.
    for sid, lv in zip(range(14201, 14208), [5, 10, 16, 23, 32, 40, 50]):
        k.eod(ES, lv, sid)
    for sid, lv, af in zip(range(14234, 14241), [7, 12, 17, 26, 33, 43, 50], [68, 94, 136, 165, 250, 360, 400]):
        k.eod(ES, lv, sid, Value=af)  # 1.125
    for sid, lv in zip(range(14210, 14216), [11, 15, 21, 27, 37, 46]):
        k.eod(ES, lv, sid)  # 1.121 Infernal Tear 36 -> 37
    for sid, lv in zip(range(14260, 14265), [10, 20, 30, 40, 50]):
        k.eod(ES, lv, sid)
    for sid, lv, absorb in zip(range(14190, 14196), [9, 21, 25, 32, 41, 49], [10, 15, 20, 25, 30, 33]):
        k.eod(ES, lv, sid, Value=absorb)  # 1.121 moved Warmth and Heat from the baseline; 1.125 values
    # 1.121 removed the single and group damage shields and the group buff-shear procs.
    # 1.121 single-stat debuffs, 2.8 s, 1750 range, 45 s.
    for kind, ranks in [('ConstitutionDebuff', [(11301, 4, 'Dark Horror', 11, 5), (11302, 20, 'Mind Horror', 25, 14),
                                                (11303, 31, 'Evil Horror', 31, 18), (11304, 42, 'Demon Horror', 41, 22)]),
                        ('StrengthDebuff', [(673, 3, 'Soften Joints', 11, 5), (674, 13, 'Soften Limbs', 16, 9),
                                            (10171, 22, 'Soften Bones', 25, 14), (10177, 34, 'Soften Muscle', 31, 18),
                                            (10177, 44, 'Soften Strength', 41, 22)]),
                        ('DexterityDebuff', [(2524, 6, 'Heat Wave', 11, 5), (2525, 16, 'Heat Rush', 16, 9),
                                             (2526, 25, 'Heal Swell', 25, 14), (2527, 35, 'Heat Coil', 31, 18),
                                             (2528, 45, 'Heat Flux', 41, 22)])]:
        for icon, lv, name, value, pw in ranks:
            k.new(ES, lv, name, icon, Type=kind, Value=value, Duration=45, CastTime=2.8, Range=1750, Power=pw, DamageType=HEAT)
    k.new(ES, 36, 'Endowment Seize', 1583, Type='StrengthConstitutionShear', CastTime=3.0, Range=1750, Power=12, DamageType=HEAT)
    # 1.123 Hellflower chant: instant, pulses every 6 s, 10% power, group health and armor factor (1.125 values).
    for rank, (lv, name, value) in enumerate([(5, "Hellflower's Flourish", 1), (15, "Hellflower's Bud", 2), (25, "Hellflower's Sprout", 3),
                                              (35, "Hellflower's Effloresce", 4), (45, "Hellflower's Bloom", 6)]):
        # Art: the client's live "health af aura" effects, grey to red.
        k.new(ES, lv, name, 15351 + rank, Type='HereticHellflower', Target='Group', Range=1500, Radius=1500, Value=value, Duration=6,
              CastTime=0, Pulse=1, Frequency=60, RecastDelay=5, Power=-10, DamageType=0)

    # Enhancement baseline: concentration buffs; Buffer of Warmth/Heat moved to the specialization (1.121).
    for sid, lv in [(1461, 2), (1462, 5), (1463, 10), (1464, 16), (1465, 22), (1466, 31)]:
        k.eod(BASE, lv, sid)
    k.eod(BASE, 42, 1467, Value=150)  # 1.122b
    for sid, lv in [(1451, 3), (1452, 7), (1453, 14), (1454, 20), (1455, 30), (1456, 41), (1457, 50),
                    (1471, 8), (1472, 13), (1473, 19), (1474, 28), (1475, 38), (1476, 48),
                    (1481, 6), (1482, 11), (1483, 15), (1484, 24), (1485, 33), (1487, 39), (1486, 43)]:
        k.eod(BASE, lv, sid)

    # Styles: EoD rows with the class library effects as procs, plus the 1.121-1.126 changes.
    def bleed(name, damage):
        return k.proc(name, 'StyleBleeding', damage=damage, duration=20, effect=2130, Frequency=40)

    def asd(name, value):
        return k.proc(name, 'StyleCombatSpeedDebuff', value=value, duration=20, effect=2140)

    def snare(name, duration):
        return k.proc(name, 'StyleSpeedDecrease', value=40, duration=duration, effect=2135)

    def stun(name, duration):
        return k.proc(name, 'StyleStun', duration=duration, effect=2132, damage_type=0)

    def taunt(name, value):
        return k.proc(name, 'StyleTaunt', value=value, effect=7353 if value > 0 else 7354, damage_type=0)

    def heat(name, damage, drain=0):
        return k.proc(name, 'Lifedrain' if drain else 'DirectDamage', damage=damage, effect=9644, damage_type=HEAT, LifeDrainReturn=drain)

    C, F, S = 'Crush', 'Flexible', 'Shields'
    k.style(C, 1, 71, 533)
    k.style(C, 2, 529, 532, follows='Daze', Icon=75, TwoHandAnimation=75, procs=[(bleed('Crusher Effect', 8), 100)])  # no Heretic client style
    k.style(C, 4, 72, 517, procs=[(asd('Back Crush Effect', 16), 100)])
    k.style(C, 6, 73, 543, procs=[(taunt('Maul Effect', -19), 100)])
    k.style(C, 8, 74, 521, procs=[(taunt('Bludgeon Effect', 17), 100)])
    k.style(C, 10, 75, 525, procs=[(stun('Bruiser Effect', 3), 100)])
    k.style(C, 12, 76, 528, procs=[(asd('Concussion Effect', 18), 100)])
    k.style(C, 15, 77, 530, procs=[(stun('Contusions Effect', 4), 100)])
    k.style(C, 18, 78, 519, procs=[(bleed('Blackjack Effect', 14), 100)])
    k.style(C, 21, 79, 546)
    k.style(C, 25, 80, 537, procs=[(snare('Divine Hammer Effect', 15), 100)])
    k.style(C, 29, 81, 549)
    k.style(C, 34, 82, 548, procs=[(snare('Side Crush Effect', 19), 100)])
    # 1.121 Very High damage; 1.123 removes a random positive effect from every enemy within 350.
    shear = k.proc('Bone Crusher Effect', 'RandomBuffShear', effect=13165, Radius=350)
    k.style(C, 39, 83, 523, GrowthRate=eod('Style', 'StyleID')[529]['GrowthRate'], procs=[(shear, 100)])
    k.style(C, 44, 84, 522, procs=[(stun('Body Masher Effect', 8), 100)])
    k.style(C, 50, 85, 534, procs=[(asd('Devastate Effect', 30), 100)])
    # 1.123 Shadowfire: back positional, 113 Heat damage. (Hellfire Tendrils has no client style and is not added.)
    k.style(C, 50, 583, 534, Name='Shadowfire', OpeningRequirementType=2, OpeningRequirementValue=0, AttackResultRequirement=0,
            procs=[(heat('Shadowfire Effect', 113), 100)])

    k.style(F, 1, 554, 1673)
    k.style(F, 2, 355, 520)
    k.style(F, 4, 356, 540, procs=[(bleed('Kingsnake Effect', 8), 100)])
    k.style(F, 6, 357, 535, procs=[(taunt('Diamondback Effect', 17), 100)])
    k.style(F, 8, 358, 516, procs=[(taunt('Asp Effect', -19), 100)])
    k.style(F, 10, 359, 554)
    k.style(F, 12, 360, 531, procs=[(stun('Copperhead Effect', 5), 100)])
    k.style(F, 15, 361, 553, procs=[(asd('Tigersnake Effect', 22), 100)])
    k.style(F, 18, 362, 539, procs=[(heat('Hellfire Bane', 45, drain=30), 100)])  # 1.126: 70% -> 30% returned
    k.style(F, 21, 363, 524, procs=[(snare('Boomslang Effect', 19), 100)])
    curse = k.proc('Hellfire Curse', 'StrengthDebuff', value=30, duration=30, effect=673, damage_type=HEAT)
    k.style(F, 25, 364, 547, procs=[(curse, 100)])
    k.style(F, 29, 365, 552, procs=[(snare('Taipan Effect', 23), 100)])
    k.style(F, 34, 366, 529, procs=[(heat('Demonic Pain', 45), 100)])
    k.style(F, 39, 367, 515, procs=[(stun('Anaconda Effect', 8), 100)])
    k.style(F, 44, 368, 527, procs=[(heat('Demonic Soul', 130, drain=100), 100)])
    # 1.123 Leviathan: back positional, 113 Heat damage.
    k.style(F, 50, 369, 541, OpeningRequirementType=2, OpeningRequirementValue=0, AttackResultRequirement=0,
            procs=[(heat('Demonic Touch', 113), 100)])

    for sid, lv, cid, duration in [(1668, 1, 563, 0), (544, 3, 221, 2), (551, 8, 222, 3), (536, 13, 223, 4), (538, 18, 224, 5),
                                   (545, 23, 225, 6), (518, 29, 226, 7), (542, 35, 227, 8), (550, 42, 228, 5), (526, 50, 229, 10)]:
        name = eod('Style', 'StyleID')[sid]['Name']
        k.style(S, lv, cid, sid, procs=[(stun(f'{name} Effect', duration), 100)] if duration else [])
    return k



# ---------------------------------------------------------------------------------------------------------------
# Death Knight (66): the live 1.122B Necromancer redesign with the 1.122C-1.130A tuning, beside the classic
# Necromancer (12). Spell/line/spec keys are its own; the display names match live. Levels, costs, timers and
# sub-spell values come from the live spell data (daoc.gg planner, 1.123b baseline plus its patch log through
# 1.130a); where the patch notes changed a value after that baseline, the patched value is used.
# ---------------------------------------------------------------------------------------------------------------
SPIRIT, MATTER, COLD, ENERGY, HEAT = 15, 14, 11, 12, 13
DK_GROUND_TIMER = 6601   # one reuse timer for every Death Knight ground spell
DK_FORM_TIMER = 6602     # 2 s reuse shared by all forms and Revert Form
DK_EMPOWER_TIMER = 6603  # 5 s reuse shared by the Empowerment chants
DK_CONVERT_TIMER = 6604  # 60 s reuse shared by the magic conversion line
DK_PET_TEMPLATES = dict(Aegis=66001, Soultorn=66002, Fiend=66003, Priest=66004, Succubus=66005)
DK_LEGION_TEMPLATE = 66006
DK_SPIRIT_OFFSET = 10    # DeathKnight.SpiritTemplateOffset: the servant's Spirit Form template
DK_RAS = ('AtlasOF_AugStr', 'AtlasOF_AugDex', 'AtlasOF_AugCon', 'AtlasOF_AugQui', 'AtlasOF_AugAcuity', 'AtlasOF_LongWind',
          'AtlasOF_Serenity', 'AtlasOF_Toughness', 'AtlasOF_EtherealBond', 'AtlasOF_AoM', 'AtlasOF_Lifter', 'AtlasOF_VeilRecovery',
          'AtlasOF_MasteryOfPain', 'AtlasOF_MasteryOfMagery', 'Mastery of Focus', 'AtlasOF_WildPower', 'AtlasOF_WildMinion',
          'AtlasOF_Determination', 'AtlasOF_FirstAid', 'AtlasOF_SecondWind', 'AtlasOF_IgnorePain', 'AtlasOF_MasteryOfConcentration',
          'AtlasOF_Concentration', 'AtlasOF_EmptyMind', 'AtlasOF_MCL', 'AtlasOF_RagingPower', 'AtlasOF_SoldiersBarricade',
          'AtlasOF_VolcanicPillar', 'AtlasOF_NegativeMaelstrom', 'AtlasOF_Ichor', 'AtlasOF_Juggernaut', 'Dual Threat', 'AtlasOF_Purge')
DK_RR5 = dict(KeyName='DeathKnight Call of Darkness', Name='Call of Darkness', InternalID=3105,
              Implementation='DOL.GS.RealmAbilities.ModernDeathKnightDarkness',
              Description='Death Knight RR5: 45 seconds of Darkness, the benefits of every form increased by 10%.')
# Conjured blade bonuses from the live item data (eProperty: 3 Con, 4 Qui, 5 Int, 10 hits, 12 cold resist, 155 melee
# speed, 163 all magic skills, 173 melee damage, 197 resist pierce, 198 spell damage, 200 style damage), by level.
ICEBRAND_BONUSES = (
    (1, [(10, 5), (3, 3), (4, 3), (5, 3), (198, 1), (173, 1)]),
    (10, [(10, 15), (3, 10), (4, 7), (5, 3), (198, 1), (173, 1)]),
    (22, [(10, 35), (3, 15), (4, 10), (5, 5), (173, 2), (155, 2), (198, 2), (12, 3)]),
    (28, [(10, 35), (3, 20), (4, 15), (5, 10), (173, 2), (155, 2), (198, 2), (12, 4), (200, 2)]),
    (45, [(4, 20), (163, 4), (197, 3), (198, 2), (173, 3), (155, 3), (200, 2), (12, 5)]),
)
NETHERSBANE_BONUSES = [(4, 40), (163, 5), (197, 5), (198, 4), (173, 4), (155, 4), (200, 4), (12, 5)]
# Icons and spell effects (client spells.csv rows). Where a live spell keeps an older spell's name, it uses that
# spell's effect (the classic Necromancer ranks); each rank of a line steps through its effect series; the rest use
# the closest dedicated client effect (Dead Awakening, Grapple, Arawn's Gift, the Demonic pet spells).
DK_ICONS = {
    'Vitality Theft': 9015,
    'Locust Flock': 9322, 'Locust Cloud': 9322, 'Locust Mass': 9324, 'Locust Horde': 9324, 'Locust Swarm': 9326,
    'Billowing Death': 9321, 'Flowing Death': 9323, 'Unending Death': 9325, 'Swelling Death': 9327, 'Heightening Death': 9328,
    'Infinite Death': 9329,
    'Dark Horror': 11301, 'Vile Horror': 11302, 'Mind Horror': 11302, 'Evil Horror': 11303, 'Demon Horror': 11304,
    'Eviscerating Protector': 9515,
    'Power Drain': 9111, 'Power Vacuum': 9112, 'Power Leech': 9113, 'Power Siphon': 9114, 'Power Absorb': 9115,
    'Power Blast': 9161, 'Focus Blast': 9162, 'Essence Blast': 9163, 'Death Blast': 9164, 'Final Blast': 9164,
    'Communion with Death': 9102, 'Intimacy with Death': 9103, 'Gift of Arawn': 9128,
    'Wake Servant': 9222, 'Power Lock': 7275, 'Power Locked': 7275, "Arawn's Legion": 9408, 'Spirit Shell': 3919,
    'Aegis Shell': 5683, 'Fiend Swings': 5682, "Arawn's Heal": 5672, "Arawn's Cleansing": 5672,
}
# The Regenerate line uses the classic rows' separate icon (946x) and effect (941x).
DK_REGEN_ICONS = {'Regenerate Flesh': (9461, 9411), 'Regenerate Blood': (9462, 9412), 'Regenerate Muscle': (9464, 9414),
                  'Regenerate Body': (9466, 9416), 'Dead Flesh Living': (9467, 9417), 'Imbue the Abyss': (9468, 9418)}
DK_TRAINER_NAMES = ('Morwenna', 'Caedric', 'Ysolde', 'Thane Malric', 'Severine', 'Aldous', 'Gwenllian')


def death_knight():
    k = Kit(66)
    DSB, DSS, PWB, PWS, SVB, SVS = KITS[66]['lines']
    nochthonic = dict(DkNoChthonic=1)

    # Fixed rows first: the RR5 Darkness form (ModernDeathKnightDarkness.SpellId) and the Decrepit disease proc it shares.
    darkness_id = k.info['spells']
    decrepit_disease = darkness_id + 1
    k.new(None, 50, 'Darkness', 7051, Type='DeathKnightForm', Target='Self', Range=0, Value=4, Duration=30, CastTime=0,
          DamageType=0, _params=dict(DkDisease=decrepit_disease))
    k.new(None, 0, 'Wasting Disease', 9313, Type='Disease', Duration=10, Value=15, CastTime=0, Range=1500, DamageType=0)

    def form(line, level, name, icon, value):
        return k.new(line, level, name, icon, Type='DeathKnightForm', Target='Self', Range=0, Value=value, CastTime=0,
                     Power=-20, DamageType=0, SharedTimerGroup=DK_FORM_TIMER, RecastDelay=2, _params=dict(DkDisease=decrepit_disease))

    def ground(line, level, name, icon, kind, power, radius, rng, duration, pulse, value=0, damage=0, sub=0, targets=16):
        return k.new(line, level, name, icon, Type='DeathKnightGround', Target='Area', Range=rng, Radius=radius, CastTime=0,
                     Duration=duration, Power=power, Value=value, Damage=damage, SubSpellID=sub, RecastDelay=90,
                     SharedTimerGroup=DK_GROUND_TIMER, DamageType=COLD if kind == 2 else 0,
                     _params=dict(GroundKind=kind, GroundPulse=pulse, GroundTargets=targets))

    # ---- Deathsight baseline ----
    form(DSB, 1, 'Decrepit Form', 9021, 1)
    k.new(DSB, 1, 'Revert Form', 9073, Type='DeathKnightRevert', Target='Self', Range=0, CastTime=0, DamageType=0,
          SharedTimerGroup=DK_FORM_TIMER, RecastDelay=2)
    for lv, name, dmg, pw, icon in [(2, 'Locust Flock', 2, 8, 9321), (12, 'Locust Cloud', 7, 15, 9321), (22, 'Locust Mass', 21, 28, 9323),
                                    (32, 'Locust Horde', 30, 28, 9323), (42, 'Locust Swarm', 69, 55, 9323)]:
        k.new(DSB, lv, name, icon, Type='DamageOverTime', Damage=dmg, Duration=10, Frequency=20, CastTime=2.8, DamageType=MATTER,
              Power=pw)
    for lv, name, dmg, pw, icon in [(3, 'Lifeforce Evacuation', 17, 3, 9011), (9, 'Spirit Evacuation', 33, 5, 9013),
                                    (19, 'Vitality Theft', 73, 13, 9016), (29, 'Theft of Vigor', 92, 18, 9016),
                                    (39, 'Theft of Energy', 126, 24, 9018), (49, 'Theft of Liveliness', 179, 33, 9019)]:
        k.new(DSB, lv, name, icon, Type='Lifedrain', Damage=dmg, LifeDrainReturn=50, CastTime=2.5, Power=pw, DamageType=SPIRIT)
    # 1.122C replaced the slow ground with a wasting disease; 1.123 90 s reuse; 1.126 15 s duration; live: a pulse a
    # second on up to 8 enemies; 1.130A Unholy Ground radius 375.
    for lv, name, radius, pw in [(6, 'Decrepit Ground', 250, 20), (16, 'Wretched Ground', 275, 30), (26, 'Rotting Ground', 300, 45),
                                 (36, 'Desecrated Ground', 325, 62), (46, 'Unholy Ground', 375, 75)]:
        ground(DSB, lv, name, 9313, 1, pw, radius, 1000, 15, 1000, sub=decrepit_disease, targets=8)

    # ---- Deathsight specialization ----
    for lv, name, dmg, freq, pw, icon in [(1, 'Billowing Death', 2, 50, 6, 9321), (7, 'Flowing Death', 17, 50, 18, 9321),
                                          (17, 'Unending Death', 30, 40, 30, 9323), (27, 'Swelling Death', 60, 40, 42, 9323),
                                          (37, 'Heightening Death', 88, 30, 50, 9323), (47, 'Infinite Death', 121, 25, 64, 9323)]:
        k.new(DSS, lv, name, icon, Type='DamageOverTime', Radius=350, Damage=dmg, Duration=20, Frequency=freq, CastTime=3.0,
              Power=pw, DamageType=SPIRIT)
    # AF debuff: 1.122C 15 s, 1.123 20 s.
    for lv, name, af, pw, icon in [(3, 'Glimpse of the Inevitable', 25, 8, 9002), (13, 'Glimpse of Chaos', 55, 17, 9001),
                                   (23, 'Glimpse of the Grave', 100, 25, 9003), (33, 'Glimpse of Nightmares', 165, 36, 9003),
                                   (43, 'Glimpse of Death', 250, 50, 9004)]:
        k.new(DSS, lv, name, icon, Type='ArmorFactorDebuff', Value=af, Duration=20, CastTime=3.0, Power=pw, DamageType=SPIRIT)
    # PBAoE (1.123 damage at 35/45; usable in Decrepit and Spirit Form, not Chthonic).
    for lv, name, dmg, pw, icon in [(5, 'Channeled Anger', 52, 22, 9501), (15, 'Channeled Hatred', 104, 30, 9503),
                                    (25, 'Channeled Fury', 176, 46, 9506), (35, 'Channeled Wrath', 240, 58, 9507),
                                    (45, 'Channeled Frenzy', 305, 65, 9508)]:  # 1.130A: 65 power
        k.new(DSS, lv, name, icon, Range=0, Radius=300, Damage=dmg, CastTime=2.5, Power=pw, DamageType=SPIRIT, _params=nochthonic)
    for lv, name, dur, pw, icon in [(9, 'Minor Body Lock', 7, 15, 771), (19, 'Lesser Body Lock', 19, 28, 771), (29, 'Body Lock', 48, 48, 772),
                                    (39, 'Greater Body Lock', 61, 60, 773), (49, 'Superior Body Lock', 73, 72, 774)]:
        k.new(DSS, lv, name, icon, Type='SpeedDecrease', Value=99, Duration=dur, CastTime=2.5, Power=pw, DamageType=ENERGY)
    for rank, (lv, name, value, pw, pp) in enumerate([(6, 'Magic Empowerment', 1, 24, 5), (16, 'Evil Empowerment', 2, 40, 8), (26, 'Dark Empowerment', 3, 60, 10),
                                                      (36, 'Deadly Empowerment', 4, 80, 15), (46, 'Necrotic Empowerment', 5, 100, 25)]):
        k.new(DSS, lv, name, 15227 + rank, Type='DeathKnightEmpowerment', Target='Group', Range=1500, Radius=1500, Value=value, Duration=6,
              Frequency=60, Pulse=1, PulsePower=pp, CastTime=3.0, Power=pw, DamageType=0, RecastDelay=5, SharedTimerGroup=DK_EMPOWER_TIMER)
    k.new(DSS, 24, 'Death Bladeturn', 13520, Type='Bladeturn', Target='Self', Range=0, Duration=1200, CastTime=4.0, Power=-8, DamageType=0)
    # 1.127: Speed of the Dead replaced Bringer of Death.
    k.new(DSS, 50, 'Speed of the Dead', 13024, Type='VampiirFlight', Target='Self', Range=0, Value=235, Duration=20, CastTime=0,
          RecastDelay=300, DamageType=0)

    # ---- Painworking baseline ----
    form(PWB, 8, 'Chthonic Form', 9024, 2)
    for lv, name, value, pw in [(4, 'Dark Horror', 11, 5), (14, 'Vile Horror', 18, 20), (24, 'Mind Horror', 25, 28),
                                (34, 'Evil Horror', 31, 34), (44, 'Demon Horror', 41, 48)]:
        k.new(PWB, lv, name, 11301, Type='ConstitutionDebuff', Value=value, Duration=45, CastTime=0, RecastDelay=7, Power=pw, DamageType=SPIRIT)
    for lv, name, dps, icon in [(7, 'Edge of Hatred', 5.8, 9514), (17, 'Eviscerating Protector', 8.9, 9516), (27, 'Knives of Death', 11.6, 9516),
                                (37, 'Flaying Shield', 15.3, 9517), (47, 'Soul Sundering Shield', 21.1, 9518)]:
        k.new(PWB, lv, name, icon, Type='DamageShield', Target='Self', Range=0, Damage=dps, Duration=1200, CastTime=2.2, Power=-20,
              DamageType=SPIRIT)
    # Icy Ground: 1.123 90 s reuse, 1.124D damage, 1.126 15 s duration.
    for lv, name, dmg, pw in [(1, 'Icy Ground', 3, 12), (11, 'Chilling Ground', 12, 28), (21, 'Frigid Ground', 27, 45),
                              (31, 'Numbing Ground', 72, 54), (41, 'Freezing Ground', 112, 62)]:
        hit = k.new(None, lv, f'{name} Strike', 241, Damage=dmg, CastTime=0, Range=3000, DamageType=COLD)
        ground(PWB, lv, name, 241, 2, pw, 200, 200, 15, 3000, damage=dmg, sub=hit)

    # ---- Painworking specialization ----
    # Ice snares: 1.122C snare that ignores immunity, 1.123 durations, 1.123B range/reuse, 1.128C 70%.
    for lv, name, dur, rng, reuse, icon in [(11, 'Ice Bond', 1, 500, 300, 15192), (21, 'Ice Cable', 2, 500, 300, 15193),
                                            (31, 'Ice Chain', 4, 750, 180, 15194), (41, 'Ice Bracelet', 6, 1000, 60, 15195)]:
        k.new(PWS, lv, name, icon, Type='DeathKnightSnare', Value=70, Duration=dur, Range=rng, RecastDelay=reuse, CastTime=0,
              Power=0, DamageType=COLD)
    for lv, name, value in [(2, 'Anti-Magic Skin', 10), (12, 'Anti-Magic Shell', 20), (22, 'Anti-Magic Armor', 30),
                            (32, 'Anti-Magic Wall', 40), (42, 'Anti-Magic Barrier', 50)]:
        k.new(PWS, lv, name, 3904, Type='AllSecondaryMagicResistsBuff', Target='Self', Range=0, Value=value, Duration=15,
              RecastDelay=600, CastTime=0, Power=0, DamageType=0)
    # Magic conversion: 1.123 5 s cast and 30% power, 1.125 renewals, 1.127 conversion, 1.129B self only.
    for rank, (lv, name, renew, convert) in enumerate([(4, 'Soul of Magic', 30, 5), (14, 'Sense of Magic', 25, 10), (24, 'Awareness of Magic', 20, 25),
                                                       (34, 'Expectancy of Magic', 16, 50), (44, 'Way of Magic', 12, 75)]):
        k.new(PWS, lv, name, 15238 + rank, Type='DeathKnightMagicWard', Target='Self', Range=0, Value=9999, Damage=convert,
              Duration=renew, Frequency=renew * 10, Pulse=1, CastTime=5.0, Power=-30, DamageType=0, RecastDelay=60,
              SharedTimerGroup=DK_CONVERT_TIMER, _params=dict(WardHeal=convert))
    # (The 1.122B Arawn parry buffs are not in the live spell list; Chthonic Form's parry replaced them.)
    # Ignore line: 1.123 range 2000; 1.129B 20 s and 180 s reuse.
    for lv, name, value, icon in [(9, 'Ignore Weakness', 25, 10513), (19, 'Ignore Debilitation', 35, 10514), (29, 'Ignore Infirmity', 50, 10515),
                                  (39, 'Ignore Impunities', 70, 10516), (49, 'Ignore Depletion', 100, 10518)]:
        k.new(PWS, lv, name, icon, Type='DeathKnightIgnore', Target='Realm', Range=2000, Value=value, Duration=20, RecastDelay=180,
              CastTime=0, Power=-10, DamageType=0)
    # Freezing Howl line: instant DoT and slow (1.123, 1.124D and 1.126 damage/reuse; slow ignores immunity).
    for lv, name, dmg, slow, reuse, freq, pw, icon in [(7, 'Freezing Hold', 2, 0, 60, 20, 12, 15192), (17, 'Freezing Grasp', 7, 5, 60, 20, 24, 15193),
                                                       (27, 'Freezing Terror', 12, 10, 30, 20, 38, 15194), (37, 'Freezing Clench', 20, 15, 30, 20, 52, 15195),
                                                       (47, 'Freezing Howl', 43, 25, 20, 15, 65, 15196)]:
        sub = k.new(None, lv, f'{name} Slow', icon, Type='DeathKnightSnare', Value=slow, Duration=10, CastTime=0, Range=500,
                    Radius=250, DamageType=COLD) if slow else 0
        k.new(PWS, lv, name, icon, Type='DamageOverTime', Range=500, Radius=250, Damage=dmg, Duration=10, Frequency=freq,
              RecastDelay=reuse, CastTime=0, Power=pw, DamageType=COLD, SubSpellID=sub)
    k.new(PWS, 1, 'Conjure Icebrand', 15185, Type='DeathKnightConjure', Target='Self', Range=0, Value=1, CastTime=10.0, Power=-25, DamageType=0)
    k.new(PWS, 50, 'Nethersbane', 15184, Type='DeathKnightConjure', Target='Self', Range=0, Value=50, CastTime=15.0, Power=-50, DamageType=0)
    # Nethersbane's procs: a 150 cold strike and its cold resistance debuff (live item: "resist debuff").
    k.nether_procs = (k.proc('Nethersbane Strike', 'DirectDamage', damage=150, effect=15184, damage_type=COLD),
                      k.proc('Nethersbane Chill', 'ColdResistDebuff', value=15, duration=10, effect=15184))

    # ---- Death Servant baseline ----
    form(SVB, 30, 'Spirit Form', 9026, 3)
    for lv, name, key, icon in [(5, 'Summon Aegis', 'Aegis', 9405), (15, 'Summon Soultorn', 'Soultorn', 9404), (25, 'Summon Fiend', 'Fiend', 9406),
                                (35, 'Summon Priest', 'Priest', 9403), (45, 'Summon Succubus', 'Succubus', 9407)]:
        k.new(SVB, lv, name, icon, Type='DeathKnightServant', Target='Self', Range=0, CastTime=6.0, Power=-40, Damage=-100, Value=50, Duration=65535,
              LifeDrainReturn=DK_PET_TEMPLATES[key], DamageType=0, _params=nochthonic)
    # Live names and heals; live lists 2/4/10 power for the first three ranks and none for the rest, so the
    # higher ranks continue that progression.
    for lv, name, value, pw, icon in [(1, 'Regenerate Flesh', 2, 2, 9411), (8, 'Regenerate Blood', 4, 4, 9412), (18, 'Regenerate Muscle', 16, 10, 9414),
                                      (28, 'Regenerate Body', 39, 14, 9414), (38, 'Dead Flesh Living', 51, 18, 9416), (48, 'Imbue the Abyss', 61, 22, 9416)]:
        k.new(SVB, lv, name, icon, Type='DeathKnightRegenerate', Target='Self', Range=2000, Value=value, Duration=15, Frequency=30,
              RecastDelay=30, CastTime=0, Power=pw, DamageType=0)
    # Power drains: 150% of the damage returns as power (1.127 delve fix, 1.130A).
    for lv, name, dmg in [(7, 'Power Drain', 6), (17, 'Power Vacuum', 16), (27, 'Power Leech', 26), (37, 'Power Siphon', 36), (47, 'Power Absorb', 56)]:
        k.new(SVB, lv, name, 9112, Type='PowerDrain', Damage=dmg, LifeDrainReturn=150, RecastDelay=20, CastTime=0, Power=0, DamageType=SPIRIT)
    # Power restore storms: 200 radius, 16 allies, every 6 s (1.130A: Mystic Ground 70 power).
    for lv, name, value, pw in [(4, 'Enchanted Ground', 5, 20), (14, 'Infused Ground', 11, 44), (24, 'Majestic Ground', 20, 65),
                                (34, 'Spellbound Ground', 28, 65), (44, 'Mystic Ground', 35, 70)]:
        ground(SVB, lv, name, 15232, 3, pw, 200, 2000, 30, 6000, value=value)
    k.new(SVB, 26, 'Wake Servant', 9125, Type='CureMezz', Target='Pet', Range=1000, CastTime=2.0, Power=-6, DamageType=0)

    # ---- Death Servant specialization ----
    for lv, name, value, icon in [(1, 'Gift of Power', 25, 9125), (11, 'Gift of Essence', 40, 9126), (21, 'Gift of Force', 70, 9127),
                                  (31, 'Gift of Vim', 105, 9122), (41, 'Gift of Arawn', 150, 9127)]:
        k.new(SVS, lv, name, icon, Type='PowerTransfer', Target='Realm', Value=value, CastTime=3.0, DamageType=0)
    # Exhaustion snares: moved here in 1.123 (no form needed), 1.125 reuse at 4/14, ignore immunity (1.122C).
    for rank, (lv, name, value, reuse) in enumerate([(3, 'Crippling Exhaustion', 10, 600), (13, 'Constricting Exhaustion', 15, 450),
                                                     (23, 'Disabling Exhaustion', 20, 120), (33, 'Debilitating Exhaustion', 25, 60), (43, 'Snaring Exhaustion', 30, 60)]):
        k.new(SVS, lv, name, 15233 + rank, Type='DeathKnightSnare', Value=value, Duration=10 + 5 * rank, RecastDelay=reuse, CastTime=0, Power=-25,
              Range=1000, DamageType=SPIRIT)
    # Pet fear: 1.123B durations, 1.124B 5 s cast and 60 s immunity.
    for i, (lv, name, dur, pw) in enumerate([(2, 'Fear Servant', 5, 6), (12, 'Expel Servant', 9, 15), (22, 'Intimidate Servant', 15, 26),
                                             (32, 'Daunt Servant', 22, 35), (42, 'Terrify Servant', 30, 35)]):
        k.new(SVS, lv, name, 15197 + i, Type='WarlockPetFear', Duration=dur, CastTime=5.0, Power=pw, DamageType=0)
    for lv, name, dmg, pw in [(4, 'Power Blast', 23, 16), (14, 'Focus Blast', 51, 30), (24, 'Essence Blast', 156, 44),
                              (34, 'Death Blast', 251, 70), (44, 'Final Blast', 317, 99)]:
        k.new(SVS, lv, name, 9162, Type='Bolt', Range=2000, Damage=dmg, CastTime=2.0, RecastDelay=15, Power=pw, DamageType=SPIRIT,
              _params=nochthonic)
    # Realm ABS buff: 1.124D 10 minutes.
    for lv, name, value in [(8, 'Ambition for Death', 1), (18, 'Hunger for Death', 2), (28, 'Longing for Death', 5),
                            (38, 'Communion with Death', 7), (48, 'Intimacy with Death', 10)]:
        k.new(SVS, lv, name, 9101, Type='ArmorAbsorptionBuff', Target='Realm', Value=value, Duration=600, CastTime=3.0, Power=-20, DamageType=0)
    # Plague nukes: 1.123 20% snare, 1.124B 25/35% at 39/49, 1.128C damage.
    for lv, name, dmg, snare, dur, pw, icon in [(9, 'Plague Burst', 38, 20, 5, 6, 2021), (19, 'Plague Trap', 76, 20, 10, 14, 2021),
                                                (29, 'Plague Torrent', 135, 20, 20, 30, 2024), (39, 'Plague Barrage', 164, 25, 20, 46, 2024),
                                                (49, 'Plague Surge', 199, 35, 20, 66, 2106)]:
        k.new(SVS, lv, name, icon, Type='DamageSpeedDecrease', Damage=dmg, Value=snare, Duration=dur, CastTime=2.8, Power=pw, DamageType=MATTER)
    k.new(SVS, 26, 'Spirit Bladeturn', 13520, Type='Bladeturn', Target='Self', Range=0, Duration=1200, CastTime=5.0, Power=-15, DamageType=0)  # 1.128C
    k.new(SVS, 25, 'Power Vortex', 15243, Type='PowerDrain', Range=0, Radius=350, Damage=100, LifeDrainReturn=100, RecastDelay=30,
          CastTime=0, DamageType=SPIRIT)
    k.new(SVS, 35, 'Power Shield', 9122, Type='DeathKnightPowerShield', Target='Self', Range=0, CastTime=0, DamageType=0)
    # Power Lock: 10 s grapple, the target stunned (1.125D) and drained of 15% power a second (1.124D), 90 s reuse.
    locked = k.new(None, 45, 'Power Locked', 9112, Type='Stun', Range=350, Duration=10, CastTime=0, DamageType=ENERGY)
    k.new(SVS, 45, 'Power Lock', 9112, Type='DeathKnightPowerLock', Range=350, Duration=10, Value=15, RecastDelay=90, CastTime=0,
          DamageType=ENERGY, SubSpellID=locked)
    # Arawn's Legion: 1.124 8 s hard cast (10 s with the base), 1.124D 8 targets, 30 s, 10 minute reuse.
    k.new(SVS, 50, "Arawn's Legion", 9407, Type='DeathKnightLegion', Target='Self', Range=0, Radius=2000, Duration=30, CastTime=10.0,
          RecastDelay=600, Damage=-90, Value=50, LifeDrainReturn=DK_LEGION_TEMPLATE, DamageType=0, _params=nochthonic)

    # ---- Servant spells (NPC templates): live level-50 values, scaled to the servant's level by the server ----
    pet = dict(Range=1500, DamageType=0)
    rabid_crack = k.new(None, 50, 'Armor Crack', 9002, Type='ArmorFactorDebuff', Value=10, Duration=10, CastTime=0, **pet)
    arawn_cure = k.new(None, 50, "Arawn's Cleansing", 9411, Type='CureAll', Target='Realm', CastTime=0, **pet)
    k.pet_spells = dict(
        Aegis=[k.new(None, 50, 'Aegis Shell', 9101, Type='SpecArmorFactorBuff', Target='Self', Range=0, Value=500, Duration=600, CastTime=0,
                     DamageType=0)],
        Soultorn=[k.new(None, 50, 'Demonic Collapse', 2021, Type='DamageSpeedDecrease', Damage=150, Value=15, Duration=15, CastTime=3.5,
                        Range=1500, DamageType=MATTER),
                  k.new(None, 50, "Soultorn's Death", 9321, Type='DamageOverTime', Damage=15, Duration=20, Frequency=50, CastTime=2.1,
                        Range=1500, DamageType=MATTER)],
        Fiend=[k.new(None, 50, 'Fiend Swings', 13035, Type='CombatSpeedBuff', Target='Self', Range=0, Value=25, Duration=600, CastTime=0,
                     DamageType=0)],
        Priest=[k.new(None, 50, "Arawn's Heal", 9411, Type='Heal', Target='Realm', Value=215, CastTime=2.8, Range=2000, DamageType=0,
                      SubSpellID=arawn_cure)],
        Succubus=[k.new(None, 50, 'Demonic Entrancement', 13145, Type='Mesmerize', Range=1500, Duration=20, CastTime=6.0, DamageType=ENERGY)])
    # Spirit Form abilities, added while the master is in Spirit Form (DeathKnight.SpiritTemplate).
    k.spirit_spells = dict(
        Aegis=[k.new(None, 50, 'Spirit Aegis Burst', 241, Type='DirectDamage', Damage=59, Radius=200, CastTime=3.0, Range=1350, DamageType=HEAT),
               k.new(None, 50, 'Spirit Shell', 3904, Type='AllMagicResistsBuff', Target='Self', Range=0, Value=10, Duration=600, CastTime=0,
                     DamageType=0)],
        Soultorn=[k.new(None, 50, "Soultorn's Greater Plague", 9313, Type='Disease', Value=35, Duration=30, CastTime=3.5, Range=1500,
                        DamageType=MATTER)],
        Fiend=[k.new(None, 50, 'Rabid Sickness', 9002, Type='ArmorAbsorptionDebuff', Value=10, Duration=60, CastTime=0, SubSpellID=rabid_crack,
                     **pet)],
        Priest=[],
        Succubus=[k.new(None, 50, 'Demonic Entrancement', 13145, Type='Mesmerize', Range=1500, Radius=200, Duration=20, CastTime=6.0,
                        DamageType=ENERGY)])

    # ---- Painworking styles: EoD Friar staff rows for the client art; names, chains, openings, endurance, to-hit and
    # defense bonuses and procs from the live style data ----
    P = 'Painworking'
    k.style_defaults = dict(WeaponTypeRequirement=1001)  # Style.SpecialWeaponType.AnyWeapon
    villain = k.proc('Villainous Strike Effect', 'ArmorFactorDebuff', value=3, duration=30, effect=2140)
    k.style(P, 1, 230, 495, Name='Villainous Strike', EnduranceCost=5, BonusToHit=5, BonusToDefense=0, procs=[(villain, 100)])
    chill = k.new(None, 3, 'Chilling Touch Effect', 13070, Type='EvadeBuff', Target='Self', Range=0, Value=5, Duration=10, CastTime=0, DamageType=0)
    k.style(P, 3, 234, 494, Name='Chilling Touch', follows='Villainous Strike', EnduranceCost=15, BonusToHit=0, BonusToDefense=-10,
            procs=[(chill, 100)])
    k.style(P, 13, 235, 492, Name='Shadow Beckon', EnduranceCost=5, BonusToHit=0, BonusToDefense=5,
            procs=[(k.proc('Shadow Beckon Effect', 'StyleTaunt', value=20, effect=7353, damage_type=0), 100)])
    k.style(P, 16, 240, 489, Name='Arctic Death', OpeningRequirementType=1, OpeningRequirementValue=0, AttackResultRequirement=3,
            EnduranceCost=10, BonusToHit=10, BonusToDefense=5,
            procs=[(k.proc('Arctic Death Effect', 'StyleCombatSpeedDebuff', value=26, duration=20, effect=2140), 100)])  # 1.123: 26%
    icebringer = k.new(None, 23, 'Icebringer Disease', 9313, Type='Disease', Value=15, Duration=20, CastTime=0, Range=500, DamageType=COLD)
    k.style(P, 23, 237, 490, Name='Icebringer', OpeningRequirementType=2, OpeningRequirementValue=1, AttackResultRequirement=0,
            EnduranceCost=10, BonusToHit=10, BonusToDefense=0, procs=[(icebringer, 100)])
    strip = k.proc('Ablative Remover', 'DeathKnightAblativeStrip', effect=2140, damage_type=0)
    k.style(P, 26, 239, 482, Name='Vanquisher', follows='Arctic Death', EnduranceCost=5, BonusToHit=15, BonusToDefense=0,
            procs=[(strip, 100)])
    cleave = k.proc('Icy Cleave Effect', 'DirectDamage', damage=55, effect=241, damage_type=COLD, Radius=125)
    k.style(P, 33, 233, 484, Name='Icy Cleave', OpeningRequirementType=2, OpeningRequirementValue=2, AttackResultRequirement=0,
            EnduranceCost=25, BonusToHit=0, BonusToDefense=10, procs=[(cleave, 100)])
    edge = k.proc('Frozen Edge Effect', 'ColdResistDebuff', value=25, duration=12, effect=241)  # 1.125: 25%; live 12 s
    k.style(P, 36, 241, 493, Name='Frozen Edge', OpeningRequirementType=2, OpeningRequirementValue=0, AttackResultRequirement=0,
            EnduranceCost=10, BonusToHit=10, BonusToDefense=0, procs=[(edge, 100)])
    k.style(P, 43, 242, 491, Name='Frostbite', follows='Icebringer', EnduranceCost=5, BonusToHit=10, BonusToDefense=5,
            procs=[(k.proc('Frostbite Effect', 'StyleStun', duration=7, effect=2132, damage_type=0), 100)])
    # Live: the Deathseeker proc halves the target's healing for 25 s.
    seeker = k.new(None, 46, 'Deathseeker', 9313, Type='Disease', Value=0, Duration=25, CastTime=0, Range=1500, DamageType=COLD)
    k.style(P, 46, 244, 486, Name='Deathseeker', follows='Frozen Edge', EnduranceCost=15, BonusToHit=15, BonusToDefense=0,
            procs=[(seeker, 100)])
    for _, _, row in k.rows:
        if row['Name'] in DK_ICONS:
            row['Icon'] = row['ClientEffect'] = DK_ICONS[row['Name']]
        if row['Name'] in DK_REGEN_ICONS:
            row['Icon'], row['ClientEffect'] = DK_REGEN_ICONS[row['Name']]
    return k


def death_knight_world(c, info, kit):
    """Spell lines, specialisations, servants, conjured weapons, trainers and realm abilities for the Death Knight."""
    package = info['package']
    lines = info['lines']
    specs = ('Deathsight', 'Deathsight', 'Painworking', 'Painworking', 'Death Servant', 'Death Servant')
    c.execute('delete from SpellLine where ClassIDHint=66')
    for key, spec, baseline in zip(lines, specs, (1, 0, 1, 0, 1, 0)):
        name = spec + ('' if baseline else ' Mastery')
        _insert(c, 'SpellLine', dict(KeyName=key, Name=name, Spec=spec, IsBaseLine=baseline, ClassIDHint=66))
    c.execute('delete from ClassXSpecialization where ClassID=66')
    for spec, acquired in [('AlbClothCasterCareer', -100), ('DeathKnightCareer', -100), ('Deathsight', -3), ('Painworking', -2), ('Death Servant', -2)]:
        _insert(c, 'ClassXSpecialization', dict(ClassID=66, SpecKeyName=spec, LevelAcquired=acquired))
    if not c.execute("select 1 from Specialization where KeyName='DeathKnightCareer'").fetchone():
        _insert(c, 'Specialization', dict(KeyName='DeathKnightCareer', Name='Death Knight Career', Icon=0, Description='',
                                          Implementation='DOL.GS.LiveCareerSpecialization'))

    # Servants level with the caster. Models matched against live screenshots (names as live shows them): DR Fiery
    # Scorpion (the DR mesh pairs with the spirit aegis), Wraith (DR wraith model), the green Hulker and the Succubus; the priest of Arawn has no matching
    # model here and the Inquisitor stands in. Each has a Spirit Form template (DK_SPIRIT_OFFSET) with its spirit
    # look and the abilities it gains; Arawn's legion uses the Legion demon.
    c.execute('delete from NpcTemplate where PackageID=?', (package,))
    pets = dict(Aegis=('umbral aegis', '2150', 175, 10, 0, 30, 'Intercept|1'), Soultorn=('soultorn', '655', 200, 0, 5, 0, ''),
                Fiend=('plated fiend', '657', 230, 10, 10, 0, ''), Priest=('priest of Arawn', '2119', 200, 0, 5, 0, ''),
                Succubus=('succubus', '644', 200, 0, 10, 0, ''))
    spirits = dict(Aegis=('spirit aegis', '1257'), Soultorn=('phantom', '1745'), Fiend=('umbral hulk', '662'),
                   Priest=('image of Arawn', '645'), Succubus=('arch demon', '605'))

    def template(tid, key, name, model, spells, speed=200, parry=0, evade=0, block=0, abilities='', size='50'):
        if c.execute('select 1 from NpcTemplate where TemplateId=? and coalesce(PackageID,"")<>?', (tid, package)).fetchone():
            raise ValueError(f'NPC template {tid} collision')
        _insert(c, 'NpcTemplate', dict(TemplateId=tid, Name=name, ClassType='', Model=model, Size=size, Level='0', MaxSpeed=speed,
                                       Flags=0, MeleeDamageType=2, ParryChance=parry, EvadeChance=evade, BlockChance=block,
                                       Spells=';'.join(str(s) for s in spells), Styles='', Abilities=abilities,
                                       Race=2009, BodyType=11, PackageID=package, NpcTemplate_ID=f'{package}-pet-{key}'))

    for key, (name, model, speed, parry, evade, block, abilities) in pets.items():
        template(DK_PET_TEMPLATES[key], key, name, model, kit.pet_spells[key], speed, parry, evade, block, abilities)
        spirit_name, spirit_model = spirits[key]
        template(DK_PET_TEMPLATES[key] + DK_SPIRIT_OFFSET, f'{key}-spirit', spirit_name, spirit_model, kit.spirit_spells[key])
    template(DK_LEGION_TEMPLATE, 'Legion', "legionnaire of Arawn", '634', [], speed=220, size='30')

    # Conjured weapons: Icebrand per five levels (the translucent blue Midgard spirit great sword, as on live) and
    # Nethersbane; two-handed swords that deal cold damage in combat.
    c.execute('delete from ItemTemplate where PackageID=?', (package,))
    base = dict(c.execute("select * from ItemTemplate where Id_nb='Alcorn`s Staff'").fetchone())
    def bonuses(item, pairs):
        for i in range(1, 11):
            item[f'Bonus{i}'] = 0; item[f'Bonus{i}Type'] = 0
        for i, (prop, value) in enumerate(pairs, 1):
            item[f'Bonus{i}Type'] = prop; item[f'Bonus{i}'] = value

    for band in range(0, 55, 5):
        level = max(1, band)
        item = dict(base, Id_nb=f'deathknight_icebrand_{band}', Name='Icebrand', Level=level, Model=4842, Effect=27, DPS_AF=int(12 + 3 * level),
                    SPD_ABS=45, Hand=1, Type_Damage=2, Object_Type=6, Item_Type=12, Realm=1, AllowedClasses='66', Bonus=0,
                    IsPickable=0, IsDropable=0, CanDropAsLoot=0, IsTradable=0, Price=0, PackageID=package,
                    Description='A Chthonic blade conjured by a Death Knight. Deals cold damage.', ItemTemplate_ID=f'deathknight_icebrand_{band}')
        bonuses(item, next(b for lv, b in reversed(ICEBRAND_BONUSES) if level >= lv))
        item.update(SpellID=0, SpellID1=0, ProcSpellID=0, ProcSpellID1=0, ProcChance=0, Charges=0, MaxCharges=0)
        _insert(c, 'ItemTemplate', item)
    nether = dict(item, Id_nb='deathknight_nethersbane', Name='Nethersbane', Level=50, Model=4410, Effect=473, DPS_AF=165, SPD_ABS=50,
                  ProcSpellID=kit.nether_procs[0], ProcSpellID1=kit.nether_procs[1], ProcChance=10,
                  Description="Arawn's evil blade. Removed when its wielder logs out.", ItemTemplate_ID='deathknight_nethersbane')
    bonuses(nether, NETHERSBANE_BONUSES)
    _insert(c, 'ItemTemplate', nether)

    # Starting equipment: the Necromancer's cloth outfit and weapon.
    c.execute("delete from StarterEquipment where Class='66;'")
    for row in c.execute('select Class, TemplateID from StarterEquipment').fetchall():
        classes = [x for x in str(row[0]).split(';') if x]
        if '12' in classes:
            _insert(c, 'StarterEquipment', dict(Class='66;', TemplateID=row[1]))

    # Trainers beside every Necromancer trainer.
    c.execute('delete from Mob where PackageID=?', (package,))
    trainers = c.execute("select * from Mob where ClassType='DOL.GS.Trainer.NecromancerTrainer' order by Mob_ID").fetchall()
    for i, row in enumerate(trainers):
        mob = dict(row)
        mob.update(Mob_ID=f'{package}-trainer-{i + 1}', Name=DK_TRAINER_NAMES[i % len(DK_TRAINER_NAMES)], Guild='Death Knight Trainer',
                   ClassType='DOL.GS.Trainer.DeathKnightTrainer', X=row['X'] + 64, Y=row['Y'] + 64, PackageID=package)
        _insert(c, 'Mob', mob)

    # Realm abilities: the 1.122B Necromancer list less Mastery of Parry (1.124D), plus the Death Knight RR5.
    if not c.execute('select 1 from Ability where KeyName=?', (DK_RR5['KeyName'],)).fetchone():
        icon = c.execute("select IconID from Ability where KeyName='Call of Darkness'").fetchone()
        _insert(c, 'Ability', dict(DK_RR5, IconID=icon[0] if icon else 0))
    c.execute('delete from ClassXRealmAbility_Atlas where CharClass=66')
    for key in DK_RAS + (DK_RR5['KeyName'],):
        if not c.execute('select 1 from Ability where KeyName=?', (key,)).fetchone():
            raise ValueError(f'Missing realm ability {key}')
        _insert(c, 'ClassXRealmAbility_Atlas', dict(CharClass=66, AbilityKey=key, ClassXRealmAbility_Atlas_ID=f'{package}-ra-{key}'))
    return dict(trainers=len(trainers), servants=len(pets))


BUILDERS = {39: bainshee, 58: vampiir, 33: heretic, 66: death_knight}
EXTRAS = {66: death_knight_world}


def spread_levels(rows):
    """Give a spell that shares its line and level with an earlier one the nearest level no spell in the line uses.

    The client addresses a list spell by line index and level (UseSpellHandler.GetSkill takes the first match), so a
    second spell at the same level is unreachable. Every other spell keeps its live level.
    """
    original = {}
    for line, level, _ in rows:
        if line:
            original.setdefault(line, set()).add(level)
    seen, moved = {}, []
    for index, (line, level, row) in enumerate(rows):
        if not line:
            continue
        used = seen.setdefault(line, set())
        if level in used:
            blocked = original[line] | used
            free = min((lv for lv in range(1, 51) if lv not in blocked), key=lambda lv: (abs(lv - level), lv < level))
            moved.append((row['Name'], line, level, free))
            rows[index] = (line, free, row)
            level = free
        used.add(level)
    return moved


HYBRID = {33}  # Heretic specs use LiveSpellHybridSpecialization: cast by skill slot, not by line and level


def build(cls):
    kit = BUILDERS[cls]()
    kit.moved_levels = [] if cls in HYBRID else spread_levels(kit.rows)
    return kit


def definitions(classes=(39,)):
    return [(cls, line, level, row) for cls in classes for line, level, row in build(cls).rows]


def validate_icons(root, rows):
    sys.path.insert(0, str(HERE.parent / 'new-client/pipeline'))
    from daoc_mpk import MpakArchive
    archive = MpakArchive(root / 'runtime/client-modern/app/gamedata.mpk')
    catalog = {int(r[0]): r for r in csv.reader(io.StringIO(archive.read('spells.csv').decode('latin1'))) if r and r[0].isdigit()}
    icons = {int(r[0]) for r in csv.reader(io.StringIO(archive.read('icons.csv').decode('latin1'))) if r and r[0].isdigit()}
    for _, line, _, row in rows:
        if row['Icon'] == 0 and line is None:
            continue  # style procs carry no icon, like the stock ones
        if row['Icon'] not in catalog or int(catalog[row['Icon']][2]) not in icons:
            raise ValueError(f"Missing client artwork {row['Icon']} for {row['Name']}")
    return len({r['Icon'] for _, _, _, r in rows})


def _insert(c, table, row):
    c.execute(f'insert into "{table}" (' + ','.join(f'"{k}"' for k in row) + ') values (' + ','.join('?' for _ in row) + ')',
              list(row.values()))


def _set_property(c, key, value, description):
    if c.execute('select 1 from ServerProperty where lower(Key)=?', (key,)).fetchone():
        c.execute('update ServerProperty set Value=? where lower(Key)=?', (value, key))
    else:
        _insert(c, 'ServerProperty', dict(Category='classes', Key=key, Description=description, DefaultValue='False',
                                          Value=value, ServerProperty_ID='local-' + key))


def apply(c, classes=(39,)):
    c.row_factory = sqlite3.Row
    columns = {r[1] for r in c.execute('pragma table_info(Spell)')}
    summary = {}
    for cls in classes:
        info = KITS[cls]
        lo, hi = info['spells'], info['spells'] + SPAN - 1
        tlo, thi = info['tooltips'], info['tooltips'] + SPAN - 1
        if c.execute("select 1 from Spell where (SpellID between ? and ? or TooltipId between ? and ?) and coalesce(PackageID,'')<>?",
                     (lo, hi, tlo, thi, info['package'])).fetchone():
            raise ValueError(f"{info['name']} spell/tooltip ID collision")
        for line in info['lines']:
            if c.execute('select 1 from LineXSpell where LineName=? and SpellID not between ? and ?', (line, lo, hi)).fetchone():
                raise ValueError(f"{line} holds unknown spells; review before replacing")
        c.execute('delete from LineXSpell where SpellID between ? and ?', (lo, hi))
        c.execute('delete from SpellXCustomValues where SpellID between ? and ?', (lo, hi))
        c.execute('delete from Spell where PackageID=?', (info['package'],))
        kit = build(cls)
        rows = kit.rows
        for line, level, row in rows:
            _insert(c, 'Spell', {k: v for k, v in row.items() if k in columns})
            for key, value in row.get('_params', {}).items():
                _insert(c, 'SpellXCustomValues', dict(SpellID=row['SpellID'], KeyName=key, Value=str(value)))
            if line:
                _insert(c, 'LineXSpell', dict(LineName=line, SpellID=row['SpellID'], Level=level, LineXSpell_ID=row['Spell_ID']))
        if 'styles' in info:
            slo, shi = info['styles'], info['styles'] + STYLE_SPAN - 1
            if c.execute('select 1 from Style where StyleID between ? and ? and ClassId<>?', (slo, shi, cls)).fetchone():
                raise ValueError(f"{info['name']} style ID collision")
            if c.execute('select 1 from Style where ClassId=? and StyleID not between ? and ?', (cls, slo, shi)).fetchone():
                raise ValueError(f"{info['name']} has unknown styles; review before replacing")
            c.execute('delete from StyleXSpell where StyleID between ? and ?', (slo, shi))
            c.execute('delete from Style where StyleID between ? and ?', (slo, shi))
            style_columns = {r[1] for r in c.execute('pragma table_info(Style)')}
            for row, procs in kit.styles:
                _insert(c, 'Style', {k: v for k, v in row.items() if k in style_columns})
                for spell, chance in procs:
                    _insert(c, 'StyleXSpell', dict(SpellID=spell, ClassID=cls, StyleID=row['StyleID'], Chance=chance,
                                                   StyleXSpell_ID=f"{info['package']}-style-{row['StyleID']}-{spell}"))
        if info.get('career'):
            for key, internal, implementation, description in NEW_ABILITIES if cls == 58 else ():
                if not c.execute('select 1 from Ability where KeyName=?', (key,)).fetchone():
                    _insert(c, 'Ability', dict(KeyName=key, Name=key, InternalID=internal, Description=description, IconID=0,
                                               Implementation=implementation))
            for key in {a for _, a, _ in CAREER[info['career']]}:
                if not c.execute('select 1 from Ability where KeyName=?', (key,)).fetchone():
                    raise ValueError(f'Missing ability {key}')
            c.execute('delete from SpecXAbility where Spec=?', (info['career'],))
            for level, key, ability_level in CAREER[info['career']]:
                _insert(c, 'SpecXAbility', dict(Spec=info['career'], SpecLevel=level, AbilityKey=key, AbilityLevel=ability_level, ClassId=0))
        # A class without a menu-region-zero start saves new characters at region 0 and cannot log in.
        if not c.execute('select 1 from StartupLocation where ClassID=? and RealmID=? and RaceID=0 and ClientRegionID=0 and Region>0',
                         (cls, info['realm'])).fetchone():
            source = c.execute('select * from StartupLocation where RealmID=? and Region in (1,100,200) and XPos>0 and YPos>0 '
                               'order by ClientRegionID=0 desc, RaceID=0 desc, MinVersion desc limit 1', (info['realm'],)).fetchone()
            if source is None:
                raise ValueError('Missing realm start ' + str(info['realm']))
            start = dict(source)
            start.pop('StartupLoc_ID')
            start.update(ClassID=cls, RaceID=0, ClientRegionID=0, MinVersion=1130)
            _insert(c, 'StartupLocation', start)
        for key in REMOVED_RAS.get(cls, ()):
            c.execute('delete from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?', (cls, key))
        for key, _ in LIVE_RAS.get(cls, ()):
            if not c.execute('select 1 from Ability where KeyName=?', (key,)).fetchone():
                raise ValueError(f'Missing realm ability {key}')
            if not c.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?', (cls, key)).fetchone():
                _insert(c, 'ClassXRealmAbility_Atlas', dict(CharClass=cls, AbilityKey=key,
                                                            ClassXRealmAbility_Atlas_ID=f"{info['package']}-ra-{key}"))
        extra = EXTRAS[cls](c, info, kit) if cls in EXTRAS else {}
        disabled = c.execute("select Value from ServerProperty where lower(Key)='disabled_classes'").fetchone()[0]
        ids = set()
        for token in disabled.split(';'):
            if token.strip():
                bounds = list(map(int, token.split('-')))
                ids.update(range(bounds[0], bounds[-1] + 1))
        ids.discard(cls)
        c.execute("update ServerProperty set Value=? where lower(Key)='disabled_classes'", (';'.join(map(str, sorted(ids))),))
        _set_property(c, info['property'], 'True', f"Modern-live {info['name']} test kit")
        summary[info['name']] = dict(spells=len(rows), learnable=sum(1 for line, _, _ in rows if line), styles=len(kit.styles), **extra)
    return summary
