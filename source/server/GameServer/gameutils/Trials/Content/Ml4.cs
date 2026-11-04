using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;
using static DOL.GS.Trials.Ml34Kit;

namespace DOL.GS.Trials
{
    /// <summary>
    /// Master Level 4: Stygia and the Land of Atum. The stones, the blood and the figurine of the old trials are
    /// not items here: finishing the earlier step stands for holding them.
    /// </summary>
    public static class Ml4
    {
        private const ushort Scorpion = 1263;
        private const ushort Mau = 1039;
        private const ushort MauPriest = 1041;
        private const ushort Setian = 1035;
        private const ushort SetianArmored = 1036;
        private const ushort Pharaoh = 1037;
        private const ushort Lion = 1193;
        private const ushort Djinn = 1196;
        private const ushort Whirlwind = 1269;
        private const ushort Crocodile = 34026;
        private const ushort Snake = 1233;
        private const ushort Gem = 1905;
        private const ushort Chest = 2362;
        private const ushort MagicPortal = 1438;
        private const ushort Swirl = 1684;
        private const ushort Colossus = 1264;
        private const ushort Obelisk = 1905;

        /// <summary>How close Martikhoras must stand to a falling obelisk for it to crush him.</summary>
        public const int ObeliskReach = 1200;
        public const double ObeliskHitShare = 0.18;
        public const double ObeliskMissShare = 0.05;

        public static double ObeliskShare(double distance) => distance <= ObeliskReach ? ObeliskHitShare : ObeliskMissShare;

        public static readonly string[] Stones =
        {
            "Crystalized Ghillian Eye", "Sandstone", "Radiant Sunstone", "Eye of Ra", "Storm Crystal", "Bloodstone",
        };

        /// <summary>The six Sobek statues along the Iter, west to east, from the client's zone fixtures.</summary>
        public static readonly TrialPoint[] Statues =
        {
            new(277248, 424576, 8056), new(288768, 430976, 8136), new(301440, 425088, 8176),
            new(313600, 430848, 8128), new(327680, 424192, 8048), new(342272, 432256, 8128),
        };

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return Sting();
            yield return Storms();
            yield return Roar();
            yield return LostGoddess();
            yield return MastersOfTheDesert();
            yield return Ghillan();
            yield return Portal();
            yield return Blood();
            yield return Oasis();
            yield return TheRisingPyramid();
        }

        private static TrialDefinition Sting()
        {
            TrialPoint camp = new(331500, 418106, 8373);
            return new TrialDefinition
            {
                ML = 4,
                Step = 1,
                Name = "Sting",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = camp,
                StarterName = "Mau Scorpion Tracker",
                StarterModel = Mau,
                Intro = "Thin out the scorpions here and the big ones come to see why. Thin those and something far older climbs down off the rocks. " +
                    "We call it Colossal. It carries a bloodstone in its gut, and the crocodiles of the Iter want that stone back.",
                Victory = "Colossal curls up and dies. The Bloodstone is yours in all but name: the statues of the Iter will know you.",
                Replaces = new[] { "Colossal" },
                TimeLimitSeconds = 1200,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The rocks rattle with scorpions.",
                        OnStart = run => Wave(run, Mob("large scorpion", Scorpion, 58, 58, 3000, 0.7, tag: "large", melee: eDamageType.Thrust), 5, camp, 450),
                        Done = Cleared("large"),
                    },
                    new TrialPhase
                    {
                        Announce = "Three giants answer the noise.",
                        OnStart = run => Wave(run, Mob("giant scorpion", Scorpion, 62, 112, 5000, 0.9, tag: "giant", melee: eDamageType.Thrust), 3, camp, 500),
                        Done = Cleared("giant"),
                    },
                    new TrialPhase
                    {
                        Announce = "Look up! Colossal drops from the rocks.",
                        Mobs = { Mob("Colossal", Scorpion, 66, 150, 20000, 1.1, On(camp, 300, 0, 2), "colossal", melee: eDamageType.Thrust) },
                        OnStart = run => Wave(run, Mob("young scorpion", Scorpion, 56, 41, 2000, 0.6, tag: "young", required: false, melee: eDamageType.Thrust), 3, camp, 600),
                        Done = Cleared("colossal"),
                    },
                },
            };
        }

        private static IEnumerable<TrialPhase> TakeTown(string name, string key, TrialPoint town, TrialPoint[] camps)
        {
            const int LaborerSeconds = 30;
            TrialMobSpec defender = Mob("setian warrior", SetianArmored, 60, 51, 3500, 0.9, tag: key, melee: eDamageType.Slash);

            yield return new TrialPhase
            {
                Announce = $"{name}: three camps guard the town. Clear them and let the tents burn.",
                OnStart = run =>
                {
                    foreach (TrialPoint camp in camps)
                        Wave(run, Mob("setian saut", Setian, 58, 50, 3000, 0.8, tag: key, melee: eDamageType.Slash), 3, camp, 250);
                },
                Done = Cleared(key),
            };
            yield return new TrialPhase
            {
                Announce = $"The camps of {name} are on fire. Take the town itself.",
                OnStart = run =>
                {
                    Wave(run, defender, 4, town, 300);
                    run.Spawn(Mob("setian stormlord", Setian, 62, 52, 6000, 1.0, town, key));
                },
                Done = Cleared(key),
            };
            yield return new TrialPhase
            {
                Announce = $"{name} burns, but the fortress is sending laborers to put it out. Kill them before they reach the fires!",
                OnStart = run => Wave(run, Mob("setian laborer", Setian, 54, 42, 2000, 0.4, tag: key, aggro: 300), 6, town, 900),
                OnTick = run =>
                {
                    if (!Every(run, $"{key} labor", LaborerSeconds))
                        return;
                    foreach (TrialMob laborer in run.Mobs(key).Where(mob => mob.Name == "setian laborer").ToList())
                    {
                        run.Tell("A laborer reaches the fire and calls for help!");
                        TrialPoint at = Where(laborer);
                        laborer.Delete();
                        run.Spawn(At(defender, at));
                    }
                },
                Done = Cleared(key),
            };
        }

        private static TrialDefinition Storms()
        {
            TrialPoint gate = new(277737, 404022, 8040);
            TrialPoint seti = new(277632, 399779, 8722);

            List<TrialPhase> phases = new();
            phases.AddRange(TakeTown("the eastern town", "east", new TrialPoint(289024, 407552, 8360),
                new[] { new TrialPoint(292736, 404096, 7952), new TrialPoint(290816, 413952, 7752), new TrialPoint(293760, 409216, 7672) }));
            phases.AddRange(TakeTown("the town before the fortress", "front", new TrialPoint(277248, 415104, 8336),
                new[] { new TrialPoint(281600, 417280, 7880), new TrialPoint(275840, 419840, 7872), new TrialPoint(271744, 415104, 8328) }));
            phases.AddRange(TakeTown("the western town", "western", new TrialPoint(266752, 399232, 7984),
                new[] { new TrialPoint(260992, 402560, 8048), new TrialPoint(259328, 399104, 7952), new TrialPoint(268416, 407040, 8312) }));
            phases.Add(new TrialPhase
            {
                Announce = "All three towns burn. The fortress gate stands open, and its garrison comes out to meet you.",
                OnStart = run =>
                {
                    Wave(run, Mob("setian thunder trooper", SetianArmored, 62, 50, 4000, 1.0, tag: "garrison", melee: eDamageType.Slash), 6, gate, 350);
                },
                Done = Cleared("garrison"),
            });
            phases.Add(new TrialPhase
            {
                Announce = "Seti the Pharaoh stands in his temple. His chaos priests shield him. Kill them first!",
                Mobs = { Mob("Seti the Pharaoh", Pharaoh, 67, 62, 60000, 1.3, seti, "seti", immune: true, melee: eDamageType.Slash) },
                OnStart = run => Wave(run, Mob("setian chaos priest", SetianArmored, 62, 50, 5000, 0.9, tag: "priest"), 4, seti, 200),
                Done = Cleared("priest"),
            });
            phases.Add(new TrialPhase
            {
                Announce = "The priests are dead. Seti's protection is gone!",
                OnStart = run => run.SetImmune("seti", false),
                Done = Cleared("seti"),
            });

            return new TrialDefinition
            {
                ML = 4,
                Step = 2,
                Name = "Storms",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(295500, 406000, 8169),
                StarterName = "Mau Rebel Scout",
                StarterModel = Mau,
                Intro = "The Fortress of Storms lives off three towns, and each town lives off three camps. Go at the fortress first and all of them fall on you. " +
                    "Work inwards. Start at the eastern town, then the one before the gate, then the one by the western dunes. Burn the camps, then the town, and when the laborers come, kill them before they reach the fires. " +
                    "Only then go for Seti. He holds the Storm Crystal.",
                Victory = "The Fortress of Storms burns and Seti lies dead. The Storm Crystal is yours in all but name.",
                Replaces = new[] { "Seti the Pharaoh" },
                TimeLimitSeconds = 2400,
                LeashRange = 36000,
                Phases = phases,
            };
        }

        private static TrialDefinition Roar()
        {
            TrialPoint den = new(289594, 437217, 7917);
            return new TrialDefinition
            {
                ML = 4,
                Step = 3,
                Name = "Roar",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = den,
                StarterName = "Mau Lion Warden",
                StarterModel = MauPriest,
                Intro = "Tutankhsekhmet walks these sands with a pride of sacred lions and the Eye of Ra in his keeping. Kill him and the Fires of Seth come down where he dies. " +
                    "Heal through them, and when they burn out, take the Eye from the ground.",
                Victory = "You lift the Eye of Ra from the sand.",
                Replaces = new[] { "Tutankhsekhmet" },
                TimeLimitSeconds = 1200,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "A great roar rolls across the dunes.",
                        Mobs = { Mob("Tutankhsekhmet", Lion, 65, 62, 18000, 1.1, On(den, 300, 0, 2), "lion king", melee: eDamageType.Slash) },
                        OnStart = run => Wave(run, Mob("sacred lion", Lion, 58, 50, 3000, 0.7, tag: "pride", required: false, melee: eDamageType.Slash), 4, den, 450),
                        Done = Cleared("lion king"),
                    },
                    new TrialPhase
                    {
                        Announce = "The Fires of Seth fall from the sky!",
                        Pulses = { new TrialPulse { IntervalSeconds = 3, Damage = 180, Radius = 800, Message = "Fire rains down around Tutankhsekhmet's body." } },
                        SurviveSeconds = 13,
                    },
                    new TrialPhase
                    {
                        Announce = "The fire dies. Something glitters in the ash.",
                        Mobs = { Clickable("Eye of Ra", Gem, 12, On(den, 150, 1, 2), "The Eye of Ra is warm in your hand.") },
                    },
                },
            };
        }

        private static TrialDefinition LostGoddess()
        {
            TrialPoint caravan = new(256726, 411174, 8006);
            TrialMobSpec Nomad() => Mob("mausekhmet nomad", Mau, 55, 50, 2500, 0.7, tag: "caravan", required: false, melee: eDamageType.Slash);

            void Child(TrialRun run, TrialMob mob) => run.Set("bauble", Where(mob));

            TrialMobSpec Miw(int index)
            {
                TrialMobSpec child = Mob("miw-shersekhmet", Mau, 50, 36, 3000, 0.4, On(caravan, 350, index, 2), "miw");
                child.OnDeath = Child;
                return child;
            }

            return new TrialDefinition
            {
                ML = 4,
                Step = 4,
                Name = "Lost Goddess",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = caravan,
                StarterName = "Mau Caravan Scribe",
                StarterModel = MauPriest,
                Intro = "The mausekhmet think a Radiant Sunstone is a holy thing, yet their priest let the children of the caravan take it as a plaything. " +
                    "Stand here and she will cry out to the whole caravan. Kill her through the nomads, then find the little ones. They are no threat, and one of them will have your stone.",
                Victory = "The Radiant Sunstone is yours. To the children it was only ever a bright pebble.",
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The mausekhmet high priest shrieks for the wagons to be defended!",
                        Mobs = { Mob("mausekhmet high priest", MauPriest, 62, 55, 40000, 1.0, On(caravan, 300, 0, 2), "priest") },
                        OnStart = run => Wave(run, Nomad(), 8, caravan, 500),
                        Done = Cleared("priest"),
                    },
                    new TrialPhase
                    {
                        Announce = "Two small figures bolt from the tents with nomads at their heels.",
                        Mobs = { Miw(0), Miw(1) },
                        OnStart = run => Wave(run, Nomad(), 6, caravan, 600),
                        Done = Cleared("miw"),
                    },
                    new TrialPhase
                    {
                        Announce = "A bright pebble lies where the child fell.",
                        OnStart = run =>
                        {
                            TrialMobSpec stone = Clickable("Radiant Sunstone", Gem, 12, run.Get("bauble", caravan), "You pick up the Radiant Sunstone.");
                            stone.Tag = "sunstone";
                            run.Spawn(stone);
                        },
                        Done = Cleared("sunstone"),
                    },
                },
            };
        }

        private static TrialDefinition MastersOfTheDesert()
        {
            TrialPoint dunes = new(265973, 444393, 7636);
            int[] calls = { 60, 15 };
            const int FormSeconds = 12;
            TrialMobSpec Sand() => Mob("whirlwind of sand", Whirlwind, 58, 50, 2500, 0.6, tag: "sand", required: false);

            void Storm(TrialRun run)
            {
                if (First(run, "jann") is not { } boss)
                    return;

                foreach (int percent in calls.Where(percent => HealthPercent(boss) <= percent && !run.Get<bool>($"called {percent}")))
                {
                    run.Set($"called {percent}", true);
                    run.Tell("Jamaluddin screams to the desert, and the whirlwinds answer!");
                    Wave(run, Sand(), 8, Where(boss), 500);
                }

                int form = run.Get<int>("form");
                if (form > 0)
                {
                    run.Set("form", form - 1);
                    if (form == 1)
                        boss.Model = Djinn;
                }
                else if (Every(run, "turn", 45))
                {
                    run.Set("form", FormSeconds);
                    boss.Model = Whirlwind;
                    run.Tell("Jamaluddin dissolves into a storm of sand. Stay on him!");
                }

                if (Every(run, "tornado", form > 0 ? 4 : 14))
                    Hurt(run, boss, Ring(run, Where(boss), 0, 650), 160, eDamageType.Crush);
            }

            return new TrialDefinition
            {
                ML = 4,
                Step = 5,
                Name = "Masters of the Desert",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = dunes,
                StarterName = "Mau Dune Reader",
                StarterModel = Mau,
                Intro = "Jamaluddin the Dao rules the whirlwinds here, and he holds a Sandstone. He will call them twice, early and again when he is nearly done, and more come than you would believe. " +
                    "Stay on him even when he loses his shape. If he is left alone he will bring the whole desert down on you.",
                Victory = "The dunes lie still. The Sandstone is yours in all but name.",
                Replaces = new[] { "Jamaluddin the Dao", "whirlwind of sand" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The sand lifts in columns around Jamaluddin.",
                        Mobs = { Mob("Jamaluddin the Dao", Djinn, 67, 50, 70000, 1.4, On(dunes, 300, 0, 2), "jann") },
                        OnStart = run => Wave(run, Sand(), 6, dunes, 600),
                        OnTick = Storm,
                        Done = Cleared("jann"),
                    },
                },
            };
        }

        private static TrialDefinition Ghillan()
        {
            TrialPoint circle = new(244291, 416646, 8376);
            const int MaxClones = 10;

            void Split(TrialRun run)
            {
                if (First(run, "oukesson") is not { } boss)
                    return;
                int cap = Scaled(MaxClones, run.HealthScale, 3);
                SplitMeter meter = run.Get<SplitMeter>("meter");
                foreach (TrialHit hit in TakeHits(run, "blows").Where(hit => hit.Damage > 0))
                {
                    if (meter.Hit(hit.AttackType == AttackData.eAttackType.Ranged) && run.Mobs("clone").Count() < cap)
                        run.Spawn(Mob(boss.Name, Djinn, 63, 50, 2500, 0.7, On(Where(boss), 250, Random.Shared.Next(8), 8), "clone", required: false));
                }
                if (run.Mobs("clone").Count() >= cap)
                {
                    boss.Health = Math.Min(boss.MaxHealth, boss.Health + boss.MaxHealth / 100);
                    if (Every(run, "mend", 10))
                        run.Tell("Oukesson's clones pour their strength back into him. Thin them out!");
                }
            }

            return new TrialDefinition
            {
                ML = 4,
                Step = 6,
                Name = "Ghillan",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = circle,
                StarterName = "Mau Ghillan Watcher",
                StarterModel = Mau,
                Intro = "Oukesson the Ghillan multiplies when he is struck. Every few blows bring a copy of him into the world. Arrows seem not to wake the split. " +
                    "Let ten of them stand and they begin to mend him. Only the first of them matters: keep your eyes on the one who stood here from the start.",
                Victory = "Oukesson and all his copies fall still. The Crystalized Ghillian Eye is yours in all but name.",
                Replaces = new[] { "Oukesson the Ghillan" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Oukesson stirs. Mark him well: every blow may bring a double.",
                        Mobs = { Mob("Oukesson the Ghillan", Djinn, 67, 50, 36000, 1.3, On(circle, 300, 0, 2), "oukesson") },
                        OnStart = run =>
                        {
                            run.Set("meter", new SplitMeter(6));
                            WatchHits(run, First(run, "oukesson"), "blows");
                        },
                        OnTick = Split,
                        Done = Cleared("oukesson"),
                    },
                },
            };
        }

        private static TrialDefinition Portal()
        {
            List<TrialPhase> phases = new();
            for (int i = 0; i < Statues.Length; i++)
            {
                TrialPoint statue = Statues[i];
                string stone = Stones[i];
                phases.Add(new TrialPhase
                {
                    Announce = $"Statue {i + 1} of {Statues.Length}: the {stone} belongs here. Crocodiles guard the socket.",
                    Mobs = { Clickable($"niche for the {stone}", Gem, 15, On(statue, 200, 1, 4), $"The {stone} clicks home, and the crocodile's head grinds round to face the pyramid.") },
                    OnStart = run => Wave(run, Mob("iter croc", Crocodile, 62, 60, 3000, 0.8, tag: "croc", melee: eDamageType.Crush), 3, statue, 350),
                });
            }

            return new TrialDefinition
            {
                ML = 4,
                Step = 7,
                Name = "Portal",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = Statues[0],
                StarterName = "Mau River Priest",
                StarterModel = MauPriest,
                Intro = "Six stone crocodiles watch over the Iter, from here to the far end of the Delta, and each wants the stone you took from the last six trials. " +
                    "Those deeds are the only key you need. Walk the river from west to east, drive off the crocodiles at each statue and turn its head towards the pyramid. " +
                    "When all six look on the pyramid, a way opens at its peak.",
                Victory = "All six guardians of the Iter face the pyramid. A light kindles at its peak.",
                RequiresSteps = new[] { 1, 2, 3, 4, 5, 6 },
                TimeLimitSeconds = 1800,
                LeashRange = 75000,
                Phases = phases,
            };
        }

        private static TrialDefinition Blood()
        {
            TrialPoint peak = new(256300, 425600, 9344);
            TrialPoint valley = new(346240, 404352, 8824);
            TrialPoint daehien = new(353613, 406725, 8824);
            int[] lanes = { -500, 0, 500 };
            const int ClosestRing = 600;

            void Burst(TrialRun run, TrialPoint at)
            {
                Hurt(run, run.Starter, Ring(run, at, 0, 400), 220, eDamageType.Heat);
                run.Tell("An iaculus bursts in a sheet of flame!");
            }

            TrialMobSpec Fuse()
            {
                TrialMobSpec snake = Mob("iaculus", Snake, 60, 29, 2000, 0.3, tag: "fuse", required: false, aggro: 0);
                snake.OnDeath = (run, mob) => Burst(run, Where(mob));
                return snake;
            }

            void Fuses(TrialRun run)
            {
                foreach (TrialMob fuse in run.Mobs("fuse").Where(mob => Ring(run, Where(mob), 0, 170).Any()).ToList())
                {
                    Burst(run, Where(fuse));
                    fuse.Delete();
                }

                if (First(run, "daehien") is not { } boss)
                    return;
                if (!run.Get<bool>("circling"))
                {
                    if (!boss.InCombat)
                        return;
                    run.Set("circling", true);
                    run.Set("ring", 1600);
                    run.Tell("The iaculus turn and begin to circle Daehien. Get inside the ring before it closes!");
                }

                if (Every(run, "tighten", 3))
                {
                    int ring = Math.Max(ClosestRing, run.Get<int>("ring") - 100);
                    run.Set("ring", ring);
                    List<TrialMob> circle = run.Mobs("fuse").ToList();
                    for (int i = 0; i < circle.Count; i++)
                    {
                        TrialPoint spot = On(Where(boss), ring, i, circle.Count);
                        circle[i].WalkTo(new Vector3(spot.X, spot.Y, spot.Z), 180);
                    }
                }
            }

            return new TrialDefinition
            {
                ML = 4,
                Step = 8,
                Name = "Blood",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = peak,
                StarterName = "Warden of the Peak",
                StarterModel = MauPriest,
                Intro = "With the six statues turned, the portal on this peak stands open to a hidden valley. Its snakes are full of fire. Touch one and it bursts, and that goes for killing them too, so pick your way between them. " +
                    "Daehien waits at the far end. When he is roused the snakes will circle him, tighter and tighter. Be inside that ring, not on it.",
                Victory = "Daehien's blood runs out over the sand. You have what you came for.",
                Replaces = new[] { "Daehien" },
                RequiresSteps = new[] { 7 },
                TimeLimitSeconds = 1800,
                LeashRange = 120000,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The portal shivers. Step through when your party is gathered.",
                        Mobs = { Clickable("Portal of the Peak", MagicPortal, 50, On(peak, 200, 1, 4), "The light closes around you.") },
                    },
                    new TrialPhase
                    {
                        Announce = "A long valley, thick with sleeping snakes. Daehien lies at the far end.",
                        Mobs = { Mob("Daehien", Snake, 70, 250, 100000, 1.5, daehien, "daehien", aggro: 900, melee: eDamageType.Thrust) },
                        OnStart = run =>
                        {
                            MoveParty(run, valley);
                            int count = Scaled(24, run.HealthScale, 8);
                            for (int i = 0; i < count; i++)
                                run.Spawn(At(Fuse(), Along(valley, daehien, 0.12 + 0.68 * i / Math.Max(1, count - 1), lanes[i % lanes.Length])));
                        },
                        OnTick = Fuses,
                        Done = Cleared("daehien"),
                    },
                    new TrialPhase
                    {
                        Announce = "The snakes fall dead. In a few moments the portal will carry you back to the peak.",
                        OnStart = run =>
                        {
                            foreach (TrialMob fuse in run.Mobs("fuse").ToList())
                                fuse.Delete();
                        },
                        OnTick = run =>
                        {
                            if (!Every(run, "home", 10))
                                return;
                            MoveParty(run, peak);
                            run.Set("back", true);
                        },
                        Done = run => run.Get<bool>("back"),
                    },
                },
            };
        }

        private static TrialDefinition Oasis()
        {
            TrialPoint ramp = new(251000, 425600, 8082);
            TrialPoint gaurmaes = new(252104, 425615, 8750);
            TrialPoint[] tornados =
            {
                new(252236, 425066, 8661), new(252716, 425743, 8981), new(251390, 426593, 8303), new(252791, 425684, 9032), new(252241, 426118, 8661),
            };

            void Hover(TrialRun run, string tag)
            {
                foreach (TrialMob mob in run.Mobs(tag))
                    mob.Flags |= GameNPC.eFlags.FLYING;
            }

            void Raise(TrialRun run)
            {
                int count = Scaled(tornados.Length, run.HealthScale);
                for (int i = 0; i < count; i++)
                    run.Spawn(Mob("Tornado", Whirlwind, 62, 100, 6000, 0.8, tornados[i], "tornado", required: false));
                Hover(run, "tornado");
                run.SetImmune("gaurmaes", true);
            }

            return new TrialDefinition
            {
                ML = 4,
                Step = 9,
                Name = "Oasis",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = ramp,
                StarterName = "Pyramid Dust Priest",
                StarterModel = MauPriest,
                Intro = "Gaurmaes the marid will not show himself for less than the blood of Daehien, and what you spilled in the valley will serve. " +
                    "Pour it out at the foot of the steps. He comes in a killing blast, so whoever pours it should expect that, and the rest should keep their distance. " +
                    "He cannot be touched while his tornados turn. Bring them down, and bring them down again.",
                Victory = "Gaurmaes bursts like a wave on rock. In the wet sand lies a Marid Figurine, or the right to one: the pyramid will open to you.",
                Replaces = new[] { "Gaurmaes", "Tornado" },
                RequiresSteps = new[] { 8 },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The chest at the foot of the ramp waits for the blood of Daehien.",
                        Mobs = { Clickable("Blood of Daehien", Chest, 30, On(ramp, 200, 2, 4), "You pour out the blood. The ground begins to shake.") },
                    },
                    new TrialPhase
                    {
                        Announce = "The air tightens. Get away from the ramp!",
                        Pulses = { new TrialPulse { IntervalSeconds = 5, Damage = 280, Radius = 900, DamageType = eDamageType.Cold, Message = "Gaurmaes arrives in a crash of water!" } },
                        SurviveSeconds = 6,
                    },
                    new TrialPhase
                    {
                        Announce = "Gaurmaes looms over the steps, wrapped in tornados. Bring them down!",
                        Mobs = { Mob("Gaurmaes", Djinn, 69, 150, 85000, 1.5, gaurmaes, "gaurmaes", immune: true) },
                        OnStart = run =>
                        {
                            Hover(run, "gaurmaes");
                            Raise(run);
                        },
                        OnTick = run =>
                        {
                            if (First(run, "gaurmaes") is not { } boss)
                                return;
                            if (boss.Immune && !run.Mobs("tornado").Any())
                            {
                                boss.Immune = false;
                                run.Tell("The tornados are gone. Gaurmaes is exposed!");
                            }
                            if (HealthPercent(boss) <= 50 && !run.Get<bool>("second wind"))
                            {
                                run.Set("second wind", true);
                                run.Tell("Gaurmaes roars, and new tornados spin up around him!");
                                Raise(run);
                            }
                        },
                        Done = Cleared("gaurmaes"),
                    },
                },
            };
        }

        private static TrialDefinition TheRisingPyramid()
        {
            TrialPoint door = new(32898, 28195, 16900);
            TrialPoint martikhoras = new(30311, 33031, 15700);
            (TrialPoint Spot, ushort Model)[] court =
            {
                (new TrialPoint(32563, 34536, 15870), 1172), (new TrialPoint(31409, 34532, 15870), 1172), (new TrialPoint(33381, 33736, 15870), 1173),
                (new TrialPoint(33058, 32901, 16000), 1174), (new TrialPoint(31002, 32904, 16000), 1172), (new TrialPoint(30603, 33713, 15870), 1174),
            };
            TrialPoint[] obelisks =
            {
                new(32563, 34536, 15870), new(31409, 34532, 15870), new(33381, 33736, 15870), new(30603, 33713, 15870),
            };

            void Falls(TrialRun run, TrialMob obelisk)
            {
                if (First(run, "martikhoras") is not { } boss)
                    return;
                double share = ObeliskShare(Distance(Where(boss), Where(obelisk)));
                boss.Health = Math.Max(1, boss.Health - (int)(boss.MaxHealth * share));
                run.Tell(share == ObeliskHitShare ? "The obelisk crashes down on Martikhoras!" : "The obelisk crashes down, and Martikhoras is barely caught by the edge of it.");
            }

            TrialMobSpec Sphinx(TrialPoint at, ushort model) => Mob("corrupt androsphinx", model, 62, 100, 6000, 1.1, at, "sphinx", melee: eDamageType.Slash);

            return new TrialDefinition
            {
                ML = 4,
                Step = 10,
                Name = "The Rising Pyramid",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Pyramid,
                Anchor = door,
                StarterName = "Keeper of the Lower Door",
                StarterModel = MauPriest,
                Intro = "Beating Gaurmaes earned you the Marid Figurine, and the pad before this door knows it. Past the door wait the sphinxes, and past them Martikhoras. " +
                    "Steel alone will take far too long. Four black obelisks stand in his hall. Bring one down while he stands beside it and it will break him. Get him under all four, and then finish it.",
                Victory = "Martikhoras lies crushed beneath his own obelisks. The Great Pyramid is silent, and your fourth Master Level is won.",
                Replaces = new[] { "Martikhoras", "corrupt androsphinx" },
                TimeLimitSeconds = 2400,
                LeashRange = 12000,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The pad sinks a finger's width. Clicks run away beneath your feet.",
                        Mobs = { Clickable("Figurine Pad", Swirl, 40, On(door, 150, 1, 4), "You set the figurine on the pad. The way down opens.") },
                    },
                    new TrialPhase
                    {
                        Announce = "Two sphinxes bar the first chamber.",
                        Mobs = { Sphinx(new TrialPoint(33403, 29450, 16600), 1173), Sphinx(new TrialPoint(32403, 29445, 16600), 1173) },
                        Done = Cleared("sphinx"),
                    },
                    new TrialPhase
                    {
                        Announce = "The court of Martikhoras rises. Clear it before you wake its lord.",
                        OnStart = run =>
                        {
                            int count = Scaled(court.Length, run.HealthScale);
                            for (int i = 0; i < count; i++)
                                run.Spawn(Sphinx(court[i].Spot, court[i].Model));
                        },
                        Done = Cleared("sphinx"),
                    },
                    new TrialPhase
                    {
                        Announce = "Martikhoras wakes! Stand him beside an obelisk, then bring it down on him.",
                        Mobs = { Mob("Martikhoras", Colossus, 70, 200, 150000, 1.7, martikhoras, "martikhoras", melee: eDamageType.Slash) },
                        OnStart = run =>
                        {
                            foreach (TrialPoint at in obelisks)
                            {
                                TrialMobSpec spec = Mob("black obelisk", Obelisk, 65, 60, 20000, 0.01, at, "obelisk", required: false, aggro: 0);
                                spec.OnDeath = Falls;
                                run.Spawn(spec).MaxSpeedBase = 0;
                            }
                        },
                        OnTick = run =>
                        {
                            if (First(run, "martikhoras") is { } boss && Every(run, "sweep", 25))
                            {
                                Hurt(run, boss, Ring(run, Where(boss), 0, 700), 280, eDamageType.Slash);
                                run.Tell("Martikhoras sweeps the hall with his claws.");
                            }
                        },
                        Done = Cleared("martikhoras"),
                    },
                },
            };
        }
    }
}
