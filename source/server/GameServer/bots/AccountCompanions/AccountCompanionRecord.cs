using DOL.Database;
using DOL.Database.Attributes;

namespace DOL.GS
{
    /// <summary>
    /// Companion-only data for one character on a player's account. The character itself
    /// (level, experience, specializations, equipment, position) stays in the normal character
    /// and inventory tables, so it is playable as usual. This row only remembers the bot's
    /// training plan so it keeps training the same build every time it is summoned.
    /// </summary>
    [DataTable(TableName = "account_companions")]
    public sealed class AccountCompanionRecord : DataObject
    {
        [PrimaryKey(AutoIncrement = true)] public long Id { get; set; }
        [DataElement(AllowDbNull = false, Index = true, Varchar = 255)] public string CharacterId { get; set; } = string.Empty;
        [DataElement(AllowDbNull = false)] public string Style { get; set; } = string.Empty;
        [DataElement(AllowDbNull = false)] public string BuildPlan { get; set; } = string.Empty;
        [DataElement(AllowDbNull = false)] public string LastSummonedUtc { get; set; } = string.Empty;
        // Off by default (and for rows saved before this column existed): the owner trains the
        // companion's lines by hand with /companion spec. On, it spends free points along BuildPlan.
        [DataElement(AllowDbNull = false)] public bool AutoTrain { get; set; }
    }
}
