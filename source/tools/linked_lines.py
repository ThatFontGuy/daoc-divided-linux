"""Live (1.130a) spells built from a parent and its child spells (Class-Research/claude/followup-2026-10-25).

From daoc.gg's client spell data (the 1.123b extraction with its child effects) and the dated patches through 1.130a,
checked against the official notes:
  - Bonedancer totems (TimedPulseArea): placed at the target's spot (damage and snare totems) or at the caster's
    feet (Sable, Protection). One totem per caster; the damage and snare totems share a 30 s reuse.
      Darkness:    Dusk/Gloom/Murk/Shadow/Obsidian Totem: 35*/66.4/109.5/162.5/252.5 Cold every 3 s for 30 s, 300 radius,
                   16 enemies, 1,500 range, 2 s cast (1.123), 10% power. *Dusk: the official 1.122B 35; the client says 10.
                   Sable Totem: 15 s, every 0.3 s (1.130a), 200 radius, 6 allies' spells can't be interrupted, 10 min reuse.
      Suppression: Slowing/Crawling/Bone/Hindering/Grasping Totem: a 3 s snare of 10/20/40/55/75% every 3 s (1.130a)
                   for 30 s, 250 radius, 8 enemies, 1,000 range, 2 s cast; ignores root immunity and grants none.
                   Protection Totem: 15 s, every 3 s (1.130a), 300 radius, 8 allies get a 350 melee barrier, 5 min reuse.
    They go in new class-hinted lines beside Bone Mystics and Bone Guardians: list lines cast by line and level.
  - Thane Swirling Thunder (Stormcalling 42): 26.9 Energy every 2.5 s for 15 s around the Thane, 350 radius, 8 enemies;
    instant, 60 s reuse (1.123), 20% power.
  - Champion Call of the Champion (Valor 50): instant, 30 s, 10 min reuse, 60% power. Nearby allies' (600) melee becomes
    Energy for 30 s (Champion's Call); every Champion melee hit adds 20.5 Energy damage and a 30% Energy resist debuff
    for 20 s (Victorious Energy, Mark of the Champion).
  - Cleric Helping Hand line (Smite 3-43): on an enemy for 20 s, each of its melee hits heals its victim 5/10/25/60/100;
    2.8 s cast, 1,000 range, power 18/30/40/52/66 (the client's).
  - Champion Stoutness/Girth/Resilience/Vigor/Vitality of Valor and Thane Minor Health/Health/Major Health/
    Empowerment/Bulwark of Thor (1.128c, levels 5-45): group chants of +1/2/3/4/6% max health and armor factor. No source
    gives their timings; the owner's call is that they are chants, so they use the Paladin chants': instant, a pulse
    every 6 s, 1,500 range, no power. The ranks of a chant share one group, so only the best shows.
  - Bonedancer commander commands (CommanderCommand: the commander casts the child on the target at once):
      Familiar Dart/Jolt/Blast/Burst/Defeat (Bone Army 8-48): 3.0/16.9/41.7/61.5/85.3 Cold (live 30-860 at the DD
      scale), 1,250 range from the commander, 15 s reuse.
      Ghostly/Undead/Skeletal/Hallowed/Deathly Wail (Bone Army 3-43): the commander taunts (6.3-55.6), 2,300 range.
      Punish Combatant/Assailant/Aggressor/Opponent/Soldier (Suppression 1-41): the commander disarms for 3/6/8/12/15 s;
      5/5/3/1/1 min reuse.
    The orders reach 2,300 from the Bonedancer; their lines are new list lines beside Bone Warriors and Bone Guardians.
    1.122B's notes: the Familiar spells are Body damage and cost 20% power; the Punish spells cost 20% power.
Second gap pass (owner: "work on all of the still missing"), from the client data and the 1.122B notes:
  - Bonedancer summons, on the local pet templates (the live pets' own spell kits aren't modelled):
      Summon Commander (Bone Army base 1): one scaling commander, up to level 50 at 100% of the caster's level.
      Summon Bone Spellbinder/Mender/Elite/Hexer (Bone Army 11/15/25/31): the caster, healer, melee and debuffer minions,
      up to level 45 at 75%.
      Summon Dread Guardian (Suppression 40), Dread Lich (Darkness 45), Dread Lord (Bone Army 50, level 52): commanders.
  - Bone Phantoms/Ghasts/Spirits/Haunts/Revenants (Darkness 6-46): phantoms sent to the target's spot seek enemies within
    1,500 and strike for 12/25/90/175/300 Cold every 15/15/10/10/5 s for 25 s; 1/1/1/2/3 at a time; 2 s cast, 1,250 range.
  - Harden/Toughen/Strengthen/Augment/Bolster Bone Army (Suppression 5-45): group +1/2/3/6/9% absorb, 10 minutes, 10 s
    cast, 15% power.
  - Assist/Improve Bonecaster (Darkness 2/12): instant 5/10% Body resist debuff, 15 s, 5 s reuse, 10% power.
  - Hunter: Call the Hounds (Beastcraft 30): a 60 s hound fighting beside the pet, 15 min reuse. Wolfen Frenzy (2): the
    pet's attack speed +50% and damage +25% for 30 s (the -25% absorb part isn't built), 60 s reuse. Gleipnir's Wish/
    Will/Command (20/35/50): the pet's hits hinder (30% snare) for 2/4/6 s, 60 s, 90 s reuse. The stock Hunter's Elder
    Protector (40) and Elder Avatar (50) join Beastcraft as 5-minute pets with a 90 s reuse; the Avatar at the
    caster's level (1.122B).
  - Shaman: Spirit Shell (Augmentation 41): all damage taken -50% for 10 s, 60 s reuse. Caustic Carapace (36): 250% of
    melee damage taken is returned for 15 s. Minor..Superior Earth Vivification (2-42): an endurance-regen chant, 3-7.
    Tribal/Shaman Unity (30/40): group 18/24% Heat/Cold/Matter resists for 30 s (resist set 93, client formatter).
    Escape Hold (Cave 16): frees another realm member from roots and snares, 10 s cast, 5 min reuse. Weary/Fizzle/
    Suppress/Suspend/Halt Magic (Cave 3-43): spell damage -5/10/25/50/75% for 30 s, 45 s reuse. Bane of Magic/Arcane/
    Power/Augury/Prophecy (Cave 9-49): power costs +10/25/50/75/99.9% for 25-30 s, 30 s reuse.
  - Minstrel: Song of Magic/Arcane/Wizardic/Supreme/Sorcerous Reach (8-48): group spell range +2/4/6/8/10% for 30 s.
    Song of Spell Protection/Warding/Shielding/Degradation/Invulnerability (9-49): group 3/7/10/15/20% secondary
    magic resists for 15 s (resist set 95; 1.123's notes: magic damage reduction, not primary resists).
  Not built: Dread Charge, Frigg's Grace, Blight Surge, the Fervor songs, the Harmony charms and Siegebreaker (the data
  doesn't say what they change).
"""
import sqlite3
import sys
import hybrid_lines

PACKAGE = 'local-linked-live-v1'
FIRST, LAST = 77200, 77399
TOOLTIP_BASE = 20700  # 20700-20899 are unused; 23200-23999 is the Death Knight's reserved block
RESERVED_TOOLTIPS = (23200, 23999)
TOTEM_TIMER = 77390  # the damage and snare totems share one reuse

# New list lines: (key, spec, class hint, base line).
LINES = [('Bone Mystics (Totems)', 'Darkness', 30, 0), ('Bone Guardians (Totems)', 'Suppression', 30, 0),
         # The Bone Army lines carry no class hint (a hinted line would hide them), the Suppression ones do.
         ('Bone Warriors (Commands)', 'Bone Army', 0, 0), ('Bone Guardians (Commands)', 'Suppression', 30, 0),
         ('Bone Army (Summons)', 'Bone Army', 0, 0), ('Bone Army (Commanders)', 'Bone Army', 0, 1)]

# Stock spells live put in a line: (line, SpellID, level, field updates).
STOCK_LINKS = [('Beastcraft', 3591, 40, dict(Duration=300, RecastDelay=90)),
               ('Beastcraft', 3592, 50, dict(Duration=300, RecastDelay=90, Damage=-100))]

ENERGY, COLD, BODY, SPIRIT = 12, 11, 10, 15
MELEE, HEALER, CASTER, DEBUFFER = 0, 1, 2, 3  # BdSubPet.SubPetType


def single(level, name, art, family=None, **fields):
    return dict(level=level, name=name, art=art, family=family, children=[], parent=fields)


def summon(level, name, art, kind, template, cap, percent, sub_type=0):
    return single(level, name, art, Type=kind, Target='Self', Power=-20, CastTime=6.0, Duration=65535, Value=cap, Damage=-percent,
                  LifeDrainReturn=template, DamageType=sub_type, Range=0, RecastDelay=0)


def phantom(level, name, damage, every, count):
    return dict(level=level, name=name, art=2501, family='bd-phantoms',
                parent=dict(Type='TimedPulseArea', Target='Enemy', LifeDrainReturn=3, Range=1250, Radius=1500, Duration=25,
                            Frequency=every * 10, Value=count, CastTime=2.0, RecastDelay=0, Power=-10),
                children=[dict(Type='DirectDamage', Target='Enemy', Damage=damage, DamageType=COLD, Range=0)])


def command(level, name, art, child, **parent):
    return dict(level=level, name=name, art=art, children=[child],
                parent=dict(dict(Type='CommanderCommand', Target='Enemy', Range=2300, CastTime=0, RecastDelay=0, Power=0,
                                 SubSpellID='child:0'), **parent))


def chant(level, name, percent, family):
    return dict(level=level, name=name, art=1031, family=family, children=[],
                parent=dict(Type='HealthArmorChant', Target='Group', Value=percent, Pulse=1, Frequency=60, Duration=6, Range=1500,
                            CastTime=0, RecastDelay=0, Power=0, PulsePower=0, Radius=0))


def totem(level, name, art, child, **parent):
    return dict(level=level, name=name, art=art, parent=dict(dict(Type='TimedPulseArea', Duration=30, Frequency=30, CastTime=2.0,
                                                                  RecastDelay=30, SharedTimerGroup=TOTEM_TIMER, LifeDrainReturn=1,
                                                                  Target='Enemy'), **parent), children=[child])


def damage_totem(level, name, damage):
    return totem(level, name, 2706, dict(Type='DirectDamage', Target='Enemy', Damage=damage, DamageType=COLD, Range=0),
                 Range=1500, Radius=300, Value=16, Power=-10)


def snare_totem(level, name, slow, power):
    return totem(level, name, 2706, dict(Type='TotemSnare', Target='Enemy', Value=slow, Duration=3, DamageType=SPIRIT, Range=0),
                 Range=1000, Radius=250, Value=8, Power=power)


# (line, entries). An entry: level, name, art (a stock SpellID), parent fields, and child rows; a child's own
# SubSpellID may name a later child (index into the entry's children, as 'child:n').
ENTRIES = [
    ('Bone Mystics (Totems)', [
        damage_totem(4, 'Dusk Totem', 35.0), damage_totem(14, 'Gloom Totem', 66.4), damage_totem(24, 'Murk Totem', 109.5),
        damage_totem(34, 'Shadow Totem', 162.5), damage_totem(44, 'Obsidian Totem', 252.5),
        dict(level=50, name='Sable Totem', art=10082,
             parent=dict(Type='TimedPulseArea', Target='Self', Duration=15, Frequency=3, Radius=200, Value=6, LifeDrainReturn=2,
                         CastTime=0, RecastDelay=600, Power=-10, Range=0),
             children=[dict(Type='UninterruptibleAura', Target='Realm', Duration=3, Range=0)]),
    ]),
    ('Bone Guardians (Totems)', [
        snare_totem(7, 'Slowing Totem', 10, 20), snare_totem(17, 'Crawling Totem', 20, 30), snare_totem(27, 'Bone Totem', 40, 45),
        snare_totem(37, 'Hindering Totem', 55, 62), snare_totem(47, 'Grasping Totem', 75, 75),
        dict(level=50, name='Protection Totem', art=10082,
             parent=dict(Type='TimedPulseArea', Target='Self', Duration=15, Frequency=30, Radius=300, Value=8, LifeDrainReturn=2,
                         CastTime=0, RecastDelay=300, Power=-10, Range=0),
             children=[dict(Type='AblativeArmor', Target='Realm', Value=350, Damage=100, Duration=3, Range=0)]),
    ]),
    ('Stormcalling', [
        dict(level=42, name='Swirling Thunder', art=3527,
             parent=dict(Type='TimedPulseArea', Target='Self', Duration=15, Frequency=25, Radius=350, Value=8, LifeDrainReturn=0,
                         CastTime=0, RecastDelay=60, Power=-20, Range=0),
             children=[dict(Type='DirectDamage', Target='Enemy', Damage=26.9, DamageType=ENERGY, Range=0)]),
    ]),
    ('Valor', [
        dict(level=50, name='Call of the Champion', art=3528,
             parent=dict(Type='OffensiveProc', Target='Self', Duration=30, Frequency=100, CastTime=0, RecastDelay=600, Power=-60,
                         Range=0, Value='child:0', SubSpellID='child:2'),
             children=[dict(Type='DirectDamage', Name='Victorious Energy', Target='Enemy', Damage=20.5, DamageType=ENERGY, Range=600,
                            SubSpellID='child:1'),
                       dict(Type='EnergyResistDebuff', Name='Mark of the Champion', Target='Enemy', Value=30, Duration=20,
                            DamageType=ENERGY, Range=600),
                       dict(Type='MeleeDamageTypeAura', Name="Champion's Call", Target='Realm', Duration=30, Radius=600, Range=0,
                            DamageType=ENERGY)]),
    ]),
    ('Terrible Hammer', [
        dict(level=lv, name=name, art=1654,
             parent=dict(Type='HelpingHand', Target='Enemy', Value=heal, Duration=20, CastTime=2.8, Range=1000, Power=power,
                         RecastDelay=0, DamageType=SPIRIT),
             children=[])
        for lv, name, heal, power in [(3, 'Helping Hand', 5, 18), (13, 'Healing Hand', 10, 30), (23, 'Light Hand', 25, 40),
                                      (33, 'Pure Hand', 60, 52), (43, 'Holy Hand', 100, 66)]
    ]),
    ('Valor', [chant(lv, name, pct, 'valor-chant') for lv, name, pct in [
        (5, 'Stoutness of Valor', 1), (15, 'Girth of Valor', 2), (25, 'Resilience of Valor', 3), (35, 'Vigor of Valor', 4),
        (45, 'Vitality of Valor', 6)]]),
    ('Bone Warriors (Commands)', [
        *[command(lv, name, 2501, dict(Type='DirectDamage', Target='Enemy', Damage=damage, DamageType=BODY, Range=1250), RecastDelay=15,
                  Power=-20)
          for lv, name, damage in [(8, 'Familiar Dart', 3.0), (18, 'Familiar Jolt', 16.9), (28, 'Familiar Blast', 41.7),
                                   (38, 'Familiar Burst', 61.5), (48, 'Familiar Defeat', 85.3)]],
        *[command(lv, name, 1070, dict(Type='Taunt', Target='Enemy', Value=value, Range=2300))
          for lv, name, value in [(3, 'Ghostly Wail', 6.3), (13, 'Undead Wail', 22.4), (23, 'Skeletal Wail', 36.5),
                                  (37, 'Hallowed Wail', 51.5), (43, 'Deathly Wail', 55.6)]],
    ]),
    ('Bone Guardians (Commands)', [
        command(lv, name, 1070, dict(Type='Disarm', Target='Enemy', Duration=duration, Range=1500), RecastDelay=reuse, Power=-20)
        for lv, name, duration, reuse in [(1, 'Punish Combatant', 3, 300), (11, 'Punish Assailant', 6, 300), (21, 'Punish Aggressor', 8, 180),
                                          (31, 'Punish Opponent', 12, 60), (41, 'Punish Soldier', 15, 60)]
    ]),
    ('Stormcalling', [chant(lv, name, pct, 'thor-chant') for lv, name, pct in [
        (5, 'Minor Health of Thor', 1), (15, 'Health of Thor', 2), (25, 'Major Health of Thor', 3), (35, 'Empowerment of Thor', 4),
        (45, 'Bulwark of Thor', 6)]]),
    # Second gap pass.
    ('Bone Army (Commanders)', [summon(1, 'Summon Commander', 10104, 'SummonCommander', 52, 50, 100)]),
    ('Bone Army (Summons)', [
        summon(11, 'Summon Bone Spellbinder', 10006, 'SummonMinion', 58, 45, 75, CASTER),
        summon(15, 'Summon Bone Mender', 10066, 'SummonMinion', 76, 45, 75, HEALER),
        summon(25, 'Summon Bone Elite', 10166, 'SummonMinion', 88, 45, 75, MELEE),
        summon(31, 'Summon Bone Hexer', 10016, 'SummonMinion', 64, 45, 75, DEBUFFER),
        summon(50, 'Summon Dread Lord', 10104, 'SummonCommander', 52, 52, 104),
    ]),
    ('Bone Guardians (Commands)', [
        summon(40, 'Summon Dread Guardian', 10104, 'SummonCommander', 52, 50, 100),
        *[single(lv, name, 10069, 'bd-army-absorb', Type='ArmorAbsorptionBuff', Target='Group', Value=v, Duration=600, CastTime=10.0,
                 Power=-15, Range=1500, RecastDelay=0)
          for lv, name, v in [(5, 'Harden Bone Army', 1), (15, 'Toughen Bone Army', 2), (25, 'Strengthen Bone Army', 3),
                              (35, 'Augment Bone Army', 6), (45, 'Bolster Bone Army', 9)]],
    ]),
    ('Bone Mystics (Totems)', [
        summon(45, 'Summon Dread Lich', 10104, 'SummonCommander', 52, 50, 100),
        phantom(6, 'Bone Phantoms', 12, 15, 1), phantom(16, 'Bone Ghasts', 25, 15, 1), phantom(26, 'Bone Spirits', 90, 10, 1),
        phantom(36, 'Bone Haunts', 175, 10, 2), phantom(46, 'Bone Revenants', 300, 5, 3),
        *[single(lv, name, 10031, 'bd-bonecaster', Type='BodyResistDebuff', Target='Enemy', Value=v, Duration=15, CastTime=0,
                 RecastDelay=5, Power=-10, Range=1500, DamageType=BODY)
          for lv, name, v in [(2, 'Assist Bonecaster', 5), (12, 'Improve Bonecaster', 10)]],
    ]),
    ('Beastcraft', [
        single(30, 'Call the Hounds', 3590, Type='SummonTheurgistPet', Target='Enemy', Range=1500, CastTime=5.0, RecastDelay=900,
               Duration=60, Value=50, Damage=-80, LifeDrainReturn=40, Power=-25),
        dict(level=2, name='Wolfen Frenzy', art=1021, family='hunter-frenzy',
             parent=dict(Type='CombatSpeedBuff', Target='Pet', Value=50, Duration=30, RecastDelay=60, Range=1500, CastTime=0, Power=0,
                         SubSpellID='child:0'),
             children=[dict(Type='MeleeDamageBuff', Target='Pet', Value=25, Duration=30, Range=1500)]),
        *[dict(level=lv, name=name, art=1560, family='hunter-gleipnir',
               parent=dict(Type='OffensiveProc', Target='Pet', Range=1500, CastTime=0, Power=0, Duration=60, Frequency=100, RecastDelay=90,
                           Value='child:0'),
               children=[dict(Type='SpeedDecrease', Name='Hindered', Target='Enemy', Value=30, Duration=d, Range=500)])
          for lv, name, d in [(20, "Gleipnir's Wish", 2), (35, "Gleipnir's Will", 4), (50, "Gleipnir's Command", 6)]],
    ]),
    ('Shaman Augmentation Spec', [
        single(41, 'Spirit Shell', 1001, Type='DamageReduction', Target='Realm', Value=50, Duration=10, CastTime=2.5, RecastDelay=60,
               Range=1500, Power=0),
        single(36, 'Caustic Carapace', 2874, Type='DamageReflection', Target='Realm', Value=250, LifeDrainReturn=1, Duration=15,
               CastTime=3.0, RecastDelay=60, Range=1500, Power=0),
        *[single(lv, name, 1081, 'shaman-vivification', Type='EnduranceRegenBuff', Target='Group', Value=v, Pulse=1, Frequency=50,
                 Duration=6, CastTime=3.0, Range=2000, Power=0, PulsePower=0, RecastDelay=0)
          for lv, name, v in [(2, 'Minor Earth Vivification', 3), (12, 'Lesser Earth Vivification', 4), (22, 'Earth Vivification', 5),
                              (32, 'Greater Earth Vivification', 6), (42, 'Superior Earth Vivification', 7)]],
        *[single(lv, name, 1031, 'shaman-unity', Type='HeatColdMatterBuff', Target='Group', Value=v, Duration=30, CastTime=3.0,
                 Range=2000, Power=0, RecastDelay=0)
          for lv, name, v in [(30, 'Tribal Unity', 18), (40, 'Shaman Unity', 24)]],
    ]),
    ('Subterranean Spec', [
        single(16, 'Escape Hold', 1081, Type='CureRoot', Target='Realm', CastTime=10.0, RecastDelay=300, Range=1500, Power=0),
        *[single(lv, name, 30001, 'shaman-weary-magic', Type='SpellDamageDebuff', Target='Enemy', Value=v, Duration=30, CastTime=2.8,
                 RecastDelay=45, Range=rng, Power=0, DamageType=BODY)
          for lv, name, v, rng in [(3, 'Weary Magic', 5, 1000), (13, 'Fizzle Magic', 10, 1000), (23, 'Suppress Magic', 25, 1000),
                                   (33, 'Suspend Magic', 50, 1500), (43, 'Halt Magic', 75, 1500)]],
        *[single(lv, name, 30001, 'shaman-bane', Type='PowerCostDebuff', Target='Enemy', Value=v, Duration=d, CastTime=3.0,
                 RecastDelay=30, Range=1500, Power=0, DamageType=BODY)
          for lv, name, v, d in [(9, 'Bane of Magic', 100, 30), (19, 'Bane of Arcane', 250, 25), (29, 'Bane of Power', 500, 25),
                                 (39, 'Bane of Augury', 750, 25), (49, 'Bane of Prophecy', 999, 30)]],
    ]),
    ('Instruments', [
        *[single(lv, name, 1031, 'minstrel-reach', Type='SpellRangeBuff', Target='Group', Value=v, Duration=30, CastTime=0, Range=1500,
                 Power=0, RecastDelay=0)
          for lv, name, v in [(8, 'Song of Magic Reach', 2), (18, 'Song of Arcane Reach', 4), (28, 'Song of Wizardic Reach', 6),
                              (38, 'Song of Supreme Reach', 8), (48, 'Song of Sorcerous Reach', 10)]],
        *[single(lv, name, 1031, 'minstrel-spell-songs', Type='AllSecondaryMagicResistsBuff', Target='Group', Value=v, Duration=15, CastTime=3.5,
                 Range=1500, Power=0, RecastDelay=0)
          for lv, name, v in [(9, 'Song of Spell Protection', 3), (19, 'Song of Spell Warding', 7), (29, 'Song of Spell Shielding', 10),
                              (39, 'Song of Spell Degradation', 15), (49, 'Song of Spell Invulnerability', 20)]],
    ]),
]


def definitions(m=None):
    """A package's rows (m: a module like this one, with PACKAGE, FIRST, LAST, TOOLTIP_BASE, LINES, ENTRIES, STOCK_LINKS).
    (line or None, level, fields, art SpellID) per row: each entry's parent, then its children."""
    m = m or sys.modules[__name__]
    rows, spell_id, group, families = [], m.FIRST, m.FIRST, {}
    for line, entries in m.ENTRIES:
        for entry in entries:
            family = entry.get('family')  # the ranks of one family share a group
            if family in families:
                entry_group = families[family]
            else:
                entry_group, group = group, group + 1
                if family:
                    families[family] = entry_group
            parent_id = spell_id
            child_ids = [parent_id + 1 + i for i in range(len(entry['children']))]

            def resolve(fields):
                return {k: (child_ids[int(v.split(':')[1])] if isinstance(v, str) and v.startswith('child:') else v) for k, v in fields.items()}

            # A parent may keep its own EffectGroup (a stock stacking group) or Description (read by its handler).
            parent = resolve(dict(dict(SpellGroup=entry_group, EffectGroup=entry_group, Description=f"{entry['name']} (live 1.130a {line})."),
                                  **entry['parent'], Name=entry['name'], SpellID=parent_id))
            if entry['children'] and parent['Type'] == 'TimedPulseArea':
                parent['SubSpellID'] = child_ids[0]
            rows.append((line, entry['level'], parent, entry['art']))
            for child_id, child in zip(child_ids, entry['children']):
                fields = resolve(dict(dict(Name=entry['name']), **child, SpellID=child_id,
                                      Description=f"{child.get('Name', entry['name'])}: part of {entry['name']}."))
                rows.append((None, entry['level'], fields, entry['art']))
            spell_id = parent_id + 1 + len(child_ids)
    assert spell_id - 1 <= m.LAST and spell_id - 1 < getattr(m, 'TOTEM_TIMER', m.LAST + 1)
    for _, _, fields, _ in rows:
        fields.update(Spell_ID=f"{m.PACKAGE}-{fields['SpellID']}", PackageID=m.PACKAGE, TooltipId=m.TOOLTIP_BASE + fields['SpellID'] - m.FIRST)
    return rows


def apply(db, m=None):
    m = m or sys.modules[__name__]
    db.row_factory = sqlite3.Row
    rows = definitions(m)
    if any(m.RESERVED_TOOLTIPS[0] <= f['TooltipId'] <= m.RESERVED_TOOLTIPS[1] for _, _, f, _ in rows):
        raise ValueError("Linked tooltips would enter the Death Knight's reserved block")
    if db.execute("select 1 from Spell where (SpellID between ? and ? or TooltipId between ? and ?) and coalesce(PackageID,'')<>?",
                  (m.FIRST, m.LAST, m.TOOLTIP_BASE, m.TOOLTIP_BASE + m.LAST - m.FIRST, m.PACKAGE)).fetchone():
        raise ValueError('Linked spell/tooltip collision')
    db.execute('delete from LineXSpell where SpellID between ? and ?', (m.FIRST, m.LAST))
    db.execute('delete from LineXSpell where LineXSpell_ID like ?', (m.PACKAGE + '-stock-%',))
    db.execute('delete from Spell where PackageID=?', (m.PACKAGE,))
    for key, spec, hint, base in m.LINES:
        db.execute('delete from SpellLine where KeyName=?', (key,))
        db.execute('insert into SpellLine (KeyName,Name,Spec,IsBaseLine,ClassIDHint,LastTimeRowUpdated) values (?,?,?,?,?,?)',
                   (key, key, spec, base, hint, '2000-01-01 00:00:00'))
    for line, level, fields, _ in rows:
        if line is None:
            continue
        if not db.execute('select 1 from SpellLine where KeyName=?', (line,)).fetchone():
            raise ValueError('Missing spell line ' + line)
        if db.execute("""select 1 from LineXSpell l join Spell s on s.SpellID=l.SpellID where l.LineName=? and s.Name=?
                         and coalesce(s.PackageID,'')<>?""", (line, fields['Name'], m.PACKAGE)).fetchone():
            raise ValueError(f"{line} already has {fields['Name']}")
    template = hybrid_lines.blank_spell(db)
    for line, level, fields, art in rows:
        source = db.execute('select ClientEffect, Icon from Spell where SpellID=?', (art,)).fetchone()
        if source is None:
            raise ValueError(f"No stock spell {art} to borrow art from")
        row = dict(template, **fields, ClientEffect=source['ClientEffect'], Icon=source['Icon'])
        row.update(Message1=f"You are affected by {row['Name']}.", Message2=f"{{0}} is affected by {row['Name']}.",
                   Message3=f"{row['Name']} ends.", Message4=f"{row['Name']} ends on {{0}}.")
        db.execute('insert into Spell (' + ','.join(f'"{k}"' for k in row) + ') values (' + ','.join('?' * len(row)) + ')', list(row.values()))
        if line:
            db.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)', (line, row['SpellID'], level, row['Spell_ID']))
    for line, spell_id, level, fields in m.STOCK_LINKS:
        if not db.execute("select 1 from Spell where SpellID=? and coalesce(PackageID,'') not like 'local-%'", (spell_id,)).fetchone():
            raise ValueError(f'Missing stock spell {spell_id}')
        db.execute('update Spell set ' + ','.join(f'"{k}"=?' for k in fields) + ' where SpellID=?', (*fields.values(), spell_id))
        db.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)',
                   (line, spell_id, level, f'{m.PACKAGE}-stock-{spell_id}'))
    key = getattr(m, 'RESULT_KEY', 'linked')
    return {f'{key}_package': m.PACKAGE, f'{key}_spells': sum(1 for r in rows if r[0]), f'{key}_children': sum(1 for r in rows if not r[0]),
            f'{key}_lines': len(m.LINES), f'{key}_stock': len(m.STOCK_LINKS)}
