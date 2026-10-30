"""Live (1.130a) spells for the next ten classes (owner: "do the next classes"), on linked_lines' machinery.

From daoc.gg's client spell data and the dated patches through 1.130a, in this server's units: direct damage at x0.0992,
lifedrains in tenths (drain return x10), damage adds in tenths of DPS, a snare's Value is the slow (live keeps the speed
left), casts are live's timer + 2 s. The list casters' spells go into new "<line> (Live)" lines beside the old ones (same
spec, class hint and base flag; one spell per level); the hybrid classes' go into their lines with a group per family.
  - Spiritmaster: Transfer Power..Spirit (power to a realm member, 25-150), Otherworldly Dissipation..Annihilation
    (10-75% snare within 400 of the caster, 15 s), Spirit Shock..Drain (power drains, 20% of the damage as power),
    Spirit Revival (a 500-radius resurrection, 25% health / 10% power, 10 min reuse), Soul Abolition (the level 50
    point-blank nuke: 392 to enemies within 300 of the caster, 2.5 s cast; the Enchanter's Disenchanting Explosion,
    the Cabalist's Molten Earthquake, the Wizard's Steaming Tempest and the Eldritch's Mana Deluge are the same spell).
  - Enchanter: Enchanted..Mana Barrier (a 15 s 30-1,500 point absorb on a realm member), Enchantment of Ice (the group's
    hits snare 50% for 5 s) and of Mana (40%: 109 Energy around the target), Radiant Glint..Glare (7-15% absorb
    debuff), Disenchanting Explosion (the level 50 ground nuke).
  - Runemaster: Mark..Rune of Thunder (Energy DDs 43-208), Greater Agony/Misery Rune (group damage adds), Rune of
    Sapping..Dissipating (absorb debuffs). Cabalist: Molten Earthquake (the level 50 ground nuke), Convert Minion..Simulacrum
    (the pet becomes power), Awaken Simulacrum (wakes a mezzed pet), Simulacrum Superiority/Brilliance (the pet's
    attackers are slowed 10% for 5 s).
  - Warlock: Major Shield..Superior Barricade (self AF 40-250), Fascinating/Magical Buffer (self absorb 5/10%),
    Hexed Tangling/Tenacious/Detaining Root (350-radius roots), Charmed Gift/Boon/Favor of Health (spread heals).
  - The Bainshee (and the Vampiir and Heretic) are left to the expansion kit (install_expansion_test.py), which already
    gives them their live lines.
  - Animist: Fungal Potency (turrets' resist piercing 15%), Spoil/Decompose/Decay Armor (AF debuffs).
  - Healer: Amelioration..Emendation of Eir (25% when hit, heals the struck group member 15-100), Calming
    Contemplation..Concentration (mez duration reduction 10-40%), Eir's Suggestion..Intervention (40% on own attacks,
    a lifetap 29-183). Friar: Golestandt's Fire/Breath/Heart (group Heat/Cold/Matter resists 12/18/24%, resist set 93),
    Novice..Grandmaster Staffman (+2-10 Staff), Meditation (damage taken -50% for 5 s). Shaman: Compulsion/
    Coercion of the Deep (group damage adds).
Fourth pass (owner: "keep going"):
  - Valewalker: Thorned/Bristled/Spurred Weapons (group damage adds), Forest Sage's Presence..Perfection (a group
    spell-range chant, 2-10%), Blight Burst (a 300-radius disease around the caster, 45 s reuse), Blizzardstrike (25% on
    own hits: a 15% Energy resist debuff for 15 s).
  - Wizard: Earthen Rage / Greater Earthen Rage (group damage adds; the Theurgist shares the base line and has them on
    live too), Dusted..Soil Vision (nearsight), Fear..Terrify Minion (pet fear), Steaming Tempest (the ground nuke).
  - Sorcerer: Minor..Water Breath (group water breathing), Circle of Perception..Lucidity (group power regen 4-10),
    Suggested Rage (group melee damage +10% for 10 s), Mollifying Suggestion (spell damage -30% for 30 s).
  - Mentalist: Cloud of Distortion..Blindness (nearsight), Illusion of Guarding/Shielding/Protection (a pulsing group
    absorb, 60-120 points at 30%). Bard: Neriad's Call..Breath of Leviathan (water breathing). Skald: Crescendo, Great
    Crescendo, March of Bragi (speed bursts). Druid: Free Wind (frees from roots and snares), Morning Sun (wakes the
    pet), Nature's Cocoon (damage taken -50% for 10 s), Nature's Frenzy (the pet's attack speed +50%, damage +25%).
    Warden: Cure Sight.
Fifth pass, from Codex's sourced research (Class-Research/codex/followup-2026-10-25: client formatter decodes and
official notes), checked against Gemini's leads; where they disagree, the sourced answer is used:
  - Shaman Frigg's Grace / Superior (heals on the target +25/50%, 45 s). Enchanter Calming..Graceful Light (heals the
    target casts +5/10/20/33/50%, 30 s; the formatter's bonus / 10 - 100).
  - Minstrel Fervor songs (group melee haste 24/28/31/37% for 15 s, 2 s cast, 1.128c). Bard Whisper line (self
    endurance regen 1-5 for 20 minutes), Hymn of Soul Guarding/Protection (8/12% Body/Spirit/Energy: resist set 98 per
    the client formatter; older Bard notes said all magic). Warden Glimmer Shield/Guard/Barrier (12/18/24%
    Body/Spirit/Energy, resist set 94).
  - Friar Sharpness (+15% evade within 200 for 20 s, 60 s reuse), Saint's Resolve (a pulsing 5% endurance-consumption
    cut), Tranquility (5% health to realm members within 1,500 every second for 15 s; the power and endurance parts and
    1.123's 25% damage reduction aren't built).
  - Runemaster Empowerments (a group spell-crit pulse, +1-5%). Sorcerer Forced Trance (instant 30 s mez, 10 min
    reuse), Mindfulness (resets Quickcast, 60 s reuse), Mass Gateway (the group within 1,000 returns to its bind points;
    members in combat stay; 42 s cast). Warlock Conjured Bubble (self bladeturn, 20 minutes).
  - Skald Disorienting Yelp / Cry (monster confusion within 500/750 for 20 s, 85/100% chance, 90/60 s reuse).
    Paladin Cure of the Righteous / Virtuous / Faithful (poison / disease / poison, disease and more, within 350,
    a shared 45 s reuse; 1.114b). Bonedancer Dread Charge (the pet +165% speed for 10 s, 90 s reuse; 1.123B).
Sixth pass, from Codex's all-class audit (Class-Research/codex/all-classes-2026-10-26): Eldritch Crumble/Fade/Vanquish
Spirit (Spirit resist debuffs 15/30/40%, 15 s, 30 s reuse) and Mana Deluge; Cleric Hand of God (damage taken -50%
for 10 s, 60 s reuse), Blessing of Movement (frees from roots and snares, 10 s cast, 5 min reuse) and Ascendance
(+100% melee damage for 25 s, 10 min reuse); Shaman Induce Ailment (disease) and the Warding Aid..Tribute group heals
(20-205; their absorb part isn't built); Thane Gift of Lightning (the realm member's melee becomes Energy for 60 s).
Not built: the class pets and turrets with no matching local template (Spiritmaster spirits, Animist turrets and main
pets, Underhill Stalker, Night's Servant), Hel's charms, Gates of Valhalla, the Healing Lights, the Imbue spells, Sharpness,
Tranquility, Confounding Cast, the Vampiir bolts and Shadow's Nimbleness, Unshakable Cast, Conjured Bubble, and the
Runemaster Empowerments (no handler, or the data doesn't say what they change).
Seventh pass (owner: "start on all of the not built items"), new handlers in spells/LiveRound7Handlers.cs:
  - Charms: Spiritmaster Hel's Control/Possession/Domination, Mentalist Phantom/Ghostly/Dream Adversary, Minstrel
    Engaging/Engrossing/Enthralling Harmony (caps 26/40/50, the libraries). The client's charm formatter reads the body
    type from parm (3 humanoid ... 53 adds undead); these records have none, like the stock Sorcerer charms, so they
    charm any body type (AmnesiaChance 0).
  - Friar Imbue Lesser Haste..Greater Alacrity (6-46): single-target concentration haste 8/12/15/17/20% (the Friar
    library; 1.121B kept the values), concentration 1/7/11/14/19 as the Healer's and Druid's hastes of the same power level.
  - Confounding Cast (Healer 35, Friar 40, Warden 40): a 15 s monster confusion, 70% like the Bard's parm-5 Cadence.
  - Enchanter: Enchantment of Stone (melee becomes Matter, +300 AF) and Fire (Heat, +25% melee damage), Truth (melee
    can't miss and pierces bladeturn, 15 s), Zeal (style damage bonus x3; styled hits heal the rest of the group, shared).
  - Druid Heart of Nature: frees the group from roots and snares and roots 2 enemies within 200 of each ally for 15 s.
  - Reaver Malefic Horror: enemy pets and monsters within 350 flee for 15 s. Assassins' Overshadow: stealths an ally
    (not a stealther or a Minstrel) for 10 s. Champion/Skald/Minstrel Siegebreaker: +20 melee damage to keep doors,
    walls and siege weapons for 15 s (the siege-weapon bonus has no figure; not built).
  - Mentalist Speedwarp: a 2,000-radius ward at the caster for 300 s that negates enemies' speed boosts (1 s pulses).
  - Thane Chain Lightning: 396.8 Energy, then up to 4 random enemies within 500 of the target, 10% less a jump.
  - Grapples: Wizard Ice Grip (held, can't be damaged, may still melee, 6 s), Flame Cocoon (self: held, silenced,
    melee-proof, 200 health every 1.5 s, 7 s), Warrior Battle Control (Warrior plus 4 group members or pets within 400
    can't move, melee or be meleed for 8 s; a new Warrior Shields (Live) line).
  - Shaman Blight Surge: 10 s immune to damage, 3% health every 2 s; enemies within 250 lose 50 endurance and take 50
    Matter and a disease each pulse (1.123/1.126 and the delve; the data's 3 s child record is unreconciled).
  - Theurgist Summon Greater Ice Elemental (Refrigeration 48): the unused stock template 25, shaped like its siblings.
  Unshakable Cast already existed as "Unshakeable Cast" (66015, local-warlock-test-v1). Still not built: the Mauler
  Farseer realm gift damage for ranks 1-4 (no figure in any source).
Pets (owner-approved PETS-PROPOSAL-2026-10-25.md): live's pet spells from the class data, the pets' own spells from the
client spell map, each pet on a copy of the closest local template (PET_TEMPLATES, 77900-77922) with the live name:
  - Animist bombers Heavy..Bulging Spirit (Arboreal, Body) and Spirit of Deceit..Guile (Creeping spec, Matter) on the
    shared Bomber template; spore turrets Forest's Blight..Menace (a disease plus a Matter DoT), heal turrets Grove
    Sibyl..Druid (20-215) and Shroom of Life (a 400 heal-over-time); the level 40 main pets Guardian of the Forest, Heart
    of the Grove and Harbinger of War at the caster's level. The Creeping and Verdant spec pets go in "(Live)" lines:
    the stock lines hold the older pets at those levels.
  - Spiritmaster Spirit Hunter/Runemaster/Shaman/Valkyrie/Warrior (copies of spirit champion, its stock spell kit) in
    Summoning (Live); Gates of Valhalla: every 12 s for 60 s a Fallen Einherjar (the soultorn einherjar) fights an
    enemy within 1,500 for 15 s.
  - Druid Summon Grove Guardian (31, cap 34) and Grove Protector (40, cap 40) in Nature Magic, Call Nature Sage (spec
    40; tree, bear, lynx and wolf forms); Enchanter Underhill Stalker (31, a copy of the zealot).
  The stock pets live dropped (Spirit Fighter..Champion, Call Greater Nature Spirit) stay, and the Underhill pets keep
  their levels (owner's call). The live pets' own spell kits aren't modelled.
"""
import linked_lines

PACKAGE = 'local-round3-live-v1'
FIRST, LAST = 77500, 77899
TOOLTIP_BASE = 24600  # 24600-24999 are unused; 23200-23999 is the Death Knight's reserved block
RESERVED_TOOLTIPS = (23200, 23999)
RESULT_KEY = 'round3'
STOCK_LINKS = []
BODY, COLD, ENERGY, HEAT, MATTER, SPIRIT = 10, 11, 12, 13, 14, 15
DD = 0.0992

# New list lines: (key, spec, class hint, base line), beside the line they are named after.
LINES = [('Spirit Enhancement (Live)', 'Summoning', 0, 0), ('Spirit Suppression (Live)', 'Suppression', 27, 0),
         ('Enchantment Mastery (Live)', 'Enchantments', 0, 0), ('Bedazzling (Live)', 'Light', 41, 0), ('Empowering (Live)', 'Mana', 41, 0),
         ('Runes of Darkness (Live)', 'Darkness', 29, 0), ('Runes of Destruction (Live)', 'Runecarving', 0, 0),
         ('Runes of Suppression (Live)', 'Suppression', 29, 0), ('Matter Manipulation (Live)', 'Matter Magic', 13, 0),
         ('Spirit Animation (Live)', 'Spirit Magic', 0, 1), ('Vivification (Live)', 'Spirit Magic', 0, 0),
         ('Cursing (Live)', 'Cursing', 0, 1), ('Hexing (Live)', 'Hexing', 0, 0), ('Witchcraft (Live)', 'Witchcraft', 0, 0),
         ('Creeping Path Spec (Live)', 'Creeping Path', 0, 0), ('Creeping Path (Live)', 'Creeping Path', 0, 1),
         ('Valewalker Arboreal Path Base (Live)', 'Arboreal Path', 56, 1), ('Valewalker Arb Path Spec (Live)', 'Arboreal Path', 56, 0),
         ('Path of Earth (Live)', 'Earth Magic', 0, 1), ('Calefaction (Live)', 'Earth Magic', 7, 0), ('Liquifaction (Live)', 'Cold Magic', 7, 0),
         ('Pyromancy (Live)', 'Fire Magic', 7, 0), ('Mind Twisting (Live)', 'Mind Magic', 0, 1), ('Domination (Live)', 'Mind Magic', 0, 0),
         ('Holism (Live)', 'Mana', 42, 0), ('Mind Mastery (Live)', 'Mentalism', 0, 0),
         ('Shadow Control (Live)', 'Light', 40, 0), ('Vacuumancy (Live)', 'Mana', 40, 0),
         ('Warrior Shields (Live)', 'Shields', 22, 0), ('Verdant Path Spec (Live)', 'Verdant Path', 0, 0),
         ('Summoning (Live)', 'Summoning', 0, 1)]

# Live pets on copies of the closest local templates (PETS-PROPOSAL-2026-10-25.md, approved by the owner): new TemplateId,
# source TemplateId (and its row's name where one ID holds variants), new name.
FIRST_TEMPLATE = 77900
PET_TEMPLATES = [
    *[(77900 + i, 235, None, name) for i, name in enumerate(["forest's blight", "forest's curse", "forest's scourge", "forest's torment",
                                                              "forest's menace"])],
    *[(77905 + i, 2130, None, name) for i, name in enumerate(['grove sibyl', 'grove augur', 'grove oracle', 'grove druid', 'shroom of life'])],
    (77910, 117, None, 'guardian of the forest'), (77911, 137, None, 'heart of the grove'), (77912, 98, None, 'harbinger of war'),
    *[(77913 + i, 5, None, name) for i, name in enumerate(['spirit hunter', 'spirit runemaster', 'spirit shaman', 'spirit valkyrie',
                                                            'spirit warrior'])],
    (77918, 60166399, None, 'fallen einherjar'),
    (77919, 47, 'greater nature spirit', 'grove guardian'), (77920, 145, None, 'grove protector'),
    *[(77921, source, None, 'nature sage') for source in (145, 48, 146, 147)],  # the tree, bear, lynx and wolf forms
    (77922, 35, None, 'underhill stalker'),
]


def single(level, name, art, family=None, **fields):
    return dict(level=level, name=name, art=art, family=family, children=[], parent=fields)


def proc(level, name, art, family, kind, chance, child, **fields):
    return dict(level=level, name=name, art=art, family=family, children=[child],
                parent=dict(dict(Type=kind, Frequency=chance, Value='child:0', CastTime=3.0, Power=0, RecastDelay=0), **fields))


def detonate(level, name, damage_type):
    """The level 50 nuke: a point-blank area around the caster (live group DAMAGEPBAE, no range; target 12 is the
    client's "enemy realm only", Codex's target decoder)."""
    return single(level, name, 2501, Type='DirectDamage', Target='Enemy', Damage=round(3950 * DD, 1), Radius=300, Range=0, CastTime=2.5,
                  Power=0, DamageType=damage_type, RecastDelay=0)


def bomber(level, name, art, child, kind, **fields):
    """An Animist bomber (the shared Bomber template 730): it runs to the target and explodes for the child's damage."""
    return dict(level=level, name=name, art=art, family=None,
                parent=dict(dict(Type='Bomber', Target='Enemy', Damage=50, Value=50, LifeDrainReturn=730, DamageType=kind, SubSpellID='child:0'),
                            **fields),
                children=[dict(Type='DirectDamage', Name=f'{name} (Damage)', Target='Enemy', Damage=child, DamageType=kind, Range=1500)])


def turret(level, name, art, template, power, child, dot=None, **fields):
    """An Animist fire-and-forget turret casting its child (and the child's DoT); 120 s at 88% of level 44, as the stock ones."""
    return dict(level=level, name=name, art=art, family=None,
                parent=dict(dict(Type='SummonAnimistFnF', Target='Self', LifeDrainReturn=template, Value=44, Damage=-88, Duration=120,
                                 CastTime=3.5, Power=power, RecastDelay=0, DamageType=BODY, SubSpellID='child:0'), **fields),
                children=[child] + ([dot] if dot else []))


def main_pet(level, name, art, template, pet_spell):
    """An Animist main pet at the caster's level (cap 50; 1.122B), with its source template's spell."""
    return single(level, name, art, Type='SummonAnimistPet', Target='Self', LifeDrainReturn=template, Value=50, Damage=-100,
                  Duration=65535, CastTime=5.0, Power=60, Range=1000, RecastDelay=0, SubSpellID=pet_spell)


def ranks(rows, art, family, **common):
    """single() per (level, name, fields) row with shared fields."""
    return [single(lv, name, art, family, **dict(common, **fields)) for lv, name, fields in rows]


ENTRIES = [
    ('Spirit Enhancement (Live)', [
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(2, 'Transfer Power', 25), (12, 'Transfer Essence', 40), (22, 'Transfer Force', 70),
                                                             (32, 'Transfer Soul', 105), (42, 'Transfer Spirit', 150)]],
               2874, 'sm-transfer', Type='PowerTransfer', Target='Realm', Range=1500, CastTime=3.0, Power=0, RecastDelay=0),
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(3, 'Otherworldly Dissipation', 10), (13, 'Otherworldly Explosion', 20),
                                                             (23, 'Otherworldly Banish', 30), (33, 'Otherworldly Destruction', 50),
                                                             (43, 'Otherworldly Annihilation', 75)]],
               2874, 'sm-otherworldly', Type='SpeedDecrease', Target='Enemy', Duration=15, Radius=400, Range=0, CastTime=2.5, Power=0,
               DamageType=SPIRIT, RecastDelay=0),
        *ranks([(lv, name, dict(Damage=round(d * DD, 1))) for lv, name, d in [(5, 'Spirit Shock', 240), (15, 'Spirit Jolt', 580),
                                                                             (25, 'Spirit Burst', 1120), (35, 'Spirit Siphon', 1430),
                                                                             (45, 'Spirit Drain', 1890)]],
               2874, 'sm-drain', Type='PowerDrain', Target='Enemy', LifeDrainReturn=20, Range=1500, CastTime=2.8, Power=0,
               DamageType=SPIRIT, RecastDelay=0),
        single(40, 'Spirit Revival', 2874, Type='Resurrect', Target='Corpse', Radius=500, Range=1875, ResurrectHealth=25, ResurrectMana=10,
               RecastDelay=600, CastTime=0, Power=0),
    ]),
    ('Spirit Suppression (Live)', [detonate(50, 'Soul Abolition', SPIRIT)]),
    ('Enchantment Mastery (Live)', [
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(1, 'Enchanted Barrier', 30), (11, 'Magic Barrier', 150), (21, 'Empowered Barrier', 350),
                                                             (31, 'Arcane Barrier', 750), (41, 'Mana Barrier', 1500)]],
               1001, 'ench-barrier', Type='BothAblativeArmor', Target='Realm', Damage=100, Duration=15, Range=2000, CastTime=3.0, Power=0,
               RecastDelay=0),
        proc(33, 'Enchantment of Ice', 1560, None, 'OffensiveProc', 100,
             dict(Type='SpeedDecrease', Name='Freezing Weapons', Target='Enemy', Value=50, Duration=5, Range=4000, DamageType=ENERGY),
             Target='Group', Duration=30, Range=1500, CastTime=2.3),
        proc(40, 'Enchantment of Mana', 1560, None, 'OffensiveProc', 40,
             dict(Type='DirectDamage', Name='Enchanting Eruption', Target='Enemy', Damage=round(1100 * DD, 1), Radius=300, Range=350,
                  DamageType=ENERGY), Target='Group', Duration=30, Range=1500),
    ]),
    ('Bedazzling (Live)', ranks([(lv, name, dict(Value=v)) for lv, name, v in [
        (6, 'Radiant Glint', 7), (18, 'Radiant Glimmer', 9), (26, 'Radiant Gleam', 11), (38, 'Radiant Glare', 13), (47, 'Radiant Glare', 15)]],
        30001, 'ench-radiant', Type='ArmorAbsorptionDebuff', Target='Enemy', Duration=20, Range=1500, RecastDelay=8, CastTime=0, Power=0,
        DamageType=ENERGY)),
    ('Empowering (Live)', [detonate(50, 'Disenchanting Explosion', ENERGY)]),
    ('Runes of Darkness (Live)', ranks([(33, 'Greater Agony Rune', dict(Damage=7.9)), (41, 'Greater Misery Rune', dict(Damage=10.0))],
                                       10200, 'rm-damage-add', Type='DamageAdd', Target='Group', Duration=600, Range=1000, CastTime=10.0,
                                       Power=0, DamageType=SPIRIT, RecastDelay=0)),
    ('Runes of Destruction (Live)', ranks([(lv, name, dict(Damage=round(d * DD, 1))) for lv, name, d in [
        (6, 'Mark of Thunder', 432), (16, 'Insignia of Thunder', 865), (26, 'Seal of Thunder', 1332), (36, 'Signet of Thunder', 1637),
        (46, 'Rune of Thunder', 2097)]], 2501, 'rm-thunder', Type='DirectDamage', Target='Enemy', Range=1500, CastTime=2.8, Power=0,
        DamageType=ENERGY, RecastDelay=0)),
    ('Runes of Suppression (Live)', ranks([(lv, name, dict(Value=v)) for lv, name, v in [
        (6, 'Rune of Sapping', 7), (15, 'Rune of Weakening', 9), (28, 'Rune of Depleting', 11), (38, 'Rune of Diminishing', 13),
        (47, 'Rune of Dissipating', 15)]], 30001, 'rm-sapping', Type='ArmorAbsorptionDebuff', Target='Enemy', Duration=20, Range=1500,
        RecastDelay=8, CastTime=0, Power=0, DamageType=SPIRIT)),
    ('Matter Manipulation (Live)', [detonate(50, 'Molten Earthquake', MATTER)]),
    ('Spirit Animation (Live)', [single(25, 'Awaken Simulacrum', 1081, Type='CureMezz', Target='Pet', Range=1000, CastTime=0, Power=0,
                                        RecastDelay=0)]),
    ('Vivification (Live)', [
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(11, 'Convert Minion', 25), (21, 'Convert Retainer', 50), (31, 'Convert Servant', 100),
                                                             (41, 'Convert Simulacrum', 150)]],
               1081, 'cab-convert', Type='PetConversion', Target='Pet', Range=500, CastTime=3.0, Power=0, RecastDelay=0),
        *[proc(lv, name, 1560, 'cab-simulacrum', 'DefensiveProc', 100,
               dict(Type='SpeedDecrease', Name='Dreading Slow', Target='Enemy', Value=10, Duration=5, Range=1000, DamageType=ENERGY),
               Target='Pet', Duration=1200, Range=1500, CastTime=5.0)
          for lv, name in [(33, 'Simulacrum Superiority'), (43, 'Simulacrum Brilliance')]],
    ]),
    ('Cursing (Live)', [
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [
            (3, 'Major Shield', 40), (11, 'Greater Shield', 58), (14, 'Superior Shield', 75), (18, 'Minor Barricade', 95),
            (24, 'Lesser Barricade', 124), (32, 'Major Barricade', 162), (42, 'Greater Barricade', 211), (49, 'Superior Barricade', 250)]],
            1001, 'wl-shield', Type='BaseArmorFactorBuff', Target='Self', Duration=1200, CastTime=3.0, Range=0, Power=0, RecastDelay=0),
        *ranks([(30, 'Fascinating Buffer', dict(Value=5)), (41, 'Magical Buffer', dict(Value=10))], 10069, 'wl-buffer',
               Type='ArmorAbsorptionBuff', Target='Self', Duration=1200, CastTime=3.0, Range=0, Power=0, RecastDelay=0),
    ]),
    ('Hexing (Live)', ranks([(lv, name, dict(Duration=d)) for lv, name, d in [
        (28, 'Hexed Tangling Root', 50), (40, 'Hexed Tenacious Root', 61), (49, 'Hexed Detaining Root', 73)]],
        30022, 'wl-root', Type='SpeedDecrease', Target='Enemy', Value=99, Radius=350, Range=1500, CastTime=2.5, Power=0, DamageType=MATTER,
        RecastDelay=0)),
    ('Witchcraft (Live)', ranks([(lv, name, dict(Value=v)) for lv, name, v in [
        (31, 'Charmed Gift of Health', 135), (39, 'Charmed Boon of Health', 180), (47, 'Charmed Favor of Health', 225)]],
        1443, 'wl-spread', Type='SpreadHeal', Target='Self', Range=2000, CastTime=3.5, Power=0, RecastDelay=0)),
    ('Creeping Path Spec (Live)', ranks([(lv, name, dict(Value=v)) for lv, name, v in [
        (30, 'Spoil Armor', 100), (39, 'Decompose Armor', 165), (49, 'Decay Armor', 250)]],
        30001, 'an-armor', Type='ArmorFactorDebuff', Target='Enemy', Duration=20, Range=1500, CastTime=3.0, Power=0, DamageType=MATTER,
        RecastDelay=0)),
    ('Creeping Path (Live)', [single(29, 'Fungal Potency', 1081, Type='ResiPierceBuff', Target='Pet', Value=15, Radius=350, Duration=60,
                                     Range=2000, CastTime=0, Power=0, RecastDelay=0)]),
    ('Healer Augmentation Spec', [
        *[proc(lv, name, 1560, 'hl-eir-heal', 'DefensiveProc', 25, dict(Type='Heal', Target='Self', Value=heal),
               Target='Group', Duration=1200, Range=1500)
          for lv, name, heal in [(9, 'Amelioration of Eir', 15), (17, 'Purification of Eir', 32), (25, 'Recovery of Eir', 49),
                                 (33, 'Reparation of Eir', 66), (41, 'Reconstruction of Eir', 83), (49, 'Emendation of Eir', 100)]],
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(16, 'Calming Contemplation', 10), (26, 'Calming Meditation', 20),
                                                             (35, 'Calming Focus', 30), (44, 'Calming Concentration', 40)]],
               1001, 'hl-calming', Type='MesmerizeDurationBuff', Target='Self', Duration=1200, CastTime=4.0, Range=0, Power=0, RecastDelay=0),
    ]),
    ('Pacification Spec', [
        proc(lv, name, 1560, 'hl-eir-tap', 'OffensiveProc', 40,
             dict(Type='Lifedrain', Target='Enemy', Damage=round(d / 10, 1), Value=-70, LifeDrainReturn=70, Range=1000, DamageType=BODY),
             Target='Self', Duration=1200, Range=0)
        for lv, name, d in [(7, "Eir's Suggestion", 290), (13, "Eir's Instruction", 520), (19, "Eir's Guidance", 760), (26, "Eir's Direction", 1020),
                            (37, "Eir's Mandate", 1450), (47, "Eir's Intervention", 1830)]
    ]),
    ('Friar Enhancement Spec', [
        *ranks([(13, "Golestandt's Fire", dict(Value=12)), (31, "Golestandt's Breath", dict(Value=18)), (43, "Golestandt's Heart", dict(Value=24))],
               1031, 'fr-golestandt', Type='HeatColdMatterBuff', Target='Group', Duration=30, CastTime=3.0, Range=2000, Power=0, RecastDelay=0),
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(7, 'Novice Staffman', 2), (17, 'Apprentice Staffman', 4), (27, 'Expert Staffman', 6),
                                                             (37, 'Master Staffman', 8), (47, 'Grandmaster Staffman', 10)]],
               1001, 'fr-staffman', Type='StaffSkillBuff', Target='Self', Duration=1200, CastTime=3.0, Range=0, Power=0, RecastDelay=0),
        single(30, 'Meditation', 1001, Type='DamageReduction', Target='Self', Value=50, Duration=5, RecastDelay=180, CastTime=0, Range=0, Power=0),
    ]),
    ('Shaman Augmentation Spec', ranks([(35, 'Compulsion of the Deep', dict(Damage=7.9)), (45, 'Coercion of the Deep', dict(Damage=10.0))],
                                       10200, 'sh-deep', Type='DamageAdd', Target='Group', Duration=600, Range=1000, CastTime=10.0, Power=0,
                                       DamageType=SPIRIT, RecastDelay=0)),
    # Fourth pass.
    ('Valewalker Arboreal Path Base (Live)', ranks([(28, 'Thorned Weapons', dict(Damage=6.4)), (38, 'Bristled Weapons', dict(Damage=7.8)),
                                                    (48, 'Spurred Weapons', dict(Damage=10.0))],
                                                   10200, 'vw-weapons', Type='DamageAdd', Target='Group', Duration=1200, Range=1000,
                                                   CastTime=3.0, Power=0, DamageType=SPIRIT, RecastDelay=0)),
    ('Valewalker Arb Path Spec (Live)', [
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(4, "Forest Sage's Presence", 2), (17, "Forest Sage's Ubiquity", 4),
                                                             (24, "Forest Sage's Acumen", 6), (30, "Forest Sage's Sagacity", 8),
                                                             (45, "Forest Sage's Perfection", 10)]],
               1031, 'vw-sage', Type='SpellRangeBuff', Target='Group', Pulse=1, Frequency=60, Duration=6, Range=1500, CastTime=0, Power=0,
               PulsePower=0, RecastDelay=0),
        single(37, 'Blight Burst', 30003, Type='Disease', Target='Enemy', Duration=60, Radius=300, Range=0, CastTime=0, RecastDelay=45, Power=0,
               DamageType=BODY),
        proc(50, 'Blizzardstrike', 1560, None, 'OffensiveProc', 25,
             dict(Type='EnergyResistDebuff', Target='Enemy', Value=15, Duration=15, Range=1000, DamageType=ENERGY),
             Target='Self', Duration=1200, Range=0),
    ]),
    ('Path of Earth (Live)', ranks([(35, 'Earthen Rage', dict(Damage=7.9)), (45, 'Greater Earthen Rage', dict(Damage=10.0))],
                                   10200, 'wz-earthen-rage', Type='DamageAdd', Target='Group', Duration=600, Range=1000, CastTime=10.0,
                                   Power=0, DamageType=MATTER, RecastDelay=0)),
    ('Calefaction (Live)', ranks([(lv, name, dict(Range=rng)) for lv, name, rng in [(19, 'Dusted Vision', 2000), (27, 'Encrusted Vision', 2100),
                                                                                   (37, 'Mire Vision', 2200), (45, 'Soil Vision', 2300)]],
                                 30001, 'wz-vision', Type='Nearsight', Target='Enemy', Value=45, Duration=60, CastTime=2.0, Power=0,
                                 DamageType=MATTER, RecastDelay=0)),
    ('Liquifaction (Live)', [detonate(50, 'Steaming Tempest', COLD)]),
    ('Pyromancy (Live)', ranks([(lv, name, dict(Duration=d)) for lv, name, d in [(9, 'Fear Minion', 5), (20, 'Expel Minion', 13),
                                                                                (29, 'Intimidate Minion', 21), (39, 'Daunt Minion', 30),
                                                                                (49, 'Terrify Minion', 42)]],
                               30001, 'wz-fear', Type='WarlockPetFear', Target='Enemy', Range=1500, CastTime=3.5, Power=0, RecastDelay=0)),
    ('Mind Twisting (Live)', ranks([(lv, name, dict(Value=v)) for lv, name, v in [(14, 'Minor Water Breath', 70), (24, 'Lesser Water Breath', 80),
                                                                                 (34, 'Greater Water Breath', 90), (44, 'Water Breath', 100)]],
                                   74023, 'so-breath', Type='WaterBreathing', Target='Group', Duration=1800, Range=1500, CastTime=3.0, Power=0,
                                   RecastDelay=0)),
    ('Domination (Live)', [
        *ranks([(16, 'Circle of Perception', dict(Value=4, CastTime=3.0)), (22, 'Circle of Perspicuity', dict(Value=6, CastTime=3.0)),
                (31, 'Circle of Cognition', dict(Value=8, CastTime=4.0)), (42, 'Circle of Lucidity', dict(Value=10, CastTime=4.0))],
               1081, 'so-circle', Type='PowerRegenBuff', Target='Group', Duration=600, Range=1500, Power=0, RecastDelay=0),
        single(45, 'Suggested Rage', 1021, Type='MeleeDamageBuff', Target='Group', Value=10, Duration=10, Range=1500, CastTime=3.2,
               RecastDelay=30, Power=0),
        single(49, 'Mollifying Suggestion', 30001, Type='SpellDamageDebuff', Target='Enemy', Value=30, Duration=30, Range=1500, CastTime=2.8,
               RecastDelay=60, Power=0, DamageType=SPIRIT),
    ]),
    ('Holism (Live)', ranks([(lv, name, dict(Range=rng)) for lv, name, rng in [(18, 'Cloud of Distortion', 2000), (26, 'Cloud of Obscurity', 2100),
                                                                              (38, 'Cloud of Darkness', 2200), (47, 'Cloud of Blindness', 2300)]],
                            30001, 'mt-cloud', Type='Nearsight', Target='Enemy', Value=45, Duration=60, CastTime=2.0, Power=0,
                            DamageType=ENERGY, RecastDelay=0)),
    ('Mind Mastery (Live)', ranks([(lv, name, dict(Value=v)) for lv, name, v in [(30, 'Illusion of Guarding', 60), (39, 'Illusion of Shielding', 90),
                                                                                (48, 'Illusion of Protection', 120)]],
                                  1001, 'mt-illusion', Type='BothAblativeArmor', Target='Group', Damage=30, Pulse=1, Frequency=60, Duration=6,
                                  Range=1500, CastTime=0, RecastDelay=8, Power=0, PulsePower=0)),
    ('Bard Music', ranks([(lv, name, dict(Value=v)) for lv, name, v in [(17, "Neriad's Call", 70), (27, "Neriad's Breath", 80),
                                                                       (37, "Neriad's Blessing", 90), (47, 'Breath of Leviathan', 100)]],
                         74023, 'bd-breath', Type='WaterBreathing', Target='Group', Duration=1800, Range=1500, CastTime=3.0, Power=0,
                         RecastDelay=0)),
    ('Battlesongs', [
        *ranks([(35, 'Crescendo', dict(Value=115, Duration=7)), (44, 'Great Crescendo', dict(Value=135, Duration=9))], 1021, 'sk-crescendo',
               Type='SpeedEnhancement', Target='Realm', Range=1500, CastTime=0, RecastDelay=45, Power=0),
        single(50, 'March of Bragi', 1021, Type='SpeedEnhancement', Target='Group', Value=135, Duration=9, Range=1500, CastTime=3.0,
               RecastDelay=600, Power=0),
    ]),
    ('Druid Nature Spec', [
        single(13, 'Free Wind', 1081, Type='CureRoot', Target='Realm', CastTime=10.0, RecastDelay=300, Range=1500, Power=0),
        single(21, 'Morning Sun', 1081, Type='CureMezz', Target='Pet', Range=1000, CastTime=0, Power=0, RecastDelay=0),
        dict(level=2, name="Nature's Frenzy", art=1021, family=None,
             parent=dict(Type='CombatSpeedBuff', Target='Pet', Value=50, Duration=30, RecastDelay=60, Range=1500, CastTime=0, Power=0,
                         SubSpellID='child:0'),
             children=[dict(Type='MeleeDamageBuff', Target='Pet', Value=25, Duration=30, Range=1500)]),
    ]),
    ('Druid Nurture Spec', [single(41, "Nature's Cocoon", 1001, Type='DamageReduction', Target='Realm', Value=50, Duration=10, CastTime=2.5,
                                   RecastDelay=60, Range=1500, Power=0)]),
    ('Regrowth Warden Spec', [single(25, 'Cure Sight', 1081, Type='CureNearsight', Target='Realm', Range=1500, CastTime=6.0, Power=0,
                                     RecastDelay=0)]),
    # Fifth pass (sourced research).
    ('Shaman Augmentation Spec', ranks([(24, "Frigg's Grace", dict(Value=25)), (35, "Frigg's Superior Grace", dict(Value=50))],
                                       1081, 'sh-grace', Type='HealingReceivedBuff', Target='Realm', Duration=45, Range=1500, CastTime=0,
                                       RecastDelay=15, Power=0)),
    ('Enchantment Mastery (Live)', ranks([(9, 'Calming Light', dict(Value=5)), (19, 'Peaceful Light', dict(Value=10)),
                                          (29, 'Harmonic Light', dict(Value=20)), (39, 'Serene Light', dict(Value=33)),
                                          (49, 'Graceful Light', dict(Value=50, RecastDelay=30))],
                                         1081, 'ench-light', Type='HealingDoneBuff', Target='Realm', Duration=30, Range=1500, CastTime=2.0,
                                         RecastDelay=0, Power=0)),
    ('Instruments', ranks([(lv, name, dict(Value=v)) for lv, name, v in [(16, 'Song of Inspiring Fervor', 24), (26, 'Song of Rallying Fervor', 28),
                                                                        (36, 'Song of Awakening Fervor', 31), (46, 'Song of Everlasting Fervor', 37)]],
                          1021, 'mi-fervor', Type='CombatSpeedBuff', Target='Group', Duration=15, Range=2000, CastTime=2.0, Power=0,
                          RecastDelay=0)),
    ('Bard Nurture Spec', [
        *ranks([(lv, name, dict(Value=v)) for lv, name, v in [(5, 'Whisper of Hibernia', 1), (15, 'Whisper of Earth', 2), (25, 'Whisper of Nature', 3),
                                                             (35, 'Whisper of the World', 4), (45, 'Whisper of the Cosmos', 5)]],
               1081, 'bd-whisper', Type='EnduranceRegenBuff', Target='Self', Duration=1200, Range=0, CastTime=3.0, Power=0, RecastDelay=0),
        *ranks([(27, 'Hymn of Soul Guarding', dict(Value=8)), (46, 'Hymn of Soul Protection', dict(Value=12))], 1031, 'bd-hymn',
               Type='BodySpiritEnergyBuff', Target='Realm', Duration=30, Range=1500, CastTime=4.0, Power=0, RecastDelay=0),
    ]),
    ('Nurture Warden Spec', ranks([(22, 'Glimmer Shield', dict(Value=12)), (32, 'Glimmer Guard', dict(Value=18)), (43, 'Glimmer Barrier', dict(Value=24))],
                                  1031, 'wd-glimmer', Type='BodySpiritEnergyBuff', Target='Group', Duration=30, Range=2000, CastTime=3.0,
                                  Power=0, RecastDelay=0)),
    ('Friar Enhancement Spec', [
        single(20, 'Sharpness', 1021, Type='EvadeBuff', Target='Group', Value=15, Duration=20, Range=200, CastTime=0, RecastDelay=60, Power=0),
        single(2, "Saint's Resolve", 1081, Type='FatigueConsumptionBuff', Target='Group', Value=5, Pulse=1, Frequency=50, Duration=5,
               Range=1500, CastTime=0, RecastDelay=8, Power=0, PulsePower=0),
        dict(level=50, name='Tranquility', art=1081, family=None,
             parent=dict(Type='TimedPulseArea', Target='Self', LifeDrainReturn=0, Radius=1500, Value=0, Duration=15, Frequency=10, CastTime=0,
                         RecastDelay=600, Power=0, Range=0),
             children=[dict(Type='Heal', Target='Realm', Value=-5, Range=0)]),
    ]),
    ('Runes of Darkness (Live)', ranks([(lv, name, dict(Value=v)) for lv, name, v in [
        (7, 'Dusk Empowerment', 1), (16, 'Gloom Empowerment', 2), (26, 'Murk Empowerment', 3), (36, 'Freezing Empowerment', 4),
        (45, 'Runic Empowerment', 5)]], 1031, 'rm-empowerment', Type='SpellCritAura', Target='Group', Pulse=1, Frequency=50, Duration=6,
        Range=1500, CastTime=3.0, RecastDelay=5, Power=0, PulsePower=0)),
    ('Domination (Live)', [
        single(48, 'Forced Trance', 30001, Type='Mesmerize', Target='Enemy', Duration=30, Range=1500, CastTime=0, RecastDelay=600, Power=0,
               DamageType=SPIRIT),
        single(50, 'Mindfulness', 1081, Type='ResetQuickcast', Target='Self', Range=0, CastTime=0, RecastDelay=60, Power=0),
    ]),
    ('Mind Twisting (Live)', [single(40, 'Mass Gateway', 1081, Type='GroupBindRecall', Target='Group', Radius=1000, Range=0, CastTime=42.0,
                                     RecastDelay=0, Power=0)]),
    ('Cursing (Live)', [single(19, 'Conjured Bubble', 1001, Type='Bladeturn', Target='Self', Duration=1200, Range=0, CastTime=4.0, Power=0,
                               RecastDelay=0)]),
    ('Battlesongs', ranks([(27, 'Disorienting Yelp', dict(Value=85, Radius=500, RecastDelay=90)),
                           (47, 'Disorienting Cry', dict(Value=100, Radius=750, RecastDelay=60))],
                          30001, 'sk-disorient', Type='Confusion', Target='Enemy', Duration=20, Range=0, CastTime=0, Power=0, DamageType=SPIRIT)),
    ('Chants', [single(lv, name, 1081, f'pa-cure-{kind}', Type=kind, Target='Realm', Radius=350, Range=0, CastTime=0, RecastDelay=45,
                       SharedTimerGroup=77898, Power=0)
                for lv, name, kind in [(30, 'Cure of the Righteous', 'CurePoison'), (40, 'Cure of the Virtuous', 'CureDisease'),
                                       (50, 'Cure of the Faithful', 'CureAll')]]),
    ('Bone Army (Commanders)', [single(50, 'Dread Charge', 1021, Type='SpeedEnhancement', Target='Pet', Value=165, Duration=10, Range=2000,
                                       CastTime=0, RecastDelay=90, Power=-10)]),
    # Sixth pass (Codex all-class audit).
    ('Shadow Control (Live)', ranks([(20, 'Crumble Spirit', dict(Value=15, Power=10)), (30, 'Fade Spirit', dict(Value=30, Power=16)),
                                     (40, 'Vanquish Spirit', dict(Value=40, Power=24))],
                                    30001, 'el-spirit', Type='SpiritResistDebuff', Target='Enemy', Duration=15, Range=1500, CastTime=0,
                                    RecastDelay=30, DamageType=SPIRIT)),
    ('Vacuumancy (Live)', [detonate(50, 'Mana Deluge', ENERGY)]),
    ('Guardian Angel', [single(41, 'Hand of God', 1001, Type='DamageReduction', Target='Realm', Value=50, Duration=10, Range=1500,
                               CastTime=2.5, RecastDelay=60, Power=-25)]),
    ('Terrible Hammer', [
        single(13, 'Blessing of Movement', 1081, Type='CureRoot', Target='Realm', Range=1500, CastTime=10.0, RecastDelay=300, Power=-10),
        single(50, 'Ascendance', 1021, Type='MeleeDamageBuff', Target='Self', Value=100, Duration=25, Range=0, CastTime=0, RecastDelay=600,
               Power=0),
    ]),
    ('Subterranean Incantations', [single(5, 'Induce Ailment', 30003, Type='Disease', Target='Enemy', Duration=20, Range=1500, CastTime=3.0,
                                          Power=4, DamageType=BODY, RecastDelay=0)]),
    ('Subterranean Spec', ranks([(9, 'Warding Aid', dict(Value=20, CastTime=3.2)), (19, 'Warding Favor', dict(Value=50, CastTime=3.0)),
                                 (29, 'Warding Boon', dict(Value=145, CastTime=2.8)), (39, 'Warding Dispensation', dict(Value=160, CastTime=2.6)),
                                 (49, 'Warding Tribute', dict(Value=205, CastTime=2.5))],
                                1081, 'sh-warding', Type='Heal', Target='Group', Range=1875, Power=-25, RecastDelay=0)),
    ('Stormcalling', [single(32, 'Gift of Lightning', 1021, Type='MeleeDamageTypeAura', Target='Realm', Duration=60, Range=1500, CastTime=2.4,
                             Power=-10, Radius=0, DamageType=ENERGY, RecastDelay=0)]),
    # Seventh pass (owner: "start on all of the not built items"). Unshakable Cast was already built as "Unshakeable Cast"
    # (66015, local-warlock-test-v1).
    *[(line, ranks(rows, 955, family, Type='Charm', Target='Enemy', Range=1000, CastTime=4.0, Power=-25, Damage=100, Duration=65535,
                   AmnesiaChance=0, DamageType=ENERGY, RecastDelay=0))
      for line, family, rows in [
          ('Spirit Dimming', 'sm-hel-charm', [(12, "Hel's Control", dict(Value=26)), (26, "Hel's Possession", dict(Value=40)),
                                              (34, "Hel's Domination", dict(Value=50))]),
          ('Illusions', 'mt-adversary', [(11, 'Phantom Adversary', dict(Value=26)), (20, 'Ghostly Adversary', dict(Value=40)),
                                         (32, 'Dream Adversary', dict(Value=50))]),
          ('Instruments', 'mi-harmony', [(11, 'Engaging Harmony', dict(Value=26)), (21, 'Engrossing Harmony', dict(Value=40)),
                                         (31, 'Enthralling Harmony', dict(Value=50))])]],
    ('Friar Enhancement Spec', ranks([(6, 'Imbue Lesser Haste', dict(Value=8, Concentration=1)),
                                      (16, 'Imbue Greater Haste', dict(Value=12, Concentration=7)),
                                      (26, 'Imbue Lesser Alacrity', dict(Value=15, Concentration=11)),
                                      (36, 'Imbue Alacrity', dict(Value=17, Concentration=14)),
                                      (46, 'Imbue Greater Alacrity', dict(Value=20, Concentration=19))],
                                     5051, 'fr-imbue', Type='CombatSpeedBuff', Target='Realm', Range=1500, CastTime=3.5, Power=0, Duration=0,
                                     EffectGroup=100, Uninterruptible=1, RecastDelay=0)),
    *[(line, [single(lv, 'Confounding Cast', 5351, Type='Confusion', Target='Enemy', Value=70, Duration=15, Range=1500, CastTime=2.5, Power=31,
                     DamageType=SPIRIT, RecastDelay=0)])
      for line, lv in [('Healer Mending Spec', 35), ('Rebirth', 40), ('Regrowth Warden Spec', 40)]],
    ('Enchantment Mastery (Live)', [
        dict(level=16, name='Enchantment of Stone', art=1001, family=None,
             parent=dict(Type='MeleeDamageTypeAura', Target='Group', Range=4000, Duration=30, CastTime=2.3, Power=-30, DamageType=MATTER,
                         RecastDelay=0, SubSpellID='child:0'),
             children=[dict(Type='ArmorFactorBuff', Name='Stone Skin', Target='Group', Value=300, Duration=30, Range=4000)]),
        dict(level=26, name='Enchantment of Fire', art=1021, family=None,
             parent=dict(Type='MeleeDamageTypeAura', Target='Group', Range=4000, Duration=30, CastTime=2.3, Power=-30, DamageType=HEAT,
                         RecastDelay=0, SubSpellID='child:0'),
             children=[dict(Type='MeleeDamageBuff', Name='Burning Fury', Target='Group', Value=25, Duration=30, Range=4000)]),
        single(46, 'Enchantment of Truth', 1021, Type='MeleeTruth', Target='Group', Range=4000, Duration=15, CastTime=2.3, Power=-30,
               RecastDelay=0),
        single(50, 'Enchantment of Zeal', 1081, Type='StyleZeal', Target='Group', Value=3, Range=4000, Duration=30, CastTime=10.0, Power=-30,
               RecastDelay=600),
    ]),
    ('Druid Nature Spec', [single(50, 'Heart of Nature', 30022, Type='HeartOfNature', Target='Group', Range=2000, Radius=200, Duration=15,
                                  CastTime=0, RecastDelay=600, Power=-25)]),
    ('Soulrending', [single(39, 'Malefic Horror', 30001, Type='MaleficHorror', Target='Enemy', Radius=350, Range=0, Duration=15, CastTime=0,
                            RecastDelay=300, Power=-5, DamageType=SPIRIT)]),
    *[(line, [single(39, 'Overshadow', 1001, Type='AllyStealth', Target='Realm', Range=1000, Duration=10, CastTime=0, RecastDelay=180, Power=0)])
      for line in ['Infiltrator Stealth', 'Nightshade Stealth', 'Shadowblade Stealth']],
    *[(line, [single(40, 'Siegebreaker', 1021, Type='Siegebreaker', Target='Group', Damage=20, Range=2000, Radius=150, Duration=15, CastTime=0,
                     RecastDelay=90, Power=0)])
      for line in ['Valor', 'Battlesongs', 'Instruments']],
    ('Mind Mastery (Live)', [dict(level=49, name='Speedwarp', art=30001, family=None,
                                  parent=dict(Type='TimedPulseArea', Target='Enemy', LifeDrainReturn=2, Radius=2000, Range=50, Duration=300,
                                              Frequency=10, Value=0, CastTime=0, RecastDelay=300, Power=0),
                                  children=[dict(Type='Speedwarp', Target='Enemy', Duration=2, Range=0, DamageType=SPIRIT)])]),
    ('Stormcalling', [single(49, 'Chain Lightning', 2501, Type='ChainDirectDamage', Target='Enemy', Damage=round(4000 * DD, 1),
                             DamageType=ENERGY, Range=1875, CastTime=0, RecastDelay=600, Power=0, Uninterruptible=1)]),
    ('Liquifaction (Live)', [single(44, 'Ice Grip', 30022, Type='IceGrip', Target='Enemy', Range=1500, Duration=6, CastTime=3.0, RecastDelay=300,
                                    Power=0, DamageType=COLD)]),
    ('Pyromancy (Live)', [single(45, 'Flame Cocoon', 1001, Type='FlameCocoon', Target='Self', Value=200, Frequency=15, Duration=7, Range=0,
                                 CastTime=0, RecastDelay=300, Power=0, DamageType=HEAT)]),
    ('Warrior Shields (Live)', [single(50, 'Battle Control', 1001, Type='BattleControl', Target='Self', Value=5, Radius=400, Range=0,
                                       Duration=8, CastTime=0, RecastDelay=600, Power=0)]),
    ('Subterranean Spec', [dict(level=50, name='Blight Surge', art=30003, family=None,
                                parent=dict(Type='BlightSurge', Target='Self', Value=3, Damage=50, Radius=250, Duration=10, Frequency=20,
                                            Range=0, CastTime=0, RecastDelay=600, Power=0, LifeDrainReturn='child:0', DamageType=MATTER),
                                children=[dict(Type='DirectDamage', Name='Blight', Target='Enemy', Damage=50, DamageType=MATTER, Range=0,
                                               SubSpellID='child:1'),
                                          dict(Type='Disease', Name='Blight Sickness', Target='Enemy', Duration=10, Range=0,
                                               DamageType=BODY)])]),
    # The stock world's unused "greater ice elemental" (template 25), shaped like its Ice/Aged Ice Elemental siblings (266/267)
    # but at live's 1,875 range.
    ('Refrigeration', [single(48, 'Summon Greater Ice Elemental', 267, Type='SummonTheurgistPet', Target='Enemy', LifeDrainReturn=25, Value=50,
                              Damage=-88, Duration=25, CastTime=3.0, Power=-12, Range=1875, RecastDelay=0, ResurrectHealth=-88,
                              ResurrectMana=44, AmnesiaChance=25)]),
    # Pets (PETS-PROPOSAL-2026-10-25.md). The pets' own spells are live's (the client spell map, by delve_spell).
    ('Arboreal Mastery', [
        *[bomber(lv, name, 11130, Power=50, CastTime=5.0, Range=1875, Duration=300, RecastDelay=120, child=round(d * DD, 1), kind=BODY)
          for lv, name, d in [(13, 'Heavy Spirit', 1349), (23, 'Plump Spirit', 1999), (33, 'Inflated Spirit', 2699), (45, 'Bulging Spirit', 4499)]],
        main_pet(40, 'Guardian of the Forest', 11129, 77910, 11158),
    ]),
    ('Creeping Path Spec (Live)', [
        *[bomber(lv, name, 11457, Power=power, CastTime=2.8, Range=1500, Duration=20, RecastDelay=0, child=round(d * DD, 1), kind=MATTER)
          for lv, name, power, d in [(7, 'Spirit of Deceit', 5, 344), (16, 'Spirit of Cunning', 10, 684), (27, 'Spirit of Trickery', 13, 1224),
                                     (38, 'Spirit of Deception', 25, 1534), (47, 'Spirit of Guile', 31, 1994)]],
        *[turret(lv, name, 11443, template, power, Range=1000,
                 child=dict(Type='Disease', Name=spores, Target='Enemy', Range=850, CastTime=4.0, Duration=duration, DamageType=MATTER,
                            SubSpellID='child:1'),
                 dot=dict(Type='DamageOverTime', Name=spores, Target='Enemy', Range=850, Damage=damage, Duration=duration, Frequency=40,
                          DamageType=MATTER))
          for lv, name, template, power, spores, duration, damage in [
              (5, "Forest's Blight", 77900, 8, 'Blight Spores', 15, 6), (14, "Forest's Curse", 77901, 16, 'Curse Spores', 15, 6),
              (20, "Forest's Scourge", 77902, 34, 'Scourge Spores', 30, 9), (31, "Forest's Torment", 77903, 50, 'Torment Spores', 30, 12),
              (41, "Forest's Menace", 77904, 65, 'Menace Spores', 30, 15)]],
        *[turret(lv, name, 11350, template, power, Range=1500,
                 child=dict(Type='Heal', Name=heal_name, Target='Realm', Range=850, CastTime=4.0, Value=heal))
          for lv, name, template, power, heal_name, heal in [
              (9, 'Grove Sibyl', 77905, 16, 'Forest Resurgance', 20), (21, 'Grove Augur', 77906, 38, 'Forest Restoration', 55),
              (32, 'Grove Oracle', 77907, 50, 'Forest Renascence', 100), (42, 'Grove Druid', 77908, 65, 'Forest Revivify', 215)]],
        turret(50, 'Shroom of Life', 11350, 77909, -25, Range=1500, Duration=10, CastTime=0, RecastDelay=300,
               child=dict(Type='HealOverTime', Name="Forest's Grace", Target='Realm', Range=350, Radius=350, Value=400, Duration=15,
                          Frequency=30)),
        main_pet(40, 'Heart of the Grove', 11469, 77911, 11434),
    ]),
    ('Verdant Path Spec (Live)', [main_pet(40, 'Harbinger of War', 11677, 77912, 11669)]),
    ('Summoning (Live)', [single(lv, name, 2805, 'sm-spirit', Type='SummonSpiritFighter', Target='Self', LifeDrainReturn=template, Value=50,
                                Damage=-100, Duration=65535, CastTime=6.0, Power=-40, Range=0, RecastDelay=0)
                         for lv, name, template in [(11, 'Spirit Hunter', 77913), (21, 'Spirit Runemaster', 77914), (31, 'Spirit Shaman', 77915),
                                                    (41, 'Spirit Valkyrie', 77916), (50, 'Spirit Warrior', 77917)]]),
    ('Spirit Enhancement (Live)', [dict(level=50, name='Gates of Valhalla', art=2805, family=None,
                                        parent=dict(Type='TimedPulseArea', Target='Self', LifeDrainReturn=2, Radius=1500, Range=1500, Duration=60,
                                                    Frequency=120, Value=1, CastTime=8.0, RecastDelay=600, Power=-25),
                                        children=[dict(Type='SummonTheurgistPet', Name='Fallen Einherjar', Target='Enemy', Range=1500,
                                                       Duration=15, Value=50, Damage=-100, LifeDrainReturn=77918, CastTime=0, Power=0)])]),
    ('Druid Nature Magic', [single(lv, name, 5255, None, Type='SummonDruidPet', Target='Self', LifeDrainReturn=template, Value=cap,
                                   Damage=-percent, Duration=65535, CastTime=6.0, Power=-25, Range=0, RecastDelay=0)
                            for lv, name, template, cap, percent in [(31, 'Summon Grove Guardian', 77919, 34, 75),
                                                                     (40, 'Summon Grove Protector', 77920, 40, 80)]]),
    ('Druid Nature Spec', [single(40, 'Call Nature Sage', 5255, Type='SummonDruidPet', Target='Self', LifeDrainReturn=77921, Value=50,
                                  Damage=-100, Duration=65535, CastTime=6.0, Power=-25, Range=0, RecastDelay=0)]),
    ('Enchantment', [single(31, 'Underhill Stalker', 4705, Type='SummonUnderhill', Target='Self', LifeDrainReturn=77922, Value=50, Damage=-100,
                            Duration=65535, CastTime=6.0, Power=-40, Range=0, RecastDelay=0)]),
]


def copy_templates(db):
    """The pet templates: each a copy of its local source with the new ID and name (one ID may hold several variant rows)."""
    db.execute('delete from NpcTemplate where PackageID=?', (PACKAGE,))
    columns = [r[1] for r in db.execute('pragma table_info(NpcTemplate)')]
    for index, (template_id, source, source_name, name) in enumerate(PET_TEMPLATES):
        if db.execute('select 1 from NpcTemplate where TemplateId=? and coalesce(PackageID,"")<>?', (template_id, PACKAGE)).fetchone():
            raise ValueError(f'Template {template_id} is taken')
        rows = db.execute('select * from NpcTemplate where TemplateId=?' + (' and Name=?' if source_name else ''),
                          (source, source_name) if source_name else (source,)).fetchall()
        if len(rows) != 1:
            raise ValueError(f'Template {source} ({source_name}) has {len(rows)} rows')
        row = dict(zip(columns, rows[0]), TemplateId=template_id, Name=name, PackageID=PACKAGE, NpcTemplate_ID=f'{PACKAGE}-pet-{index}')
        db.execute('insert into NpcTemplate (' + ','.join(f'"{c}"' for c in row) + ') values (' + ','.join('?' * len(row)) + ')',
                   list(row.values()))
    return len(PET_TEMPLATES)


def definitions():
    return linked_lines.definitions(__import__(__name__))


def apply(db):
    templates = copy_templates(db)
    return dict(linked_lines.apply(db, __import__(__name__)), round3_pet_templates=templates)
