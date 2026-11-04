using System;
using System.Collections.Generic;
using System.Linq;
using static DOL.GS.Trials.Ml7Kit;

namespace DOL.GS.Trials
{
    /// <summary>
    /// Master Level 8 trials, in Green Glades and Arbor Glen: rebuilding Agne. Each step's body part stands for itself;
    /// the finale's step requirement takes the place of carrying the pieces to the Constructor.
    /// </summary>
    public static class Ml8
    {
        private const ushort Servant = 995, Jinni = 1198, Centaur = 1213, Bowman = 1214, Soldier = 1315, Gorgon = 1182, Cobra = 1234, Whirlwind = 1269, Marble = 994, Reliquary = 1203;
        private const string ServantName = "Constructor's Servant";

        private const int StormSeconds = 25;
        private const int LastTorsoKill = 12;

        private static readonly TrialPoint Kratos = new(455206, 686214, 13781);
        private static readonly TrialPoint Constructor = new(461608, 688125, 14405);
        private static readonly TrialPoint Battlefield = new(463000, 688100, 13957);

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return AgnesCrystal();
            yield return AgnesShield();
            yield return AgnesSword();
            yield return CentaursHunt();
            yield return TreasureOfTheCyclops();
            yield return AgnesWill();
            yield return AgnesMight();
            yield return GorgonsSecret();
            yield return AgnesSpareArm();
            yield return AgnesGreatMight();
        }

        /// <summary>Ibn breaks into storms at each of these marks, once each.</summary>
        public static int IbnStorms(int healthPercent) => MarksPassed(healthPercent, 75, 50, 25);

        /// <summary>Dawar flees at each of these marks, once each.</summary>
        public static int DawarFlights(int healthPercent) => MarksPassed(healthPercent, 66, 33);

        /// <summary>The torso turns up on a lucky break, and always by the last kill.</summary>
        public static bool TorsoFound(int kills, double roll) => kills >= LastTorsoKill || roll < 0.15;

        public static bool TalosCallsForHealing(int healthPercent, bool alreadyHealed) => !alreadyHealed && healthPercent <= 25;

        /// <summary>Lets a run pick one chest of several in its own game of chance.</summary>
        private static List<TrialMobSpec> Chests(string name, TrialPoint[] spots, string key, string rightText, string wrongText, Action<TrialRun, TrialMob> wrong)
        {
            List<TrialMobSpec> chests = new();
            for (int i = 0; i < spots.Length; i++)
            {
                int index = i;
                chests.Add(Clickable(name, Reliquary, 28, spots[i], "The lid gives under your hand.", "chest", (run, mob) =>
                {
                    if (run.Get(key, -1) == index)
                    {
                        run.Tell(rightText);
                        run.Set(key + ".found", true);
                        return;
                    }
                    run.Tell(wrongText);
                    wrong(run, mob);
                }));
            }
            return chests;
        }

        private static void ClearChests(TrialRun run)
        {
            foreach (TrialMob chest in run.Mobs("chest").ToList())
                chest.Delete();
        }

        private static TrialDefinition AgnesCrystal()
        {
            TrialPoint[] guards =
            {
                new(368773, 692749, 8104),
                new(366581, 693245, 8161),
                new(369404, 695535, 8161),
                new(371334, 691608, 8161),
            };

            static TrialMobSpec Statue(string name, ushort model, int x, int y, int z) => Foe(name, model, 60, 100, 6000, 1.1, new TrialPoint(x, y, z));

            static TrialPhase Set(string announce, TrialPoint flight, TrialMobSpec first, TrialMobSpec second, TrialMobSpec third) => new()
            {
                Announce = announce,
                Mobs = { first, second, third },
                OnStart = run =>
                {
                    foreach (TrialMob bisul in run.Mobs("bisul").ToList())
                        Relocate(run, bisul, flight);
                },
                Done = run => !run.Mobs().Any(mob => mob.Spec.Required),
            };

            return new TrialDefinition
            {
                ML = 8,
                Step = 1,
                Name = "Agne's Crystal",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(367575, 695413, 8133),
                StarterName = ServantName,
                StarterModel = Servant,
                Replaces = new[] { "Bisul", "Bronze Statue", "Stone Statue", "Veined Marble Statue" },
                Intro = "My master cannot wake Agne without the control crystal, and the jinni Bisul keeps it. Four sets of statues shield Bisul; while one stands, nothing you do will touch the jinni. Break the set beside Bisul, and Bisul will run to the next. Follow, and finish them all.",
                Victory = "Bisul falls, and Agne's control crystal is yours.",
                TimeLimitSeconds = 2400,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Bisul sees you, and the first statues step down.",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Bisul",
                                Model = Jinni,
                                Level = 66,
                                Size = 60,
                                Health = 45000,
                                DamageFactor = 1.6,
                                At = guards[0],
                                Tag = "bisul",
                                Immune = true,
                                Required = false,
                                MeleeDamage = eDamageType.Heat,
                            },
                            Statue("bronze sentinel", 995, 368894, 692606, 8104),
                            Statue("stone sentinel", 997, 368891, 692578, 8104),
                            Statue("marble sentinel", Marble, 368803, 692565, 8104),
                        },
                        Done = run => !run.Mobs().Any(mob => mob.Spec.Required),
                    },
                    Set("Bisul flees west to the second set!", guards[1],
                        Statue("bronze sentinel", 995, 366581, 693052, 8161), Statue("stone sentinel", 997, 367100, 693244, 8161), Statue("marble sentinel", Marble, 366578, 693437, 8161)),
                    Set("Bisul flees south to the third set!", guards[2],
                        Statue("bronze sentinel", 995, 369597, 695755, 8161), Statue("stone sentinel", 997, 369404, 695313, 8161), Statue("marble sentinel", Marble, 369213, 695754, 8161)),
                    Set("Bisul flees east to the last set!", guards[3],
                        Statue("bronze sentinel", 995, 371223, 691301, 8161), Statue("stone sentinel", 997, 371086, 691821, 8161), Statue("marble sentinel", Marble, 371597, 691701, 8161)),
                    new TrialPhase
                    {
                        Announce = "No statue is left to shield Bisul. Strike!",
                        OnStart = run => run.SetImmune("bisul", false),
                        Done = run => Gone(run, "bisul"),
                    },
                },
            };
        }

        private static TrialDefinition AgnesShield()
        {
            TrialPoint academy = new(441650, 712211, 13515);
            TrialPoint champion = new(442176, 712735, 13528);
            TrialPoint commander = new(442702, 712218, 13515);
            TrialPoint general = new(442174, 713593, 13528);
            TrialPoint lord = new(442176, 713148, 13558);

            static TrialMobSpec Guard(int x, int y) => Foe("Tholos' soldier", Soldier, 60, 75, 4000, 0.9, new TrialPoint(x, y, 13515), melee: eDamageType.Slash);

            return new TrialDefinition
            {
                ML = 8,
                Step = 2,
                Name = "Agne's Shield",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = academy,
                StarterName = "Tholos at the Military Academy",
                StarterModel = Soldier,
                Replaces = new[] { "Tholos at the Military Academy", "Trainee", "Tholos' soldier", "Tholos Tournament Champion", "Commander Tholos", "General Tholos", "Lord Tholos" },
                Intro = "Stone remembers. Agne's shield was lost, but his brother Tholos carried its twin, and every age of Tholos stands in this hall. Read each one's inscription and it will test you, up to the Lord himself. He strikes without pity. Do not stand before him.",
                Victory = "Lord Tholos topples, and the twin of Agne's shield is yours.",
                TimeLimitSeconds = 2400,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The trainees step down from their plinths.",
                        Mobs =
                        {
                            Foe("Trainee", Soldier, 58, 62, 3000, 0.7, new TrialPoint(441643, 712546, 13515), melee: eDamageType.Slash),
                            Foe("Trainee", Soldier, 58, 62, 3000, 0.7, new TrialPoint(441661, 712949, 13515), melee: eDamageType.Slash),
                            Foe("Trainee", Soldier, 58, 62, 3000, 0.7, new TrialPoint(441980, 712211, 13515), melee: eDamageType.Slash),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "An inscription glows on the Tournament Champion.",
                        Mobs = { Clickable("Tholos Tournament Champion", Soldier, 72, champion, "'Glory first, and then the field,' reads the base. The stone stirs.") },
                    },
                    new TrialPhase
                    {
                        Mobs =
                        {
                            Foe("Tholos Tournament Champion", Soldier, 62, 72, 12000, 1.2, champion, melee: eDamageType.Slash),
                            Guard(441651, 713348),
                            Guard(442707, 713350),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "An inscription glows on the Commander.",
                        Mobs = { Clickable("Commander Tholos", Soldier, 82, commander, "'Who follows, wins,' reads the base. The soldiers turn their heads.") },
                    },
                    new TrialPhase
                    {
                        Mobs =
                        {
                            Foe("Commander Tholos", Soldier, 65, 82, 22000, 1.4, commander, melee: eDamageType.Slash),
                            Guard(442370, 712211),
                            Guard(442696, 712958),
                            Guard(442703, 712546),
                            Guard(441972, 714088),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "An inscription glows on the General.",
                        Mobs = { Clickable("General Tholos", Soldier, 92, general, "'All stand when I stand,' reads the base, and the whole hall answers.") },
                    },
                    new TrialPhase
                    {
                        Announce = "The whole room comes to life! Break the soldiers while someone keeps the General busy.",
                        Mobs =
                        {
                            Foe("General Tholos", Soldier, 67, 92, 40000, 1.7, general, melee: eDamageType.Slash),
                            Guard(441638, 713766),
                            Guard(441645, 714096),
                            Guard(442389, 714091),
                            Guard(442705, 713771),
                            Guard(442706, 714086),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "One statue is left, and its inscription burns.",
                        Mobs = { Clickable("Lord Tholos", Soldier, 110, lord, "'Truth shall always succeed,' reads the base. The Lord lifts his head.") },
                    },
                    new TrialPhase
                    {
                        Announce = "Lord Tholos walks. Stay behind him!",
                        Mobs = { Foe("Lord Tholos", Soldier, 70, 110, 80000, 2.2, lord, melee: eDamageType.Slash) },
                    },
                },
            };
        }

        private static TrialDefinition AgnesSword()
        {
            TrialPoint ibn = new(404813, 703252, 12214);
            TrialPoint[] chests = Enumerable.Range(0, 5).Select(i => new TrialPoint(404213 + i * 300, 703852, 12214)).ToArray();
            TrialPoint[] hideouts = { new(405700, 702700, 12214), new(404000, 702500, 12214), new(405600, 703900, 12214) };

            static TrialMobSpec Sword(TrialPoint at) => Foe("animated sword", 997, 62, 40, 3000, 0.9, at, "sword", eDamageType.Slash, false);

            return new TrialDefinition
            {
                ML = 8,
                Step = 3,
                Name = "Agne's Sword",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = ibn,
                StarterName = "Ibn",
                StarterModel = Jinni,
                Replaces = new[] { "Ibn" },
                Intro = "A sword? Agne's sword? I may have seen such a thing. I will even give you a key. Here are five chests, friend, and one of them holds what you seek. The rest hold what I find funny. And if you do find the sword, do not imagine I will just hand it over.",
                Victory = "Ibn scatters on the wind, and Agne's sword drops into the grass.",
                TimeLimitSeconds = 2400,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Five chests stand in the grass. Choose.",
                        Mobs = Chests("Ibn's chest", chests, "sword", "There it hangs, above the open chest! Ibn laughs and takes it for himself.", "Blades rise out of the chest!",
                            (run, mob) =>
                            {
                                foreach (TrialPoint point in Circle(new TrialPoint(mob.X, mob.Y, mob.Z), 150, 3))
                                    run.Spawn(Sword(point));
                            }),
                        OnStart = run => run.Set("sword", Util.Random(0, chests.Length - 1)),
                        Done = run => run.Get("sword.found", false),
                    },
                    new TrialPhase
                    {
                        Announce = "'Mine,' says Ibn. Take it from him. When he turns to dust, stay out of the storms and wait for him to reform.",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Ibn the Trickster",
                                Model = Jinni,
                                Level = 68,
                                Size = 60,
                                Health = 60000,
                                DamageFactor = 1.8,
                                At = ibn,
                                Tag = "ibn",
                                Required = false,
                                MeleeDamage = eDamageType.Energy,
                            },
                        },
                        Pulses = { new TrialPulse { IntervalSeconds = 4, Damage = 200, Radius = 350, SourceTag = "storm", DamageType = eDamageType.Slash } },
                        OnStart = ClearChests,
                        OnTick = run =>
                        {
                            TrialMob trickster = run.Mobs("ibn").FirstOrDefault();
                            if (trickster == null)
                                return;

                            int storm = run.Get("storm.left", 0);
                            if (storm > 0)
                            {
                                run.Set("storm.left", storm - 1);
                                if (storm > 1)
                                    return;
                                foreach (TrialMob dust in run.Mobs("storm").ToList())
                                    dust.Delete();
                                run.SetImmune("ibn", false);
                                run.Tell("The storms die away, and Ibn stands whole again.");
                                return;
                            }

                            int passed = IbnStorms(trickster.HealthPercent);
                            if (passed > run.Get("storms", 0))
                            {
                                run.Set("storms", passed);
                                run.Set("storm.left", StormSeconds);
                                run.SetImmune("ibn", true);
                                run.Tell("Ibn bursts into whirling dust!");
                                TrialPoint from = new(trickster.X, trickster.Y, trickster.Z);
                                foreach (TrialPoint point in Circle(from, 250, 3))
                                {
                                    TrialMobSpec dust = Foe("duststorm", Whirlwind, 66, 70, 5000, 0.4, point, "storm", eDamageType.Slash, false);
                                    dust.Immune = true;
                                    run.Spawn(dust);
                                }
                                Relocate(run, trickster, hideouts[passed - 1]);
                                return;
                            }

                            if (trickster.HealthPercent <= 50 && Count(run, "swords") % 30 == 0 && run.Mobs("sword").Count() < 6)
                            {
                                run.Tell("Ibn calls his blades.");
                                foreach (TrialPoint point in Circle(new TrialPoint(trickster.X, trickster.Y, trickster.Z), 150, 2))
                                    run.Spawn(Sword(point));
                            }
                        },
                        Done = run => Gone(run, "ibn"),
                    },
                },
            };
        }

        private static TrialDefinition CentaursHunt()
        {
            static TrialPhase Camp(string announce, string chief, TrialPoint at, int riders) => new()
            {
                Announce = announce,
                Mobs = AtEach(Circle(at, 300, riders), point => Foe("centaur outrider", Centaur, 60, 57, 3000, 0.9, point, melee: eDamageType.Thrust))
                    .Append(Foe(chief, Bowman, 65, 60, 18000, 1.4, at, melee: eDamageType.Thrust)).ToList(),
            };

            return new TrialDefinition
            {
                ML = 8,
                Step = 4,
                Name = "Centaur's Hunt",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(366490, 709300, 8083),
                StarterName = ServantName,
                StarterModel = Servant,
                Replaces = new[] { "Chief Arsene", "Chief Oighrig" },
                Intro = "Centaurs dragged a bronze limb into these camps and each chief claims a share of it. It is no use to them and they will not give it up. Go to both chiefs. Mind their riders.",
                Victory = "With both chiefs dead, Agne's leg lies among the spears.",
                TimeLimitSeconds = 1500,
                Phases =
                {
                    Camp("Chief Oighrig blows his horn in the north camp.", "Chief Oighrig", new TrialPoint(365582, 706299, 8080), 4),
                    Camp("Chief Arsene answers from the south camp, with more riders.", "Chief Arsene", new TrialPoint(365448, 710857, 8080), 5),
                },
            };
        }

        private static TrialDefinition TreasureOfTheCyclops()
        {
            TrialPoint gaspara = new(410339, 702297, 11857);
            TrialPoint[] chests = Enumerable.Range(0, 5).Select(i => new TrialPoint(409739 + i * 300, 702797, 11857)).ToArray();

            static TrialMobSpec Son(string name, ushort model, int x, int y, int z) => Foe(name, model, 62, 60, 5000, 1.0, new TrialPoint(x, y, z), melee: eDamageType.Thrust);
            static TrialMobSpec Warder(int x, int y) => Foe("Ghita's statue", 986, 60, 50, 4000, 0.9, new TrialPoint(x, y, 12144));

            return new TrialDefinition
            {
                ML = 8,
                Step = 5,
                Name = "Treasure of the Cyclops",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = Kratos,
                StarterName = "Kratos",
                StarterModel = 1229,
                Replaces = new[] { "Kratos", "Ghita", "Gaspara", "controlled statue", "Adras son of Creon", "Maur son of Creon", "Nemos son of Creon", "Piet son of Creon", "Sarpedon son of Creon", "Teurcer son of Creon" },
                Intro = "The leg? Yes, I have your bronze leg, and I want payment. A ketos fillet and spring water, those my crate here already holds if you will fetch them out. Then Ghita's stone from the northern ruins, the six heads of Creon's sons, and my own chest out of Gaspara's game in the Glades. All of it, or no leg.",
                Victory = "Kratos counts it all twice, grunts, and drops Agne's leg at your feet.",
                TimeLimitSeconds = 2400,
                LeashRange = 60000,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Open the crate beside Kratos.",
                        Mobs =
                        {
                            Clickable("Kratos's fish crate", Reliquary, 30, new TrialPoint(455006, 686214, 13786), "A ketos fillet, still cold. You set it aside for him."),
                            Clickable("Kratos's water cask", Reliquary, 30, new TrialPoint(455006, 686414, 13786), "Oasis water, sealed and heavy. You set it aside for him."),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "Now Ghita. Her ruins lie far to the northwest, and her statues stand with her.",
                        Mobs =
                        {
                            Foe("Ghita", 1183, 66, 60, 18000, 1.4, new TrialPoint(428874, 677215, 12144), melee: eDamageType.Thrust),
                            Warder(428606, 677215),
                            Warder(429275, 676815),
                            Warder(429408, 677483),
                            Warder(429676, 677216),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "Ghita's stone is yours. Now the six sons of Creon, in the village south of her ruins.",
                        Mobs =
                        {
                            Son("Adras son of Creon", 1215, 442621, 695271, 11976),
                            Son("Maur son of Creon", 1214, 440037, 696377, 11992),
                            Son("Nemos son of Creon", 1214, 442942, 694081, 12397),
                            Son("Piet son of Creon", 1215, 441401, 695793, 12009),
                            Son("Sarpedon son of Creon", 1213, 442422, 697718, 11992),
                            Son("Teurcer son of Creon", 1213, 444048, 696755, 11976),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "Six heads, bagged. Last, go to Gaspara in Green Glades and pick the chest that holds Kratos's treasure.",
                        Mobs = Chests("Gaspara's chest", chests, "cyclops", "Kratos's chest lies inside. Take it back to him.", "Something very hot climbs out!",
                            (run, mob) => run.Spawn(Foe("Gaspara's fire elemental", 125, 68, 80, 12000, 1.4, new TrialPoint(mob.X, mob.Y, mob.Z), "fire", eDamageType.Heat, false))),
                        OnStart = run =>
                        {
                            run.Set("cyclops", Util.Random(0, chests.Length - 1));
                            run.Spawn(new TrialMobSpec { Name = "Gaspara", Model = 1195, Level = 65, Size = 50, At = gaspara, Objective = true, ObjectiveText = "Gaspara only smiles and points at the chests.", Required = false });
                        },
                        Done = run => run.Get("cyclops.found", false),
                    },
                    new TrialPhase
                    {
                        Announce = "Bring it all back to Kratos.",
                        OnStart = ClearChests,
                        Done = run => Near(run.Leader, Kratos, 500),
                    },
                },
            };
        }

        private static TrialDefinition AgnesWill()
        {
            TrialPoint home = new(413031, 673814, 10539);
            TrialPoint[] flights = { new(413700, 674300, 10539), new(412500, 674400, 10539) };

            return new TrialDefinition
            {
                ML = 8,
                Step = 6,
                Name = "Agne's Will",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(412451, 674100, 10416),
                StarterName = ServantName,
                StarterModel = Servant,
                Replaces = new[] { "Dawar" },
                Intro = "Dawar has made Agne's head into a thing to be carried. His controlled statue bears it, and he stands behind it. Fell the statue, and only then can Dawar be reached. He will not stay near you, and he burns from further off than you would like.",
                Victory = "Dawar is dead, and Agne's bronze head stares up at you.",
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Dawar sends his servant forward.",
                        Mobs =
                        {
                            Foe("Dawar's statue", 989, 64, 72, 25000, 1.5, new TrialPoint(412451, 673534, 10416)),
                            new TrialMobSpec
                            {
                                Name = "Dawar",
                                Model = 1194,
                                Level = 68,
                                Size = 60,
                                Health = 50000,
                                DamageFactor = 1.3,
                                At = home,
                                Tag = "dawar",
                                Immune = true,
                                Required = false,
                                MeleeDamage = eDamageType.Energy,
                            },
                        },
                        Done = run => !run.Mobs().Any(mob => mob.Spec.Required),
                    },
                    new TrialPhase
                    {
                        Announce = "The statue falls. Dawar can be hurt!",
                        Pulses = { new TrialPulse { IntervalSeconds = 9, Damage = 240, Radius = 1000, SourceTag = "dawar", DamageType = eDamageType.Energy, Message = "Dawar's power washes outward!" } },
                        OnStart = run => run.SetImmune("dawar", false),
                        OnTick = run =>
                        {
                            foreach (TrialMob dawar in run.Mobs("dawar").ToList())
                            {
                                int passed = DawarFlights(dawar.HealthPercent);
                                if (passed <= run.Get("fled", 0))
                                    continue;
                                run.Set("fled", passed);
                                run.Tell("Dawar flees across the clearing!");
                                Relocate(run, dawar, flights[passed - 1]);
                            }
                        },
                        Done = run => Gone(run, "dawar"),
                    },
                },
            };
        }

        private static TrialDefinition AgnesMight()
        {
            TrialPoint camp = new(397333, 664878, 8058);
            TrialPoint[] spots = Circle(camp, 500, 6).ToArray();

            TrialMobSpec Statue(TrialPoint at) => new()
            {
                Name = "cracked self-maintaining statue",
                Model = Servant,
                Level = 60,
                Size = 60,
                Health = 3500,
                DamageFactor = 0.9,
                At = at,
                Tag = "statue",
                Required = false,
                OnDeath = (run, mob) =>
                {
                    int kills = Count(run, "kills");
                    if (TorsoFound(kills, Util.RandomDouble()))
                    {
                        run.Tell("You have found Agne's torso among the rubble!");
                        run.Set("torso", true);
                        return;
                    }
                    run.Spawn(Statue(spots[kills % spots.Length]));
                },
            };

            return new TrialDefinition
            {
                ML = 8,
                Step = 7,
                Name = "Agne's Might",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = camp,
                StarterName = ServantName,
                StarterModel = Servant,
                Intro = "These statues mend themselves from whatever bronze comes to hand, and one of them has used Agne's torso for the work. There is no telling which. Break them until it shows, and do not dawdle: a cracked statue will have closed its wounds before long.",
                Victory = "Agne's torso comes away from the wreck in one piece.",
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The statues turn toward you.",
                        Mobs = spots.Select(Statue).ToList(),
                        OnTick = run =>
                        {
                            if (Count(run, "mend") % 10 != 0)
                                return;
                            foreach (TrialMob statue in run.Mobs("statue"))
                                statue.Health = Math.Min(statue.MaxHealth, statue.Health + statue.MaxHealth * 5 / 100);
                        },
                        Done = run => run.Get("torso", false),
                    },
                },
            };
        }

        private static TrialDefinition GorgonsSecret()
        {
            static IEnumerable<TrialMobSpec> Snakes(TrialPoint at, int count) => count == 0 ? Enumerable.Empty<TrialMobSpec>()
                : AtEach(Circle(at, 240, count), point => Foe("summoned cobra", Cobra, 60, 45, 2000, 0.7, point, "cobra", eDamageType.Thrust, false));

            static TrialPhase Named(string name, string announce, TrialPoint at, int snakes) => new()
            {
                Announce = announce,
                Mobs = Snakes(at, snakes).Append(Foe(name, Gorgon, 66, 60, 20000, 1.4, at, melee: eDamageType.Thrust)).ToList(),
            };

            TrialPoint kynthia = new(485110, 715254, 15208);

            return new TrialDefinition
            {
                ML = 8,
                Step = 8,
                Name = "Gorgon's Secret",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(481000, 712100, 15238),
                StarterName = ServantName,
                StarterModel = Servant,
                Replaces = new[] { "Lomandeara", "Giathna", "Quaria", "Minarak", "Kynthia", "Kynthia's Guide" },
                Intro = "The gorgons remember what the old trials cost them, and they have hidden Agne's left arm to spite us. Kynthia has it. Go through her sisters first, in order, and each will bring fewer snakes than the last. Kill her Guide next. Kynthia shrugs off magic, so bring your blades to her.",
                Victory = "Kynthia lies still, and Agne's left arm is found beneath her.",
                TimeLimitSeconds = 2400,
                Phases =
                {
                    Named("Lomandeara", "Lomandeara calls her snakes, far to the north.", new TrialPoint(484736, 707904, 15240), 8),
                    Named("Giathna", "Giathna comes on, here at the western shaft.", new TrialPoint(481363, 711803, 15238), 6),
                    Named("Quaria", "Quaria stirs to the south.", new TrialPoint(482268, 715065, 15208), 4),
                    Named("Minarak", "Minarak waits alone.", new TrialPoint(484397, 712332, 15213), 0),
                    new TrialPhase
                    {
                        Announce = "Kynthia's Guide stands before her, and while it lives she burns all she sees!",
                        Mobs =
                        {
                            Foe("Kynthia's Guide", Gorgon, 66, 55, 15000, 1.2, new TrialPoint(485177, 715236, 15208), "guide", eDamageType.Thrust, false),
                            new TrialMobSpec
                            {
                                Name = "Kynthia",
                                Model = Gorgon,
                                Level = 69,
                                Size = 72,
                                Health = 40000,
                                DamageFactor = 1.5,
                                At = kynthia,
                                Tag = "kynthia",
                                Immune = true,
                                Required = false,
                                MeleeDamage = eDamageType.Thrust,
                            },
                        },
                        Pulses = { new TrialPulse { IntervalSeconds = 6, Damage = 280, Radius = 1500, SourceTag = "kynthia", DamageType = eDamageType.Spirit, Message = "Kynthia's stare burns!" } },
                        OnStart = run =>
                        {
                            foreach (TrialMob gorgon in run.Mobs("kynthia"))
                            {
                                Resist(gorgon, 70, eProperty.Resist_Body, eProperty.Resist_Cold, eProperty.Resist_Energy, eProperty.Resist_Heat, eProperty.Resist_Matter, eProperty.Resist_Spirit);
                                Resist(gorgon, -20, eProperty.Resist_Crush, eProperty.Resist_Slash, eProperty.Resist_Thrust);
                            }
                        },
                        Done = run => Gone(run, "guide"),
                    },
                    new TrialPhase
                    {
                        Announce = "The Guide is dead. Close on Kynthia with steel!",
                        OnStart = run => run.SetImmune("kynthia", false),
                        Done = run => Gone(run, "kynthia"),
                    },
                },
            };
        }

        private static TrialDefinition AgnesSpareArm()
        {
            TrialPoint exit = new(439050, 661800, 12101);
            TrialPoint hall = new(439050, 665600, 12110);

            static TrialMobSpec Statue(string name, int x, int y, int z, bool required = true) => Foe(name, Marble, 62, 100, 4000, 1.0, new TrialPoint(x, y, z), required: required);

            TrialMobSpec Case() => Clickable("Agne's reliquary", Reliquary, 40, hall, "You lift Agne's right arm out of the reliquary, and every statue in the hall turns to look.", "case",
                (run, _) => run.Set("arm", true));

            return new TrialDefinition
            {
                ML = 8,
                Step = 9,
                Name = "Agne's Spare Arm",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = exit,
                StarterName = ServantName,
                StarterModel = Servant,
                Intro = "This row of statues was once the great hall of a temple, and Agne's right arm still lies at the heart of it. Clear this side of the hall and the reliquary will open. Whoever takes the arm must carry it out past me alive, for the far side of the hall will wake. Drop it, and it goes back to its case.",
                Victory = "You carry Agne's right arm clear of the hall.",
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The near side of the hall wakes.",
                        Mobs =
                        {
                            Statue("chrysiron statue", 438556, 662968, 12096),
                            Statue("chrysiron statue", 439510, 662989, 12096),
                            Statue("chrysiron statue", 438446, 663467, 12096),
                            Statue("chrysiron statue", 439601, 663494, 12097),
                            Statue("chrysiron statue", 439489, 664078, 12096),
                            Statue("chrysiron statue", 438577, 664095, 12096),
                            Statue("helicaon statue", 438707, 664845, 12096),
                            Statue("helicaon statue", 439381, 664870, 12096),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "The reliquary stands open at the heart of the hall.",
                        Mobs = { Case() },
                    },
                    new TrialPhase
                    {
                        Announce = "Run! Bring the arm out past the Servant!",
                        Mobs =
                        {
                            Statue("helicaon statue", 438638, 666316, 12121, false),
                            Statue("helicaon statue", 439402, 666343, 12115, false),
                            Statue("chrysiron statue", 438721, 667095, 12119, false),
                            Statue("chrysiron statue", 439515, 667108, 12127, false),
                            Statue("chrysiron statue", 438571, 667728, 12096, false),
                            Statue("chrysiron statue", 439645, 667730, 12120, false),
                        },
                        OnTick = run =>
                        {
                            if (!run.Get("arm", false) || run.Leader.IsAlive)
                                return;
                            run.Set("arm", false);
                            run.Tell("The arm falls from dead hands and returns to its reliquary.");
                            run.Spawn(Case());
                        },
                        Done = run => run.Get("arm", false) && run.Leader.IsAlive && Near(run.Leader, exit, 500),
                    },
                },
            };
        }

        private static TrialDefinition AgnesGreatMight()
        {
            TrialPoint talosHome = new(481060, 691913, 16457);
            TrialPoint[] altheus = { new(479498, 691349, 16411), new(481689, 693529, 16411) };

            static TrialPhase Wave(string announce, int warriors, int sages, int mages)
            {
                List<TrialPoint> spots = Circle(Battlefield, 500, warriors + sages + mages).ToList();
                return new TrialPhase
                {
                    Announce = announce,
                    Mobs = spots.Take(warriors).Select(at => Foe("Statue Warrior", 1321, 60, 60, 4000, 1.0, at, melee: eDamageType.Slash))
                        .Concat(spots.Skip(warriors).Take(sages).Select(at => Foe("Statue Sage", 1319, 60, 60, 3500, 0.8, at, "caster")))
                        .Concat(spots.Skip(warriors + sages).Select(at => Foe("Statue Mage", 1343, 60, 60, 3000, 0.7, at, "caster")))
                        .ToList(),
                    Pulses = { new TrialPulse { IntervalSeconds = 10, Damage = 140, Radius = 800, SourceTag = "caster", DamageType = eDamageType.Energy } },
                };
            }

            return new TrialDefinition
            {
                ML = 8,
                Step = 10,
                Name = "Agne's Great Might",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = Constructor,
                StarterName = "Agne's Constructor",
                StarterModel = Servant,
                Replaces = new[] { "Agne's Constructor", "Statue Warrior", "Statue Mage", "Statue Sage", "Guardian of the Talos Crystal", "Talos", "altheus Talos" },
                Intro = "Crystal, shield, sword, head, torso, arms and legs: you have earned them all, and the earning is what I take from you, for I have already fitted them. Stand clear. Agne will come down the steps and call his army to prove himself. Beat them, then beat him. His key opens what wakes Talos, and Talos must be toppled in his temple. His two guardians will try to mend him. Break them when they come.",
                Victory = "Talos crashes down across his temple, and his gold rings on the stones.",
                TimeLimitSeconds = 2400,
                LeashRange = 30000,
                Phases =
                {
                    Wave("Agne stands, and his first rank marches onto the field.", 6, 0, 0),
                    Wave("The second rank comes on, sages among them.", 4, 3, 0),
                    Wave("The last rank has mages. Take them first!", 3, 2, 3),
                    new TrialPhase
                    {
                        Announce = "Agne himself comes down the steps.",
                        Mobs = { Foe("Agne", Servant, 68, 120, 45000, 1.7, Battlefield, melee: eDamageType.Slash) },
                    },
                    new TrialPhase
                    {
                        Announce = "Agne falls, and a key rolls from his hand. His chest stands open to it, but not for long.",
                        Mobs = { Clickable("Agne's chest", Reliquary, 34, Battlefield, "The key turns. A crystal tumbles from the chest and lands in the grass.") },
                    },
                    new TrialPhase
                    {
                        Announce = "The crystal lies on the ground. Pick it up!",
                        Mobs = { Clickable("Talos crystal", 966, 30, new TrialPoint(463200, 688100, 13957), "It hums in your hand, and the great floating temple answers.") },
                    },
                    new TrialPhase
                    {
                        Announce = "Carry the crystal to the golden statue in Talos's temple.",
                        Mobs = { Clickable("Talos", 1181, 125, talosHome, "You set the crystal into the gold. The ring around the statue begins to rise.") },
                    },
                    new TrialPhase
                    {
                        Announce = "Talos wakes!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Talos",
                                Model = 1181,
                                Level = 70,
                                Size = 125,
                                Health = 140000,
                                DamageFactor = 2.2,
                                At = talosHome,
                                Tag = "talos",
                                Required = false,
                            },
                        },
                        OnTick = run =>
                        {
                            TrialMob talos = run.Mobs("talos").FirstOrDefault();
                            if (talos == null)
                                return;
                            if (TalosCallsForHealing(talos.HealthPercent, run.Get("healed", false)))
                            {
                                run.Set("healed", true);
                                talos.Health = talos.MaxHealth * 55 / 100;
                                run.SetImmune("talos", true);
                                run.Tell("The guardians step from their plinths and pour their strength into Talos. Break them!");
                                run.Spawn(Foe("altheus Talos", 998, 66, 125, 8000, 1.2, altheus[0], "altheus", required: false));
                                run.Spawn(Foe("altheus Talos", 989, 66, 125, 8000, 1.2, altheus[1], "altheus", required: false));
                                return;
                            }
                            if (run.Get("healed", false) && talos.Immune && Gone(run, "altheus"))
                            {
                                run.SetImmune("talos", false);
                                run.Tell("The guardians are down. Talos can be hurt again!");
                            }
                        },
                        Done = run => Gone(run, "talos"),
                    },
                },
            };
        }
    }
}
