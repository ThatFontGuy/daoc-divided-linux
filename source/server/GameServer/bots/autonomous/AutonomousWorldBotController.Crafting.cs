using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using DOL.Database;

namespace DOL.GS
{
    public sealed partial class AutonomousWorldBotController
    {
        private enum eCraftTripPhase
        {
            Start,
            Master,
            Shop,
            Station,
            Work,
            Done,
        }

        /// <summary>Longest walk to one stop of a craft trip before the trip ends.</summary>
        private const long CraftLegMilliseconds = 8 * 60_000;

        private string _craftAssignment = string.Empty;
        private eCraftTripPhase _craftPhase;
        private CraftNPC _craftMaster;
        private GameMerchant _craftMerchant;
        private GameStaticItem _craftStation;
        private AutonomousBotCrafting.Session _craftSession;
        private AutonomousBotCrafting.Purchase _craftPurchase;
        private long _craftLegStartedTick;
        private long _craftWorkDoneTick;
        private int _craftMade;

        /// <summary>
        /// The executor of <see cref="eAutonomousActivity.Craft"/>, one between-task trip: join an order if the bot has no
        /// craft, buy the materials, walk to a station and work there. True while the trip uses this turn; false when it is over.
        /// </summary>
        private bool HandleCraftTrip(GameBot bot)
        {
            string assignment = bot.PersistentRecord?.ObjectiveAssignmentId ?? string.Empty;
            if (!string.Equals(_craftAssignment, assignment, StringComparison.Ordinal))
            {
                _craftAssignment = assignment;
                _craftPhase = eCraftTripPhase.Start;
                _craftSession = null;
                _craftMade = 0;
                AutonomousBotCrafting.ForgetTrip(bot);
            }
            if (!AutonomousBotCrafting.Enabled)
                _craftPhase = eCraftTripPhase.Done;
            switch (_craftPhase)
            {
                case eCraftTripPhase.Start:
                    if (AutonomousBotCrafting.IsTrained(bot))
                        return BeginCraftShopping(bot);
                    eCraftingSkill profession = AutonomousBotCrafting.ProfessionFor((eCharacterClass)bot.CharacterClass.ID, bot.CharacterClass.ClassType, bot.DatabaseID);
                    _craftMaster = NearestByTravel(bot, AutonomousBotCrafting.MastersOf(profession, bot.Realm));
                    if (_craftMaster == null)
                        return EndCraftTrip(bot, "No craft master of this order is in reach");
                    SetCraftLeg(eCraftTripPhase.Master);
                    return true;
                case eCraftTripPhase.Master:
                    if (WalkToCraftStop(bot, _craftMaster, Math.Max(32, GS.ServerProperties.Properties.WORLD_PICKUP_DISTANCE) - 16, "Join a crafting order"))
                        return true;
                    if (!bot.IsWithinRadius(_craftMaster, GS.ServerProperties.Properties.WORLD_PICKUP_DISTANCE))
                        return EndCraftTrip(bot, "Could not reach the craft master");
                    AutonomousBotCrafting.Train(bot, _craftMaster);
                    return BeginCraftShopping(bot);
                case eCraftTripPhase.Shop:
                    if (WalkToCraftStop(bot, _craftMerchant, Math.Max(32, GS.ServerProperties.Properties.WORLD_PICKUP_DISTANCE) - 16, "Buy crafting materials"))
                        return true;
                    if (!AutonomousBotCrafting.TryBuy(bot, _craftMerchant, _craftPurchase))
                        return EndCraftTrip(bot, "Could not buy the materials");
                    return NextCraftPurchase(bot);
                case eCraftTripPhase.Station:
                    if (_craftStation != null && WalkToCraftStop(bot, _craftStation, AbstractCraftingSkill.CRAFT_DISTANCE - 64, "Work at a crafting station"))
                        return true;
                    if (_craftStation != null && !bot.IsWithinRadius(_craftStation, AbstractCraftingSkill.CRAFT_DISTANCE))
                        return EndCraftTrip(bot, "Could not reach the crafting station");
                    bot.StopMovingOnPath();
                    bot.StopMoving();
                    _craftWorkDoneTick = GameLoop.GameLoopTime + AutonomousBotCrafting.WorkSeconds(bot, _craftSession) * 1000L;
                    _craftPhase = eCraftTripPhase.Work;
                    SetStatus(bot, $"Crafting {_craftSession.Recipe.Product.Name}",
                        _craftSession.OrderId != null ? "Make a piece another bot paid for" : "Craft real items at a real station",
                        $"Skill {AutonomousBotCrafting.SkillValue(bot.PersistentRecord.SerializedCraftingSkills, _craftSession.Skill)} {_craftSession.Skill}", string.Empty);
                    return true;
                case eCraftTripPhase.Work:
                    if (bot.IsMoving)
                    {
                        // A moved crafter loses the attempt, as a player does.
                        _craftPhase = eCraftTripPhase.Station;
                        return true;
                    }
                    if (GameLoop.GameLoopTime < _craftWorkDoneTick)
                        return true;
                    DbInventoryItem made = AutonomousBotCrafting.Attempt(bot, _craftSession, out bool stop);
                    if (made != null)
                        _craftMade++;
                    if (stop || _craftMade >= _craftSession.Copies)
                        return EndCraftTrip(bot, $"Finished at the station; made {_craftMade}");
                    _craftPhase = eCraftTripPhase.Station;
                    return true;
                default:
                    return false;
            }
        }

        private void SetCraftLeg(eCraftTripPhase phase)
        {
            _craftPhase = phase;
            _craftLegStartedTick = GameLoop.GameLoopTime;
        }

        private bool EndCraftTrip(GameBot bot, string reason)
        {
            _craftPhase = eCraftTripPhase.Done;
            AutonomousBotCrafting.MarkTripDone(bot);
            bot.StopMovingOnPath();
            bot.StopMoving();
            // The end of the trip is the crafter's task break: commissioned pieces go to their buyers now.
            int delivered = AutonomousBotCraftOrders.Enabled ? AutonomousBotCraftOrders.Deliver(bot) : 0;
            SetStatus(bot, "Done crafting", "Use or sell what was made", delivered > 0 ? $"{reason}; delivered {delivered} order(s)" : reason);
            return false;
        }

        private bool BeginCraftShopping(GameBot bot)
        {
            _craftSession = AutonomousBotCrafting.PlanSession(bot);
            if (_craftSession == null)
                return EndCraftTrip(bot, "Nothing to craft at this skill and purse");
            return NextCraftPurchase(bot);
        }

        private bool NextCraftPurchase(GameBot bot)
        {
            AutonomousBotCrafting.Purchase purchase = AutonomousBotCrafting.ShoppingFor(bot, _craftSession).FirstOrDefault();
            if (purchase != null)
            {
                _craftPurchase = purchase;
                _craftMerchant = NearestByTravel(bot, AutonomousBotCrafting.Sellers(purchase.Material, bot.Realm));
                if (_craftMerchant == null)
                    return EndCraftTrip(bot, $"No merchant in reach sells {purchase.Material.Name}");
                SetCraftLeg(eCraftTripPhase.Shop);
                return true;
            }
            string station = AutonomousBotCrafting.StationFor(_craftSession.Skill, _craftSession.Recipe.Product.Object_Type,
                _craftSession.Recipe.Ingredients.Select(part => part.Material.Model));
            _craftStation = station == null ? null : NearestByTravel(bot, AutonomousBotCrafting.Stations(station));
            if (station != null && _craftStation == null)
                return EndCraftTrip(bot, $"No {station} in reach");
            SetCraftLeg(eCraftTripPhase.Station);
            return true;
        }

        private T NearestByTravel<T>(GameBot bot, IEnumerable<T> stops) where T : GameObject
        {
            HashSet<ushort> reachable = ReachableRegions(bot.Realm, bot.CurrentRegionID);
            return stops
                .Where(stop => stop.ObjectState == GameObject.eObjectState.Active && reachable.Contains(stop.CurrentRegionID) &&
                               stop.CurrentZone != null && IsZoneAccessible(bot.Realm, stop.CurrentZone) && stop.CurrentZone.IsDungeon == false &&
                               !(stop is GameNPC npc && AutonomousServiceReachability.IsSkipped(AutonomousServiceReachability.Key(npc), bot.DatabaseID, GameLoop.GameLoopTime)))
                .OrderBy(stop => EstimateTravelMinutes(bot, stop.CurrentRegionID, stop.X, stop.Y))
                .FirstOrDefault();
        }

        /// <summary>One turn of walking to a stop; false once the bot stands within <paramref name="radius"/> of it, or gives up.</summary>
        private bool WalkToCraftStop(GameBot bot, GameObject stop, int radius, string goal)
        {
            if (stop?.ObjectState is not GameObject.eObjectState.Active || GameLoop.GameLoopTime - _craftLegStartedTick > CraftLegMilliseconds)
            {
                if (stop is GameNPC npc)
                    AutonomousServiceReachability.ReportFailure(AutonomousServiceReachability.Key(npc), bot.DatabaseID, GameLoop.GameLoopTime);
                return false;
            }
            var destination = new CampDestination($"craft-{stop.ObjectID}", stop.Name, stop.CurrentZone?.Description ?? string.Empty,
                stop.CurrentRegionID, stop.X, stop.Y, stop.Z, 1, false, false);
            if (bot.CurrentRegionID != stop.CurrentRegionID)
            {
                CampDestination previous = _camp;
                _camp = destination;
                bool moving = TravelAcrossRegions(bot);
                _camp = previous;
                return moving;
            }
            if (bot.IsWithinRadius(stop, radius))
                return false;
            Vector3 raw = new(stop.X, stop.Y, stop.Z);
            if (!TryResolveConnectedApproach(bot, raw, Math.Max(16, radius - 16), out Vector3 point))
                point = raw;
            if (TryBeginFasterStableRoute(bot, point, stop.Name))
                return true;
            IssuePath(bot, point, preciseArrival: true);
            SetStatus(bot, $"Traveling to {stop.Name}", goal, "A craft trip between tasks", stop.Name, destination.ZoneName);
            return true;
        }
    }
}
