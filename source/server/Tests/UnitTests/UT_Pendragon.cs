using System.Linq;
using DOL.GS;
using DOL.GS.PlayerClass;
using DOL.GS.Realm;
using DOL.GS.Spells;
using NUnit.Framework;

namespace DOL.UnitTests
{
    [TestFixture]
    public class UT_Pendragon
    {
        [Test]
        public void AlbionHasItsOwnIdentityAndMatchesMidgardCombatCurves()
        {
            var albion=new ClassPendragonSovereign();var midgard=new ClassStormforged();
            Assert.That(albion.ID,Is.EqualTo(65));
            Assert.That(albion.BaseHP,Is.EqualTo(midgard.BaseHP));
            Assert.That(albion.WeaponSkillBase,Is.EqualTo(midgard.WeaponSkillBase));
            Assert.That(albion.ClassType,Is.EqualTo(midgard.ClassType));
            Assert.That(albion.EligibleRaces.Select(r=>r.ID),Is.EquivalentTo(PlayerRace.AllRaces.Where(r=>r.Realm==eRealm.Albion).Select(r=>r.ID)));
            Assert.That(StormforgedRules.OverviewClass(65,1),Is.EqualTo(60));
            Assert.That(StormforgedRules.OverviewClass(64,2),Is.EqualTo(61));
            Assert.That(StormforgedRules.OverviewClass(65,2),Is.EqualTo(65));
        }
        [Test]
        public void AlbionUsesTheSamePowerTableWithSeparateSpellAndEffectIdentities()
        {
            foreach(var entry in StormSovereignAbilities.Build().Where(e=>e.Id<63000))
            {
                var albion=MasterLevelAbilities.For(entry.Id+1600);
                Assert.That(albion,Is.SameAs(MasterLevelAbilities.For(entry.Id)));
                Assert.That(StormSovereignAbilities.Owns(entry.Id+1600),Is.True);
                Assert.That(StormSovereignAbilities.Toggle(entry.Id+1600),Is.EqualTo(StormSovereignAbilities.Toggle(entry.Id)));
                Assert.That(StormSovereignAbilities.Key(entry.Id+1600),Is.EqualTo(StormSovereignAbilities.Key(entry.Id)));
            }
            foreach(int id in Enumerable.Range(64335,7)) Assert.That(MasterLevelAbilities.For(id),Is.Not.Null);
            Assert.That(StormSovereignAbilities.IsHammerfall(64245),Is.True);
            Assert.That(DOL.GS.PacketHandler.PacketLib1110.UsesOwnTooltipIdentity(64560),Is.True);
            Assert.That(DOL.GS.PacketHandler.PacketLib1110.UsesOwnTooltipIdentity(64560990),Is.True);
            Assert.That(StormSovereignAbilities.Owns(64990),Is.False,"stock Valkyrie package remains independent");
        }
    }
}
