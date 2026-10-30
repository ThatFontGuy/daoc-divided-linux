using System;
using System.Collections.Generic;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>Shared lookup for effects read where they apply: the strongest active rank's Value.</summary>
    internal static class StrongestEffect
    {
        public static int Value(GameLiving living, eEffect type)
        {
            if (living?.effectListComponent == null)
                return 0;

            int best = 0;
            foreach (ECSGameSpellEffect effect in living.effectListComponent.GetSpellEffects(type))
            {
                if (effect.IsActive)
                    best = Math.Max(best, (int) effect.SpellHandler.Spell.Value);
            }

            return best;
        }
    }

    /// <summary>
    /// Shaman Frigg's Grace / Superior Grace (live 1.130a): heals cast on the target are Value% more effective
    /// (the client's ehealth formatter: +25/+50%). Read in HealSpellHandler.HealTarget.
    /// </summary>
    [SpellHandler(eSpellType.HealingReceivedBuff)]
    public class HealingReceivedBuffSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Heals cast on the target are {Spell.Value}% more effective.";

        public static int Percent(GameLiving living) => StrongestEffect.Value(living, eEffect.HealingReceivedBuff);
    }

    /// <summary>
    /// Enchanter Calming..Graceful Light (live 1.130a): heal spells cast by the target are Value% more effective (the
    /// client's heal_bonus formatter: bonus / 10 - 100, so 1050..1500 = +5..+50%). Read in HealSpellHandler.HealTarget.
    /// </summary>
    [SpellHandler(eSpellType.HealingDoneBuff)]
    public class HealingDoneBuffSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Heal spells cast by the target are {Spell.Value}% more effective.";

        public static int Percent(GameLiving living) => StrongestEffect.Value(living, eEffect.HealingDoneBuff);
    }

    /// <summary>
    /// Runemaster Dusk..Runic Empowerment (live 1.128c): a pulse raising the group's spell critical chance by Value%.
    /// Read in CriticalSpellHitChanceCalculator.
    /// </summary>
    [SpellHandler(eSpellType.SpellCritAura)]
    public class SpellCritAuraSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Increases the group's chance to critically hit with spells by {Spell.Value}%.";

        public static int Percent(GameLiving living) => StrongestEffect.Value(living, eEffect.SpellCritAura);
    }

    /// <summary>Sorcerer Mindfulness (live 1.130a, reset_qc): Quickcast can be used again at once.</summary>
    [SpellHandler(eSpellType.ResetQuickcast)]
    public class ResetQuickcastSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "Resets your Quickcast timer.";

        public override bool StartSpell(GameLiving target)
        {
            if (Caster is not GamePlayer player)
                return false;

            player.TempProperties.SetProperty(GamePlayer.QUICK_CAST_CHANGE_TICK, 0L);
            Skill quickcast = SkillBase.GetAbility(Abilities.Quickcast);
            if (quickcast != null)
                player.RemoveDisabledSkill(quickcast);
            MessageToCaster("Your mind clears: Quickcast is ready.", eChatType.CT_Spell);
            return true;
        }
    }

    /// <summary>
    /// Sorcerer Mass Gateway (live 1.125): the caster's group within Radius returns to its bind points. Members in
    /// combat stay behind.
    /// </summary>
    [SpellHandler(eSpellType.GroupBindRecall)]
    public class GroupBindRecallSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Returns your group within {Spell.Radius} units to its bind points. Members in combat stay behind.";

        public override bool StartSpell(GameLiving target)
        {
            List<GameLiving> members = Caster.Group?.GetMembersInTheGroup() ?? [Caster];

            foreach (GameLiving member in members)
            {
                if (member is not GamePlayer player || !player.IsAlive || player.InCombatPvE || player.InCombatPvP)
                    continue;
                if (player != Caster && (Spell.Radius <= 0 || !player.IsWithinRadius(Caster, Spell.Radius)))
                    continue;

                player.MoveToBind();
            }

            return true;
        }
    }

    /// <summary>Assassin Blur (live 1.121, shadow_step): teleports the caster to the target player; works while rooted.</summary>
    [SpellHandler(eSpellType.ShadowStep)]
    public class ShadowStepSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => $"Teleports you to a player within {Spell.Range} units.";

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if (selectedTarget is not GamePlayer || selectedTarget == Caster)
            {
                MessageToCaster("You must target another player.", eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }

        public override bool StartSpell(GameLiving target)
        {
            if (target is not GamePlayer || target == Caster || target.CurrentRegionID != Caster.CurrentRegionID ||
                !Caster.IsWithinRadius(target, Spell.Range))
                return false;

            Caster.MoveTo(target.CurrentRegionID, target.X, target.Y, target.Z, target.Heading);
            return true;
        }
    }
}
