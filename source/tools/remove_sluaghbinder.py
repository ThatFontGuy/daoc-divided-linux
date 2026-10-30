"""Removes the retired custom Sluaghbinder (class 63) from a world: its spells, lines, specializations, styles, pets,
epic and loadout items, realm abilities, start points and trainer. Stock rows that only share the name (the balorian
sluaghan and Sluagh Footsoldier monsters) stay. Characters of class 63 must not exist: the migration refuses then.
Only world tables are touched; install_hybrid_lines.py verifies the saved-progress tables are unchanged.
"""
SPECS = ('SluaghbinderCareer', 'Sluagh Host', "Abhartach's Rot", 'Cairn Oath', "Dullahan's Bulwark", "Abhartach's Bane",
         'Sluagh Covenant', 'Epic Spells')
FIRST, LAST = 59000, 59111
MOBS = ('sluaghbinder_trainer_tir_na_nog', 'sluaghbinder_bound_wisp_tir_na_nog')
REALM_ABILITIES = ('AtlasOF_CripplingPlague',)


def marks(values):
    return ','.join('?' * len(values))


def apply(db):
    if db.execute('select 1 from DOLCharacters where Class=63').fetchone():
        raise ValueError('A Sluaghbinder character exists; convert or delete it first')
    lines = [r[0] for r in db.execute(f'select KeyName from SpellLine where ClassIDHint=63 or Spec in ({marks(SPECS)})', SPECS)]
    if db.execute(f'select 1 from ClassXSpecialization where ClassID<>63 and SpecKeyName in ({marks(SPECS)})', SPECS).fetchone():
        raise ValueError('Another class uses a Sluaghbinder specialization')
    items = [r[0] for r in db.execute("select Id_nb from ItemTemplate where Id_nb like 'sluagh\\_%' escape '\\' "
                                      "or Id_nb like 'offline50\\_%\\_c63\\_%' escape '\\'")]
    pets = [r[0] for r in db.execute("select NpcTemplate_ID from NpcTemplate where PackageID='Sluaghbinder_Pets'")]
    removed = {}

    def delete(name, sql, args=()):
        removed[name] = removed.get(name, 0) + db.execute(sql, args).rowcount

    delete('LineXSpell', f'delete from LineXSpell where SpellID between ? and ? or LineName in ({marks(lines) or "null"})', (FIRST, LAST, *lines))
    delete('Spell', 'delete from Spell where SpellID between ? and ?', (FIRST, LAST))
    delete('SpellLine', f'delete from SpellLine where KeyName in ({marks(lines) or "null"})', lines)
    delete('SpecXAbility', f'delete from SpecXAbility where Spec in ({marks(SPECS)})', SPECS)
    delete('ClassXSpecialization', 'delete from ClassXSpecialization where ClassID=63')
    delete('Specialization', f'delete from Specialization where KeyName in ({marks(SPECS)})', SPECS)
    delete('Style', 'delete from Style where ClassId=63')
    delete('ClassXRealmAbility_Atlas', 'delete from ClassXRealmAbility_Atlas where CharClass=63')
    delete('ClassXRealmAbility_Atlas', f'delete from ClassXRealmAbility_Atlas where AbilityKey in ({marks(REALM_ABILITIES)})', REALM_ABILITIES)
    delete('Ability', f'delete from Ability where KeyName in ({marks(REALM_ABILITIES)})', REALM_ABILITIES)
    delete('StartupLocation', 'delete from StartupLocation where ClassID=63')
    delete('offline_level50_loadouts', 'delete from offline_level50_loadouts where ClassId=63')
    delete('ItemTemplate', f'delete from ItemTemplate where Id_nb in ({marks(items) or "null"})', items)
    delete('NpcTemplate', f'delete from NpcTemplate where NpcTemplate_ID in ({marks(pets) or "null"})', pets)
    delete('NPCEquipment', "delete from NPCEquipment where TemplateID like 'sluagh\\_%' escape '\\' or TemplateID like 'Sluaghbinder%'")
    delete('Mob', f'delete from Mob where Mob_ID in ({marks(MOBS)}) or ClassType like ?', (*MOBS, '%Sluaghbinder%'))
    return dict(sluaghbinder_removed={k: v for k, v in removed.items() if v})
