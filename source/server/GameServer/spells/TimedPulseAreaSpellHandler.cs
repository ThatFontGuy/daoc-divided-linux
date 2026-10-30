using System.Collections.Generic;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// A timed pulsing area (live Bonedancer totems, Thane Swirling Thunder): for Duration seconds, every Frequency ms
    /// (first at once), the SubSpellID spell is cast on each living in Radius of the area's centre, up to Value of them
    /// (0: no cap): enemies for a harmful child, realm members otherwise. The centre (LifeDrainReturn):
    ///   0 FOLLOW  — moves with the caster (Swirling Thunder);
    ///   1 TARGET  — the target's spot when the spell lands (the damage and snare totems);
    ///   2 FEET    — the caster's spot (Sable and Protection Totems).
    ///   3 PHANTOM — the target's spot, like TARGET, but kept apart from totems (Bonedancer Bone Phantoms..Revenants,
    ///               phantoms that seek enemies near where they were sent).
    /// A caster has one area per kind (following, a placed totem, phantoms): a new one replaces the old.
    /// </summary>
    [SpellHandler(eSpellType.TimedPulseArea)]
    public class TimedPulseAreaSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public const int FOLLOW = 0;
        public const int TARGET = 1;
        public const int FEET = 2;
        public const int PHANTOM = 3;
        private const string PROPERTY = "TIMED_PULSE_AREA_";

        public override string ShortDescription
        {
            get
            {
                Spell child = SkillBase.GetSpellByID(Spell.SubSpellID);
                string what = child == null ? "an effect" : ScriptMgr.CreateSpellHandler(Caster, child, SpellLine)?.ShortDescription ?? child.Name;
                return $"Every {Spell.Frequency / 1000.0:0.#} seconds for {Spell.Duration / 1000} seconds, within {Spell.Radius} units: {what}";
            }
        }

        public override bool StartSpell(GameLiving target)
        {
            Spell child = SkillBase.GetSpellByID(Spell.SubSpellID);
            if (child == null || Spell.Frequency <= 0 || Spell.Duration <= 0)
                return false;

            int mode = Spell.LifeDrainReturn;
            bool atTarget = mode is TARGET or PHANTOM;
            if (atTarget && target == null)
                return false;

            GameObject anchor = mode == FOLLOW ? Caster : null;
            Point3D spot = atTarget ? new Point3D(target.X, target.Y, target.Z) : new Point3D(Caster.X, Caster.Y, Caster.Z);
            ushort region = Caster.CurrentRegionID;
            string key = PROPERTY + (mode switch { FOLLOW => "FOLLOW", PHANTOM => "PHANTOM", _ => "PLACED" });

            Caster.TempProperties.GetProperty<ECSGameTimer>(key)?.Stop();

            long ends = GameLoop.GameLoopTime + Spell.Duration;
            ECSGameTimer timer = null;
            timer = new ECSGameTimer(Caster, _ =>
            {
                if (!Caster.IsAlive || Caster.ObjectState != GameObject.eObjectState.Active || Caster.CurrentRegionID != region ||
                    GameLoop.GameLoopTime > ends)
                {
                    Caster.TempProperties.RemoveProperty(key);
                    return 0;
                }

                Point3D centre = anchor != null ? new Point3D(anchor.X, anchor.Y, anchor.Z) : spot;
                Pulse(child, centre, region);
                return Spell.Frequency;
            });
            Caster.TempProperties.SetProperty(key, timer);
            timer.Start(1);
            return true;
        }

        /// <summary>One pulse: the child on each eligible living in the area, nearest first.</summary>
        private void Pulse(Spell child, Point3D centre, ushort region)
        {
            List<GameLiving> found = new();
            foreach (GamePlayer player in WorldMgr.GetPlayersCloseToSpot(region, centre.X, centre.Y, centre.Z, (ushort) Spell.Radius))
                found.Add(player);
            foreach (GameNPC npc in WorldMgr.GetNPCsCloseToSpot(region, centre.X, centre.Y, centre.Z, (ushort) Spell.Radius))
                found.Add(npc);

            found.Sort((a, b) => a.GetDistanceTo(centre).CompareTo(b.GetDistanceTo(centre)));
            int cap = Spell.Value > 0 ? (int) Spell.Value : int.MaxValue;
            int hit = 0;

            foreach (GameLiving living in found)
            {
                if (hit >= cap)
                    break;
                if (!living.IsAlive || !Affects(child, living))
                    continue;

                ScriptMgr.CreateSpellHandler(Caster, child, SpellLine)?.StartSpell(living);
                hit++;
            }
        }

        private bool Affects(Spell child, GameLiving living) => child.IsHarmful
            ? GameServer.ServerRules.IsAllowedToAttack(Caster, living, true)
            : GameServer.ServerRules.IsSameRealm(Caster, living, true);

        public override void SendSpellMessages()
        {
            MessageToCaster($"You call {Spell.Name}!", eChatType.CT_Spell);
        }
    }

    /// <summary>Sable Totem's pulse: spells of the affected can't be interrupted while it lasts.</summary>
    [SpellHandler(eSpellType.UninterruptibleAura)]
    public class UninterruptibleAuraSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "The target's spells cannot be interrupted.";

        public static bool Protects(GameLiving living) =>
            living != null && living.effectListComponent.ContainsEffectForEffectType(eEffect.UninterruptibleAura);
    }
}
