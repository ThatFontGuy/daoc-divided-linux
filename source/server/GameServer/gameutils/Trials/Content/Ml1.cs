using System;
using System.Collections.Generic;
using System.Linq;
using DOL.AI.Brain;

namespace DOL.GS.Trials
{
    /// <summary>Master Level 1 trials: the seas of Oceanus and Cetus' Pit.</summary>
    public static class Ml1
    {
        private const ushort FireGiantModel = 1349;
        private const ushort OrbModel = 1391;
        private const ushort TritonModel = 33745;
        private const ushort TritonMageModel = 33746;
        private const ushort TritonChiefModel = 33747;
        private const ushort TritonGuardModel = 33744;
        private const ushort NereidModel = 33748;
        private const ushort HammerheadModel = 33740;
        private const ushort HarpyModel = 992;
        private const ushort NedfallModel = 929;

        private const int PurrosFuse = 30;
        private const int PurrosEvery = 8;
        private const int MirrorOrbSeconds = 30;

        /// <summary>Each purros that dies, however it dies, costs Zopureo this share of his health.</summary>
        public const double PurrosShare = 0.125;

        private static readonly TrialPoint SunkaioSpot = new(432028, 544158, 8320);
        private static readonly TrialPoint ZopureoSpot = new(431700, 544400, 8320);
        private static readonly TrialPoint AithosSpot = new(432401, 543998, 8335);

        /// <summary>Rocks near Lornas where a thief can hide, with the way he points.</summary>
        public static readonly (TrialPoint Spot, string Way)[] Hideouts =
        {
            (new TrialPoint(353328, 552047, 6510), "south, on the big rock past the weed beds"),
            (new TrialPoint(357641, 549915, 6432), "east, among the plants on the plateau"),
            (new TrialPoint(351827, 549920, 6528), "west, where the rock falls away"),
        };

        public static readonly string[] Champions = { "Agnon", "Sethrendar", "Xalarian", "Jilena", "Malison", "Regent" };

        private static readonly TrialPoint[] ChampionSeats =
        {
            new(444019, 560383, 3845),
            new(443941, 560406, 3833),
            new(443982, 560455, 3845),
            new(443953, 560514, 3845),
            new(443888, 560579, 3845),
            new(443882, 560628, 3845),
        };

        private static readonly ushort[] ChampionModels = { 33744, 33745, 33746, 33748, 33744, 33745 };

        private static readonly TrialPoint Arena = new(443950, 560500, 3845);

        private static readonly TrialPoint[] MonumentPads =
        {
            new(428483, 536145, 8354),
            new(428541, 536574, 8354),
            new(428798, 536320, 8345),
        };

        private static readonly TrialPoint Monument = new(428600, 536350, 8350);

        private static readonly TrialPoint[] NedfallTraps =
        {
            new(434687, 548369, 8272),
            new(436220, 546847, 8272),
            new(436483, 551790, 8248),
        };

        private static readonly TrialPoint CetusLair = new(31914, 33601, 16222, 2048);
        private static readonly TrialPoint CetusFocus = new(31914, 34200, 16222);

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return Survivor();
            yield return Retrieval();
            yield return GreaterGood();
            yield return Barrier();
            yield return Conflict();
            yield return Curses();
            yield return TheMonument();
            yield return TheRuby();
            yield return TheCrown();
            yield return ConqueringTheSea();
        }

        /// <summary>The two hideouts a roll picks. They always differ.</summary>
        public static (int First, int Second) PickHideouts(int roll)
        {
            int first = Math.Abs(roll) % Hideouts.Length;
            return (first, (first + 1) % Hideouts.Length);
        }

        /// <summary>Cetus breaks for his lair at 75%, 50% and 25%, and no more than that.</summary>
        public static bool CetusFlees(int healthPercent, int flights) => flights < 3 && healthPercent <= 75 - 25 * flights;

        private static TrialDefinition Survivor()
        {
            return new TrialDefinition
            {
                ML = 1,
                Step = 1,
                Name = "Survivor",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(431100, 541433, 8481, 3777),
                StarterName = "Ianetor",
                StarterModel = 1194,
                Intro = "So you have come to play with fire! Three of the great burning ones sleep on this island, and I can wake them. " +
                    "Beat Sunkaio first, and fight him up close: he hurls flame at anyone who hangs back. Leave Zopureo alone, for no blade will bite him. " +
                    "Kill the purros he breeds and each one that dies burns him down. Aithos comes last. Stand well clear of each other for that one.",
                Victory = "Ianetor laughs and claps as the last flames gutter out. You have survived his game!",
                Replaces = new[] { "Ianetor", "Sunkaio", "Aithos" },
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The ground grows hot. You have half a minute to reach the middle of the island.",
                        SurviveSeconds = 30,
                    },
                    new TrialPhase
                    {
                        Announce = "Sunkaio rises from the ash!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Sunkaio",
                                Model = FireGiantModel,
                                Size = 150,
                                Level = 62,
                                Health = 20000,
                                DamageFactor = 0.9,
                                MeleeDamage = eDamageType.Heat,
                                At = SunkaioSpot,
                                Tag = "sunkaio",
                            },
                        },
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 5, Damage = 110, Radius = 300, SourceTag = "sunkaio", DamageType = eDamageType.Heat },
                        },
                        OnTick = ScorchTheDistant,
                    },
                    new TrialPhase
                    {
                        Announce = "Zopureo wakes and his purros begin to pop. Strike the purros, not Zopureo!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Zopureo",
                                Model = FireGiantModel,
                                Size = 150,
                                Level = 62,
                                Health = 20000,
                                DamageFactor = 0.6,
                                MeleeDamage = eDamageType.Heat,
                                At = ZopureoSpot,
                                AggroRange = 0,
                                Immune = true,
                                Tag = "zopureo",
                            },
                        },
                        OnStart = run => Ml12Kit.Fix(run, "zopureo"),
                        OnTick = BreedPurros,
                    },
                    new TrialPhase
                    {
                        Announce = "Aithos strides out of the flames!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Aithos",
                                Model = FireGiantModel,
                                Size = 150,
                                Level = 64,
                                Health = 34000,
                                DamageFactor = 1.1,
                                MeleeDamage = eDamageType.Heat,
                                At = AithosSpot,
                                Tag = "aithos",
                            },
                        },
                        OnStart = run => Ml12Kit.Clear(run, "purros"),
                        OnTick = FireballFromAithos,
                    },
                },
            };
        }

        private static void ScorchTheDistant(TrialRun run)
        {
            TrialMob sunkaio = run.Mobs("sunkaio").FirstOrDefault();
            if (sunkaio == null || !Ml12Kit.Every(run, "scorch", 8))
                return;
            foreach (GameLiving target in run.Hostiles(sunkaio, 2500).Where(target => !target.IsWithinRadius(sunkaio, 600)))
                Ml12Kit.Strike(run, sunkaio, target, 180, eDamageType.Heat);
        }

        private static void BreedPurros(TrialRun run)
        {
            if (!run.Mobs("zopureo").Any())
                return;

            Dictionary<TrialMob, int> fuses = run.Get<Dictionary<TrialMob, int>>("fuses");
            if (fuses == null)
            {
                fuses = new Dictionary<TrialMob, int>();
                run.Set("fuses", fuses);
            }

            foreach (TrialMob purros in run.Mobs("purros").ToList())
            {
                fuses.TryGetValue(purros, out int age);
                fuses[purros] = ++age;
                if (age < PurrosFuse)
                    continue;
                run.Tell("A purros bursts in a sheet of flame!");
                Ml12Kit.Burst(run, purros, purros, 700, 120, eDamageType.Heat);
                purros.Die(run.Starter);
            }

            if (Ml12Kit.Every(run, "purros", PurrosEvery) && run.Mobs("purros").Count() < 3)
            {
                int popped = run.Get("popped", 0);
                run.Set("popped", popped + 1);
                run.Spawn(Purros(Ml12Kit.Ring(ZopureoSpot, 500, popped, 6)));
            }
        }

        private static TrialMobSpec Purros(TrialPoint at)
        {
            return new TrialMobSpec
            {
                Name = "purros",
                Model = FireGiantModel,
                Size = 45,
                Level = 55,
                Health = 2000,
                DamageFactor = 0.3,
                MeleeDamage = eDamageType.Heat,
                At = at,
                AggroRange = 0,
                Required = false,
                Tag = "purros",
                OnDeath = (run, _) =>
                {
                    TrialMob zopureo = run.Mobs("zopureo").FirstOrDefault();
                    if (zopureo != null)
                        Ml12Kit.Wound(run, zopureo, PurrosShare);
                },
            };
        }

        private static void FireballFromAithos(TrialRun run)
        {
            TrialMob aithos = run.Mobs("aithos").FirstOrDefault();
            if (aithos == null || !Ml12Kit.Every(run, "fireball", 5))
                return;
            GameLiving target = Ml12Kit.RandomHostile(run, aithos, 1500);
            if (target != null)
                Ml12Kit.Burst(run, aithos, target, 400, 170, eDamageType.Heat);
        }

        private static TrialDefinition Retrieval()
        {
            return new TrialDefinition
            {
                ML = 1,
                Step = 2,
                Name = "Retrieval",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(354560, 549120, 6488, 1752),
                StarterName = "Lornas",
                StarterModel = TritonMageModel,
                Intro = "Two brothers robbed me, Borjan and Borjad, and they have gone to ground on the rock plateaus. My scouts can tell you where. " +
                    "Catching one is enough, for either one carries what they took. Mind that he does not stay put once he is hurt.",
                Victory = "You drag what was stolen back to Lornas, and he thanks you for it.",
                Replaces = new[] { "Lornas" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The thieves are somewhere close. Listen for where Lornas points.",
                        OnStart = PlaceThieves,
                        OnTick = ThiefSlips,
                        Done = run => run.Get<bool>("caught"),
                    },
                },
            };
        }

        private static void PlaceThieves(TrialRun run)
        {
            (int first, int second) = PickHideouts(Util.Random(0, Hideouts.Length - 1));
            run.Spawn(Thief("Borjan", Hideouts[first].Spot));
            run.Spawn(Thief("Borjad", Hideouts[second].Spot));
            run.Tell($"Lornas says: Borjan was seen to the {Hideouts[first].Way}.");
            run.Tell($"Lornas says: Borjad was seen to the {Hideouts[second].Way}.");
        }

        private static TrialMobSpec Thief(string name, TrialPoint at)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = TritonModel,
                Size = 55,
                Level = 58,
                Health = 16000,
                DamageFactor = 0.9,
                MeleeDamage = eDamageType.Slash,
                At = at,
                AggroRange = 700,
                Tag = "thief",
                OnDeath = (run, _) => run.Set("caught", true),
            };
        }

        private static void ThiefSlips(TrialRun run)
        {
            foreach (TrialMob thief in run.Mobs("thief").ToList())
            {
                string key = $"slipped:{thief.Name}";
                if (thief.HealthPercent > 50 || run.Get<bool>(key))
                    continue;
                run.Set(key, true);
                TrialPoint spot = Ml12Kit.Ring(thief.Spec.At.GetValueOrDefault(), 600, Util.Random(0, 3), 4);
                thief.MoveTo(thief.CurrentRegionID, spot.X, spot.Y, spot.Z, spot.Heading);
                run.Tell($"{thief.Name} slips into the weeds! Look around the rock.");
            }
        }

        private static TrialDefinition GreaterGood()
        {
            TrialPoint oxomis = new(374154, 517386, 5165);
            return new TrialDefinition
            {
                ML = 1,
                Step = 3,
                Name = "Greater Good",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(370099, 526771, 6406, 2628),
                StarterName = "Zhton Chief Arxem",
                StarterModel = TritonChiefModel,
                Intro = "Our clans are dying and still Oxomis of the Kynhroe will not stop this war. Swim north to his rock in Oceanus Boreal and end him. " +
                    "His monitors will keep mending him while they live, so cut them down, and expect his goons at his side.",
                Victory = "Chief Oxomis falls, and the Zhton war drums go quiet.",
                Replaces = new[] { "Zhton Chief Arxem", "Kynhroe Chief Oxomis" },
                LeashRange = 14000,
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Chief Oxomis waits on his rock to the north with his cronies about him.",
                        Mobs = BuildGreaterGood(oxomis),
                        OnTick = run =>
                        {
                            TrialMob chief = run.Mobs("chief").FirstOrDefault();
                            int menders = run.Mobs("monitor").Count();
                            if (chief != null && menders > 0 && Ml12Kit.Every(run, "mend", 6))
                                Ml12Kit.Heal(chief, 0.015 * menders);
                        },
                    },
                },
            };
        }

        private static List<TrialMobSpec> BuildGreaterGood(TrialPoint oxomis)
        {
            List<TrialMobSpec> mobs = new()
            {
                new TrialMobSpec
                {
                    Name = "Kynhroe Chief Oxomis",
                    Model = TritonChiefModel,
                    Size = 60,
                    Level = 60,
                    Health = 40000,
                    DamageFactor = 1.0,
                    MeleeDamage = eDamageType.Thrust,
                    At = oxomis,
                    AggroRange = 900,
                    Tag = "chief",
                },
            };
            mobs.AddRange(Ml12Kit.Circle(oxomis, 400, 3, at => new TrialMobSpec
            {
                Name = "Kynhroe monitor",
                Model = TritonModel,
                Size = 54,
                Level = 56,
                Health = 3000,
                DamageFactor = 0.5,
                At = at,
                AggroRange = 900,
                Required = false,
                Tag = "monitor",
            }));
            mobs.AddRange(Ml12Kit.Circle(oxomis, 700, 4, at => new TrialMobSpec
            {
                Name = "Kynhroe goon",
                Model = TritonGuardModel,
                Size = 52,
                Level = 56,
                Health = 3500,
                DamageFactor = 0.7,
                MeleeDamage = eDamageType.Slash,
                At = at,
                AggroRange = 900,
                Required = false,
                Tag = "goon",
            }));
            return mobs;
        }

        private static TrialDefinition Barrier()
        {
            TrialPoint fadrin = new(289574, 555101, 2081);
            return new TrialDefinition
            {
                ML = 1,
                Step = 4,
                Name = "Barrier",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(289782, 555943, 2151),
                StarterName = "Taken Nereid",
                StarterModel = NereidModel,
                Intro = "The barrier on the sea floor holds Fadrin, and he holds all of us who were taken. Break it and he comes out, so be ready. " +
                    "Finish him before the barrier grows back, for he cannot be touched behind it and it mends him while it stands.",
                Victory = "Fadrin is dead and the barrier dissolves. His belt lies in the silt, and it will serve you on Firestorm Island.",
                Replaces = new[] { "Fadrin" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The barrier shimmers before you. Morphed things turn toward the noise.",
                        Mobs = BuildBarrier(fadrin),
                        OnStart = run => Ml12Kit.Fix(run, "barrier"),
                        Done = run => !run.Mobs("barrier").Any(),
                    },
                    new TrialPhase
                    {
                        Announce = "The barrier shatters! Fadrin is free!",
                        OnStart = run =>
                        {
                            run.SetImmune("fadrin", false);
                            Ml12Kit.Wake(run, "fadrin", 1500);
                        },
                        OnTick = run => FightFadrin(run, fadrin),
                        Done = run => !run.Mobs("fadrin").Any(),
                    },
                },
            };
        }

        private static List<TrialMobSpec> BuildBarrier(TrialPoint fadrin)
        {
            List<TrialMobSpec> mobs = new()
            {
                BarrierSpec(fadrin, 14000),
                new TrialMobSpec
                {
                    Name = "Fadrin",
                    Model = 1033,
                    Size = 50,
                    Level = 62,
                    Health = 24000,
                    DamageFactor = 1.0,
                    At = fadrin,
                    AggroRange = 0,
                    Immune = true,
                    Tag = "fadrin",
                },
            };
            mobs.AddRange(Ml12Kit.Circle(fadrin, 600, 3, at => new TrialMobSpec
            {
                Name = "morphed shark",
                Model = 33739,
                Size = 41,
                Level = 56,
                Health = 3000,
                DamageFactor = 0.6,
                MeleeDamage = eDamageType.Thrust,
                At = at,
                AggroRange = 900,
                Required = false,
            }));
            return mobs;
        }

        private static TrialMobSpec BarrierSpec(TrialPoint at, int health)
        {
            return new TrialMobSpec
            {
                Name = "Barrier",
                Model = OrbModel,
                Size = 120,
                Level = 60,
                Health = health,
                DamageFactor = 0.1,
                At = at,
                AggroRange = 0,
                Required = false,
                Tag = "barrier",
                Hurts = TrialDamageKind.Melee,
            };
        }

        private static void FightFadrin(TrialRun run, TrialPoint fadrin)
        {
            TrialMob boss = run.Mobs("fadrin").FirstOrDefault();
            if (boss == null)
                return;

            bool shielded = run.Mobs("barrier").Any();
            boss.Immune = shielded;
            if (shielded)
            {
                if (Ml12Kit.Every(run, "mend", 5))
                    Ml12Kit.Heal(boss, 0.01);
                return;
            }

            if (Ml12Kit.Every(run, "nuke", 10))
            {
                GameLiving target = Ml12Kit.RandomHostile(run, boss, 1500);
                if (target != null)
                    Ml12Kit.Strike(run, boss, target, 150, eDamageType.Cold);
            }

            if (Ml12Kit.Every(run, "regrow", 240))
            {
                run.Tell("Fadrin chants, and the barrier closes around him again!");
                run.Spawn(BarrierSpec(fadrin, 7000));
                Ml12Kit.Fix(run, "barrier");
            }
        }

        private static TrialDefinition Conflict()
        {
            return new TrialDefinition
            {
                ML = 1,
                Step = 5,
                Name = "Conflict",
                Scope = TrialScope.Solo,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(443912, 561549, 3954, 1956),
                StarterName = "Lady Farahnaz",
                StarterModel = 33750,
                Intro = "Lord Krojer keeps six champions on the sea floor just north of here, and he will test anyone who dares to ask. " +
                    "When you begin, swim to the arena and touch the champion you will face. It is single combat: friends may watch, but their blows will not land. " +
                    "One victory is all the proof he asks.",
                Victory = "Krojer nods from his seat. You have proven yourself in single combat.",
                Replaces = new[] { "Krojer", "Lady Farahnaz", "Agnon", "Sethrendar", "Xalarian", "Jilena", "Malison", "Regent", "Sentinel" },
                ReplaceRadius = 4500,
                TimeLimitSeconds = 900,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The champions wait in the arena. Touch the one you would fight.",
                        Mobs = BuildSeats(),
                        Done = run => run.Get<string>("champion") != null,
                    },
                    new TrialPhase
                    {
                        Announce = "Your champion steps forward!",
                        OnStart = run =>
                        {
                            Ml12Kit.Clear(run, "seat");
                            run.Spawn(ChampionSpec(run.Get<string>("champion")));
                            if (run.Get<string>("champion") == "Agnon")
                                run.Spawn(CrocodileSpec());
                        },
                        OnTick = ChampionTrick,
                        Done = run => !run.Mobs("fighter").Any(),
                    },
                },
            };
        }

        private static List<TrialMobSpec> BuildSeats()
        {
            List<TrialMobSpec> seats = new()
            {
                new TrialMobSpec
                {
                    Name = "Krojer",
                    Model = TritonChiefModel,
                    Size = 50,
                    Level = 60,
                    At = new TrialPoint(443808, 560400, 3810, 1331),
                    Objective = true,
                    ObjectiveText = "Krojer says: Do not trouble me. Choose one of my champions and show me what you are.",
                    Required = false,
                },
            };
            for (int i = 0; i < Champions.Length; i++)
            {
                seats.Add(new TrialMobSpec
                {
                    Name = Champions[i],
                    Model = ChampionModels[i],
                    Size = 50,
                    Level = 55,
                    At = ChampionSeats[i],
                    Objective = true,
                    ObjectiveText = $"{Champions[i]} accepts your challenge.",
                    Required = false,
                    Tag = "seat",
                    OnDeath = (run, mob) =>
                    {
                        if (run.Get<string>("champion") == null)
                            run.Set("champion", mob.Name);
                    },
                });
            }
            return seats;
        }

        private static TrialMobSpec ChampionSpec(string name)
        {
            int index = Array.IndexOf(Champions, name);
            TrialMobSpec spec = new()
            {
                Name = name,
                Model = ChampionModels[index],
                Size = 50,
                Level = 55,
                Health = 2400,
                DamageFactor = 0.45,
                At = ChampionSeats[index],
                AggroRange = 1500,
                Tag = "fighter",
            };
            switch (name)
            {
                case "Agnon":
                    spec.Health = 2200;
                    spec.MeleeDamage = eDamageType.Thrust;
                    break;
                case "Sethrendar":
                    spec.MeleeDamage = eDamageType.Crush;
                    break;
                case "Xalarian":
                    spec.Health = 2600;
                    spec.MeleeDamage = eDamageType.Crush;
                    break;
                case "Jilena":
                    spec.Health = 2600;
                    spec.DamageFactor = 0.5;
                    spec.MeleeDamage = eDamageType.Slash;
                    break;
                case "Malison":
                    spec.MeleeDamage = eDamageType.Crush;
                    break;
                default:
                    spec.Health = 2800;
                    spec.DamageFactor = 0.5;
                    spec.MeleeDamage = eDamageType.Slash;
                    break;
            }
            return spec;
        }

        private static TrialMobSpec CrocodileSpec()
        {
            return new TrialMobSpec
            {
                Name = "Agnon's crocodile",
                Model = 34026,
                Size = 60,
                Level = 50,
                Health = 600,
                DamageFactor = 0.25,
                MeleeDamage = eDamageType.Thrust,
                At = Ml12Kit.Ring(Arena, 200, 0, 4),
                AggroRange = 1500,
                Required = false,
            };
        }

        private static void ChampionTrick(TrialRun run)
        {
            TrialMob champion = run.Mobs("fighter").FirstOrDefault();
            if (champion == null)
                return;

            switch (champion.Name)
            {
                case "Sethrendar" when Ml12Kit.Every(run, "trick", 9):
                    run.Tell("Sethrendar's staff saps your strength.");
                    Ml12Kit.Strike(run, champion, run.Leader, 60, eDamageType.Spirit);
                    break;
                case "Xalarian" when Ml12Kit.Every(run, "trick", 15):
                    TrialPoint spot = Ml12Kit.Ring(Arena, 350, Util.Random(0, 7), 8);
                    champion.MoveTo(champion.CurrentRegionID, spot.X, spot.Y, spot.Z, spot.Heading);
                    run.Tell("Xalarian folds out of sight and appears across the arena!");
                    break;
                case "Jilena" when Ml12Kit.Every(run, "trick", 6):
                    Ml12Kit.Strike(run, champion, run.Leader, 55, eDamageType.Body);
                    break;
                case "Malison" when Ml12Kit.Every(run, "trick", 10):
                    Ml12Kit.Strike(run, champion, run.Leader, 90, eDamageType.Energy);
                    break;
            }
        }

        private static TrialDefinition Curses()
        {
            return new TrialDefinition
            {
                ML = 1,
                Step = 6,
                Name = "Curses",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(433401, 546420, 8481, 3777),
                StarterName = "Ianetor",
                StarterModel = 1194,
                Intro = "Kirkleis hates the face in his mirror, and he has sown his island with traps. The gem you won from my game shows you where they lie: touch each one and it goes dead. " +
                    "The belt you took from Fadrin is your shield in his temple. Whoever began this trial carries its calm, so keep close to that one when the curse goes out. " +
                    "You need no item for this: having finished the Survivor and Barrier trials stands for the gem and the belt.",
                Victory = "Kirkleis lies still, and for once the mirror shows him nothing.",
                RequiresSteps = new[] { 1, 4 },
                Replaces = new[] { "Kirkleis" },
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The traps around the temple are live! Find them and touch each one.",
                        Mobs = BuildTraps(),
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 10, Damage = 120, Radius = 900, SourceTag = "trap", DamageType = eDamageType.Cold },
                        },
                        OnTick = SpringNedfalls,
                    },
                    new TrialPhase
                    {
                        Announce = "The last trap dies. Kirkleis turns from his mirror!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Kirkleis",
                                Model = 995,
                                Size = 150,
                                Level = 63,
                                Health = 42000,
                                DamageFactor = 1.1,
                                MeleeDamage = eDamageType.Slash,
                                At = new TrialPoint(435315, 549214, 8370, 1683),
                                Tag = "kirkleis",
                            },
                        },
                        OnTick = KirkleisCurse,
                    },
                },
            };
        }

        private static List<TrialMobSpec> BuildTraps()
        {
            return NedfallTraps.Select((at, index) => new TrialMobSpec
            {
                Name = "Nedfall trap",
                Model = NedfallModel,
                Size = 50,
                Level = 55,
                At = at,
                Objective = true,
                ObjectiveText = "Ianetor's gem answers from afar, and the trap goes dead.",
                Tag = "trap",
            }).ToList();
        }

        private static void SpringNedfalls(TrialRun run)
        {
            if (!Ml12Kit.Every(run, "spring", 20) || run.Mobs("nedfall").Count() >= 6)
                return;
            List<TrialMob> live = run.Mobs("trap").ToList();
            if (live.Count == 0)
                return;
            TrialMob trap = live[Util.Random(live.Count - 1)];
            TrialPoint at = new(trap.X, trap.Y, trap.Z);
            foreach (TrialMobSpec spec in Ml12Kit.Circle(at, 200, 2, spot => new TrialMobSpec
            {
                Name = "nuker nedfall",
                Model = NedfallModel,
                Size = 50,
                Level = 55,
                Health = 2000,
                DamageFactor = 0.5,
                At = spot,
                Required = false,
                Tag = "nedfall",
            }))
            {
                run.Spawn(spec);
            }
        }

        private static void KirkleisCurse(TrialRun run)
        {
            TrialMob kirkleis = run.Mobs("kirkleis").FirstOrDefault();
            if (kirkleis == null || !Ml12Kit.Every(run, "curse", 9))
                return;
            run.Tell("Kirkleis' curse rolls out across the temple!");
            Ml12Kit.Burst(run, kirkleis, kirkleis, 1200, 220, eDamageType.Heat,
                target => run.Leader.IsAlive && target.IsWithinRadius(run.Leader, 500));
        }

        private static TrialDefinition TheMonument()
        {
            return new TrialDefinition
            {
                ML = 1,
                Step = 7,
                Name = "The Monument",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(430786, 536271, 8270),
                StarterName = "Dark Portal Stone",
                StarterModel = OrbModel,
                Intro = "The portals lie dark. Touch the three pads under the great dome in the middle of this island and they will wake, and the guardians with them. " +
                    "Someone must stand by a pad for as long as the statues walk, or they will knit themselves whole again. When the last wave breaks, Rassa comes.",
                Victory = "Rassa crumbles, and a mirror lies among the shards. The portals glow again.",
                Replaces = new[] { "Rassa" },
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Touch the three pads under the great dome.",
                        Mobs = MonumentPads.Select(at => new TrialMobSpec
                        {
                            Name = "dark pad",
                            Model = OrbModel,
                            Size = 30,
                            Level = 55,
                            At = at,
                            Objective = true,
                            ObjectiveText = "The pad wakes beneath your hand.",
                        }).ToList(),
                    },
                    StatueWave("The first statues step down from their plinths!", "atevo statue", 993, 50, 56, 3000, 4),
                    StatueWave("More statues grind to life. Hold the pads!", "olemo statue", 994, 51, 58, 3500, 4),
                    StatueWave("The stone keeps coming!", "mikoos statue", 997, 55, 60, 5000, 3),
                    StatueWave("The dome shakes as the great statues wake!", "helicaon statue", 994, 110, 62, 8000, 2),
                    new TrialPhase
                    {
                        Announce = "Rassa descends from the dome!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Rassa",
                                Model = 994,
                                Size = 80,
                                Level = 64,
                                Health = 45000,
                                DamageFactor = 1.1,
                                At = new TrialPoint(428799, 536319, 8345),
                                Tag = "rassa",
                            },
                        },
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 8, Damage = 150, Radius = 600, SourceTag = "rassa", DamageType = eDamageType.Energy },
                        },
                    },
                },
            };
        }

        private static TrialPhase StatueWave(string announce, string name, ushort model, byte size, byte level, int health, int count)
        {
            return new TrialPhase
            {
                Announce = announce,
                Mobs = Ml12Kit.Circle(Monument, 450, count, at => new TrialMobSpec
                {
                    Name = name,
                    Model = model,
                    Size = size,
                    Level = level,
                    Health = health,
                    DamageFactor = 0.8,
                    At = at,
                    Tag = "statue",
                }).ToList(),
                OnTick = HoldThePads,
            };
        }

        private static void HoldThePads(TrialRun run)
        {
            bool held = run.Hostiles(run.Starter, 4000).Any(target => MonumentPads.Any(pad => Ml12Kit.Near(target.X, target.Y, pad, 400)));
            if (held)
                return;
            Ml12Kit.HealAll(run, "statue", 0.01);
            if (Ml12Kit.Every(run, "padwarn", 15))
                run.Tell("No one stands by the pads, and the statues knit themselves whole!");
        }

        private static TrialDefinition TheRuby()
        {
            TrialPoint sands = new(342122, 640800, 5060);
            return new TrialDefinition
            {
                ML = 1,
                Step = 8,
                Name = "The Ruby",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = sands,
                StarterName = "Glint in the Sand",
                StarterModel = OrbModel,
                Intro = "Something red winks up from the deep sands, and the hammerheads have scented it. Disturb the sand and an azure shark will come. " +
                    "The hammerheads will tear it apart, and in the frenzy one of them will snatch up the ruby. Kill that one. Leave the rest alone as long as you can: they ignore you until the frenzy breaks.",
                Victory = "The ruby spills out of the shark's jaws and into your hands.",
                Replaces = new[] { "azure shark" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "An azure shark drifts in and the hammerheads go into a frenzy!",
                        Mobs = BuildFrenzy(sands),
                        OnTick = run =>
                        {
                            TrialMob azure = run.Mobs("azure").FirstOrDefault();
                            if (azure != null)
                                Ml12Kit.Wound(run, azure, 0.05);
                        },
                        Done = run => !run.Mobs("azure").Any(),
                    },
                    new TrialPhase
                    {
                        Announce = "A hammerhead noses through the sand and comes up with something red in its jaws!",
                        OnStart = run => RubyCarrier(run, sands),
                        OnTick = CarrierFights,
                        Done = run => run.Get<bool>("ruby"),
                    },
                },
            };
        }

        private static List<TrialMobSpec> BuildFrenzy(TrialPoint sands)
        {
            List<TrialMobSpec> mobs = new()
            {
                new TrialMobSpec
                {
                    Name = "azure shark",
                    Model = 33739,
                    Size = 50,
                    Level = 60,
                    Health = 3000,
                    At = sands,
                    AggroRange = 0,
                    Immune = true,
                    Required = false,
                    Tag = "azure",
                },
            };
            mobs.AddRange(Ml12Kit.Circle(sands, 500, 6, at => new TrialMobSpec
            {
                Name = "hammerhead shark",
                Model = HammerheadModel,
                Size = 60,
                Level = 60,
                Health = 6000,
                DamageFactor = 0.7,
                MeleeDamage = eDamageType.Thrust,
                At = at,
                AggroRange = 0,
                Required = false,
                Tag = "frenzy",
            }));
            return mobs;
        }

        private static void RubyCarrier(TrialRun run, TrialPoint sands)
        {
            List<TrialMob> sharks = run.Mobs("frenzy").ToList();
            TrialPoint at = sands;
            if (sharks.Count > 0)
            {
                TrialMob chosen = sharks[Util.Random(sharks.Count - 1)];
                at = new TrialPoint(chosen.X, chosen.Y, chosen.Z);
                chosen.Delete();
            }
            run.Spawn(new TrialMobSpec
            {
                Name = "ruby-jawed hammerhead",
                Model = HammerheadModel,
                Size = 70,
                Level = 62,
                Health = 40000,
                DamageFactor = 1.0,
                MeleeDamage = eDamageType.Thrust,
                At = at,
                AggroRange = 0,
                Tag = "carrier",
                OnDeath = (trial, _) => trial.Set("ruby", true),
            });
        }

        private static void CarrierFights(TrialRun run)
        {
            TrialMob carrier = run.Mobs("carrier").FirstOrDefault();
            if (carrier == null)
                return;

            if (carrier.HealthPercent <= 60 && !run.Get<bool>("broken"))
            {
                run.Set("broken", true);
                run.Tell("The blood in the water breaks the frenzy! The other hammerheads turn on you!");
                Ml12Kit.Wake(run, "frenzy", 1200);
            }

            if (carrier.InCombat && Ml12Kit.Every(run, "bleed", 7))
            {
                GameLiving target = Ml12Kit.RandomHostile(run, carrier, 500);
                if (target != null)
                    Ml12Kit.Strike(run, carrier, target, 80, eDamageType.Body);
            }
        }

        private static TrialDefinition TheCrown()
        {
            TrialPoint desmona = new(353219, 637836, 8119);
            return new TrialDefinition
            {
                ML = 1,
                Step = 9,
                Name = "The Crown",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(360021, 638683, 8026),
                StarterName = "Salt-Worn Cairn",
                StarterModel = 1204,
                Intro = "Scratched on the cairn: Desmona shows herself only to those who hold her token. Dig in the disturbed sand by the shore. " +
                    "Her harpies will come for it the moment it is out of the ground, so kill the one that takes it. Then go west to the ruins and the pillars, where she waits with her flock.",
                Victory = "Desmona falls among her pillars, and her crown rolls to a stop at your feet.",
                Replaces = new[] { "Desmona" },
                LeashRange = 10000,
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Find the disturbed sand by the shore, and dig.",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "disturbed sand",
                                Model = OrbModel,
                                Size = 30,
                                Level = 55,
                                At = new TrialPoint(360751, 636580, 8018),
                                Objective = true,
                                ObjectiveText = "You dig up a Desmona Revelation Token.",
                            },
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "Harpies drop out of the sky! One of them snatches the token!",
                        Mobs = BuildHarpyRaid(new TrialPoint(360751, 636580, 8018)),
                    },
                    new TrialPhase
                    {
                        Announce = "The token is yours again, and it burns toward the ruins in the west. Desmona has seen you!",
                        Mobs = BuildDesmona(desmona),
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 7, Damage = 140, Radius = 500, SourceTag = "desmona", DamageType = eDamageType.Energy },
                        },
                        OnTick = run => CallTheFlock(run, desmona),
                    },
                },
            };
        }

        private static TrialMobSpec Harpy(string name, TrialPoint at, int health, bool required)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = HarpyModel,
                Size = 50,
                Level = 56,
                Health = health,
                DamageFactor = 0.7,
                MeleeDamage = eDamageType.Slash,
                At = at,
                Required = required,
                Tag = "harpy",
            };
        }

        private static List<TrialMobSpec> BuildHarpyRaid(TrialPoint dig)
        {
            List<TrialMobSpec> mobs = Ml12Kit.Circle(dig, 500, 4, at => Harpy("desmona harpy", at, 3000, false)).ToList();
            mobs.Add(Harpy("token-thief harpy", dig, 5000, true));
            return mobs;
        }

        private static List<TrialMobSpec> BuildDesmona(TrialPoint desmona)
        {
            List<TrialMobSpec> mobs = new()
            {
                new TrialMobSpec
                {
                    Name = "Desmona",
                    Model = HarpyModel,
                    Size = 150,
                    Level = 63,
                    Health = 48000,
                    DamageFactor = 1.1,
                    MeleeDamage = eDamageType.Slash,
                    At = desmona,
                    Tag = "desmona",
                },
            };
            mobs.AddRange(Ml12Kit.Circle(desmona, 500, 4, at => Harpy("desmona harpy", at, 3500, false)));
            return mobs;
        }

        private static void CallTheFlock(TrialRun run, TrialPoint desmona)
        {
            if (Ml12Kit.Every(run, "flock", 45) && run.Mobs("desmona").Any() && run.Mobs("harpy").Count() < 5)
                run.Spawn(Harpy("desmona harpy", Ml12Kit.Ring(desmona, 700, Util.Random(0, 7), 8), 3000, false));
        }

        private static TrialDefinition ConqueringTheSea()
        {
            return new TrialDefinition
            {
                ML = 1,
                Step = 10,
                Name = "Conquering the Sea",
                Scope = TrialScope.Raid,
                Zone = TrialZone.CetusPit,
                Anchor = CetusFocus,
                StarterName = "Focus Globe",
                StarterModel = OrbModel,
                Intro = "The globe hums as you near it. The crown, the ring, the ruby and the mirror have answered to you, and having finished the nine trials stands for carrying them. " +
                    "When Cetus turns to flee to his lair, a ruby light will kindle by the pillars: touch it in time or he comes back healed. " +
                    "While he is still strong the mirror beside this globe can loose its orbs on him, once. Whoever began this trial bears the mirror, and his death-ray turns aside from that one.",
                Victory = "Cetus sinks to the floor of his pit, and the sea is conquered!",
                Replaces = new[] { "Cetus" },
                TimeLimitSeconds = 2400,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Cetus stirs in the dark water!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Cetus",
                                Model = 33741,
                                Size = 75,
                                Level = 66,
                                Health = 70000,
                                DamageFactor = 1.2,
                                MeleeDamage = eDamageType.Crush,
                                At = CetusLair,
                                AggroRange = 1200,
                                Tag = "cetus",
                            },
                            new TrialMobSpec
                            {
                                Name = "Rassa's mirror",
                                Model = OrbModel,
                                Size = 25,
                                Level = 55,
                                At = Ml12Kit.Ring(CetusFocus, 250, 0, 4),
                                Objective = true,
                                ObjectiveText = "The mirror flares and its orbs stream out toward Cetus.",
                                Required = false,
                                Tag = "mirror",
                                OnDeath = (run, mirror) =>
                                {
                                    run.Set("orbs", MirrorOrbSeconds);
                                    mirror.Delete();
                                },
                            },
                        },
                        OnTick = FightCetus,
                        Done = run => !run.Mobs("cetus").Any(),
                    },
                },
            };
        }

        private static void FightCetus(TrialRun run)
        {
            TrialMob cetus = run.Mobs("cetus").FirstOrDefault();
            if (cetus == null)
                return;

            if (cetus.HealthPercent <= 50)
                Ml12Kit.Clear(run, "mirror");

            int orbs = run.Get("orbs", 0);
            if (orbs > 0)
            {
                run.Set("orbs", orbs - 1);
                Ml12Kit.Wound(run, cetus, 0.005);
            }

            CetusFlight(run, cetus);

            if (Ml12Kit.Every(run, "ray", 20))
            {
                GameLiving target = Ml12Kit.RandomHostile(run, cetus, 1500);
                if (target == run.Leader)
                {
                    run.Tell("The mirror throws Cetus' death-ray back at him!");
                    Ml12Kit.Wound(run, cetus, 0.01);
                }
                else if (target != null)
                {
                    run.Tell($"Cetus' death-ray lances into {target.Name}!");
                    Ml12Kit.Strike(run, cetus, target, 280, eDamageType.Energy);
                }
            }
        }

        private static void CetusFlight(TrialRun run, TrialMob cetus)
        {
            int flights = run.Get("flights", 0);
            int countdown = run.Get("flight", 0);

            if (countdown == 0)
            {
                if (!CetusFlees(cetus.HealthPercent, flights))
                    return;
                run.Set("flights", flights + 1);
                run.Set("flight", 20);
                run.Set("pinned", false);
                run.Tell("Cetus shudders and turns toward his lair to heal!");
                return;
            }

            run.Set("flight", --countdown);

            if (countdown == 16)
            {
                run.Spawn(new TrialMobSpec
                {
                    Name = "ruby light",
                    Model = OrbModel,
                    Size = 35,
                    Level = 55,
                    At = Ml12Kit.Ring(CetusFocus, 300, 1 + flights % 3, 4),
                    Objective = true,
                    ObjectiveText = "You call on the ruby you won from the deep sands, and it pins Cetus in place!",
                    Required = false,
                    Tag = "ruby",
                    OnDeath = (trial, light) =>
                    {
                        trial.Set("pinned", true);
                        light.Delete();
                    },
                });
                run.Tell("A ruby light kindles by the pillars! Touch it!");
            }

            if (run.Get<bool>("pinned"))
            {
                run.Set("flight", 0);
                run.Tell("Held by the ruby, Cetus cannot flee!");
            }
            else if (countdown == 0)
            {
                Ml12Kit.Clear(run, "ruby");
                Ml12Kit.Heal(cetus, 0.25);
                run.Tell("Cetus returns from his lair with his wounds closed!");
            }
        }
    }
}
