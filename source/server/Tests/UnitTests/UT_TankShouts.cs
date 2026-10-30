using DOL.AI.Brain;
using DOL.GS;
using DOL.GS.SkillHandler;
using NUnit.Framework;

namespace DOL.UnitTests
{
    /// <summary>Bot tanks cast the same shout spells the players' ability handlers cast.</summary>
    [TestFixture]
    public class UT_TankShouts
    {
        [Test]
        public void BotShoutSpellsMatchTheAbilityHandlers()
        {
            Assert.That(BotBrain.TankShoutSpellId(Abilities.TauntingShout), Is.EqualTo(new TauntingShoutAbilityHandler().SpellID));
            Assert.That(BotBrain.TankShoutSpellId(Abilities.MetalGuard), Is.EqualTo(new MetalGuardAbilityHandler().SpellID));
            Assert.That(BotBrain.TankShoutSpellId(Abilities.BolsteringRoar), Is.EqualTo(new BolsteringRoarAbilityHandler().SpellID));
            Assert.That(BotBrain.TankShoutSpellId(Abilities.Rampage), Is.EqualTo(new RampageAbilityHandler().SpellID));
            Assert.That(BotBrain.TankShoutSpellId(Abilities.Fury), Is.EqualTo(new FuryAbilityHandler().SpellID));
            Assert.That(BotBrain.TankShoutSpellId(Abilities.Berserk), Is.Zero);
        }
    }
}
