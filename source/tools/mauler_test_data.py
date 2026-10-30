"""Shared three-realm Mauler test definitions, reconciled through live 1.129b.
The library snapshot supplies unchanged families; explicit later overrides take priority.
"""
import csv
import io
import json
from pathlib import Path
import re
import sqlite3
import sys

PACKAGE='local-mauler-test-v1'
# The client reads tooltip indexes as signed 16-bit values: every custom kit must stay below 32768.
TOOLTIP_BASE=31200
HERE=Path(__file__).resolve().parent
CLASSES=(60,61,62)
LINES=('Aura Manipulation','Aura Manipulation Baseline','Magnetism','Power Strikes',
       'Mauler Albion Gifts','Mauler Midgard Gifts','Mauler Hibernia Gifts')

def number(text,default=0):
    m=re.search(r'-?\d+(?:\.\d+)?',text)
    return float(m.group()) if m else default

def definitions():
    result=[]
    def add(id,line,level,name,icon,params=None,**kw):
        d=dict(SpellID=id,Spell_ID=f'{PACKAGE}-{id}',PackageID=PACKAGE,TooltipId=TOOLTIP_BASE+id-67000,
               Name=name,Description='Modern Mauler test kit.',Type='DirectDamage',Target='Enemy',
               Range=500,CastTime=3,DamageType=10,Icon=icon,ClientEffect=icon,SpellGroup=id,
               Message1='You are affected by '+name+'.',Message2='{0} is affected by '+name+'.',
               Message3=name+' ends.',Message4=name+' ends on {0}.')
        d.update(kw);params=dict(params or {})
        stat_types={'WeaponSkillBuff':10,'EvadeBuff':11,'ParryBuff':12,'MeleeDamageBuff':13,'FumbleChanceDebuff':14,'CastingSpeedDebuff':15}
        if d['Type'] in stat_types:
            params['MaulerStat']=stat_types[d['Type']];d['Type']='MaulerStat'
        if d.get('Pulse'):
            # Pulse is a flag in this server; Frequency stores tenths of a second.
            d['Frequency']=d['Pulse']*10;d['Pulse']=1
        result.append((line,level,d,params));return id
    for id,name,icon in [(67000,'Aura of the Wildbull',15287),(67001,'Aura of the Farseer',15288)]:
        add(id,'Aura Manipulation',1,name,icon,Type='MaulerStance',Target='Self',Range=0,CastTime=0,EffectGroup=67000,
            Description='Maintained Mauler aura. Replaces the other aura and changes the effects of your Aura Manipulation gifts.')
    # Updated baseline and specialization defenses. The latest absorb ranks replace obsolete library ranks.
    for i,(lv,n,v,p) in enumerate([(7,'Raw Discipline of Laresh',3,2),(15,'Rough Discipline of Laresh',6,5),(25,'Minor Discipline of Laresh',9,8),(40,'Lesser Discipline of Laresh',12,14)]):
        add(67010+i,'Aura Manipulation Baseline',lv,n,10648+i,Type='ArmorAbsorptionBuff',Target='Self',Range=0,Value=v,Power=p,Duration=900,EffectGroup=67010)
    for i,(lv,n,v,p) in enumerate([(12,'Discipline of Laresh',13,4),(22,'Major Discipline of Laresh',16,7),(32,'Greater Discipline of Laresh',20,11),(42,'Perfect Discipline of Laresh',28,15)]):
        add(67015+i,'Aura Manipulation',lv,n,10649+i,Type='ArmorAbsorptionBuff',Target='Self',Range=0,Value=v,Power=p,Duration=900,EffectGroup=67010)
    rows=json.loads((HERE/'mauler-library-rows.json').read_text())
    con_values=[17,24,33,44,57,70];counters={}
    for row in rows:
        if len(row)!=7:continue
        lv=int(row[0]);name=row[1].replace('\u2019',"'");low=name.lower()
        # Families retained from the library; removed Aura support pulses are deliberately excluded.
        # The library snapshot misspells Encroaching Blow.
        if low=='encoraching blow':name='Encroaching Blow';low=name.lower()
        family=None;line=None;kw={};value=number(row[5]);power=number(row[6]);params={}
        if '%' in row[6]:power=-power
        if 'stamina of the uruz' in low or any(s in low for s in ['endurance of the uruz','fortitude of the uruz','vitality of the uruz']):family='con';line='Aura Manipulation Baseline';kw=dict(Type='ConstitutionBuff',Target='Self',Range=0,Duration=900)
        elif 'strength of the forge' in low:family='strcon';line='Aura Manipulation';kw=dict(Type='StrengthConstitutionBuff',Target='Self',Range=0,Duration=900)
        elif low in ('unceasing burden','endless burden'):family='focus';line='Magnetism';kw=dict(Type='SpeedDecrease',Range=700,Value=value,Duration=6,IsFocus=1,Pulse=5,PulsePower=1,RecastDelay=5,DamageType=14)
        elif low in ('minor burden','lesser burden','modest burden','greater burden','overwhelming burden'):family='root';line='Magnetism';kw=dict(Type='SpeedDecrease',Range=0,Radius=350,Value=99,CastTime=0,Duration=[14,28,42,56,70][[7,17,27,37,47].index(lv)],RecastDelay=300,DamageType=14)
        elif low in ('rigid armor','tightening armor','inflexible armor','unbending armor','unyielding armor'):family='cone';line='Magnetism';kw=dict(Type='SpeedDecrease',Target='Cone',Range=350,Radius=90,Value=99,CastTime=2,Duration=[30,43,56,69,82][[8,18,28,38,48].index(lv)],RecastDelay=600,DamageType=14)
        elif low.startswith("tegashrig's"):family='protect';line='Magnetism';kw=dict(Type='MaulerUtility',Target='Realm',Range=2000,Value=4,Damage=value,CastTime=0,Duration=30,RecastDelay=15)
        elif low.endswith(('hindrance','encumbrance')):family='snare';line='Magnetism';lv=49 if lv==50 else lv;kw=dict(Type='SpeedDecrease',Range=0,Radius=350,Value=value,CastTime=0,Duration=5,Pulse=8,PulsePower=int(number(row[6].split('&')[-1])),DamageType=14)
        elif low.startswith('demand of '):family='castslow';line='Magnetism';kw=dict(Type='CastingSpeedDebuff',Range=0,Radius=250,Value=value,CastTime=0,Duration=8,Pulse=8,PulsePower=int(number(row[6].split('&')[-1])))
        elif low.startswith("teragani's"):family='matter';line='Magnetism';kw=dict(Type='MatterResistDebuff',Target='Cone',Range=350,Radius=90,Value=value,CastTime=2,Duration=15,RecastDelay=15,DamageType=14)
        elif low.startswith(('perfection of ','way of perfection')):family='add';line='Power Strikes';kw=dict(Type='DamageAdd',Target='Self',Range=0,Damage=value,Duration=30,RecastDelay=60)
        elif 'grasp of februstos' in low:family='end';line='Power Strikes';kw=dict(Type='MaulerEnduranceTap',Damage=value,RecastDelay=15);power=-16 if row[6]=='%' else power
        elif low.startswith("nurizane's"):family='fumble';line='Power Strikes';kw=dict(Type='FumbleChanceDebuff',Value={11:10,21:20,32:30}[lv],Duration=30,RecastDelay=180)
        elif low.startswith('test of '):family='tap';line='Power Strikes';kw=dict(Type='PowerDrain',Damage=value,LifeDrainReturn=50,RecastDelay=15)
        elif low.endswith('blow') and low.split()[0] in ('daring','hostile','encroaching','advancing','intrusive','intruding','pugnacious','destructive','assailing'):
            family='kick';line='Power Strikes';kw=dict(Damage=165 if value==0 else value,Range=250,RecastDelay=8,DamageType=1)
        elif low.startswith('veil of '):family='dehaste';line='Power Strikes';kw=dict(Type='CombatSpeedDebuff',Value=value,Duration=30,RecastDelay=60,CastTime=2)
        elif low in ('demand respect','demand reverence','demand awe'):family='silence';line='Power Strikes';kw=dict(Type='MaulerControl',Value=1,Duration={25:2,35:4,45:6}[lv],RecastDelay=45)
        elif low.startswith("perizor's disarming"):family='disarm';line='Power Strikes';kw=dict(Type='MaulerControl',Value=2,Duration={30:2,40:4,50:6}[lv],RecastDelay=45)
        if family is None:continue
        bases={'con':(67030,10658),'strcon':(67040,10664),'focus':(67100,10615),'root':(67105,10605),'cone':(67110,10610),'protect':(67115,10617),'snare':(67120,10621),'castslow':(67130,10630),'matter':(67140,10638),'add':(67200,10590),'end':(67210,10559),'fumble':(67225,10579),'tap':(67230,10597),'kick':(67240,10570),'dehaste':(67250,10582),'silence':(67260,10587),'disarm':(67265,10594)}
        index=counters.get(family,0);counters[family]=index+1;base,icon=bases[family]
        if family=='con':kw['Value']=con_values[index]
        elif family=='strcon':kw['Value']=value
        kw.update(Power=int(power),EffectGroup=base,SharedTimerGroup=base)
        add(base+index,line,lv,name,icon+index,**kw)
    # Staff-conditioned gifts: a shared visible parent dispatches a free internal effect for the selected aura.
    for family,base,levels,icon,powers,cast,reuse,required in [
        ('Nethuni',67300,[4,14,24,34,44],15267,[5,15,35,45,55],3,45,[-1]*5),
        ('Tegashrig',67310,[3,13,23,33,43],15262,[16,24,48,60,76],3,15,[-1]*5),
        ('Perizor',67320,[7,17,27,37,47],15272,[-5]*5,2.5,0,[0,5,15,25,35]),
        ('Arasthai',67330,[9,19,29,39,49],15277,[-30]*5,5,180,[0,5,15,25,35])]:
        for i,lv in enumerate(levels):
            wild=67500+(base-67300)*2+i*2;far=wild+1
            enemy=family=='Perizor';rang=[1500,1550,1600,1700,1750][i] if enemy else 0
            add(base+i,'Aura Manipulation',lv,'Gift of '+family,icon+i,
                Type='MaulerGift',Target='Enemy' if enemy else 'Self',Range=rang,CastTime=cast,Power=powers[i],RecastDelay=reuse,
                SharedTimerGroup=base,SubSpellID=wild,params={'MaulerStaffRequired':required[i],'MaulerFarseerSpell':far},
                Description=f'Aura-dependent Gift of {family}; Wildbull and Farseer effects differ. Required trained Mauler Staff: {required[i] if required[i]>=0 else "none"}.')
            if family=='Nethuni':
                add(wild,None,lv,'Nethuni Regeneration',icon+i,Type='HealOverTime',Target='Self',Range=0,CastTime=0,Value=[5,12.5,20,25,30][i],Duration=15,Frequency=30,EffectGroup=67300)
                add(far,None,lv,'Nethuni Heal',icon+i,Type='Heal',Target='Self',Range=0,CastTime=0,Value=[12.5,31,50,62.5,75][i])
            elif family=='Tegashrig':
                add(wild,None,lv,'Tegashrig Weaponskill',icon+i,Type='WeaponSkillBuff',Target='Self',Range=0,CastTime=0,Value=[5,10,15,20,25][i],Duration=30,EffectGroup=67310)
                add(far,None,lv,'Tegashrig Evasion',icon+i,Type='EvadeBuff',Target='Self',Range=0,CastTime=0,Value=[4,12,18,24,40][i],Duration=60,EffectGroup=67311)
            elif family=='Perizor':
                add(wild,None,lv,'Perizor Root',icon+i,Type='SpeedDecrease',Range=rang,CastTime=0,Value=99,Duration=[13,26,41,61,73][i],DamageType=14,EffectGroup=67320)
                add(far,None,lv,'Perizor Power Drain',icon+i,Type='MaulerUtility',Range=rang,CastTime=0,Value=6,Damage=[12,15,25,30,35][i])
            else:
                add(wild,None,lv,'Arasthai Melee Potency',icon+i,Type='MeleeDamageBuff',Target='Self',Range=0,CastTime=0,Value=[1,2,3,7,10][i],Duration=[10,10,20,30,40][i],EffectGroup=67330)
                add(far,None,lv,'Arasthai Magic Potency',icon+i,Type='MaulerUtility',Target='Self',Range=0,CastTime=0,Value=8,Damage=[1,2,3,7,10][i],Duration=[10,10,20,30,40][i],EffectGroup=67331)
    for realm,career,line,wildtype,fartype in [(1,60,'Mauler Albion Gifts',14,10),(2,61,'Mauler Midgard Gifts',11,15),(3,62,'Mauler Hibernia Gifts',13,12)]:
        for i,lv in enumerate([5,15,25,35,45]):
            id=67400+realm*10+i;wild=67600+realm*20+i*2;far=wild+1
            add(id,line,lv,'Gift of '+{1:'Albion',2:'Midgard',3:'Hibernia'}[realm],15282+i,Type='MaulerGift',Range=1500,Power=-25,CastTime=2.5,SubSpellID=wild,
                params={'MaulerStaffRequired':[0,5,15,25,35][i],'MaulerFarseerSpell':far},Description='Aura-dependent realm damage gift. Requires equipped Mauler Staff and trained Staff ranks 0/5/15/25/35.')
            add(wild,None,lv,'Realm Gift (Wildbull)',15282+i,Damage=[45,100,190,350,550][i],DamageType=wildtype,Range=1500,CastTime=0)
            add(far,None,lv,'Realm Gift (Farseer)',15282+i,Damage=[1,1,1,1,550][i],DamageType=fartype,Range=1500,CastTime=0)
    # Live Aura Manipulation 5 taunt (absent from the library snapshot); stock Gesture art.
    add(67060,'Aura Manipulation Baseline',5,'Irreverent Gesture',10545,Type='Taunt',Range=1350,CastTime=0,Value=5,RecastDelay=30,
        Description='Attracts the attention of a monster, causing it to focus its attacks on you.')
    add(67350,'Aura Manipulation',50,'Aura Convergence',15288,Type='MaulerUtility',Target='Self',Range=0,Value=7,Damage=33,CastTime=5,RecastDelay=600,Description='Sacrifices half nearby group members current power; steals enemy power within 500 units and gives group 33% magic damage protection for 30 seconds.')
    add(67700,None,41,'Renewal Heal',15271,Type='Heal',Target='Self',Range=0,CastTime=0,Value=85)
    add(67351,'Aura Manipulation',41,'Gift of Renewal',15271,Type='OffensiveProc',Target='Self',Range=0,Value=67700,Frequency=25,Duration=60,Power=65,RecastDelay=15,Uninterruptible=1)
    add(67270,'Power Strikes',41,'Gift of Form',10647,Type='ParryBuff',Target='Self',Range=0,Value=40,Duration=60,Power=65,RecastDelay=15,Uninterruptible=1)
    add(67145,'Magnetism',41,'Gift of Precision',15266,Type='WeaponSkillBuff',Target='Self',Range=0,Value=20,Duration=60,Power=65,RecastDelay=15,Uninterruptible=1)
    return result

def insert(c,table,row):
    c.execute('insert into "'+table+'" ('+','.join('"'+k+'"' for k in row)+') values ('+','.join('?' for _ in row)+')',list(row.values()))

def apply(c):
    c.row_factory=sqlite3.Row
    if c.execute("select Value from ServerProperty where Key='native_custom_class_slots'").fetchone()[0].lower()!='true':raise ValueError('Native custom slots are required; preserve custom classes')
    if c.execute("select 1 from Spell where (SpellID between 67000 and 67999 or TooltipId between 31200 and 32199) and coalesce(PackageID,'')<>?",(PACKAGE,)).fetchone():raise ValueError('Mauler spell/tooltip collision')
    for line in LINES:
        # class_lines.py (local-class-live-v1) adds live ranks to these lines; anything else is unknown.
        if c.execute("select 1 from LineXSpell l left join Spell s using(SpellID) where l.LineName=? and l.SpellID not between 67000 and 67999 and coalesce(s.PackageID,'')<>'local-class-live-v1'",(line,)).fetchone():raise ValueError('Unknown existing Mauler line content')
    c.execute('delete from LineXSpell where SpellID between 67000 and 67999');c.execute('delete from SpellXCustomValues where SpellID between 67000 and 67999');c.execute('delete from Spell where PackageID=?',(PACKAGE,))
    for name,base,career in [('Aura Manipulation Baseline',1,0),('Mauler Albion Gifts',0,60),('Mauler Midgard Gifts',0,61),('Mauler Hibernia Gifts',0,62)]:
        if not c.execute('select 1 from SpellLine where KeyName=?',(name,)).fetchone():insert(c,'SpellLine',dict(KeyName=name,Name=name,Spec='Aura Manipulation',IsBaseLine=base,ClassIDHint=career))
    spells=definitions()
    for line,level,row,params in spells:
        insert(c,'Spell',row)
        if line:insert(c,'LineXSpell',dict(LineName=line,SpellID=row['SpellID'],Level=level,LineXSpell_ID=row['Spell_ID']))
        for key,val in params.items():insert(c,'SpellXCustomValues',dict(SpellID=row['SpellID'],KeyName=key,Value=str(val)))
    # Generic menu-region-zero starts are essential for modern character creation.
    for realm,career in [(1,60),(2,61),(3,62)]:
        if not c.execute('select 1 from StartupLocation where RealmID=? and ClassID=? and ClientRegionID=0 and RaceID=0 and Region>0',(realm,career)).fetchone():
            source=c.execute('select * from StartupLocation where RealmID=? and Region in (1,100,200) and XPos>0 and YPos>0 order by ClientRegionID=0 desc,RaceID=0 desc,MinVersion desc limit 1',(realm,)).fetchone()
            if source is None:raise ValueError('Missing realm start '+str(realm))
            row=dict(source);row.pop('StartupLoc_ID');row.update(ClassID=career,RaceID=0,ClientRegionID=0,MinVersion=1130);insert(c,'StartupLocation',row)
        for key,rank,lv in [('Weaponry: Fist Wraps',0,1),('Weaponry: Mauler Staff',0,1),({1:'AlbArmor',2:'MidArmor',3:'HibArmor'}[realm],2,1),('Evade',1,5),('Protect',1,7)]:
            if not c.execute('select 1 from SpecXAbility where Spec=? and AbilityKey=? and ClassId=?',('MaulerCareer',key,career)).fetchone():insert(c,'SpecXAbility',dict(Spec='MaulerCareer',SpecLevel=lv,AbilityKey=key,AbilityLevel=rank,ClassId=career))
        if not c.execute("select 1 from SpecXAbility where Spec='Magnetism' and AbilityKey='Climbing Spikes' and ClassId=?",(career,)).fetchone():insert(c,'SpecXAbility',dict(Spec='Magnetism',SpecLevel=50,AbilityKey='Climbing Spikes',AbilityLevel=1,ClassId=career))
        # Existing starter templates, scoped to newly created Maulers only.
        templates=['plainwood_mauler_staff','local-mauler-starter-right','local-mauler-starter-left']
        for slot in (21,22,23,25,27,28):
            armor=c.execute('select Id_nb from ItemTemplate where Object_Type=33 and Level<=2 and Realm=? and Item_Type=? order by Level,Id_nb limit 1',(realm,slot)).fetchone()
            if armor:templates.append(armor[0])
        for template in templates:
            if template.startswith('local-mauler-starter') and not c.execute('select 1 from ItemTemplate where Id_nb=?',(template,)).fetchone():
                weapon=dict(c.execute("select * from ItemTemplate where Id_nb='plain_mauler_fistwrap'").fetchone());weapon.update(Id_nb=template,ItemTemplate_ID=template,Name='training fist wrap',Item_Type=10 if template.endswith('right') else 11);insert(c,'ItemTemplate',weapon)
            if not c.execute('select 1 from StarterEquipment where Class=? and TemplateID=?',(str(career)+';',template)).fetchone():insert(c,'StarterEquipment',dict(Class=str(career)+';',TemplateID=template))
    disabled=c.execute("select Value from ServerProperty where Key='disabled_classes'").fetchone()[0];ids=set()
    for token in disabled.split(';'):
        if token:
            bounds=list(map(int,token.split('-')));ids.update(range(bounds[0],bounds[-1]+1))
    ids.difference_update(CLASSES);c.execute("update ServerProperty set Value=? where Key='disabled_classes'",(';'.join(map(str,sorted(ids))),))
    for key,value in [('enable_mauler_test','True'),('mauler_test_data_version','1')]:
        if c.execute('select 1 from ServerProperty where Key=?',(key,)).fetchone():c.execute('update ServerProperty set Value=? where Key=?',(value,key))
        else:insert(c,'ServerProperty',dict(Category='classes',Key=key,Description='Modern three-realm Mauler test',DefaultValue='False',Value=value,ServerProperty_ID='local-'+key))
    styles=install_styles(c)
    common=sum(line in LINES[:4] for line,_,_,_ in spells)
    return dict(spells=c.execute('select count(*) from Spell where PackageID=?',(PACKAGE,)).fetchone()[0],
                learned_common_spells=common,learned_spells_per_realm=common+5,realm_gifts=5,classes=list(CLASSES),**styles)

def install_styles(c):
    # Defined below: never clone unrelated-class effect links.
    from mauler_test_styles import install
    return install(c)

def validate_icons(root,rows=None):
    sys.path.insert(0,str(HERE.parent/'new-client/pipeline'))
    from daoc_mpk import MpakArchive
    m=MpakArchive(root/'runtime/client-modern/app/gamedata.mpk')
    spells={int(r[0]):r for r in csv.reader(io.StringIO(m.read('spells.csv').decode('latin1'))) if r and r[0].isdigit()}
    icons={int(r[0]) for r in csv.reader(io.StringIO(m.read('icons.csv').decode('latin1'))) if r and r[0].isdigit()}
    for _,_,row,_ in (rows or definitions()):
        if row['Icon'] not in spells or int(spells[row['Icon']][2]) not in icons:raise ValueError('Missing Mauler art '+str(row['Icon']))
    return len({r['Icon'] for _,_,r,_ in (rows or definitions())})
