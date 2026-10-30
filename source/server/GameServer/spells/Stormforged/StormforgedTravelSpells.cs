using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    public abstract class StormforgedGroundSpell : StormforgedMaintainedSpell
    {
        protected StormforgedGroundSpell(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }

        protected virtual bool GetDestination(out Point3D destination)
        {
            destination = null;
            if (!Caster.GroundTarget.IsValid || !Caster.GroundTargetInView)
                return false;
            return StormforgedTravel.TryResolvePoint(Caster,
                new Point3D(Caster.GroundTarget.X, Caster.GroundTarget.Y, Caster.GroundTarget.Z), Spell.Range, out destination);
        }

        public override bool CheckBeginCast(GameLiving target)
        {
            if (!GetDestination(out _))
            {
                MessageToCaster("Choose a visible, reachable ground target within spell range.", eChatType.CT_SpellResisted);
                return false;
            }
            return base.CheckBeginCast(target);
        }

        public override bool CheckEndCast(GameLiving target) => GetDestination(out _) && base.CheckEndCast(target);
    }

    [SpellHandler(eSpellType.StormforgedStep)]
    public class StormforgedStep : StormforgedMaintainedSpell
    {
        public StormforgedStep(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override bool UnstealthCasterOnStart => true;
        public override bool UnstealthCasterOnFinish => true;
        public override string ShortDescription => "Instantly strike to your enemy target up to 2000 units away and unleash 350-radius lightning on arrival. Eight-second reuse timer.";

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            if (target == null || !target.IsAlive || target.CurrentRegion != Caster.CurrentRegion)
                return;
            Point3D landing = StormforgedTravel.ResolveBeside(Caster, target);
            if (Caster.MoveTo(Caster.CurrentRegionID, landing.X, landing.Y, landing.Z, Caster.GetHeading(target)))
                StormforgedHeroicRules.CastBurst(Caster, Spell, SpellLine, Caster);
        }
    }

    [SpellHandler(eSpellType.StormforgedRecall)]
    public class StormforgedRecall : StormforgedGroundSpell
    {
        public StormforgedRecall(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => "Gather your placed lightning storms in this region at your visible ground target within 1000 units and refresh their two-minute lifetime. Your melee elemental stays in place. Five-second reuse timer.";

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            if (!GetDestination(out Point3D destination))
                return;
            int moved = StormforgedTravel.RecallStorms(Caster, destination);
            MessageToCaster(moved < 0 ? "Too many turrets near that ground target." : $"Recalled {moved} lightning storms.", eChatType.CT_Spell);
        }
    }

    [SpellHandler(eSpellType.StormforgedRide)]
    public class StormforgedRide : StormforgedMaintainedSpell
    {
        public StormforgedRide(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => "Until cancelled: your elemental and placed storms within 2000 units echo your directly cast Stormbolt, Thunderclap, Chain Lightning and Stormhammer. Echoes are instant, cost no resources and never trigger further echoes.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams init) =>
            ECSGameEffectFactory.Create(init, static (in i) => new StormforgedRideEffect(i));
    }

    [SpellHandler(eSpellType.StormforgedEye)]
    public class StormforgedEye : StormforgedMaintainedSpell
    {
        public StormforgedEye(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
        public override string ShortDescription => "Until cancelled: every four seconds, draw hostile mobs within 600 units toward you. Respects crowd-control immunity and terrain; pulling an enemy reveals you.";
        public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams init) =>
            ECSGameEffectFactory.Create(init, static (in i) => new StormforgedEyeEffect(i));
    }
}
