using System.Collections.Generic;
using DOL.GS.Realm;

namespace DOL.GS.PlayerClass
{
    // Native client slot 64 (Midgard); took over the slot from the retired Stormforged.
    // Originally built on the daoc-offline-linux-server-bots project (class 65 there), migrated
    // to this server first as class 69 (to avoid colliding with PendragonSovereign), then moved
    // here to 64 once Stormforged was retired off the slot.
    [CharacterClass((int)eCharacterClass.Drengr, "Drengr", "Viking")]
    public class ClassDrengr : ClassWarrior
    {
        public ClassDrengr()
            : base()
        {
            m_manaStat = eStat.PIE;
        }

        public override eClassType ClassType => eClassType.Hybrid;

        public override List<PlayerRace> EligibleRaces => new List<PlayerRace>()
        {
            PlayerRace.Dwarf,
            PlayerRace.Kobold,
            PlayerRace.Norseman,
            PlayerRace.Troll,
        };
    }
}
