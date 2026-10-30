"""Live (1.130a) archery for the Scout, Hunter and Ranger, beside the classic bow attack this server keeps.

Live turned archery into a line of shots cast with a drawn bow (Standard, Long, Power, Critical from stealth, Point
Blank, Rapid Fire, Volley, Acid, Siege and the realm's two elemental shots) plus the Scout's self buffs and speed
bursts. Here each class's bow spec (Longbows, Composite Bow, Recurve Bow) keeps its key, so trained points and the
classic auto-fire (classes / allow_old_archery) are unchanged, and gains a class line "<Class> Archery" with those
spells. The three bow specs become live hybrid specializations, so the list shows the best rank of each shot.

archery_data.py is made by the scratch generator gen_archery.py from daoc.gg's 1.130a data:
  - Shot damage at the scale of the server's own Critical Shot ranks (same Archery handler): x0.178 of live's figure.
  - Draw times are live's timer + 2 s (the Archery handler keeps Power Shot's own 6 s).
  - Endurance costs are live's percentages; recasts, ranges and radii are live's.
  - Self buffs are left out where the class already has a line of that kind.
The 2026-10-25 research pass (Class-Research/codex) added the arrow damage-type switches (Blunt / Slashing /
Thrusting, kept on the archer), Bola Shot (a drawn-bow root, 12-36 s) and Eagle Eye (+25% archery damage for 30
minutes, free at character level 45: a class-hinted base line "<Class> Archery Abilities" that follows the level).
A follow-up pass (Class-Research/claude/followup-2026-10-25) added Patella Shot (a drawn-bow 40% snare for 15 s, the
"Hindered" child), Track (+15-45% stealth detection for 30 s while stealthed and still) and fixed the draw times:
live's timer + 2 s, as for spells (Standard Shot 4.2 s, Critical 5 s, Volley 7 s; Power Shot keeps its 6 s).
Live also moved the Hunter's self buffs from Beastcraft into Archery under the Scout's names (Determination..
Invincibility, Sharpened Senses..Perfect Acuity, Forest Shadow..Forest Phantom): HUNTER_BUFFS copies the Scout's
families into Hunter Archery (after the generated rows, so their IDs stay put) and the classic Beastcraft AF, Dex/Qui
and speed buffs leave the Beastcraft line.
Standard Solo Shot (Scout, Hunter and Ranger, Archery 49): live's record has only its damage (1,910); here it is Standard Shot 9
with that damage at the shots' scale (340.0).
"""
import sqlite3
from archery_data import LINES
import hybrid_lines

PACKAGE = 'local-archery-live-v1'
FIRST, LAST = 76000, 76399
TOOLTIP_BASE = 30184  # 30184-30583 are free
GROUP_BASE = 76000
SHOT_ART = 7427  # the local Critical Shot 1
HYBRID = 'DOL.GS.LiveSpellHybridSpecialization'
HUNTER_BUFFS = ('BaseArmorFactorBuff', 'DexterityQuicknessBuff', 'SpeedEnhancement')
SOLO_SHOT_DAMAGE = 340.0  # live's 1,910 at x0.178


def definitions():
    rows, spell_id, group = [], FIRST, GROUP_BASE
    for cls, line in LINES.items():
        for family, type_, ranks in line['families']:
            for level, name, fields in ranks:
                fields = dict(fields)
                key = line['line'] + ' Abilities' if fields.pop('BASE', False) else line['line']
                rows.append((key, level, dict(fields, Type=type_, SpellGroup=group,
                                              EffectGroup=group if type_ in ('Archery', 'SiegeArrow', 'ArcheryDamageBuff') else 0,
                                                       SpellID=spell_id, Spell_ID=f'{PACKAGE}-{spell_id}', PackageID=PACKAGE,
                                                       TooltipId=TOOLTIP_BASE + spell_id - FIRST, Name=name,
                                                       Description=f'{name} (live 1.130a Archery).')))
                spell_id += 1
            group += 1
    for family, type_, ranks in LINES['scout']['families']:
        if type_ not in HUNTER_BUFFS:
            continue
        for level, name, fields in ranks:
            rows.append((LINES['hunter']['line'], level, dict(fields, Type=type_, SpellGroup=group, EffectGroup=0, SpellID=spell_id,
                                                              Spell_ID=f'{PACKAGE}-{spell_id}', PackageID=PACKAGE,
                                                              TooltipId=TOOLTIP_BASE + spell_id - FIRST, Name=name,
                                                              Description=f'{name} (live 1.130a Archery).')))
            spell_id += 1
        group += 1
    for cls in ('scout', 'hunter', 'ranger'):
        nine = next(fields for family, _, ranks in LINES[cls]['families'] if family == 'Standard Shot' for level, name, fields in ranks
                    if name == 'Standard Shot 9')
        rows.append((LINES[cls]['line'], 49, dict(nine, Damage=SOLO_SHOT_DAMAGE, Type='Archery', SpellGroup=group, EffectGroup=group,
                                                  SpellID=spell_id, Spell_ID=f'{PACKAGE}-{spell_id}', PackageID=PACKAGE,
                                                  TooltipId=TOOLTIP_BASE + spell_id - FIRST, Name='Standard Solo Shot',
                                                  Description='Standard Solo Shot (live 1.130a Archery).')))
        spell_id += 1
        group += 1
    assert spell_id - 1 <= LAST
    return rows


def art(db, type_, target, level):
    if type_ in ('Archery', 'SiegeArrow', 'BolaShot', 'ArrowDamageTypes', 'ArcheryDamageBuff', 'TrackStealth'):
        row = db.execute('select ClientEffect, Icon, EffectGroup from Spell where SpellID=?', (SHOT_ART,)).fetchone()
    else:
        row = db.execute("""select s.ClientEffect, s.Icon, s.EffectGroup from LineXSpell l join Spell s on s.SpellID=l.SpellID
                            where s.Type=? and s.Target=? and coalesce(s.PackageID,'') not like 'local-%' and s.SpellID < 59000
                            order by abs(l.Level-?) limit 1""", (type_, target, level)).fetchone()
    if row is None:
        raise ValueError(f'No local {type_} spell to borrow art from')
    return row


def apply(db):
    db.row_factory = sqlite3.Row
    if db.execute("select 1 from Spell where (SpellID between ? and ? or TooltipId between ? and ?) and coalesce(PackageID,'')<>?",
                  (FIRST, LAST, TOOLTIP_BASE, TOOLTIP_BASE + LAST - FIRST, PACKAGE)).fetchone():
        raise ValueError('Archery spell/tooltip collision')
    db.execute('delete from LineXSpell where SpellID between ? and ?', (FIRST, LAST))
    db.execute('delete from Spell where PackageID=?', (PACKAGE,))
    for cls, line in LINES.items():
        if not db.execute('select 1 from ClassXSpecialization where ClassID=? and SpecKeyName=?', (line['cid'], line['spec'])).fetchone():
            raise ValueError(f"{cls} has no {line['spec']} spec")
        db.execute('delete from SpellLine where KeyName in (?,?)', (line['line'], line['line'] + ' Abilities'))
        db.execute('insert into SpellLine (KeyName,Name,Spec,IsBaseLine,ClassIDHint,LastTimeRowUpdated) values (?,?,?,?,?,?)',
                   (line['line'], 'Archery', line['spec'], 0, line['cid'], '2000-01-01 00:00:00'))
        db.execute('insert into SpellLine (KeyName,Name,Spec,IsBaseLine,ClassIDHint,LastTimeRowUpdated) values (?,?,?,?,?,?)',
                   (line['line'] + ' Abilities', 'Archery Abilities', line['spec'], 1, line['cid'], '2000-01-01 00:00:00'))
        db.execute('update Specialization set Implementation=? where KeyName=?', (HYBRID, line['spec']))
    template = hybrid_lines.blank_spell(db)
    rows = definitions()
    for line, level, fields in rows:
        source = art(db, fields['Type'], fields['Target'], level)
        if not fields['EffectGroup']:
            fields = dict(fields, EffectGroup=source['EffectGroup'])  # a self buff replaces the class's older one
        row = dict(template, **fields, ClientEffect=source['ClientEffect'], Icon=source['Icon'])
        row.update(Message1=f"You are affected by {row['Name']}.", Message2=f"{{0}} is affected by {row['Name']}.",
                   Message3=f"{row['Name']} ends.", Message4=f"{row['Name']} ends on {{0}}.")
        db.execute('insert into Spell (' + ','.join(f'"{k}"' for k in row) + ') values (' + ','.join('?' * len(row)) + ')', list(row.values()))
        db.execute('insert into LineXSpell (LineName,SpellID,Level,LineXSpell_ID) values (?,?,?,?)', (line, row['SpellID'], level, row['Spell_ID']))
    beastcraft = f"""from LineXSpell where LineName='Beastcraft' and SpellID in
                     (select SpellID from Spell where Type in ({','.join('?' * len(HUNTER_BUFFS))}))"""
    db.execute('delete ' + beastcraft, HUNTER_BUFFS)
    return dict(archery_package=PACKAGE, archery_spells=len(rows), archery_lines=len(LINES),
                beastcraft_buffs_left=db.execute('select count(*) ' + beastcraft, HUNTER_BUFFS).fetchone()[0])
