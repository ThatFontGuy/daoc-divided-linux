using System.Collections.Generic;

namespace DOL.GS.Spells
{
    /// <summary>
    /// The group around the caster that Metal Guard and Bolstering Roar reach: the caster's group members (and their
    /// pets) within the spell's radius, the caster excluded. Players and group bots alike.
    /// </summary>
    public static class TankShoutTargets
    {
        public static List<GameLiving> GroupAround(GameLiving caster, Spell spell)
        {
            List<GameLiving> list = GameLoop.GetListForTick<GameLiving>();
            Group group = caster.Group;

            if (group == null)
                return list;

            foreach (GameLiving member in group.GetMembersInTheGroup())
            {
                if (member == caster || !member.IsAlive || !caster.IsWithinRadius(member, spell.Radius))
                    continue;

                list.Add(member);

                if (member.ControlledBrain?.Body is GameNPC pet && pet.IsAlive && caster.IsWithinRadius(pet, spell.Radius))
                    list.Add(pet);
            }

            return list;
        }
    }
}
