using DOL.Database;
using DOL.Database.Attributes;

namespace DOL.GS
{
    /// <summary>
    /// Marks a roster bot (offline_world_bots) as a battleground bracket bot. A separate table, so DividedRealms' own bot table
    /// is not changed. Bracket bots are not logged in by the normal population controller; BracketBotService does it.
    /// </summary>
    [DataTable(TableName = "divided_bracket_bots")]
    public class BracketBotRecord : DataObject
    {
        [PrimaryKey] public long BotId { get; set; }
        [DataElement(AllowDbNull = false)] public int BattlegroundRegion { get; set; }
        [DataElement(AllowDbNull = false)] public int Realm { get; set; }
        /// <summary>The bot never levels past this (the bracket's top level).</summary>
        [DataElement(AllowDbNull = false)] public int LevelCap { get; set; }
    }
}
