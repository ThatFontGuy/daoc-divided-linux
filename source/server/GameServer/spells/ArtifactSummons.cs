using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.Events;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
    /// <summary>
    /// Items summoned by artifacts. Sun weapons come by day, Moon weapons by night, and each set is lost if its owner dies
    /// at the wrong time of day (1.68). Everything summoned vanishes on logout.
    /// </summary>
    public static partial class ArtifactSummons
    {
        public const int Sun = 1;
        public const int Moon = 2;
        public const int Trident = 3;
        public const int Javelin = 4;
        public const int Harp = 5;
        public const int BladeShadow = 6;
        public const int LightStone = 7;
        public const int DarkStone = 8;
        public const int StoneStaffBinding = 9;
        public const int StoneStaffPower = 10;

        public static IReadOnlyList<string> ItemsFor(int set, eCharacterClass characterClass, eRealm realm)
        {
            string suffix = realm switch { eRealm.Midgard => "M", eRealm.Hibernia => "H", _ => string.Empty };

            return set switch
            {
                Sun => SunByClass.TryGetValue(characterClass, out string[] weapons) ? weapons : [],
                Moon => ["Moon_Mace" + suffix, "Moon_Staff"],
                Trident => ["Golden_Trident_of_Flame" + suffix],
                Javelin => ["Artef_Javelin"],
                Harp => characterClass is eCharacterClass.Bard or eCharacterClass.Minstrel ? ["Phoebus_Summoned_Harp"] : [],
                BladeShadow => ["Blade_Shadow" + suffix],
                LightStone => ["Eerie_Light_Stone"],
                DarkStone => ["Eerie_Dark_Stone"],
                StoneStaffBinding => ["Stone_Staff_Binding"],
                StoneStaffPower => ["Stone_Staff_Power"],
                _ => []
            };
        }

        public static bool IsSummoned(string id) => AllSummoned.Contains(id);

        /// <summary>Whether a summoned item is lost when its owner releases at this time of day.</summary>
        public static bool LostOnDeath(string id, bool night)
        {
            return night ? id.StartsWith("Sun_") : id.StartsWith("Moon_");
        }

        private static void Remove(GamePlayer player, Func<string, bool> shouldGo)
        {
            lock (player.Inventory.Lock)
            {
                foreach (DbInventoryItem item in player.Inventory.GetItemRange(eInventorySlot.MinEquipable, eInventorySlot.LastBackpack).ToList())
                {
                    if (IsSummoned(item.Id_nb) && shouldGo(item.Id_nb))
                        player.Inventory.RemoveItem(item);
                }
            }
        }

        public static void OnOwnerReleased(DOLEvent e, object sender, EventArgs arguments)
        {
            if (sender is GamePlayer player)
            {
                bool night = player.CurrentRegion.IsNightTime;
                Remove(player, id => LostOnDeath(id, night));
            }
        }

        [GameServerStartedEvent]
        public static void OnServerStart(DOLEvent e, object sender, EventArgs arguments)
        {
            GameEventMgr.AddHandler(GamePlayerEvent.GameEntered, OnOwnerEntered);
        }

        // A dropped connection or a crash logs out without the Quit event, so anything left over goes at the next login.
        private static void OnOwnerEntered(DOLEvent e, object sender, EventArgs arguments)
        {
            if (sender is GamePlayer player)
                Remove(player, _ => true);
        }

        public static void OnOwnerQuit(DOLEvent e, object sender, EventArgs arguments)
        {
            if (sender is not GamePlayer player)
                return;

            Remove(player, _ => true);
            GameEventMgr.RemoveHandler(player, GamePlayerEvent.Released, OnOwnerReleased);
            GameEventMgr.RemoveHandler(player, GamePlayerEvent.Quit, OnOwnerQuit);
        }
    }

    /// <summary>Value picks the set in <see cref="ArtifactSummons"/>.</summary>
    [SpellHandler(eSpellType.ArtifactSummonItems)]
    public class ArtifactSummonItemsSpellHandler(GameLiving caster, Spell spell, SpellLine line) : SpellHandler(caster, spell, line)
    {
        public override string ShortDescription => "Summons items into your backpack.";

        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            // The timer starts with the cast, so a class with nothing to summon hears it now, not after it is spent.
            if (Caster is GamePlayer player && (eCharacterClass) player.CharacterClass.ID is not eCharacterClass.Skald &&
                ArtifactSummons.ItemsFor((int) Spell.Value, (eCharacterClass) player.CharacterClass.ID, player.Realm).Count == 0)
            {
                MessageToCaster("This artifact has nothing to give your class.", eChatType.CT_SpellResisted);
                return false;
            }

            bool night = Caster.CurrentRegion.IsNightTime;

            if ((int) Spell.Value == ArtifactSummons.Sun && night)
            {
                MessageToCaster("The powers of the Belt of the Sun can only be summoned under the sun!", eChatType.CT_SpellResisted);
                return false;
            }

            if ((int) Spell.Value == ArtifactSummons.Moon && !night)
            {
                MessageToCaster("The powers of the Belt of the Moon can only be summoned under the moon!", eChatType.CT_SpellResisted);
                return false;
            }

            return base.CheckBeginCast(selectedTarget);
        }

        public override void ApplyEffectOnTarget(GameLiving target)
        {
            if (Caster is not GamePlayer player)
                return;

            // Skalds cannot play the harp, so the necklace gives them an aura instead (1.67 hot fix).
            if ((int) Spell.Value == ArtifactSummons.Harp && (eCharacterClass) player.CharacterClass.ID is eCharacterClass.Skald)
            {
                if (SkillBase.GetSpellByID(Spell.ResurrectHealth) is { } aura)
                    ScriptMgr.CreateSpellHandler(player, aura, SpellLine).StartSpell(player);

                return;
            }

            foreach (string id in ArtifactSummons.ItemsFor((int) Spell.Value, (eCharacterClass) player.CharacterClass.ID, player.Realm))
            {
                DbItemTemplate template = GameServer.Database.FindObjectByKey<DbItemTemplate>(id);

                if (template == null)
                    continue;

                DbInventoryItem held = player.Inventory.GetFirstItemByID(id, eInventorySlot.MinEquipable, eInventorySlot.LastBackpack);

                // Summoning again refills a charged item; anything else is already all it can be.
                if (held != null && (held.MaxCharges <= 0 || !player.Inventory.RemoveItem(held)))
                    continue;

                DbInventoryItem item = GameInventoryItem.Create(template);

                if (player.Inventory.AddItem(eInventorySlot.FirstEmptyBackpack, item))
                {
                    InventoryLogging.LogInventoryAction(player, player, eInventoryActionType.Other, template, item.Count);
                    MessageToCaster("Item created: " + item.GetName(0, false), eChatType.CT_System);
                }
            }

            GameEventMgr.AddHandlerUnique(player, GamePlayerEvent.Released, ArtifactSummons.OnOwnerReleased);
            GameEventMgr.AddHandlerUnique(player, GamePlayerEvent.Quit, ArtifactSummons.OnOwnerQuit);
        }
    }
}
