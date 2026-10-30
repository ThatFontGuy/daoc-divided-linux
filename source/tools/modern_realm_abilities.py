"""Migrate audited shared RAs only; preserve world content and saved characters."""
import json
from pathlib import Path
import sqlite3
from modern_tireless import apply as tireless

KEYS = ('AugStr AugCon AugDex AugQui AugAcuity AoM MasteryOfPain MasteryOfBlocking '
        'MasteryOfParrying MasteryOfHealing MasteryOfMagery WildPower WildHealing '
        'WildMinion FalconsEye VeilRecovery Determination DeterminationHybrid '
        'Toughness EtherealBond FirstAid Serenity Lifter LongWind IgnorePain IgnorePainTank '
        'MCL RagingPower SecondWind Purge PurgeReduced Concentration BunkerOfFaith BrilliantAura '
        'SoldiersBarricade EmptyMind AmelioratingMelodies FuryOfTheGods WrathOfTheChampion VolcanicPillar '
        'NegativeMaelstrom ThornweedField StaticTempest Ichor Viper ReflexAttack MasteryOfConcentration Juggernaut').split()
EXTRA = {
    'Dual Threat': ('ModernDualThreat', 'DualThreatAbility'),
    'Strike Prediction': ('ModernStrikePrediction', 'StrikePredictionAbility'),
    'Vehement Renewal': ('ModernVehementRenewal', 'VehementRenewalAbility'),
    'Mastery of Focus': ('ModernMasteryOfFocus', 'MasteryOfFocusAbility'),
    'Physical Defense': ('ModernPhysicalDefense', 'PhysicalDefenceAbility'),
    'Charge': ('ModernCharge', 'ChargeAbility'),
    'Valkyrie_Charge': ('ModernCharge', 'ValkyrieChargeAbility'),
    'Speed of Sound': ('ModernSpeedOfSound', 'SpeedOfSoundAbility'),
    'Perfect Recovery': ('ModernPerfectRecovery', 'PerfectRecoveryAbility'),
    'Decimation Trap': ('ModernDecimationTrap', 'DecimationTrapAbility'),
    'Adrenaline Rush': ('ModernAdrenalineRush', 'AdrenalineRushAbility'),
    'Dashing Defense': ('ModernDashingDefense', 'DashingDefenseAbility'),
    'Divine Intervention': ('ModernDivineIntervention', 'DivineInterventionAbility'),
    'AtlasOF_MasteryOfStealth': ('ModernMasteryOfStealth', 'MasteryOfStealthAbility'),
    'Vanish': ('ModernVanish', 'VanishAbility'),
}
# Live 1.126: Mastery of Stealth is trainable again for every stealther (assassins and archers).
STEALTH_CLASSES = (3, 9, 23, 25, 49, 50)
# Live 1.123: Vanish left the Stealth spec (where 1.121 had moved it) and is a trainable realm ability again.
ASSASSINS = (9, 23, 49)
RETIRED_RA_KEYS = ('AtlasOF_Vanish',)
# Class-access audit: realm abilities that exist only in the Atlas old-frontiers ruleset. None of them is in the
# live realm-ability tables, so every class loses them, custom classes included. The custom classes keep their own
# unique abilities (Crippling Plague, Valhalla's Blessing, the Sovereign/Pendragon set).
CUSTOM_CLASSES = (34, 63, 64, 65)
OLD_FRONTIERS_ONLY = tuple('AtlasOF_' + key for key in (
    'ArmorOfFaith ArrowSalvaging AvoidPain BatteryOfLife BattleYell Bladedance Dodger DualistsReflexes Grapple '
    'HailOfBlows Longshot MajesticWill MasteryOfArchery MasteryOfArms MasteryOfTheArcane MasteryOfTheArt '
    'MasteryOfWater PreventFlight RainOfAnnihilation RainOfFire RainOfIce Regeneration SeeHidden Trip TrueSight '
    'Volley WhirlingDervish WildArcana').split())
# Atlas's single-class actives, which stood in for the live class RR5 abilities.
ATLAS_CLASS_ACTIVES = tuple('AtlasOF_' + key for key in (
    'CorporealDisintegration DefenderOfTheVale ExcitedFrenzy FaithHealing ForestheartAmbusher GroupPurge '
    'ResilienceOfDeath RuneOfDecimation SeveringTheTether ShadowRun SiegeBolt StrikingTheSoul StyleDoombringer '
    'StyleRavager StyleRazorback StyleTundra StyleVoid StyleWinterMoon UnquenchableThirst WhipOfEncouragement').split())
AUDIT_REMOVED = OLD_FRONTIERS_ONLY + ATLAS_CLASS_ACTIVES
# The custom classes have no live counterpart. After losing the old-frontiers passives they get the live shared
# picks of their nearest live hybrids. The Valkyrie (34) already matches live (EoD plus the 1.128 Ichor/Tempest
# moves) and needs nothing.
_SOVEREIGN = ('Dual Threat', 'Mastery of Focus', 'AtlasOF_MasteryOfConcentration', 'AtlasOF_RagingPower', 'AtlasOF_WrathOfTheChampion')
CUSTOM_ADDITIONS = {
    # Sluaghbinder: STR/INT melee and pet hybrid, compared with Champion and Valewalker.
    63: ('Dual Threat', 'Mastery of Focus', 'AtlasOF_MasteryOfMagery', 'AtlasOF_WildPower', 'AtlasOF_EtherealBond',
         'AtlasOF_MCL', 'AtlasOF_RagingPower', 'AtlasOF_MasteryOfConcentration', 'AtlasOF_MasteryOfParrying'),
    # Storm Sovereign and Pendragon Sovereign: melee, spell and stealth hybrids, compared with Thane and Paladin.
    64: _SOVEREIGN,
    65: _SOVEREIGN,
}
# Live class RR5 abilities, free at realm rank 5, bound once their handler is audited against live and its patches.
# Batch 1: self-buffs. Later batches add the remaining live RR5s.
RR5_BINDINGS = {
    'Ferocious Will': 31,       # Berserker
    'Blade Barrier': 43,        # Blademaster
    'Rune of Utter Agility': 29,  # Runemaster
    'Combat Awareness': 44,     # Hero
    "Soldier's Citadel": 2,     # Armsman
    'Testudo': 22,              # Warrior
    'Shield of Immunity': 8,    # Sorcerer
    'Arms Length': 40,          # Eldritch
    # Current live replacements built as modern handlers (ModernRr5Abilities.cs).
    'Dissolute Swings': 11,     # Mercenary (replaced Blinding Dust)
    'Fueled by Rage': 32,       # Savage (replaced Blissful Ignorance, then Frenzied Assault)
    'Frenzy of the Underhill': 41,  # Enchanter (replaced Searing Pet)
    'Restorative Mend': 28,     # Shaman
    'Far Sight': 3,             # Scout (replaced Shield Trip)
    'Bestial Heart': 25,        # Hunter (replaced Entwining Snakes)
    "Nature's Madness": 50,     # Ranger (replaced Desperate Bowman)
    'Voice of Skadi': 24,       # Skald (replaced Epiphany)
    "Mjollnir's Protection": 21,  # Thane (replaced Chain Lightning)
    # Batch 3: audited legacy handlers with live value fixes.
    'Fungal Union': 55,         # Animist
    'Allure of Death': 30,      # Bonedancer
    'Dreamweaver': 48,          # Bard
    'Selective Blindness': 42,  # Mentalist
    'Overwhelm': 9,             # Infiltrator
    'Shadow Shroud': 49,        # Nightshade
    'Blooddrinking': 23,        # Shadowblade
    # Batch 3: NF-era RR5s rebuilt as modern handlers (ModernRr5ClassicAbilities.cs).
    'Vale Defense': 56,         # Valewalker
    'Fanaticism': 33,           # Heretic
    'Selfless Devotion': 1,     # Paladin
    "Sputin's Legacy": 26,      # Healer
    'Spirit Martyr': 27,        # Spiritmaster
    'Fury of Nature': 46,       # Warden
    'Retribution of the Faithful': 6,  # Cleric
    'Mark of Prey': 58,         # Vampiir
    'Calming Notes': 4,         # Minstrel
    'Sonic Barrier': 39,        # Bainshee
    'Soul Quench': 19,          # Reaver
    'Wall of Flame': 7,         # Wizard
    'Whirling Staff': 10,       # Friar
    "Nature's Womb": 47,        # Druid
    'Resolute Minion': 13,      # Cabalist
    'Badge of Valor': 45,       # Champion
    'Boiling Cauldron': 59,     # Warlock (1.128 and 1.129b rework)
}
# Not bound yet: Necromancer (needs the 1.122b form system), Theurgist Minion Rescue (summons) and the Maulers
# (Gift of Perizor became a spec spell in 1.123).
# Warlock realm abilities added on live after the pinned baseline.
WARLOCK_LIVE_RAS = (
    'AtlasOF_MasteryOfConcentration',  # 1.114b
    'AtlasOF_MasteryOfHealing',        # 1.116
    'AtlasOF_WildHealing',             # 1.116
    'AtlasOF_Ichor',                   # 1.121 (1.128 removed it from Minstrel and Valkyrie only)
)
# Ability rows for the live replacements: (handler, private internal ID or None to keep, icon, description).
MODERN_RR5_ROWS = {
    'Dissolute Swings': ('ModernDissoluteSwings', 3041, 3039, '30 seconds: deal 25% more damage and take 25% more damage from all sources. Clears stat debuffs and blocks new ones. 10-minute reuse.'),
    'Fueled by Rage': ('ModernFueledByRage', 3042, 3068, '30 seconds: take 20% less damage; half of the prevented damage heals you. 10-minute reuse.'),
    'Frenzy of the Underhill': ('ModernFrenzyOfTheUnderhill', 3043, 3063, "30 seconds: your pet's melee attack speed and casting speed are increased by 100%. 5-minute reuse."),
    'Restorative Mend': ('ModernRestorativeMend', None, 3070, 'Group within 2000: restores 15% health, power and endurance every 2 seconds for 20 seconds, in or out of combat. 10-minute reuse.'),
    'Far Sight': ('ModernFarSight', 3044, 3045, 'Clears range-impairing effects and grants 60 seconds of nearsight immunity. For 30 seconds archery and spell range are increased by 20% and standard shots apply a 20-second 50% nearsight. Removes stealth. 10-minute reuse.'),
    'Bestial Heart': ('ModernBestialHeart', 3045, 3071, 'Shapeshift into a Dire Wolf for 30 seconds: +15% melee damage, +40% attack speed, +115% run speed, and melee attacks inflict disease. The bow cannot be used. Removes stealth. 10-minute reuse.'),
    "Nature's Madness": ('ModernNaturesMadness', 3046, 3060, 'Places a 30-second storm at your feet: enemies within 500 attack and cast 30% slower, and enemy pets inside flee in terror. Removes stealth. 10-minute reuse.'),
    'Voice of Skadi': ('ModernVoiceOfSkadi', 3047, 3065, '15 seconds of immunity to crowd control. 5-minute reuse.'),
    "Mjollnir's Protection": ('ModernMjollnirsProtection', 3048, 3066, 'Group within 2000: for 60 seconds absorbs 50% of spell damage taken, up to 1500 damage each. 10-minute reuse.'),
    # Legacy assassin handlers (1.108) that never had rows.
    'Overwhelm': ('OverwhelmAbility', 3049, 1841, 'For 30 seconds, +10% chance to bypass your target\'s block, parry and evade. 5-minute reuse.'),
    'Shadow Shroud': ('ShadowShroudAbility', 3050, 1842, 'For 30 seconds, take 10% less damage and gain a 10% chance to be missed. 10-minute reuse.'),
    'Blooddrinking': ('BloodDrinkingAbility', 3051, 1843, 'For 15 seconds, heal for 45% of the damage you deal. 5-minute reuse.'),
    # NF-era RR5s rebuilt as modern handlers; existing rows are repointed.
    'Vale Defense': ('ModernValeDefense', None, 3062, 'Group within 2000: a 1000-point, 50% ablative for 10 minutes; the Valewalker\'s own ablative holds 2000 points. 10-minute reuse.'),
    'Fanaticism': ('ModernFanaticism', None, 3087, 'Group within 2000: 25% less spell damage taken for 15 seconds. 10-minute reuse.'),
    'Selfless Devotion': ('ModernSelflessDevotion', None, 3038, 'Every 3 seconds for 15 seconds: heals you for 100 and groupmates within 750 for 300 (groups of 2-5) or 500 (6 or more). 10-minute reuse.'),
    "Sputin's Legacy": ('ModernSputinsLegacy', None, 3069, '20 seconds: a killing blow heals you for at least 30% instead. When it fires or expires you gain 5 seconds of damage and crowd-control immunity. 15-minute reuse.'),
    'Spirit Martyr': ('ModernSpiritMartyr', None, 3074, 'Sacrifices your pet to heal the group from a pool of up to 3200 (scaled by the pet\'s health), at most 600 per member. 10-minute reuse.'),
    'Fury of Nature': ('ModernFuryOfNature', None, 3053, '15 seconds: style damage is doubled and all weapon damage you deal heals your group (not you). 10-minute reuse.'),
    'Retribution of the Faithful': ('ModernRetributionOfTheFaithful', None, 3041, '30 seconds: melee attacks on you have a 50% chance to stun the attacker for 3 seconds. 5-minute reuse.'),
    'Mark of Prey': ('ModernMarkOfPrey', None, 3089, 'Group within 2000: a 30-second damage add that returns its damage to you as power, plus +20% melee and spell critical chance. 10-minute reuse.'),
    'Calming Notes': ('ModernCalmingNotes', None, 3044, 'Mesmerizes every enemy within 750 for 20 seconds. 5-minute reuse.'),
    'Sonic Barrier': ('ModernSonicBarrier', None, 3088, 'Group within 2000, including you: armor absorption is doubled for 45 seconds. 10-minute reuse.'),
    'Soul Quench': ('ModernSoulQuench', None, 3040, 'Drains about 200 health (scaled by Soulrending) from every enemy within 350 and returns 75% of it to you. 10-minute reuse.'),
    'Wall of Flame': ('ModernWallOfFlame', None, 3049, 'Drops a ward that deals 400 heat damage to enemies within 150 every 3 seconds for 15 seconds, while you keep a refreshing 700-point ablative. 10-minute reuse.'),
    'Whirling Staff': ('ModernWhirlingStaff', None, 3042, 'Deals 251 crush damage to every enemy within 350; they cannot attack for 6 seconds. 10-minute reuse.'),
    "Nature's Womb": ('ModernNaturesWomb', None, 3052, '5 seconds: you are silenced and all damage you take heals you instead. 10-minute reuse.'),
    'Resolute Minion': ('ModernResoluteMinion', None, 3046, 'Your pet is immune to crowd control for 60 seconds. Effects already on it remain. 10-minute reuse.'),
    'Boiling Cauldron': ('ModernBoilingCauldron', None, 3085, 'A cauldron at your target spills after 3.5 seconds: 650 heat damage to up to 8 enemies within 350, who are bedazzled for 20 seconds (30% chance to fumble melee attacks or miscast spells). 10-minute reuse.'),
    'Badge of Valor': ('ModernBadgeOfValor', None, 3056, '20 seconds: your target\'s armor absorption increases your melee damage instead of reducing it. 10-minute reuse.'),
}
# Single-rank Atlas versions replaced by the live five-rank key for the same class.
REPLACED_ATLAS = {'AtlasOF_SpeedOfSound': 'Speed of Sound', 'AtlasOF_PerfectRecovery': 'Perfect Recovery'}

def apply(db):
    db.row_factory = sqlite3.Row
    changed = []
    for key in KEYS:
        row = db.execute('select Implementation from Ability where KeyName=?', ('AtlasOF_'+key,)).fetchone()
        if row is None:
            raise ValueError('Missing ability: '+key)
        handler = 'DOL.GS.RealmAbilities.Modern'+key
        if row[0] != handler:
            if not row[0].startswith('DOL.GS.RealmAbilities.AtlasOF_'):
                raise ValueError('Unexpected implementation: '+key)
            changed.append('AtlasOF_'+key)
    if db.execute("select 1 from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_AvoidanceOfMagic'").fetchone():
        changed.append('AtlasOF_AvoidanceOfMagic')
    for key, (handler, old) in EXTRA.items():
        row = db.execute('select Implementation from Ability where KeyName=?', (key,)).fetchone()
        if row is None or row[0] not in ('DOL.GS.RealmAbilities.'+handler, 'DOL.GS.RealmAbilities.'+old):
            raise ValueError('Unexpected shared RA definition: '+key)
        if row[0] != 'DOL.GS.RealmAbilities.'+handler:
            changed.append(key)
    for atlas in REPLACED_ATLAS:
        if db.execute('select 1 from ClassXRealmAbility_Atlas where AbilityKey=?', (atlas,)).fetchone():
            changed.append(atlas)
    for key in RETIRED_RA_KEYS:
        if db.execute('select 1 from ClassXRealmAbility_Atlas where AbilityKey=?', (key,)).fetchone():
            changed.append(key)
    custom = ','.join(str(cls) for cls in CUSTOM_CLASSES)
    for key in AUDIT_REMOVED:
        scope = '' if key in OLD_FRONTIERS_ONLY else ' and CharClass not in (%s)' % custom
        if db.execute('select 1 from ClassXRealmAbility_Atlas where AbilityKey=?' + scope, (key,)).fetchone():
            changed.append(key)
    # A new cost table must not silently change an existing player's allocation.
    # Keep this migration non-destructive; an occupied old allocation requires a separate refund migration.
    if changed and db.execute("select 1 from sqlite_master where type='table' and name='DOLCharacters'").fetchone():
        for row in db.execute("select SerializedRealmAbilities from DOLCharacters where coalesce(SerializedRealmAbilities,'')<>''"):
            if any(part.split('|')[0] in changed for part in row[0].split(';')):
                raise ValueError('Existing old RA purchases need a refund migration before changing costs')
    summary = tireless(db)
    free_charge_removed = db.execute("delete from SpecXAbility where AbilityKey='Charge' and Spec in ('BerserkerCareer','MercenaryCareer','BlademasterCareer','SavageCareer')").rowcount
    for key in KEYS:
        db.execute('update Ability set Implementation=? where KeyName=?',
                   ('DOL.GS.RealmAbilities.Modern'+key, 'AtlasOF_'+key))
    for key, (handler, _) in EXTRA.items():
        db.execute('update Ability set Implementation=? where KeyName=?', ('DOL.GS.RealmAbilities.'+handler,key))
    db.execute("update Ability set Description='Increases maximum health by a flat amount: 25/50/75/100/150/200/250/325/400.' where KeyName='AtlasOF_Toughness'")
    db.execute("update Ability set Description='Increases maximum power by a flat amount: 15/25/40/55/75/100/130/165/200.' where KeyName='AtlasOF_EtherealBond'")
    db.execute("update Ability set Description='Out-of-combat self heal: 25/30/35/42.5/50 percent. Reuse: 600/450/300/240/180 seconds.' where KeyName='AtlasOF_FirstAid'")
    for key, name in [('AtlasOF_BunkerOfFaith','Barrier of Fortitude'),('AtlasOF_BrilliantAura','Bedazzling Aura'),('AtlasOF_FuryOfTheGods','Anger of the Gods'),('AtlasOF_WrathOfTheChampion','Wrath of Champions')]:
        db.execute('update Ability set Name=? where KeyName=?',(name,key))
    descriptions = {
        'AtlasOF_Viper':'Passive poison damage bonus: 25/35/50/75/100 percent. No activation timer.',
        'AtlasOF_ReflexAttack':'Passive 10/20/30/40/50 percent chance to counter damaging melee hits with unstyled attacks.',
        'AtlasOF_MasteryOfConcentration':'30 seconds of uninterrupted casting at 25/35/50/60/75 percent spell effectiveness. 600-second reuse.',
        'AtlasOF_Juggernaut':'Raises your pet by 10/15/20/25/30 levels for 60 seconds, capped at 70. 900-second reuse.',
        'Dual Threat':'Passive melee and spell critical chance bonus: 5/7/10/15/20 percent. Does not increase heal critical chance.',
        'Strike Prediction':'30-second group minimum evade chance: 5/7/10/15/20 percent, without adding to a higher existing chance.',
        'Speed of Sound':'Group and pets within 2000 move at speed 4 for 10/20/30/45/60 seconds, immune to stun, mez, snare and root. Each member effect ends when that member attacks or cast a harmful spell; healing does not break it. 600-second reuse.',
        'Perfect Recovery':'Instantly resurrects a dead realm mate at 10/25/50/75/100 percent health and power with no resurrection illness. 300-second reuse.',
        'Decimation Trap':'2-second uninterruptible cast. Places a trap that deals 300/450/600/750/900 energy damage in a 350 radius around the first enemy to approach. Lasts 10 minutes or until detonated. 900-second reuse.',
        'Adrenaline Rush':'Doubles base melee damage for 20 seconds. Reuse: 1200/900/600/450/300 seconds.',
        'Dashing Defense':'You block and parry for groupmates within 1000 for 10/20/30/45/60 seconds, using your own block and parry chances. Each attack can only be blocked or parried this way once. 600-second reuse.',
        'AtlasOF_MasteryOfStealth':'Passive. While stealthed: +10/15/20/25/30/35/40/45/50 percent movement speed and +75/125/175/235/300/375/450/535/625 stealth detection range. Camouflage counters the detection bonus, and it does not apply when both sides have Detect Hidden.',
        'Vanish':'Instantly hides you in unbreakable stealth, purging damage over time, bleeds and crowd control, with crowd-control immunity for 3/3/4/5/6 seconds at normal speed, speed 1, speed 3, speed 4 and speed 5. Cures poisons when it ends. You cannot attack or cast for 30 seconds. 900-second reuse.',
        'Divine Intervention':'Groupmates within 2000 (not you) share a 20-minute healing pool of 1000/1500/2000/2500/3000. Combat damage they take is healed from the pool at once. 600-second reuse.'
    }
    for key,description in descriptions.items():
        db.execute('update Ability set Description=? where KeyName=?',(description,key))
    access = json.loads(Path(__file__).with_name('modern-ra-shared-access.json').read_text(encoding='utf-8'))
    inserted = 0
    for cls, key in access['bindings']:
        # Custom classes keep their existing access and private abilities.
        if not db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?', (cls,key)).fetchone():
            db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                       (cls,key,'modern-shared-'+str(cls)+'-'+key))
            inserted += 1
    # The existing world uses a second key for the same resist RA. Keep one
    # trainable definition per class, including the custom classes, to prevent stacking.
    for row in db.execute("select CharClass from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_AvoidanceOfMagic'").fetchall():
        cls = row[0]
        if not db.execute("select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey='AtlasOF_AoM'", (cls,)).fetchone():
            db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                       (cls,'AtlasOF_AoM','modern-aom-alias-'+str(cls)))
    db.execute("delete from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_AvoidanceOfMagic'")
    # Modern costs are identical for the old reduced/tank variants. Keep the
    # existing class key so saved cooldowns remain applicable after conversion.
    for alias, canonical in [('AtlasOF_PurgeReduced','AtlasOF_Purge'),('AtlasOF_IgnorePainTank','AtlasOF_IgnorePain')]:
        db.execute('delete from ClassXRealmAbility_Atlas where AbilityKey=? and CharClass in (select CharClass from ClassXRealmAbility_Atlas where AbilityKey=?)', (canonical,alias))
    db.execute("delete from ClassXRealmAbility_Atlas where AbilityKey='Charge' and CharClass in (select CharClass from ClassXRealmAbility_Atlas where AbilityKey='Valkyrie_Charge')")
    for atlas, live in REPLACED_ATLAS.items():
        db.execute('delete from ClassXRealmAbility_Atlas where AbilityKey=? and CharClass in (select CharClass from ClassXRealmAbility_Atlas where AbilityKey=?)', (atlas,live))
    db.execute("update Ability set Name='Mastery of Stealth' where KeyName='AtlasOF_MasteryOfStealth'")
    for cls in STEALTH_CLASSES:
        if not db.execute("select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey='AtlasOF_MasteryOfStealth'", (cls,)).fetchone():
            db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                       (cls,'AtlasOF_MasteryOfStealth','modern-mos-'+str(cls)))
    db.execute('delete from ClassXRealmAbility_Atlas where AbilityKey in (%s)' % ','.join('?'*len(RETIRED_RA_KEYS)), RETIRED_RA_KEYS)
    audit_removed = db.execute('delete from ClassXRealmAbility_Atlas where AbilityKey in (%s)'
                               % ','.join('?'*len(OLD_FRONTIERS_ONLY)), OLD_FRONTIERS_ONLY).rowcount
    audit_removed += db.execute('delete from ClassXRealmAbility_Atlas where AbilityKey in (%s) and CharClass not in (%s)'
                                % (','.join('?'*len(ATLAS_CLASS_ACTIVES)), custom), ATLAS_CLASS_ACTIVES).rowcount
    for key, (handler, internal, icon, description) in MODERN_RR5_ROWS.items():
        implementation = 'DOL.GS.RealmAbilities.'+handler
        if db.execute('select 1 from Ability where KeyName=?', (key,)).fetchone():
            db.execute('update Ability set Implementation=?,IconID=?,Description=? where KeyName=?', (implementation,icon,description,key))
            continue
        owner = db.execute('select KeyName from Ability where InternalID=?', (internal,)).fetchone()
        if owner is not None:
            raise ValueError('Private RR5 internal ID %d is occupied by %s' % (internal, owner[0]))
        db.execute('insert into Ability (KeyName,Name,InternalID,Description,IconID,Implementation) values (?,?,?,?,?,?)',
                   (key,key,internal,description,icon,implementation))
    rr5_added = 0
    for key, cls in RR5_BINDINGS.items():
        row = db.execute('select Implementation from Ability where KeyName=?', (key,)).fetchone()
        if row is None or not row[0]:
            raise ValueError('Missing RR5 ability: '+key)
        if not db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?', (cls,key)).fetchone():
            db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                       (cls,key,'modern-rr5-'+str(cls)))
            rr5_added += 1
    for key in WARLOCK_LIVE_RAS:
        if not db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=59 and AbilityKey=?', (key,)).fetchone():
            db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                       (59,key,'modern-warlock-'+key))
    custom_added = 0
    for cls, keys in CUSTOM_ADDITIONS.items():
        for key in keys:
            if not db.execute('select 1 from Ability where KeyName=?', (key,)).fetchone():
                raise ValueError('Missing ability for custom class: '+key)
            if not db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?', (cls,key)).fetchone():
                db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                           (cls,key,'modern-custom-'+str(cls)+'-'+key))
                custom_added += 1
    # Undo the earlier Stealth-spec grant and bind the trainable realm ability instead.
    db.execute("delete from SpecXAbility where Spec='Stealth' and AbilityKey='Vanish'")
    for cls in ASSASSINS:
        if not db.execute("select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey='Vanish'", (cls,)).fetchone():
            db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                       (cls,'Vanish','modern-vanish-'+str(cls)))
    # Confirmed live 1.128 class-access moves, applied after the historical baseline.
    for cls,key in [(4,'AtlasOF_Ichor'),(34,'AtlasOF_Ichor'),(29,'AtlasOF_StaticTempest')]:
        db.execute('delete from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?',(cls,key))
    # Separate definitions are necessary: CostForUpgrade has no player/class parameter.
    # Live 1.129 identifies Berserker, Blademaster, Mercenary and Savage as light tanks.
    template = db.execute("select * from Ability where KeyName='AtlasOF_Determination'").fetchone()
    key = 'Modern_LightTankDetermination'
    if not db.execute('select 1 from Ability where KeyName=?', (key,)).fetchone():
        db.execute('insert into Ability (KeyName,Name,InternalID,Description,IconID,Implementation) values (?,?,?,?,?,?)',
                   (key,template['Name'],3040,template['Description'],template['IconID'],
                    'DOL.GS.RealmAbilities.ModernLightTankDetermination'))
    if db.execute('select count(*) from Ability where InternalID=3040').fetchone()[0] != 1:
        raise ValueError('Private light-tank RA internal ID 3040 is occupied')
    db.execute("delete from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_DeterminationHybrid' and CharClass in (select CharClass from ClassXRealmAbility_Atlas where AbilityKey='AtlasOF_Determination')")
    for cls in (11,31,32,43):
        db.execute("delete from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey in ('AtlasOF_Determination','AtlasOF_DeterminationHybrid')", (cls,))
        if not db.execute('select 1 from ClassXRealmAbility_Atlas where CharClass=? and AbilityKey=?',(cls,key)).fetchone():
            db.execute('insert into ClassXRealmAbility_Atlas (CharClass,AbilityKey,ClassXRealmAbility_Atlas_ID) values (?,?,?)',
                       (cls,key,'modern-light-det-'+str(cls)))
    return dict(**summary, shared_abilities_modernized=len(KEYS)+len(EXTRA), shared_bindings_added=inserted,
                light_tank_determination_classes=4, free_charge_grants_removed=free_charge_removed,
                old_frontiers_bindings_removed=audit_removed, custom_class_bindings_added=custom_added,
                rr5_bindings_added=rr5_added,
                full_live_conversion=False)
