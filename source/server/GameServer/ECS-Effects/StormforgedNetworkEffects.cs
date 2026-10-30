using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.Events;
using DOL.GS.Spells;

namespace DOL.GS
{
    public class StormforgedRideEffect : StormforgedPermanentEffect
    {
        public StormforgedRideEffect(in ECSGameEffectInitParams init) : base(init) { }

        public override void OnStartEffect()
        {
            base.OnStartEffect();
            GameEventMgr.AddHandler(Owner, GameLivingEvent.CastFinished, OnCastFinished);
        }

        public override void OnStopEffect()
        {
            GameEventMgr.RemoveHandler(Owner, GameLivingEvent.CastFinished, OnCastFinished);
            base.OnStopEffect();
        }

        private void OnCastFinished(DOLEvent e, object sender, EventArgs args)
        {
            if (args is CastingEventArgs cast)
                TryEcho(cast.SpellHandler, cast.Target);
        }

        public static bool IsEchoable(Spell spell) => spell != null && spell.SpellType == eSpellType.StormforgedStrike &&
            spell.ID is >= 62000 and <= 62159 && spell.ID % 20 is 0 or 1 or 2 or 16;

        protected virtual IEnumerable<GameNPC> EchoSources()
        {
            var main = Owner.ControlledBrain?.Body;
            if (main?.NPCTemplate?.TemplateId == 60171001 && main.Brain is DOL.AI.Brain.IControlledBrain brain && brain.Owner == Owner)
                yield return main;
            foreach (var entry in AutonomousPetSupport.OwnedFieldTurrets(Owner))
                if (StormforgedTravel.IsOwnedStorm(Owner, entry.Turret))
                    yield return entry.Turret;
        }

        public static Spell BuildEcho(Spell original, bool avatar)
        {
            return new Spell(new DbSpell
            {
                SpellID = 62214, TooltipId = 20814, Name = "Storm Echo: " + original.Name,
                Type = "DirectDamage", Target = "Enemy", Range = original.Range, Radius = original.Radius,
                Damage = original.Damage * (avatar ? 2 : 1), DamageType = (int)original.DamageType,
                CastTime = 0, Power = 0, RecastDelay = 0, Icon = original.Icon, ClientEffect = original.ClientEffect
            }, original.Level);
        }

        public int TryEcho(ISpellHandler cast, GameLiving target)
        {
            if (!IsActive || IsEnding || !Owner.IsAlive || cast?.Caster != Owner || !IsEchoable(cast.Spell))
                return 0;
            if (!cast.Spell.IsPBAoE && (target == null || !target.IsAlive))
                return 0;
            Spell echo = BuildEcho(cast.Spell, StormforgedHeroicRules.HasAvatar(Owner));
            int count = 0;
            foreach (var pet in EchoSources().Distinct().ToArray())
            {
                if (!pet.IsAlive || pet.CurrentRegion != Owner.CurrentRegion || !Owner.IsWithinRadius(pet, 2000))
                    continue;
                pet.TargetObject = echo.IsPBAoE ? pet : target;
                if (pet.CastSpell(echo, SkillBase.GetSpellLine(GlobalSpellsLines.Mob_Spells)))
                    count++;
            }
            return count;
        }
    }

    public class StormforgedEyeEffect : StormforgedPermanentEffect
    {
        public StormforgedEyeEffect(in ECSGameEffectInitParams init) : base(init) { }

        public override void OnEffectPulse()
        {
            if (!Owner.IsAlive)
            {
                End();
                return;
            }
            if (Owner.IsCrowdControlled)
                return;
            foreach (var npc in Owner.GetNPCsInRadius((ushort)SpellHandler.Spell.Radius))
                StormforgedTravel.Pull(Owner, npc);
        }
    }
}
