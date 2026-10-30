using System.Linq;
using DOL.GS;
using DOL.GS.PlayerClass;
using DOL.GS.Realm;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_Tuatha
    {
        [Test]
        public void HiberniaHasItsOwnIdentityAndMatchesMidgardCombatCurves()
        {
            var hibernia=new ClassTuathaSovereign();var midgard=new ClassStormforged();
            Assert.That(hibernia.ID,Is.EqualTo(67));
            Assert.That(hibernia.BaseHP,Is.EqualTo(midgard.BaseHP));
            Assert.That(hibernia.WeaponSkillBase,Is.EqualTo(midgard.WeaponSkillBase));
            Assert.That(hibernia.ClassType,Is.EqualTo(midgard.ClassType));
            Assert.That(hibernia.ManaStat,Is.EqualTo(midgard.ManaStat),"power comes from Piety, not Hero's none");
            Assert.That(hibernia.EligibleRaces.Select(r=>r.ID),Is.EquivalentTo(PlayerRace.AllRaces.Where(r=>r.Realm==eRealm.Hibernia).Select(r=>r.ID)));
            Assert.That(PendragonRules.IsSovereign(67),Is.True);
            Assert.That(PendragonRules.IsTuatha(67),Is.True);
            Assert.That(PendragonRules.IsPendragon(67),Is.False);
            Assert.That(System.Enum.IsDefined(typeof(eCharacterClass),(byte)63),Is.False,"the Sluaghbinder is retired; slot 63 keeps only its client name");
        }
        [Test]
        public void HiberniaUsesTheSamePowerTableWithSeparateSpellAndEffectIdentities()
        {
            foreach(var entry in StormSovereignAbilities.Build().Where(e=>e.Id<63000))
            {
                int id=entry.Id+PendragonRules.TuathaOffset;
                Assert.That(MasterLevelAbilities.For(id),Is.SameAs(MasterLevelAbilities.For(entry.Id)));
                Assert.That(StormSovereignAbilities.Owns(id),Is.True);
                Assert.That(StormSovereignAbilities.Toggle(id),Is.EqualTo(StormSovereignAbilities.Toggle(entry.Id)));
                Assert.That(StormSovereignAbilities.Key(id),Is.EqualTo(StormSovereignAbilities.Key(entry.Id)));
            }
            foreach(int id in Enumerable.Range(73335,7)) Assert.That(MasterLevelAbilities.For(id),Is.Not.Null,"Large Weapons style procs");
            Assert.That(StormSovereignAbilities.IsHammerfall(62421+PendragonRules.TuathaOffset),Is.True);
            Assert.That(DOL.GS.PacketHandler.PacketLib1110.UsesOwnTooltipIdentity(73560),Is.True);
            Assert.That(DOL.GS.PacketHandler.PacketLib1110.UsesOwnTooltipIdentity(73560990),Is.True);
            Assert.That(StormSovereignAbilities.Owns(73600),Is.False);
            Assert.That(PendragonRules.NormalizeSpell(64000),Is.EqualTo(62400),"Albion offset unchanged");
        }
        [Test]
        public void RoyalSpellbooksMergeOnlyTheirOwnLines()
        {
            Assert.That(PendragonSpellbook.OwnsLine("Tuatha.Sovereign00"),Is.True);
            Assert.That(PendragonSpellbook.OwnsLine("Pendragon.Sovereign00"),Is.True);
            Assert.That(PendragonSpellbook.OwnsLine("Stormforged.Sovereign00"),Is.False);
            Assert.That(PendragonSpellbook.For(PendragonSpellbook.Hibernia.ClientLine),Is.SameAs(PendragonSpellbook.Hibernia));
            Assert.That(PendragonSpellbook.ClientLine,Is.SameAs(PendragonSpellbook.Albion.ClientLine));
            Assert.That(PendragonSpellbook.Hibernia.ClientLine.Spec,Is.EqualTo("TuathaCareer"));
        }
        [Test]
        public void RoyalDamageTypesFollowTheRealm()
        {
            Assert.That(PendragonRules.RoyalDamage(null,eDamageType.Energy),Is.EqualTo(eDamageType.Energy));
            Assert.That(PendragonRules.RealmOffset(null),Is.Zero);
        }
    }
}
