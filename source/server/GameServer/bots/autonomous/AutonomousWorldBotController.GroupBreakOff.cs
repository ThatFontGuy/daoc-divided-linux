using System.Linq;
using DOL.AI.Brain;

namespace DOL.GS
{
    public sealed partial class AutonomousWorldBotController
    {
        private const long BreakOffCheckMilliseconds = 1_500;
        private const long BreakOffCooldownMilliseconds = 45_000;
        private long _nextBreakOffTick;

        /// <summary>
        /// An autonomous party that has lost the fight runs instead of dying one by one (playtest 2026-10-31: a party held on
        /// through a level 62 and 65 camp until all five were dead). True consumes this turn. The player's own group is left
        /// to the player, who has /bots follow.
        /// </summary>
        private bool TryGroupBreakOff(BotBrain brain, GameBot bot, long now)
        {
            if (now < _nextBreakOffTick || bot.Group == null || _groupDirective?.IsDynamic != true)
                return false;
            _nextBreakOffTick = now + BreakOffCheckMilliseconds;

            GameBot[] party = bot.Group.GetMembersInTheGroup().OfType<GameBot>().ToArray();
            GameNPC[] foes = bot.attackComponent?.AttackerTracker?.Attackers?.OfType<GameNPC>()
                .Where(npc => npc.IsAlive && npc is not GameBot).ToArray() ?? [];
            if (foes.Length == 0)
                return false;
            bool Healer(GameBot member) => member.CharacterClass != null &&
                                           BotPartyRoles.IsHealingClass((eCharacterClass)member.CharacterClass.ID);
            if (!AutonomousRouteThreatPolicy.ShouldBreakOff(party.Length, party.Count(member => member.IsAlive),
                    party.Any(Healer), party.Any(member => member.IsAlive && Healer(member)), foes.Max(npc => npc.HealthPercent),
                    foes.Max(npc => ConLevels.GetConColor(bot.GetConLevel(npc)))))
                return false;

            IPathfindingMgr nav = PathfindingProvider.Instance;
            Zone zone = bot.CurrentZone;
            if (zone == null || !nav.IsAvailable || !nav.HasNavmesh(zone))
                return false;
            _nextBreakOffTick = now + BreakOffCooldownMilliseconds;
            Log.Info($"AUTONOMOUS_GROUP_BREAK_OFF bot={bot.Name} id={bot.DatabaseID} class=\"{bot.ClassName}\" alive={party.Count(member => member.IsAlive)}/{party.Length} " +
                     $"foes={foes.Length} foe=\"{foes[0].Name}\" foeLevel={foes[0].Level} zone=\"{zone.Description}\"");
            brain.PrepareForTankPull();
            BackAwayFrom(bot, nav, zone, foes[0], foes, AutonomousRouteThreatPolicy.RangedMargin, foes);
            return true;
        }
    }
}
