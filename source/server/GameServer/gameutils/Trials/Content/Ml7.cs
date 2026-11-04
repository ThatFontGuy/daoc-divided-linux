using System;
using System.Collections.Generic;
using System.Linq;
using static DOL.GS.Trials.Ml7Kit;

namespace DOL.GS.Trials
{
    /// <summary>
    /// Master Level 7 trials, in Deep Volcanus. The bridge lies on x 32000, the four feuding races share the grid
    /// north of it, and the Mediators' arenas are sealed rooms that can only be reached by being sent there.
    /// </summary>
    public static class Ml7
    {
        private const ushort Apophian = 1199, Volurgon = 1197, Shaitan = 1198, Hephaestian = 1196, Fire = 456, Idol = 1203, Snake = 1202;

        private const int LavaWindowSeconds = 40;
        private const int ForceWindowSeconds = 30;
        private const int MaxApophians = 8;

        private static readonly TrialPoint BridgeSouth = new(32000, 28800, 15662);
        private static readonly TrialPoint BridgeGate = new(32000, 28250, 15674);
        private static readonly TrialPoint BridgeNorth = new(32000, 25200, 15668);

        private static readonly TrialPoint GridCentre = new(32000, 22300, 15675);

        private static readonly TrialPoint MediatorApophian = new(36622, 26592, 15661);
        private static readonly TrialPoint MediatorVolurgon = new(27176, 20278, 15645);
        private static readonly TrialPoint MediatorShaitan = new(37454, 20987, 15663);
        private static readonly TrialPoint MediatorHephaestian = new(26745, 27309, 15645);

        private static readonly TrialPoint ArenaApophian = new(38637, 30575, 17725);
        private static readonly TrialPoint ArenaVolurgon = new(23514, 20620, 17050);
        private static readonly TrialPoint ArenaShaitan = new(41911, 28906, 17718);
        private static readonly TrialPoint ArenaHephaestian = new(26645, 29053, 16885);

        private static readonly TrialPoint Transmuter = new(40717, 13042, 14909);
        private static readonly TrialPoint KatoriiHome = new(35078, 13048, 15677);
        private static readonly TrialPoint PetRoom = new(38091, 14233, 15678);
        private static readonly TrialPoint TyphonGate = new(42740, 15900, 14910);

        private static readonly TrialPoint Throat = new(45400, 22200, 14899);
        private static readonly TrialPoint NorthAlcove = new(45813, 21293, 14890);
        private static readonly TrialPoint SouthAlcove = new(45502, 22650, 14879);
        private static readonly TrialPoint FarWarder = new(47284, 23628, 14900);

        private static readonly TrialPoint PoolShore = new(47500, 22000, 14857);
        private static readonly TrialPoint EssenceHome = new(48805, 21418, 14741);
        private static readonly TrialPoint[] TyphonSpots =
        {
            new(50626, 19816, 14737),
            new(47000, 20000, 14741),
            new(50500, 24500, 14741),
            new(51000, 22500, 14741),
        };

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return LavaBridge();
            yield return KnowYourOpponents();
            yield return ApophiansChallenge();
            yield return VolurgonsChallenge();
            yield return ShaitansChallenge();
            yield return HephaestiansChallenge();
            yield return CrossingTheChamber();
            yield return Pillars();
            yield return FacingTyphon();
            yield return TyphonsRage();
        }

        /// <summary>One level every half minute, from 60 up to the cap of 70.</summary>
        public static byte ApophianLevel(int seconds) => (byte)Math.Min(70, 60 + seconds / 30);

        /// <summary>Which of Typhon's four pools he belongs in at this health. The last one is where he stays.</summary>
        public static int TyphonSpot(int healthPercent) => MarksPassed(healthPercent, 75, 50, 25);

        public static bool OnBridge(int x, int y) => Math.Abs(x - 32000) <= 400 && y > 25400 && y < 28300;

        private static TrialDefinition LavaBridge()
        {
            TrialMobSpec Sluice() => Clickable("lavafall sluice", Idol, 30, BridgeGate,
                "You press the gauntlet into the sluice. It holds, and the lavafall stops.", "sluice",
                (run, _) => run.Set("lava", LavaWindowSeconds));

            return new TrialDefinition
            {
                ML = 7,
                Step = 1,
                Name = "The Lava Bridge",
                Scope = TrialScope.Group,
                Zone = TrialZone.Volcanus,
                Anchor = BridgeSouth,
                StarterName = "Keeper of the Lavafall",
                StarterModel = Idol,
                Intro = "No flesh crosses while the lavafall runs. A gauntlet could turn it: salamander wool for the lining, a barracuda needle to sew it, and an unmarked volurgon hand for the shape. All three can be had in this very room if you know where the heat keeps them. One wearer is enough, but the fall will not stay shut for long.",
                Victory = "You stand on the far side of the lava bridge.",
                TimeLimitSeconds = 1200,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Gather the wool, the needle and the hand.",
                        Mobs =
                        {
                            Foe("salamander hatchling", 1261, 58, 50, 3000, 0.7, new TrialPoint(31750, 29050, 15662), melee: eDamageType.Heat),
                            Foe("salamander hatchling", 1261, 58, 50, 3000, 0.7, new TrialPoint(32250, 29050, 15662), melee: eDamageType.Heat),
                            Foe("pristine volurgon", Volurgon, 62, 55, 6000, 1.0, new TrialPoint(32000, 29150, 15662)),
                            Clickable("charred barracuda", 967, 40, new TrialPoint(31750, 28650, 15662), "You snap a clean needle from the spine of the burnt fish."),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "The parts draw together into a gauntlet. Set it to the sluice at the head of the bridge.",
                        Mobs = { Sluice() },
                    },
                    new TrialPhase
                    {
                        Announce = "The lavafall is shut. Cross now!",
                        OnStart = run => run.Set("lava", LavaWindowSeconds),
                        OnTick = run =>
                        {
                            int left = run.Get("lava", 0);
                            run.Set("lava", left - 1);
                            if (left == 1)
                            {
                                run.Tell("The lavafall breaks loose again. Return to the sluice.");
                                run.Spawn(Sluice());
                            }
                            if (left > 0)
                                return;
                            foreach (GameLiving victim in run.Hostiles(run.Starter, 4000).Where(living => OnBridge(living.X, living.Y)).ToList())
                                victim.TakeDamage(run.Starter, eDamageType.Heat, 120, 0);
                        },
                        Done = run => Near(run.Leader, BridgeNorth, 500),
                    },
                },
            };
        }

        private static TrialDefinition KnowYourOpponents()
        {
            static TrialPhase Feud(string race, ushort model, int x, int y, string announce) => new()
            {
                Announce = announce,
                Mobs = AtEach(Circle(new TrialPoint(x, y, 15675), 220, 5), at => Foe($"{race} feudist", model, 62, 55, 4000, 0.9, at)).ToList(),
            };

            return new TrialDefinition
            {
                ML = 7,
                Step = 2,
                Name = "Know your Opponents",
                Scope = TrialScope.Group,
                Zone = TrialZone.Volcanus,
                Anchor = GridCentre,
                RequiresSteps = new[] { 1 },
                StarterName = "Balance of the Four",
                StarterModel = Idol,
                Replaces = new[] { "Balance of the Four" },
                Intro = "Four races feud in these halls and I weigh them all. You will not end their quarrel, and I do not ask it. Stand in each of their rooms until each has marked you as a danger. Only then will their Mediators speak to you.",
                Victory = "All four races now know your face. Their Mediators will receive you.",
                TimeLimitSeconds = 1800,
                Phases =
                {
                    Feud("volurgon", Volurgon, 28900, 22240, "The volurgons come first, in the room to the northwest."),
                    Feud("hephaestian", Hephaestian, 28900, 23800, "You have learned all the volurgons can teach. The hephaestians wait to the southwest."),
                    Feud("shaitan", Shaitan, 35040, 22240, "You have learned all the hephaestians can teach. The shaitan wait to the northeast."),
                    Feud("apophian", Apophian, 35040, 23800, "You have learned all the shaitan can teach. The apophians wait to the southeast."),
                },
            };
        }

        /// <summary>The Mediators' shared shape: send the group to its arena, hold out, and come home.</summary>
        private static TrialDefinition Challenge(int step, string name, string mediator, ushort model, string race, TrialPoint home, TrialPoint arena, string intro, int seconds, TrialPhase fight)
        {
            Action<TrialRun> start = fight.OnStart;
            fight.SurviveSeconds = seconds;
            fight.OnStart = run =>
            {
                MoveParty(run, arena);
                start?.Invoke(run);
            };

            return new TrialDefinition
            {
                ML = 7,
                Step = step,
                Name = name,
                Scope = TrialScope.Group,
                Zone = TrialZone.Volcanus,
                Anchor = home,
                RequiresSteps = new[] { 2 },
                StarterName = mediator,
                StarterModel = model,
                Replaces = new[] { mediator },
                Intro = intro,
                Victory = $"The {race} accept that you can endure.",
                TimeLimitSeconds = 900,
                LeashRange = 12000,
                OnEnd = (run, won) =>
                {
                    if (!won)
                        MoveParty(run, home);
                },
                Phases =
                {
                    fight,
                    new TrialPhase
                    {
                        Announce = "The Mediator calls you back.",
                        OnStart = run => MoveParty(run, home),
                        SurviveSeconds = 1,
                    },
                },
            };
        }

        private static TrialPoint[] ArenaSpots(TrialPoint arena) => Circle(arena, 450, 4).ToArray();

        private static TrialMobSpec Endurer(TrialPoint at, byte level) => new()
        {
            Name = "apophian endurer",
            Model = Apophian,
            Level = level,
            Size = 60,
            Health = 12000,
            DamageFactor = 0.8,
            At = at,
            Tag = "apophian",
            Required = false,
            MeleeDamage = eDamageType.Thrust,
            OnDeath = (run, mob) =>
            {
                if (run.Mobs("apophian").Count() + 1 >= MaxApophians)
                    return;
                run.Tell("The apophian comes apart, and two rise from the pieces!");
                foreach (TrialPoint point in Circle(new TrialPoint(mob.X, mob.Y, mob.Z), 120, 2))
                    run.Spawn(Endurer(point, mob.Level));
            },
        };

        private static TrialDefinition ApophiansChallenge() => Challenge(3, "Apophian's Challenge", "Mediator of the Apophians", Apophian, "apophians", MediatorApophian, ArenaApophian,
            "My people ask one thing of you: endure. I will send you to one who grows while you stand before him. Strike him down and you will have two to deal with. Do not try to win. Be alive when he tires of you.", 480,
            new TrialPhase
            {
                Announce = "Hold him. He grows by the minute, and killing him only makes more.",
                Mobs = { Endurer(ArenaApophian, 60) },
                OnTick = run =>
                {
                    int seconds = Count(run, "seconds");
                    if (seconds % 30 != 0)
                        return;
                    foreach (TrialMob mob in run.Mobs("apophian"))
                    {
                        mob.Level = ApophianLevel(seconds);
                        mob.DamageFactor = run.DamageScale * (0.8 + seconds / 900.0);
                    }
                },
            });

        private static TrialDefinition VolurgonsChallenge()
        {
            TrialPoint[] spots = ArenaSpots(ArenaVolurgon);

            void Pop(TrialRun run, int seconds)
            {
                run.Tell("Mandra rises, and her rage comes with her.");
                run.Spawn(new TrialMobSpec
                {
                    Name = "Volurgon Mandra",
                    Model = Volurgon,
                    Level = 66,
                    Size = 70,
                    Health = 7000,
                    DamageFactor = 0.8,
                    At = spots[seconds % spots.Length],
                    Tag = "mandra",
                    Required = false,
                    OnDeath = (trial, _) =>
                    {
                        foreach (TrialMob rage in trial.Mobs("rage").ToList())
                            rage.Delete();
                        trial.Set("next", trial.Get("seconds", 0) + 6);
                    },
                });

                int rages = seconds > 300 ? 2 : 1;
                for (int i = 0; i < rages; i++)
                {
                    TrialMob rage = run.Spawn(new TrialMobSpec
                    {
                        Name = "Rage of the Volurgons",
                        Model = Fire,
                        Level = 70,
                        Size = 60,
                        Health = 5000,
                        DamageFactor = 0.1,
                        At = spots[(seconds + 2 + i) % spots.Length],
                        Tag = "rage",
                        Immune = true,
                        Required = false,
                        AggroRange = 3000,
                        MeleeDamage = eDamageType.Heat,
                    });
                    rage.MaxSpeedBase = 80;
                }
            }

            return Challenge(4, "Volurgon's Challenge", "Mediator of the Volurgons", Volurgon, "volurgons", MediatorVolurgon, ArenaVolurgon,
                "Mandra of my people does not stay dead, and her rage walks behind her. Fell her quickly and the rage goes with her. Be slow and it will reach you. Do this for as long as we ask.", 420,
                new TrialPhase
                {
                    Announce = "Kill Mandra before her rage reaches you, again and again.",
                    Pulses = { new TrialPulse { IntervalSeconds = 4, Damage = 250, Radius = 300, SourceTag = "rage" } },
                    OnTick = run =>
                    {
                        int seconds = Count(run, "seconds");
                        if (Gone(run, "mandra") && seconds >= run.Get("next", 3))
                        {
                            run.Set("next", int.MaxValue);
                            Pop(run, seconds);
                        }
                    },
                });
        }

        private static TrialDefinition ShaitansChallenge()
        {
            TrialPoint[] spots = ArenaSpots(ArenaShaitan);

            return Challenge(5, "Shaitan's Challenge", "Mediator of the Shaitan", Shaitan, "shaitan", MediatorShaitan, ArenaShaitan,
                "One of my sisters will find you in a place of her choosing, and she burns all who stand close. If she still lives when the next arrives you will have two, and cold steel is your friend either way.", 420,
                new TrialPhase
                {
                    Announce = "A great jinni is coming. Do not let her wait for her sisters.",
                    Pulses = { new TrialPulse { IntervalSeconds = 8, Damage = 200, Radius = 450, SourceTag = "jinni", Message = "Heat rolls off the jinni!" } },
                    OnTick = run =>
                    {
                        int seconds = Count(run, "seconds");
                        if (seconds % 75 != 2 || run.Mobs("jinni").Count() >= 3)
                            return;
                        TrialMob jinni = run.Spawn(Foe("Shaitan jinni", Shaitan, 66, 75, 9000, 1.0, spots[seconds / 75 % spots.Length], "jinni", eDamageType.Heat, false));
                        Resist(jinni, 50, eProperty.Resist_Heat);
                        Resist(jinni, -25, eProperty.Resist_Cold);
                    },
                });
        }

        private static TrialDefinition HephaestiansChallenge()
        {
            TrialPoint[] spots = ArenaSpots(ArenaHephaestian);

            return Challenge(6, "Hephaestian's Challenge", "Mediator of the Hephaestians", Hephaestian, "hephaestians", MediatorHephaestian, ArenaHephaestian,
                "We are many and we do not hurry. One of us will step out of the wall, and then another, and then another. Each one burns the hand that strikes it. Break them faster than they come.", 360,
                new TrialPhase
                {
                    Announce = "They step out of the walls. Keep their numbers down.",
                    OnTick = run =>
                    {
                        int seconds = Count(run, "seconds");
                        if (seconds % 20 != 2 || run.Mobs("hephaestian").Count() >= 6)
                            return;
                        TrialMobSpec spec = Foe("hephaestian tester", Hephaestian, 64, 60, 5000, 0.7, spots[seconds / 20 % spots.Length], "hephaestian", eDamageType.Heat, false);
                        spec.Reflect = 0.03;
                        Resist(run.Spawn(spec), -25, eProperty.Resist_Cold);
                    },
                });
        }

        private static TrialDefinition CrossingTheChamber() => new()
        {
            ML = 7,
            Step = 7,
            Name = "Crossing the Chamber",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Volcanus,
            Anchor = new TrialPoint(32000, 19400, 15678),
            StarterName = "Watcher of the Chamber",
            StarterModel = Idol,
            Replaces = new[] { "Flame of Volcanus" },
            Intro = "North of here the rock itself burns. The Flame of Volcanus holds the chamber, and all the small burning things that wander it are only its spillage. Leave the sparks be if you can, and put out the fire.",
            Victory = "The Flame of Volcanus gutters out, and the chamber lies open.",
            TimeLimitSeconds = 1800,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The Flame of Volcanus wakes on its island.",
                    Mobs = { Foe("Flame of Volcanus", Fire, 68, 75, 70000, 1.6, new TrialPoint(31654, 17559, 15832), "flame", eDamageType.Heat) },
                    Pulses = { new TrialPulse { IntervalSeconds = 14, Damage = 220, Radius = 700, SourceTag = "flame", Message = "The Flame flares!" } },
                    OnStart = run =>
                    {
                        foreach (TrialMob flame in run.Mobs("flame"))
                        {
                            Resist(flame, 60, eProperty.Resist_Heat);
                            Resist(flame, -25, eProperty.Resist_Cold);
                        }
                    },
                    OnTick = run =>
                    {
                        if (Count(run, "seconds") % 40 != 0 || run.Mobs("spark").Count() >= 4)
                            return;
                        foreach (TrialPoint point in Circle(new TrialPoint(31654, 17559, 15832), 120, 2))
                            run.Spawn(Foe("spark of Volcanus", Fire, 60, 25, 2000, 0.5, point, "spark", eDamageType.Heat, false));
                    },
                },
            },
        };

        private static TrialPulse Gaze() => new() { IntervalSeconds = 2, Damage = 300, Radius = 700, SourceTag = "katorii", DamageType = eDamageType.Spirit };

        private static TrialMobSpec Serpent(string name) => Foe(name, Snake, 66, 80, 22000, 1.4, PetRoom, "pet", eDamageType.Thrust, false);

        private static TrialPhase SerpentHunt(string name, string announce) => new()
        {
            Announce = announce,
            Mobs = { Serpent(name) },
            Pulses = { Gaze() },
            Done = run => Gone(run, "pet"),
        };

        private static TrialPhase Plate(string text) => new()
        {
            Announce = "It leaves a runed metal plate. Carry it to the box before Typhon's gate.",
            Mobs = { Clickable("plate box", Idol, 30, TyphonGate, text, "box") },
            Pulses = { Gaze() },
            Done = run => Gone(run, "box"),
        };

        private static TrialDefinition Pillars() => new()
        {
            ML = 7,
            Step = 8,
            Name = "Pillars",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Volcanus,
            Anchor = Transmuter,
            StarterName = "Ancient Transmuter",
            StarterModel = 1191,
            Replaces = new[] { "Ancient Transmuter", "Katorii", "Katorii's pet" },
            Intro = "Katorii walks the pillared halls above us, and no blade can reach her while her three great serpents draw breath. Do not stand where she can see you. Hunt the serpents at the top of the stairs, one at a time, and feed the plates they leave to the box at Typhon's gate. Each plate weakens her hold.",
            Victory = "Katorii falls among her pillars, and her gaze goes out.",
            TimeLimitSeconds = 2400,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Katorii's Breath stirs at the top of the stairs. Keep clear of Katorii herself: her gaze withers all it finds.",
                    Mobs =
                    {
                        new TrialMobSpec
                        {
                            Name = "Katorii",
                            Model = 1195,
                            Level = 70,
                            Size = 85,
                            Health = 80000,
                            DamageFactor = 2.0,
                            At = KatoriiHome,
                            Tag = "katorii",
                            Immune = true,
                            Required = false,
                            AggroRange = 400,
                            MeleeDamage = eDamageType.Thrust,
                        },
                        Serpent("Katorii's Breath"),
                    },
                    Pulses = { Gaze() },
                    Done = run => Gone(run, "pet"),
                },
                Plate("The plate slides home, and a scream comes through the stone."),
                SerpentHunt("Katorii's Touch", "Katorii screams and sends her Touch to the head of the stairs."),
                Plate("The plate slides home. Somewhere above, a great coil thrashes."),
                SerpentHunt("Katorii's Blood", "Katorii screams and sends her Blood to the head of the stairs."),
                Plate("The last plate slides home, and Katorii's hold on the pillars breaks."),
                new TrialPhase
                {
                    Announce = "Katorii can be hurt! Go to her in the maze. Small snakes gather to defend her.",
                    Mobs = AtEach(Circle(KatoriiHome, 280, 4), at => Foe("Katorii's hatchling", Snake, 60, 40, 3000, 0.8, at, required: false)).ToList(),
                    OnStart = run => run.SetImmune("katorii", false),
                    Done = run => Gone(run, "katorii"),
                },
            },
        };

        private static TrialDefinition FacingTyphon()
        {
            TrialMobSpec North() => Foe("apophian aggressor", Apophian, 64, 60, 6000, 1.0, NorthAlcove, "north", eDamageType.Thrust, false);
            TrialMobSpec South() => Foe("corrupt volurgon", Volurgon, 64, 60, 6000, 1.0, SouthAlcove, "south", required: false);

            return new TrialDefinition
            {
                ML = 7,
                Step = 9,
                Name = "Facing Typhon",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Volcanus,
                Anchor = Throat,
                RequiresSteps = new[] { 8 },
                StarterName = "Battlewarder",
                StarterModel = Idol,
                Replaces = new[] { "apophian aggressor", "apophian crusher", "apophian enforcer", "corrupt volurgon", "mischievous volurgon", "unruly volurgon" },
                Intro = "Your plates opened the gate. They do not open this. A force turns the air here and throws back all who push through. Two keepers feed it from the alcoves, one to the north and one to the south, and they rise again almost at once. Fell both, and in the moment it falters, walk past the far warder.",
                Victory = "You stand past the force, in sight of the lava pool.",
                TimeLimitSeconds = 1200,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The keepers stand in the alcoves. Fell them close together.",
                        Mobs = { North(), South() },
                        Pulses = { new TrialPulse { IntervalSeconds = 6, Damage = 120, Radius = 500, DamageType = eDamageType.Energy, Message = "The force throws you about." } },
                        OnTick = run =>
                        {
                            bool north = Gone(run, "north"), south = Gone(run, "south");
                            int open = run.Get("open", 0);
                            if (open > 0)
                            {
                                run.Set("open", open - 1);
                                if (open > 1)
                                    return;
                                run.Tell("The force turns again, and the keepers rise.");
                                run.Spawn(North());
                                run.Spawn(South());
                                return;
                            }
                            if (north && south)
                            {
                                run.Set("open", ForceWindowSeconds);
                                run.Set("alone", 0);
                                run.Tell("The force falters! Past the far warder, now!");
                                return;
                            }
                            if (!north && !south || Count(run, "alone") < 25)
                                return;
                            run.Set("alone", 0);
                            run.Tell("The fallen keeper rises again.");
                            run.Spawn(north ? North() : South());
                        },
                        Done = run => run.Get("open", 0) > 0 && Near(run.Leader, FarWarder, 700),
                    },
                },
            };
        }

        private static TrialMobSpec Essence() => new()
        {
            Name = "Typhon's Essence",
            Model = Fire,
            Level = 60,
            Size = 55,
            Health = 8000,
            DamageFactor = 0.5,
            At = EssenceHome,
            Tag = "essence",
            Required = false,
            AggroRange = 3500,
            MeleeDamage = eDamageType.Heat,
        };

        private static TrialDefinition TyphonsRage() => new()
        {
            ML = 7,
            Step = 10,
            Name = "Typhon's Rage",
            Scope = TrialScope.Raid,
            Zone = TrialZone.Volcanus,
            Anchor = PoolShore,
            StarterName = "Warden of the Lava Pool",
            StarterModel = Idol,
            Replaces = new[] { "Typhon", "Typhon's Essence" },
            Intro = "He lies in the pool, and he has waited a long time. The gauntlet, the favour of the four races and the plates are spent; all you carry now is that you got here. His Essence drifts above the lava, and while it is not fighting, nothing you do will mark him. Keep it busy, and do not put it out if you can help it, for it takes its time returning. Heat is nothing to him. Cold is what he fears, and a heavy blunt blow will not go amiss.",
            Victory = "Typhon sinks into his pool, and for the first time in an age the deep is quiet.",
            TimeLimitSeconds = 2400,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Typhon rises from the lava!",
                    Mobs =
                    {
                        new TrialMobSpec
                        {
                            Name = "Typhon",
                            Model = 830,
                            Level = 70,
                            Size = 100,
                            Health = 130000,
                            DamageFactor = 2.0,
                            At = TyphonSpots[0],
                            Tag = "typhon",
                            Immune = true,
                            Required = false,
                        },
                        Essence(),
                    },
                    Pulses = { new TrialPulse { IntervalSeconds = 15, Damage = 250, Radius = 900, SourceTag = "typhon", Message = "The pool heaves around Typhon!" } },
                    OnStart = run =>
                    {
                        foreach (TrialMob typhon in run.Mobs("typhon"))
                        {
                            Resist(typhon, 70, eProperty.Resist_Heat);
                            Resist(typhon, -50, eProperty.Resist_Cold);
                            Resist(typhon, -15, eProperty.Resist_Crush);
                        }
                    },
                    OnTick = TyphonTick,
                    Done = run => Gone(run, "typhon"),
                },
            },
        };

        private static void TyphonTick(TrialRun run)
        {
            bool engaged = run.Mobs("essence").Any(essence => essence.InCombat);
            if (engaged == run.Get("guarded", true))
            {
                run.Set("guarded", !engaged);
                run.SetImmune("typhon", !engaged);
                run.Tell(engaged ? "The Essence is held, and Typhon can be hurt!" : "The Essence drifts free, and Typhon's hide closes over.");
            }

            if (Gone(run, "essence") && Count(run, "essence.back") >= 20)
            {
                run.Set("essence.back", 0);
                run.Tell("Typhon's Essence rekindles above the pool.");
                run.Spawn(Essence());
            }

            foreach (TrialMob typhon in run.Mobs("typhon").ToList())
            {
                int spot = TyphonSpot(typhon.HealthPercent);
                if (spot <= run.Get("spot", 0))
                    continue;
                run.Set("spot", spot);
                run.Tell("Typhon dives, and rises across the pool!");
                Relocate(run, typhon, TyphonSpots[spot]);
            }
        }
    }
}
