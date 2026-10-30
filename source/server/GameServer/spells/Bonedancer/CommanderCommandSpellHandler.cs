using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Live Bonedancer commands (1.122B): the Bonedancer orders its commander to cast SubSpellID on the target at once
    /// (Familiar Dart..Defeat, Ghostly..Deathly Wail, Punish Combatant..Soldier). The commander's level and range count.
    /// </summary>
    [SpellHandler(eSpellType.CommanderCommand)]
    public class CommanderCommandSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription
        {
            get
            {
                Spell order = SkillBase.GetSpellByID(Spell.SubSpellID);
                string what = order == null ? "a spell" : ScriptMgr.CreateSpellHandler(Caster, order, SpellLine)?.ShortDescription ?? order.Name;
                return $"Your commander casts: {what}";
            }
        }

        private CommanderPet Commander => Caster.ControlledBrain?.Body as CommanderPet;

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if (Commander is not { IsAlive: true })
            {
                MessageToCaster("You need a commander to do that.", eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }

        // The child, not this order, carries the effect; the base cast would also fire the SubSpellID from the caster.
        public override void CastSubSpells(GameLiving target) { }

        public override bool StartSpell(GameLiving target)
        {
            CommanderPet commander = Commander;
            Spell order = SkillBase.GetSpellByID(Spell.SubSpellID);

            if (commander is not { IsAlive: true } || order == null || target == null)
                return false;

            if (order.Range > 0 && !commander.IsWithinRadius(target, order.Range))
            {
                MessageToCaster("Your commander is too far away.", eChatType.CT_SpellResisted);
                return false;
            }

            ScriptMgr.CreateSpellHandler(commander, order, SpellLine)?.StartSpell(target);
            return true;
        }

        public override void SendSpellMessages()
        {
            MessageToCaster($"You command your commander: {Spell.Name}!", eChatType.CT_Spell);
        }
    }
}
