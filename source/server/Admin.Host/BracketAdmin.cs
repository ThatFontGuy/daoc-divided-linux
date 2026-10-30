using System;
using System.Collections.Generic;
using System.Linq;
using DaocServer.Admin;

namespace DOL.GS.Admin
{
    /// <summary>Admin operations for battleground bracket bots (daoc-divided-linux addition; see GameServer/bots/bracket).</summary>
    public static class BracketAdmin
    {
        public static List<BracketBgInfo> Status() =>
            BracketBotService.Status().Select(s => new BracketBgInfo(
                s.Name, s.Region, s.PlayersInside,
                BracketBotPlanner.Realms.Select(r => s.Roster[r]).ToList(),
                BracketBotPlanner.Realms.Select(r => s.Online[r]).ToList())).ToList();

        public static BracketCreateResult Create(string battleground, int countPerRealm)
        {
            var names = new List<string>();
            try
            {
                if (battleground.Equals("all", StringComparison.OrdinalIgnoreCase))
                {
                    for (int i = 0; i < BattlegroundBrackets.Count; i++)
                        names.AddRange(BracketBotService.Create(BattlegroundBrackets.Get(i).Name, countPerRealm));
                }
                else
                {
                    names.AddRange(BracketBotService.Create(battleground, countPerRealm));
                }
            }
            catch (ArgumentException exception)
            {
                throw new AdminException(AdminErrorCodes.Invalid, exception.Message);
            }
            return new BracketCreateResult(names);
        }
    }
}
