using System;
using System.Collections.Generic;
using DOL.GS.PacketHandler;
using DOL.GS.ServerProperties;

namespace DOL.GS
{
    /// <summary>
    /// Offline Champion Levels: realm points earned at level 50 become champion experience (cl_rp_rate),
    /// CL1-15. Each realm has one Champion path that trains itself: reaching a Champion Level grants that
    /// level's ability (RealmChampionSpecialization, ChampionAbilities). Champion training starts on its own
    /// at level 50; there is no king quest or champion trainer.
    /// </summary>
    public static class ChampionRules
    {
        public static long ToChampionExperience(long realmPoints, double rate) =>
            realmPoints <= 0 || rate <= 0 ? 0 : (long)Math.Min(long.MaxValue / 2, realmPoints * rate);

        public static string PathFor(eRealm realm) => realm switch
        {
            eRealm.Albion => "ChampionAlbion",
            eRealm.Midgard => "ChampionMidgard",
            eRealm.Hibernia => "ChampionHibernia",
            _ => null
        };

        public static void GainRealmPoints(GamePlayer player, long realmPoints)
        {
            if (player.Level < GamePlayer.MAX_LEVEL || PathFor(player.Realm) == null || player.ChampionLevel >= GamePlayer.CL_MAX_LEVEL)
                return;
            long experience = ToChampionExperience(realmPoints, Properties.CL_RP_RATE);
            if (experience <= 0)
                return;
            MasterLevelRules.EnsureTraining(player);
            // Quest source: the amount is already converted, so skip the old XP-based conversion.
            player.GainChampionExperience(experience, eXPSource.Quest);
        }
    }

    /// <summary>
    /// A realm's Champion path (KeyName ChampionAlbion / ChampionMidgard / ChampionHibernia). Its spell line
    /// level is the player's Champion Level, so each CL unlocks the next ability; other realms see nothing.
    /// </summary>
    public class RealmChampionSpecialization : CareerSpecialization
    {
        public RealmChampionSpecialization(string keyname, string displayname, ushort icon, int ID)
            : base(keyname, displayname, icon, ID)
        {
        }

        public eRealm Realm => KeyName switch
        {
            "ChampionAlbion" => eRealm.Albion,
            "ChampionMidgard" => eRealm.Midgard,
            "ChampionHibernia" => eRealm.Hibernia,
            _ => eRealm.None
        };

        public bool IsFor(GameLiving living) => living is GamePlayer player && player.Realm == Realm;

        public override int GetSpecLevelForLiving(GameLiving living) => living is GamePlayer player && IsFor(player) ? player.ChampionLevel : 0;

        public override List<SpellLine> GetSpellLinesForLiving(GameLiving living) =>
            IsFor(living) ? GetSpellLinesForLiving(living, GetSpecLevelForLiving(living)) : new List<SpellLine>();

        public override IDictionary<SpellLine, List<Skill>> GetLinesSpellsForLiving(GameLiving living) =>
            IsFor(living) && GetSpecLevelForLiving(living) > 0
                ? GetLinesSpellsForLiving(living, GetSpecLevelForLiving(living))
                : new Dictionary<SpellLine, List<Skill>>();

        protected override List<Ability> GetAbilitiesForLiving(GameLiving living, int level) => new List<Ability>();
    }
}
