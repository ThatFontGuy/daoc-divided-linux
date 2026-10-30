using System;
using DOL.GS.ServerProperties;

namespace DOL.GS
{
    public static class BotBuffUpkeep
    {
        public static bool CanRefresh(Spell requested, Spell existing, bool ownEffect,
            bool active, bool ending, long expires, long now)
        {
            int seconds = Properties.BUFF_UPKEEP_REFRESH_SECONDS;
            if (seconds <= 0 || requested == null || existing == null || requested.ID != existing.ID ||
                !ownEffect || !active || ending || requested.IsHarmful || requested.IsPulsing ||
                requested.Concentration > 0 || requested.Duration < 60_000)
                return false;
            // Never spend most of a short buff's life repeatedly refreshing it.
            long window = Math.Min((long)seconds * 1000, requested.Duration / 4);
            return expires > now && expires - now <= window;
        }
    }
}
