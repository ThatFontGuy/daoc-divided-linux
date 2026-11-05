using System;
using System.Collections.Generic;
using System.Linq;
using DOL.AI.Brain;

namespace DOL.GS.Trials
{
    /// <summary>Master Level 9 trials: the City of Aerus, ending at the Phoenix.</summary>
    public static class Ml9
    {
        public const int KyrosFormSeconds = 30;
        public const int KyrosGrowthSeconds = 480;
        public const int LachlenHeals = 12;
        public const int KatriFloor = 87;
        public const int BypassX = 36296;
        public const int OperatorWalkSeconds = 60;

        private const int Statue = 993;
        private const int Sphinx = 1175;
        private const int Obelisk = 1823;
        private const int ChanZ = 12049;

        private static readonly ushort[] KyrosModels = { 1315, 1317, 1319, 1321 };
        private static readonly string[] KyrosShapes =
        {
            "Kyros squares his shoulders and raises a warrior's blade.",
            "Kyros's outline blurs into an enchanter's, and the air begins to crackle.",
            "Kyros becomes a wizard, and sparks gather at his fingertips.",
            "Kyros takes a spiritmaster's shape and calls something up from the stone.",
        };

        private static readonly TrialPoint[] Generators =
        {
            new(26298, 40302, 16268),
            new(43375, 40010, 16268),
            new(34885, 25469, 16268),
        };

        private static readonly TrialPoint[] Operators =
        {
            new(26500, 36964, 16321),
            new(40396, 41732, 16344),
            new(37672, 27327, 16312),
        };

        private static readonly TrialPoint[] CowardHides =
        {
            new(45339, 53840, 10328),
            new(42135, 52840, 10304),
        };

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return Wings();
            yield return Explorers();
            yield return Warlords();
            yield return Kings();
            yield return Scholars();
            yield return Patrol();
            yield return Host();
            yield return Guardians();
            yield return CentaursPatrol();
            yield return Phoenix();
        }

        /// <summary>Which of Kyros's four shapes he wears after this many seconds.</summary>
        public static int KyrosForm(int seconds) => seconds / KyrosFormSeconds % KyrosModels.Length;

        public static bool LachlenMayHeal(int healsDone) => healsDone < LachlenHeals;

        public static bool PastChan(int x, int z) => x > BypassX && Math.Abs(z - ChanZ) < 400;

        /// <summary>The Terrible's statues breed, but never past eight at once.</summary>
        public static int TerribleBrood(int alive) => Math.Max(0, Math.Min(Math.Max(1, alive), 8 - alive));

        /// <summary>The health percent the Phoenix cannot fall below with this many generators running.</summary>
        public static int PhoenixFloor(int generatorsUp) => Math.Clamp(generatorsUp, 0, 3) * 25;

        public static int PhoenixFireball(int generatorsUp) => Math.Clamp(generatorsUp, 0, 3) * 90;

        public static int PhoenixFlare(int generatorsUp) => Math.Clamp(generatorsUp, 0, 3) * 70;

        /// <summary>Counts seconds for a hook. Each key ticks once per call.</summary>
        internal static int Clock(TrialRun run, string key = "clock")
        {
            int seconds = run.Get(key, 0) + 1;
            run.Set(key, seconds);
            return seconds;
        }

        internal static TrialMob One(TrialRun run, string tag) => run.Mobs(tag).FirstOrDefault();

        internal static void Heal(TrialMob mob, double share) => mob?.ChangeHealth(mob, eHealthChangeType.Spell, (int)(mob.MaxHealth * share));

        internal static void Hurt(TrialRun run, GameLiving source, GameLiving target, int damage, eDamageType type) =>
            target.TakeDamage(source, type, (int)(damage * run.DamageScale), 0);

        internal static void HurtAround(TrialRun run, GameLiving source, GameObject center, int radius, int damage, eDamageType type)
        {
            foreach (GameLiving target in run.Hostiles(center, radius))
                Hurt(run, source, target, damage, type);
        }

        internal static GameLiving RandomTarget(TrialRun run, GameObject source, int radius)
        {
            List<GameLiving> targets = run.Hostiles(source, radius).ToList();
            return targets.Count == 0 ? null : targets[Util.Random(targets.Count - 1)];
        }

        /// <summary>Strikes around one random target, so a party that stands together takes it together.</summary>
        internal static void Splash(TrialRun run, GameLiving source, int reach, int radius, int damage, eDamageType type, string message)
        {
            GameLiving target = RandomTarget(run, source, reach);
            if (target == null)
                return;
            HurtAround(run, source, target, radius, damage, type);
            if (message != null)
                run.Tell(message);
        }

        /// <summary>Keeps a monster at or above a health percent. Floor 0 lets it die.</summary>
        internal static void HoldAt(TrialMob mob, int floor)
        {
            if (mob.HealthPercent < floor)
                mob.Health = mob.MaxHealth * floor / 100;
            mob.Immune = floor > 0 && mob.HealthPercent <= floor;
        }

        internal static void Root(TrialMob mob) => mob.MaxSpeedBase = 0;

        internal static void Calm(TrialRun run, string tag)
        {
            foreach (TrialMob mob in run.Mobs(tag))
                mob.Flags |= GameNPC.eFlags.PEACE;
        }

        /// <summary>Makes a dormant monster take damage and hunt the party.</summary>
        internal static void Wake(TrialRun run, string tag)
        {
            foreach (TrialMob mob in run.Mobs(tag))
            {
                mob.Immune = false;
                mob.Flags &= ~GameNPC.eFlags.PEACE;
                if (mob.Brain is StandardMobBrain brain)
                    brain.AggroRange = 1500;
            }
        }

        internal static TrialPoint Ring(TrialPoint center, int index, int count, int radius)
        {
            double angle = 2 * Math.PI * index / count;
            return new TrialPoint(center.X + (int)(radius * Math.Cos(angle)), center.Y + (int)(radius * Math.Sin(angle)), center.Z, center.Heading);
        }

        internal static TrialPoint Beside(GameObject thing, int offset = 150) => new(thing.X + offset, thing.Y, thing.Z, thing.Heading);

        private static void Remove(TrialRun run, TrialMob mob) => mob.Delete();

        private static TrialDefinition Wings() => new()
        {
            ML = 9,
            Step = 1,
            Name = "Wings of Aerus",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(41903, 30737, 8615, 3800),
            StarterName = "Statue of Kyros",
            StarterModel = 1315,
            Intro = "The stone eyes follow you. Kyros mastered every school of war before Aerus fell, and he has never once turned down a challenger. He will not fight you the same way twice.",
            Victory = "Kyros lowers his last borrowed weapon and returns to stone.",
            Replaces = new[] { "Kyros" },
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Kyros steps down from his plinth!",
                    Mobs = { new TrialMobSpec { Name = "Kyros", Model = 1315, Level = 65, Size = 150, Health = 90000, DamageFactor = 1.4, MeleeDamage = eDamageType.Slash, Tag = "kyros" } },
                    OnTick = KyrosTick,
                },
            },
        };

        private static void KyrosTick(TrialRun run)
        {
            int seconds = Clock(run);
            TrialMob kyros = One(run, "kyros");
            if (kyros == null)
                return;

            int form = KyrosForm(seconds);
            if (form != run.Get("form", -1))
            {
                run.Set("form", form);
                kyros.Model = KyrosModels[form];
                run.Tell(KyrosShapes[form]);
                if (form == 3)
                    run.Spawn(new TrialMobSpec { Name = "spirit of Kyros", Model = 1319, Level = 60, Size = 70, Health = 3000, DamageFactor = 0.7, At = Beside(kyros), Required = false });
            }

            if (form == 1 && seconds % 5 == 0)
                HurtAround(run, kyros, kyros, 500, 180, eDamageType.Energy);
            else if (form == 2 && seconds % 4 == 0)
                Splash(run, kyros, 1500, 50, 220, eDamageType.Cold, null);

            if (seconds == KyrosGrowthSeconds)
            {
                kyros.DamageFactor *= 1.5;
                run.Tell("Kyros is growing in power!");
            }
        }

        private static TrialDefinition Explorers() => new()
        {
            ML = 9,
            Step = 2,
            Name = "Lachlen's Explorers",
            Scope = TrialScope.Group,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(43461, 17329, 6921, 354),
            StarterName = "Lachlen's Porter",
            StarterModel = 997,
            Intro = "We walked off the edge of every map there was, and now the others won't know friend from stranger. Get past them and speak with Lachlen. He packs a remedy for every land he visits, but no pack is bottomless. Press him hard.",
            Victory = "Lachlen closes his journal for the last time.",
            Replaces = new[] { "Weary Explorer", "Lachlen" },
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The weary explorers turn on you!",
                    Mobs =
                    {
                        Explorer(40234, 17495, 6886),
                        Explorer(41016, 17481, 6886),
                        Explorer(43083, 16941, 6932),
                        Explorer(43599, 17134, 6903),
                        Explorer(44106, 16747, 6943),
                        Explorer(43461, 17329, 6921),
                    },
                },
                new TrialPhase
                {
                    Announce = "The way to Lachlen is clear. Speak with him.",
                    Mobs =
                    {
                        new TrialMobSpec
                        {
                            Name = "Lachlen", Model = 998, Level = 65, Size = 50, At = new TrialPoint(43889, 16264, 6911, 147), Objective = true,
                            ObjectiveText = "Lachlen looks up from his maps, sighs, and reaches for his sword.", OnDeath = Remove,
                        },
                    },
                },
                new TrialPhase
                {
                    Announce = "Lachlen will not let his last expedition end here!",
                    Mobs = { new TrialMobSpec { Name = "Lachlen", Model = 998, Level = 65, Size = 50, Health = 36000, DamageFactor = 1.2, At = new TrialPoint(43889, 16264, 6911, 147), MeleeDamage = eDamageType.Slash, Tag = "lachlen" } },
                    OnTick = LachlenTick,
                },
            },
        };

        private static TrialMobSpec Explorer(int x, int y, int z) => new()
        {
            Name = "Weary Explorer", Model = 997, Level = 60, Size = 37, Health = 3000, DamageFactor = 0.9, At = new TrialPoint(x, y, z), MeleeDamage = eDamageType.Slash,
        };

        private static void LachlenTick(TrialRun run)
        {
            int seconds = Clock(run);
            TrialMob lachlen = One(run, "lachlen");
            if (lachlen == null || seconds % 5 != 0 || lachlen.HealthPercent >= 100)
                return;

            int heals = run.Get("heals", 0);
            if (LachlenMayHeal(heals))
            {
                Heal(lachlen, 0.06);
                run.Set("heals", ++heals);
                if (!LachlenMayHeal(heals))
                    run.Tell("Lachlen reaches into his pack and finds it empty!");
            }
        }

        private static TrialDefinition Warlords() => new()
        {
            ML = 9,
            Step = 3,
            Name = "Atlantis Warlords",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(43963, 24407, 5459, 1501),
            StarterName = "Shade of Evzen",
            StarterModel = 996,
            Intro = "Three realms warred until I broke their warlords and set their likenesses here as my advisors. Lethos holds that peace in my name. Rouse the southwestern statue, then face him. Do not stand close together: the others are only pretending to sleep.",
            Victory = "The Unifier and his advisors fall silent, and Evzen's shade nods.",
            Replaces = new[] { "Lethos the Unifier", "Advisor Anzelm", "Advisor Geges", "Advisor Gyges", "Advisor Timanthes", "Advisor Zarlanthus" },
            TimeLimitSeconds = 2100,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Advisor Timanthes wakes at your approach!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Advisor Timanthes", Model = 993, Level = 64, Size = 75, Health = 8000, DamageFactor = 1.1, At = new TrialPoint(42982, 25645, 5331, 2483) },
                        Advisor("Advisor Anzelm", 994, 42513, 23964, 5278),
                        Advisor("Advisor Zarlanthus", 997, 45121, 25598, 5155),
                        Advisor("Advisor Geges", 995, 45173, 23033, 5397),
                    },
                    OnStart = run => Calm(run, "advisor"),
                },
                new TrialPhase
                {
                    Announce = "Lethos the Unifier rises to answer you!",
                    Mobs = { new TrialMobSpec { Name = "Lethos the Unifier", Model = 996, Level = 66, Size = 75, Health = 90000, DamageFactor = 1.4, At = new TrialPoint(44163, 24407, 5459, 1501), MeleeDamage = eDamageType.Slash, Tag = "lethos" } },
                    OnTick = LethosTick,
                },
                new TrialPhase
                {
                    Announce = "With Lethos gone, the remaining advisors come to life!",
                    OnStart = run => Wake(run, "advisor"),
                    Done = run => !run.Mobs("advisor").Any(),
                },
            },
        };

        private static TrialMobSpec Advisor(string name, ushort model, int x, int y, int z) => new()
        {
            Name = name, Model = model, Level = 64, Size = 75, Health = 8000, DamageFactor = 1.1, At = new TrialPoint(x, y, z),
            AggroRange = 0, Immune = true, Required = false, Tag = "advisor",
        };

        private static void LethosTick(TrialRun run)
        {
            TrialMob lethos = One(run, "lethos");
            if (lethos != null && Clock(run) % 15 == 0)
                Splash(run, lethos, 2500, 300, 280, eDamageType.Energy, "A dormant statue flares, and lightning falls among you!");
        }

        private static TrialDefinition Kings() => new()
        {
            ML = 9,
            Step = 4,
            Name = "Kings of Aerus",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(42135, 52840, 10304, 1945),
            StarterName = "Keeper of the Likenesses",
            StarterModel = 994,
            Intro = "Four likenesses of the old kings sleep here, each bound to a control crystal. You need bring no crystal of your own: each one waits beside its king, and touching it wakes him. The Tactician, the Brave, the Terrible and the Coward, in that order.",
            Victory = "The last likeness crumbles. The kings of Aerus are at rest.",
            Replaces = new[] { "The Tactician", "The Brave", "The Terrible", "The Coward" },
            TimeLimitSeconds = 2400,
            Phases =
            {
                Crystal("the Tactician", 41102, 51138, 10547),
                new TrialPhase
                {
                    Announce = "The Tactician raises a hand, and four statues answer!",
                    Mobs =
                    {
                        King("The Tactician", 41102, 51138, 10547, 3720, "tactician", true),
                        new TrialMobSpec { Name = "statue of the Tactician", Model = Statue, Level = 63, Size = 60, Health = 3000, DamageFactor = 1.0, Count = 4, At = new TrialPoint(41302, 51138, 10547), Required = false, Tag = "pawn" },
                    },
                    OnTick = TacticianTick,
                    Done = run => !run.Mobs("tactician").Any(),
                },
                Crystal("the Brave", 42135, 52640, 10304),
                new TrialPhase
                {
                    Announce = "The Brave strides forward, drinking in your strength!",
                    Mobs = { King("The Brave", 42135, 52840, 10304, 1945, "brave", false) },
                    OnTick = BraveTick,
                },
                Crystal("the Terrible", 45339, 53640, 10328),
                new TrialPhase
                {
                    Announce = "The Terrible shakes, and shards of him begin to walk!",
                    Mobs = { King("The Terrible", 45339, 53840, 10328, 2013, "terrible", false) },
                    OnTick = TerribleTick,
                    Done = run => !run.Mobs("terrible").Any(),
                },
                Crystal("the Coward", 45606, 50938, 10330),
                new TrialPhase
                {
                    Announce = "The Coward takes one look at you and thinks about running.",
                    Mobs = { King("The Coward", 45606, 51138, 10330, 2810, "coward", false) },
                    OnTick = CowardTick,
                    Done = run => !run.Mobs("coward").Any(),
                },
            },
        };

        private static TrialPhase Crystal(string king, int x, int y, int z) => new()
        {
            Announce = $"Find the control crystal beside {king} and touch it.",
            Mobs =
            {
                new TrialMobSpec
                {
                    Name = "control crystal", Model = Obelisk, Level = 60, Size = 30, At = new TrialPoint(x, y, z), Objective = true,
                    ObjectiveText = $"The crystal hums, and {king} stirs.", OnDeath = Remove,
                },
            },
        };

        private static TrialMobSpec King(string name, int x, int y, int z, ushort heading, string tag, bool immune) => new()
        {
            Name = name, Model = 998, Level = 65, Size = 60, Health = 40000, DamageFactor = 1.3, At = new TrialPoint(x, y, z, heading),
            MeleeDamage = eDamageType.Crush, Tag = tag, Immune = immune,
        };

        private static void TacticianTick(TrialRun run)
        {
            TrialMob tactician = One(run, "tactician");
            if (tactician == null)
                return;

            if (!run.Get("reserves", false) && tactician.HealthPercent <= 50)
            {
                run.Set("reserves", true);
                run.Tell("The Tactician commits his reserves!");
                run.Spawn(new TrialMobSpec { Name = "reserve of the Tactician", Model = Statue, Level = 64, Size = 70, Health = 5000, DamageFactor = 1.1, Count = 2, At = Beside(tactician, 200), Required = false, Tag = "pawn" });
            }
            tactician.Immune = run.Mobs("pawn").Any();
        }

        private static void BraveTick(TrialRun run)
        {
            TrialMob brave = One(run, "brave");
            if (brave == null || Clock(run, "brave") > 10)
                return;
            GameLiving target = RandomTarget(run, brave, 400);
            if (target == null)
                return;
            Hurt(run, brave, target, 70, eDamageType.Body);
            Heal(brave, 0.01);
        }

        private static void TerribleTick(TrialRun run)
        {
            int seconds = Clock(run, "terrible");
            TrialMob terrible = One(run, "terrible");
            if (terrible == null)
                return;

            Dictionary<TrialMob, int> born = run.Get<Dictionary<TrialMob, int>>("born") ?? new();
            run.Set("born", born);

            foreach (TrialMob shard in run.Mobs("shard").Where(shard => born.TryGetValue(shard, out int since) && seconds - since >= 40).ToList())
                shard.Delete();

            if (seconds % 12 != 0)
                return;

            int brood = TerribleBrood(run.Mobs("shard").Count());
            for (int i = 0; i < brood; i++)
            {
                TrialMob shard = run.Spawn(new TrialMobSpec { Name = "shard of the Terrible", Model = Statue, Level = 62, Size = 45, Health = 2000, DamageFactor = 0.8, At = Beside(terrible, 150 + 40 * i), Required = false, Tag = "shard" });
                born[shard] = seconds;
            }
        }

        private static void CowardTick(TrialRun run)
        {
            int seconds = Clock(run, "coward");
            TrialMob coward = One(run, "coward");
            if (coward == null)
                return;

            int hides = run.Get("hides", 0);
            if (hides < CowardHides.Length && coward.HealthPercent <= 66 - 33 * hides)
            {
                run.Set("hides", hides + 1);
                TrialPoint hide = CowardHides[hides];
                (coward.Brain as StandardMobBrain)?.ClearAggroList();
                coward.MoveInRegion(coward.CurrentRegionID, hide.X, hide.Y, hide.Z, coward.Heading, false);
                run.Tell("The Coward bolts for a nearby house! Find him!");
                run.Spawn(new TrialMobSpec { Name = "statue healer", Model = 997, Level = 60, Size = 35, Health = 2500, DamageFactor = 0.4, At = new TrialPoint(hide.X + 150, hide.Y, hide.Z), Required = false, Tag = "healer" });
            }

            if (seconds % 5 == 0 && run.Mobs("healer").Any())
                Heal(coward, 0.02);
        }

        private static TrialDefinition Scholars() => new()
        {
            ML = 9,
            Step = 5,
            Name = "Scholars of Aerus",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(28245, 24572, 8821, 3140),
            StarterName = "Nelos's Lectern",
            StarterModel = 1315,
            Intro = "Class is in session. Nelos has taught here for longer than the city has had a roof, and his students come running the moment their master is struck. The lesson is short if you are quick. If you are slow, it is very crowded.",
            Victory = "Nelos dismisses the class.",
            Replaces = new[] { "Nelos", "student of Nelos" },
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Nelos turns from his slate and looks you over.",
                    Mobs = { new TrialMobSpec { Name = "Nelos", Model = 1315, Level = 66, Size = 87, Health = 70000, DamageFactor = 1.3, Tag = "nelos" } },
                    OnTick = NelosTick,
                    Done = run => !run.Mobs("nelos").Any(),
                },
            },
        };

        private static void NelosTick(TrialRun run)
        {
            TrialMob nelos = One(run, "nelos");
            if (nelos == null || nelos.HealthPercent >= 100)
                return;

            int seconds = Clock(run);
            if (seconds == 1)
                run.Tell("Nelos rings for his students!");
            if (seconds % 15 != 1 || run.Get("students", 0) >= 16)
                return;

            run.Set("students", run.Get("students", 0) + 2);
            run.Spawn(Student(new TrialPoint(29804, 27576, 8643)));
            run.Spawn(Student(new TrialPoint(29435, 24025, 8653)));
        }

        private static TrialMobSpec Student(TrialPoint house) => new()
        {
            Name = "student of Nelos", Model = 1315, Level = 60, Size = 50, Health = 2500, DamageFactor = 1.0, At = house, AggroRange = 3500, Required = false, Tag = "student",
        };

        private static TrialDefinition Patrol() => new()
        {
            ML = 9,
            Step = 6,
            Name = "Patrolling the City",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(32113, 14034, 6872, 1040),
            StarterName = "Katri's Herald",
            StarterModel = 1216,
            Intro = "Katri walks these streets and nothing gets past her. While her personal guard stands, each mends the other faster than you can wound them, and you will not bring her down. Break the guard first. She will call the patrol, and then she can be beaten.",
            Victory = "Katri's patrol is broken. The streets are open.",
            Replaces = new[] { "Katri", "Katri's Personal Guard" },
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Katri and her guard move to bar your way!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Katri", Model = 1217, Level = 66, Size = 50, Health = 75000, DamageFactor = 1.2, At = new TrialPoint(32313, 14034, 6872, 1040), MeleeDamage = eDamageType.Thrust, Required = false, Tag = "katri" },
                        new TrialMobSpec { Name = "Katri's Personal Guard", Model = 1216, Level = 64, Size = 50, Health = 30000, DamageFactor = 1.1, At = new TrialPoint(32611, 13997, 6875, 1039), MeleeDamage = eDamageType.Thrust, Tag = "guard" },
                    },
                    OnTick = KatriGuardTick,
                },
                new TrialPhase
                {
                    Announce = "Katri cries out, and hooves answer from the street!",
                    Mobs = { new TrialMobSpec { Name = "centaur patrol", Model = 1213, Level = 63, Size = 55, Health = 5000, DamageFactor = 1.0, Count = 4, Spread = 400, MeleeDamage = eDamageType.Thrust, Required = false, Tag = "patrol" } },
                    OnStart = run => run.SetImmune("katri", false),
                    OnTick = KatriPatrolTick,
                    Done = run => !run.Mobs("katri").Any(),
                },
            },
        };

        private static void KatriGuardTick(TrialRun run)
        {
            TrialMob katri = One(run, "katri");
            TrialMob guard = One(run, "guard");
            if (katri == null)
                return;

            HoldAt(katri, KatriFloor);
            if (Clock(run) % 6 == 0)
            {
                Heal(katri, 0.03);
                Heal(guard, 0.03);
            }
        }

        private static void KatriPatrolTick(TrialRun run)
        {
            if (Clock(run, "patrol") % 6 == 0 && run.Mobs("patrol").Any())
                Heal(One(run, "katri"), 0.02);
        }

        private static TrialDefinition Host() => new()
        {
            ML = 9,
            Step = 7,
            Name = "Uncontrolled Host",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(33398, 41401, 10343, 489),
            StarterName = "Shed Iaculus Skin",
            StarterModel = 1233,
            Intro = "The skin is still warm. The iaculi of this pit eat one another, and whatever is left grows. Stir the pit and the Puissant Iaculus will start to feed. Every lesser snake you kill first is one he does not get.",
            Victory = "The Puissant Iaculus coils and lies still.",
            Replaces = new[] { "Puissant Iaculus" },
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The pit begins to writhe!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Puissant Iaculus", Model = 1233, Level = 68, Size = 132, Health = 45000, DamageFactor = 1.1, MeleeDamage = eDamageType.Thrust, Tag = "puissant" },
                        new TrialMobSpec { Name = "starving iaculus", Model = 1233, Level = 60, Size = 48, Health = 3000, DamageFactor = 0.8, Count = 6, Spread = 500, MeleeDamage = eDamageType.Thrust, Required = false, Tag = "starving" },
                    },
                    OnTick = HostTick,
                    Done = run => !run.Mobs("puissant").Any(),
                },
            },
        };

        private static void HostTick(TrialRun run)
        {
            TrialMob puissant = One(run, "puissant");
            if (puissant == null || Clock(run) % 20 != 0)
                return;

            TrialMob meal = One(run, "starving");
            if (meal == null)
                return;

            meal.Delete();
            Heal(puissant, 0.03);
            puissant.DamageFactor += 0.1;
            puissant.Size = (byte)Math.Min(180, puissant.Size + 6);
            run.Tell("The Puissant Iaculus devours one of its kin and swells!");
        }

        private static TrialDefinition Guardians() => new()
        {
            ML = 9,
            Step = 8,
            Name = "Guardians of the Phoenix",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(34963, 48751, 12049, 1126),
            StarterName = "Phoenix Herald",
            StarterModel = 1176,
            Intro = "None pass to the Phoenix until the sphinxes call them worthy. Chan holds the road, and Kiran and Roshan wait beyond him. Do not try to slip by Chan. The road remembers trespassers and sends its own guardians after them.",
            Victory = "The three sphinxes bow their heads. You may pass.",
            Replaces = new[] { "Chan", "Roshan", "Kiran" },
            TimeLimitSeconds = 2100,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Chan rises and blocks the road!",
                    Mobs = { new TrialMobSpec { Name = "Chan", Model = Sphinx, Level = 66, Size = 100, Health = 60000, DamageFactor = 1.2, At = new TrialPoint(35213, 48751, 12049, 1126), Tag = "chan" } },
                    OnTick = ChanTick,
                },
                new TrialPhase
                {
                    Announce = "Kiran calls out from further along the road.",
                    Mobs = { new TrialMobSpec { Name = "Kiran", Model = Sphinx, Level = 66, Size = 100, Health = 45000, DamageFactor = 1.3, At = new TrialPoint(38401, 50415, 12049, 2025), Tag = "kiran" } },
                },
                new TrialPhase
                {
                    Announce = "Roshan comes last, and alone.",
                    Mobs = { new TrialMobSpec { Name = "Roshan", Model = Sphinx, Level = 66, Size = 100, Health = 45000, DamageFactor = 1.3, At = new TrialPoint(40097, 48749, 12049, 1103), Tag = "roshan" } },
                },
            },
        };

        private static void ChanTick(TrialRun run)
        {
            if (run.Get("trespass", false) || !run.Players.Any(player => PastChan(player.X, player.Z)))
                return;

            run.Set("trespass", true);
            run.Tell("You have passed without leave! The road's guardians wake!");
            run.Spawn(new TrialMobSpec
            {
                Name = "Phoenix's Guardian", Model = 1177, Level = 68, Size = 90, Health = 8000, DamageFactor = 1.4, Count = 2,
                At = new TrialPoint(BypassX, 48750, 12048), AggroRange = 3000, Required = false, Tag = "bypass",
            });
        }

        private static TrialDefinition CentaursPatrol() => new()
        {
            ML = 9,
            Step = 9,
            Name = "Centaur's Patrol",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(38453, 29061, 8584, 2887),
            StarterName = "Avriel Grave Marker",
            StarterModel = 1216,
            Intro = "Neola stays out of sight while her sisters patrol, and she counts every one that falls. Thin the sisters here and she will come to answer for them. The sentries who roam the city don't count, only those who answer this marker. Her two guardians keep her safe until they are down.",
            Victory = "Neola falls among her sisters.",
            Replaces = new[] { "Neola" },
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Avriel sisters close in around the marker!",
                    Mobs = { new TrialMobSpec { Name = "avriel sister", Model = 1216, Level = 58, Size = 48, Health = 2500, DamageFactor = 0.8, Count = 8, Spread = 500, MeleeDamage = eDamageType.Thrust } },
                    KillCount = 6,
                },
                new TrialPhase
                {
                    Announce = "Neola: Enough! You will answer for my sisters!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Neola", Model = 1216, Level = 66, Size = 60, Health = 70000, DamageFactor = 1.3, MeleeDamage = eDamageType.Thrust, Immune = true, Required = false, Tag = "neola" },
                        new TrialMobSpec { Name = "Avriel Guardian", Model = 1216, Level = 64, Size = 56, Health = 6000, DamageFactor = 1.1, Count = 2, Spread = 450, MeleeDamage = eDamageType.Thrust, Required = false, Tag = "avriel" },
                    },
                    OnTick = run => run.SetImmune("neola", run.Mobs("avriel").Any()),
                    Done = run => !run.Mobs("neola").Any(),
                },
            },
        };

        private static TrialDefinition Phoenix() => new()
        {
            ML = 9,
            Step = 10,
            Name = "Rise of the Phoenix",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Aerus,
            Anchor = new TrialPoint(35318, 32993, 19050, 76),
            StarterName = "Ember Warden",
            StarterModel = 994,
            Intro = "Three generators on the ring below feed the Phoenix, and while one runs she cannot truly die. Each one holds back another quarter of her. Clear the Ozos, then break the crystal. An operator will walk out to mend it, and letting him arrive undoes your work, so kill him first. Break all three and she will burn out for good.",
            Victory = "The Phoenix burns down to ash, and this time the ash stays cold.",
            Replaces = new[] { "The Phoenix", "Phoenix Ozos", "Generator Operator", "Jai", "Lahamu" },
            TimeLimitSeconds = 2400,
            LeashRange = 12000,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The generators hum, and the Phoenix spreads her wings above the city!",
                    Mobs =
                    {
                        PhoenixSpec(),
                        GeneratorSpec(0), Ozos(0, 0), Ozos(0, 1), Ozos(0, 2),
                        GeneratorSpec(1), Ozos(1, 0), Ozos(1, 1), Ozos(1, 2),
                        GeneratorSpec(2), Ozos(2, 0), Ozos(2, 1), Ozos(2, 2),
                    },
                    OnStart = run =>
                    {
                        for (int i = 0; i < Generators.Length; i++)
                            run.Mobs($"gen{i}").ToList().ForEach(Root);
                    },
                    OnTick = PhoenixTick,
                    Done = run => GeneratorsUp(run) == 0 && !run.Mobs("phoenix").Any(),
                },
            },
        };

        private static TrialMobSpec PhoenixSpec() => new()
        {
            Name = "The Phoenix", Model = 1219, Level = 68, Size = 110, Health = 130000, DamageFactor = 1.6, At = new TrialPoint(34854, 35280, 19153, 4073),
            MeleeDamage = eDamageType.Heat, Required = false, Tag = "phoenix",
        };

        private static TrialMobSpec GeneratorSpec(int index) => new()
        {
            Name = "Phoenix Generator", Model = Obelisk, Level = 65, Size = 110, Health = 8000, DamageFactor = 0.05, At = Generators[index],
            AggroRange = 0, Immune = true, Required = false, Tag = $"gen{index}", OnDeath = (run, _) => SendOperator(run, index),
        };

        private static TrialMobSpec Ozos(int generator, int index) => new()
        {
            Name = "Phoenix Ozos", Model = 1042, Level = 62, Size = 57, Health = 3000, DamageFactor = 0.9, At = Ring(Generators[generator], index, 3, 300),
            MeleeDamage = eDamageType.Thrust, Required = false, Tag = $"ozos{generator}",
        };

        private static TrialMobSpec OperatorSpec(int index) => new()
        {
            Name = "Generator Operator", Model = Statue, Level = 65, Size = 75, Health = 6000, DamageFactor = 0.6, At = Operators[index], AggroRange = 0, Required = false, Tag = $"op{index}",
            OnDeath = (run, _) => run.Tell("The operator falls. That generator stays dark."),
        };

        private static int GeneratorsUp(TrialRun run) => Enumerable.Range(0, Generators.Length).Count(i => run.Mobs($"gen{i}").Any());

        private static void SendOperator(TrialRun run, int index)
        {
            run.Set($"walk{index}", 0);
            run.Spawn(OperatorSpec(index));
            run.Tell($"A generator goes dark, leaving {GeneratorsUp(run)} running. A Generator Operator sets out to repair it!");
        }

        private static void PhoenixTick(TrialRun run)
        {
            int seconds = Clock(run);
            for (int i = 0; i < Generators.Length; i++)
            {
                if (!run.Mobs($"ozos{i}").Any())
                    run.SetImmune($"gen{i}", false);
                WalkOperator(run, i);
            }

            int up = GeneratorsUp(run);
            TrialMob phoenix = One(run, "phoenix");
            if (phoenix == null)
            {
                if (up > 0)
                {
                    phoenix = run.Spawn(PhoenixSpec());
                    phoenix.Health = phoenix.MaxHealth * PhoenixFloor(up) / 100;
                    run.Tell("The Phoenix bursts into flame and is reborn!");
                }
                return;
            }

            HoldAt(phoenix, PhoenixFloor(up));
            if (up == 0 || !phoenix.InCombat)
                return;

            if (seconds % 10 == 0)
                Splash(run, phoenix, 2500, 350, PhoenixFireball(up), eDamageType.Heat, null);
            if (seconds % 6 == 0)
                HurtAround(run, phoenix, phoenix, 500, PhoenixFlare(up), eDamageType.Heat);
        }

        private static void WalkOperator(TrialRun run, int index)
        {
            TrialMob walker = One(run, $"op{index}");
            if (walker == null || walker.InCombat)
                return;

            TrialPoint generator = Generators[index];
            if (!walker.IsMoving)
                walker.WalkTo(new Point3D(generator.X, generator.Y, generator.Z), 60);

            if (Clock(run, $"walk{index}") < OperatorWalkSeconds)
                return;

            walker.Delete();
            TrialMob repaired = run.Spawn(GeneratorSpec(index));
            repaired.Immune = false;
            Root(repaired);
            repaired.Health = repaired.MaxHealth / 2;
            run.Tell("A Generator Operator reaches his crystal, and it lights again!");
        }
    }
}
