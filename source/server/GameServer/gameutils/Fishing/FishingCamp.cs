using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS.Fishing
{
    /// <summary>
    /// Camp kits (FishingCraft.Camps): using one from the backpack puts a campfire in front of the player, with a bedroll
    /// or tent beside it for the bigger kits. While it burns, the owner and their group (companion bots too) who are near
    /// it and out of combat get health, power and endurance back every few seconds, twice as fast for a player sitting
    /// down. A player has one camp at a time; it burns out after the kit's time, when the owner leaves the region or logs
    /// out, or on /fish camp break. Camps are plain GameStaticItems that are never saved.
    /// </summary>
    public static class FishingCamp
    {
        private const int TickMs = 3000;
        public const int Radius = 500;
        private const int FireDistance = 120;
        private const int ShelterDistance = 260;
        private const int MinSpacing = 600;

        private sealed class Camp
        {
            public readonly object Lock = new();
            public GamePlayer Owner;
            public FishingCampTier Tier;
            public ushort RegionId;
            public GameStaticItem Fire;
            public GameStaticItem Shelter;
            public long EndsAt;
            public ECSGameTimer Timer;
            public bool Ended;
        }

        private static readonly ConcurrentDictionary<string, Camp> Camps = new();

        public static bool IsCampKit(string templateId)
        {
            return FishingCraft.FindCamp(templateId) != null;
        }

        /// <summary>True when a burning campfire (anyone's) is within the camp radius: where fish can be cooked.</summary>
        public static bool IsNearCampfire(GameLiving living)
        {
            return BestCampNear(living) != null;
        }

        /// <summary>
        /// The best camp tier burning within the camp radius of <paramref name="living"/> (anyone's camp), or null. Fishing
        /// beside it adds the tier's FishingBonus.
        /// </summary>
        public static FishingCampTier BestCampNear(GameLiving living)
        {
            FishingCampTier best = null;

            foreach (Camp camp in Camps.Values)
            {
                if (!camp.Ended && camp.Fire.CurrentRegionID == living.CurrentRegionID && living.IsWithinRadius(camp.Fire, Radius)
                    && (best == null || camp.Tier.FishingBonus > best.FishingBonus))
                {
                    best = camp.Tier;
                }
            }

            return best;
        }

        /// <summary>Called from GamePlayer.UseSlot for a camp kit. The kit is used up only when the camp goes up.</summary>
        public static void TryDeploy(GamePlayer player, DbInventoryItem kit)
        {
            FishingCampTier tier = FishingCraft.FindCamp(kit?.Id_nb);

            if (player == null || tier == null)
            {
                return;
            }

            string reason = CanDeployHere(player);

            if (reason != null)
            {
                player.Out.SendMessage(reason, eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            Point2D firePoint = player.GetPointFromHeading(player.Heading, FireDistance);
            GameStaticItem fire = Spawn(player, firePoint, FishingCraft.CampfireModel, $"{player.Name}'s campfire");

            if (fire == null)
            {
                player.Out.SendMessage("You can't make camp here.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            GameStaticItem shelter = null;

            if (tier.ShelterModel != 0)
            {
                ushort side = (ushort)((player.Heading + 1024) % 4096);
                Point2D shelterPoint = fire.GetPointFromHeading(side, ShelterDistance);
                shelter = Spawn(player, shelterPoint, tier.ShelterModel, $"{player.Name}'s {tier.ShelterName}");
            }

            if (!player.Inventory.RemoveCountFromStack(kit, 1))
            {
                fire.Delete();
                shelter?.Delete();

                return;
            }

            InventoryLogging.LogInventoryAction(player, "(camp)", eInventoryActionType.Other, kit.Template, 1);

            // One camp per player: the new one replaces the old.
            BreakCamp(player, null);

            Camp camp = new()
            {
                Owner = player,
                Tier = tier,
                RegionId = player.CurrentRegion.ID,
                Fire = fire,
                Shelter = shelter,
                EndsAt = GameLoop.GameLoopTime + tier.Minutes * 60_000L,
            };
            camp.Timer = new ECSGameTimer(fire)
            {
                Callback = timer => OnTick(camp)
            };
            Camps[player.ObjectId] = camp;
            camp.Timer.Start(TickMs);

            player.Out.SendMessage($"You make camp. The fire will burn for {tier.Minutes} minutes; rest near it to recover faster.", eChatType.CT_Important, eChatLoc.CL_SystemWindow);
        }

        /// <summary>Why the player can't make camp where they stand, or null if they can.</summary>
        private static string CanDeployHere(GamePlayer player)
        {
            if (!player.IsAlive)
            {
                return "You can't make camp while dead.";
            }

            if (player.InCombat)
            {
                return "You can't make camp while in combat.";
            }

            if (player.IsMoving || player.IsStrafing)
            {
                return "You must stand still to make camp.";
            }

            if (player.IsSwimming)
            {
                return "You can't make camp in the water.";
            }

            if (player.IsOnHorse || player.IsRiding)
            {
                return "Get down from your mount first.";
            }

            if (player.CurrentRegion == null || player.CurrentRegion.HousingEnabled || player.InHouse)
            {
                return "You can't make camp here.";
            }

            foreach (Camp other in Camps.Values)
            {
                if (!other.Ended && other.Owner != player && other.Fire.CurrentRegionID == player.CurrentRegionID && player.IsWithinRadius(other.Fire, MinSpacing))
                {
                    return "There is already a camp here.";
                }
            }

            return null;
        }

        private static GameStaticItem Spawn(GamePlayer player, Point2D point, int model, string name)
        {
            GameStaticItem item = new()
            {
                CurrentRegion = player.CurrentRegion,
                X = point.X,
                Y = point.Y,
                Z = player.Z,
                Heading = player.Heading,
                Realm = player.Realm,
                Model = (ushort)model,
                Name = name
            };

            return item.AddToWorld() ? item : null;
        }

        /// <summary>Tells the player about their camp: how long it has left, or that they have none.</summary>
        public static void ShowStatus(GamePlayer player)
        {
            if (!Camps.TryGetValue(player.ObjectId, out Camp camp) || camp.Ended)
            {
                player.Out.SendMessage("You have no camp. Make a camp kit with /fish craft and use it from your backpack.", eChatType.CT_System, eChatLoc.CL_SystemWindow);

                return;
            }

            long minutes = Math.Max(0, (camp.EndsAt - GameLoop.GameLoopTime) / 60_000L);
            player.Out.SendMessage($"Your {camp.Tier.Name.Replace(" Kit", string.Empty).ToLowerInvariant()} burns for about {minutes} more minute(s). Type /fish camp break to pack it up.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        /// <summary>Puts out the player's camp, if they have one, and tells them <paramref name="reason"/>.</summary>
        public static void BreakCamp(GamePlayer player, string reason)
        {
            if (player != null && Camps.TryGetValue(player.ObjectId, out Camp camp))
            {
                End(camp, reason);
            }
        }

        private static void End(Camp camp, string reason)
        {
            lock (camp.Lock)
            {
                if (camp.Ended)
                {
                    return;
                }

                camp.Ended = true;
            }

            camp.Timer?.Stop();
            camp.Fire?.Delete();
            camp.Shelter?.Delete();
            Camps.TryRemove(new KeyValuePair<string, Camp>(camp.Owner.ObjectId, camp));

            if (!string.IsNullOrEmpty(reason) && camp.Owner.ObjectState == GameObject.eObjectState.Active)
            {
                camp.Owner.Out.SendMessage(reason, eChatType.CT_System, eChatLoc.CL_SystemWindow);
            }
        }

        private static int OnTick(Camp camp)
        {
            if (camp.Ended)
            {
                return 0;
            }

            GamePlayer owner = camp.Owner;

            if (owner.ObjectState != GameObject.eObjectState.Active || owner.CurrentRegion == null || owner.CurrentRegion.ID != camp.RegionId)
            {
                End(camp, "Your campfire burns out.");

                return 0;
            }

            if (GameLoop.GameLoopTime >= camp.EndsAt)
            {
                End(camp, "Your campfire burns out.");

                return 0;
            }

            IEnumerable<GameLiving> campers = owner.Group != null ? owner.Group.GetMembersInTheGroup() : new GameLiving[] { owner };

            foreach (GameLiving living in campers)
            {
                Restore(living, camp);
            }

            return TickMs;
        }

        private static void Restore(GameLiving living, Camp camp)
        {
            if (living == null || !living.IsAlive || living.InCombat || living.ObjectState != GameObject.eObjectState.Active)
            {
                return;
            }

            if (living.CurrentRegionID != camp.RegionId || !living.IsWithinRadius(camp.Fire, Radius))
            {
                return;
            }

            // The buff bar icon; the effect ends itself once its owner is away from every burning fire.
            if (living is GamePlayer resting && !resting.effectListComponent.ContainsEffectForEffectType(eEffect.CampRest))
            {
                ECSGameEffectFactory.Create(new(resting, 0, 1), static (in ECSGameEffectInitParams i) => new CampRestECSGameEffect(i));
            }

            int percent = RestorePercent(camp.Tier, living is GamePlayer player && player.IsSitting);

            if (living.Health < living.MaxHealth)
            {
                living.ChangeHealth(camp.Fire, eHealthChangeType.Regenerate, Math.Max(1, living.MaxHealth * percent / 100));
            }

            if (living.MaxMana > 0 && living.Mana < living.MaxMana)
            {
                living.ChangeMana(camp.Fire, eManaChangeType.Regenerate, Math.Max(1, living.MaxMana * percent / 100));
            }

            if (living.Endurance < living.MaxEndurance)
            {
                living.ChangeEndurance(camp.Fire, eEnduranceChangeType.Regenerate, Math.Max(1, living.MaxEndurance * percent / 100));
            }
        }

        /// <summary>Percent of each maximum restored per camp tick.</summary>
        public static int RestorePercent(FishingCampTier tier, bool sitting)
        {
            return tier.RestorePercent * (sitting ? 2 : 1);
        }
    }
}
