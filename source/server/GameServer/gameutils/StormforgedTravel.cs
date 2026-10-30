using System;
using System.Linq;
using System.Numerics;
using DOL.AI.Brain;
using DOL.GS.ServerProperties;

namespace DOL.GS
{
    public static class StormforgedTravel
    {
        public static bool TryResolvePoint(GameLiving origin, Point3D requested, int range, out Point3D landing)
        {
            landing = null;
            if (origin == null || requested == null || range <= 0)
                return false;
            Zone zone = origin.CurrentRegion?.GetZone(requested.X, requested.Y);
            if (zone == null || !origin.IsWithinRadius(requested, range) || Math.Abs((long)requested.Z - origin.Z) > 400)
                return false;
            landing = new Point3D(requested.X, requested.Y, requested.Z);
            if (!zone.IsPathfindingEnabled)
                return true;
            var provider = PathfindingProvider.Instance;
            var filters = provider.DefaultFilters;
            Vector3? snapped = provider.GetClosestPoint(zone, new(requested.X, requested.Y, requested.Z), 64, 64, 128, filters);
            if (!snapped.HasValue || !provider.HasLineOfSight(zone, new(origin.X, origin.Y, origin.Z), snapped.Value, filters))
                return false;
            landing = new Point3D((int)snapped.Value.X, (int)snapped.Value.Y, (int)snapped.Value.Z);
            return origin.IsWithinRadius(landing, range) && origin.CurrentRegion.GetZone(landing.X, landing.Y) != null;
        }

        /// <summary>
        /// A spot about 90 units in front of the target, on the caster's side; the target's own spot if
        /// the ground there is unusable. A caster already that close stays where they are.
        /// </summary>
        public static Point3D ResolveBeside(GameLiving caster, GameLiving target)
        {
            double dx = caster.X - target.X, dy = caster.Y - target.Y;
            double distance = Math.Sqrt(dx * dx + dy * dy);
            if (distance <= 90)
                return new Point3D(caster.X, caster.Y, caster.Z);
            var beside = new Point3D(target.X + (int)(dx * 90 / distance), target.Y + (int)(dy * 90 / distance), target.Z);
            return TryResolvePoint(target, beside, 200, out Point3D landing) ? landing : new Point3D(target.X, target.Y, target.Z);
        }

        public static bool IsOwnedStorm(GameLiving owner, GameNPC pet) =>
            pet is TurretPet { NPCTemplate.TemplateId: 60171002 } && pet.IsAlive &&
            pet.ObjectState == GameObject.eObjectState.Active &&
            pet.Brain is IControlledBrain brain && brain.Owner == owner;

        public static bool MoveStorm(GameLiving owner, TurretPet storm, Point3D destination)
        {
            if (!IsOwnedStorm(owner, storm) || storm.CurrentRegion != owner.CurrentRegion)
                return false;
            var summonEffects = storm.effectListComponent.GetSpellEffects(eEffect.Pet)
                .Where(effect => effect.IsActive && !effect.IsEnding && effect.SpellHandler.Caster == owner).ToArray();
            if (summonEffects.Length == 0 || !storm.MoveInRegion(owner.CurrentRegionID,
                    destination.X, destination.Y, destination.Z, storm.Heading, true))
                return false;
            foreach (var effect in summonEffects)
            {
                effect.Duration = 120000;
                effect.ExpireTick = GameLoop.GameLoopTime + 120000;
            }
            AutonomousPetSupport.RegisterFieldTurret(owner, storm, 120000);
            return true;
        }

        public static int RecallStorms(GameLiving owner, Point3D destination)
        {
            var storms = AutonomousPetSupport.OwnedFieldTurrets(owner).Select(entry => entry.Turret)
                .Where(storm => IsOwnedStorm(owner, storm) && storm.CurrentRegion == owner.CurrentRegion).ToArray();
            if (storms.Length == 0)
                return 0;
            if (!StormforgedTurretRules.IsStormOwner(owner) && Properties.TURRET_AREA_CAP_COUNT > 0)
            {
                int otherStorms = owner.CurrentRegion.GetNPCsInRadius(destination, (ushort)Properties.TURRET_AREA_CAP_RADIUS)
                    .Count(npc => npc is TurretFnfPet && !storms.Contains(npc));
                if (otherStorms + storms.Length > Properties.TURRET_AREA_CAP_COUNT)
                    return -1;
            }
            return storms.Count(storm => MoveStorm(owner, storm, destination));
        }

        public static bool CanPull(GameLiving owner, GameNPC target) => target != null && target != owner &&
            target.IsAlive && target.ObjectState == GameObject.eObjectState.Active &&
            target.CurrentRegion == owner.CurrentRegion && target is not GameTrainingDummy &&
            !target.HasAbility(Abilities.CCImmunity) && !target.HasAbility(Abilities.RootImmunity) &&
            GameServer.ServerRules.IsAllowedToAttack(owner, target, true);

        public static bool Pull(GameLiving owner, GameNPC target)
        {
            if (!CanPull(owner, target))
                return false;
            double dx = target.X - owner.X, dy = target.Y - owner.Y;
            double distance = Math.Sqrt(dx * dx + dy * dy);
            if (distance <= 110)
                return false;
            var nearOwner = new Point3D(owner.X + (int)(dx * 90 / distance), owner.Y + (int)(dy * 90 / distance), owner.Z);
            if (!TryResolvePoint(target, nearOwner, 700, out Point3D landing) ||
                !target.MoveInRegion(owner.CurrentRegionID, landing.X, landing.Y, landing.Z, target.Heading, true))
                return false;
            if (target.Brain is StandardMobBrain brain)
                brain.AddToAggroList(owner, 1);
            owner.Stealth(false);
            return true;
        }
    }
}
