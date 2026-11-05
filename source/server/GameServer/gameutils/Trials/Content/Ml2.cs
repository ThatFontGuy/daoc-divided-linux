using System;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS.Trials
{
    /// <summary>
    /// Master Level 2 trials: the Temple of the Sobekite Eternal. The temple's gates have no door rows in the
    /// world, so gated trials start from the hall side of the gate, move the party into the chamber, and bring
    /// it back out at the end. Keys and relics from earlier steps are not items: RequiresSteps stands for them.
    /// </summary>
    public static class Ml2
    {
        private const ushort PriestModel = 1034;
        private const ushort RobedModel = 1033;
        private const ushort BruteModel = 1032;
        private const ushort OrbModel = 1391;
        private const ushort TritonModel = 33745;
        private const ushort TritonMageModel = 33746;
        private const ushort TritonGuardModel = 33744;
        private const ushort TritonChiefModel = 33747;
        private const ushort LadyModel = 1197;
        private const ushort StatueModel = 993;

        private static readonly TrialPoint EastAlcove = new(37402, 27940, 15978);
        private static readonly TrialPoint WestAlcove = new(26941, 27602, 15977);
        private static readonly TrialPoint WestAlcoveFar = new(27756, 26573, 15977);

        private static readonly TrialPoint[] DepthsCamp =
        {
            new(29302, 32879, 13609),
            new(29449, 32879, 13650),
            new(28784, 32662, 13663),
            new(28637, 32662, 13739),
            new(28479, 32851, 13708),
            new(28567, 32809, 13651),
        };

        private static readonly TrialPoint NorthGate = new(32205, 18082, 15977);
        private static readonly TrialPoint ChessHall = new(32007, 14200, 17413);
        private static readonly TrialPoint CrackedGate = new(33543, 28584, 15978);
        private static readonly TrialPoint Amphitheater = new(32814, 25854, 15973, 3719);
        private static readonly TrialPoint CellarStair = new(36012, 26053, 15978);
        private static readonly TrialPoint Cellar = new(38146, 21633, 13794, 45);
        private static readonly TrialPoint FearChest = new(37659, 21284, 13673);
        private static readonly TrialPoint SouthGate = new(27714, 28924, 15977);
        private static readonly TrialPoint PlatformTop = new(27645, 32010, 18337);
        private static readonly TrialPoint StoneGate = new(33622, 28750, 15976);
        private static readonly TrialPoint OnurisHall = new(33548, 31018, 16007, 2036);
        private static readonly TrialPoint Runihura = new(335608, 465955, 10750, 2048);

        /// <summary>Chaths' side falls in this order. His king goes last.</summary>
        public static readonly string[] ChessOrder =
        {
            "Chaths's Queen", "Chaths's Rook", "Chaths's Bishop", "Chaths's Knight", "Chaths's Pawn", "Chaths's King",
        };

        public static readonly string[] Poisons = { "Fear", "Terror", "Horror" };

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return DeathFromShadow();
            yield return StalkingTerror();
            yield return TritonHoards();
            yield return RrionnesReflection();
            yield return TestOfStrategy();
            yield return TestOfTactics();
            yield return PickYourPoison();
            yield return StandFast();
            yield return BattleMasters();
            yield return ImmortalImposter();
        }

        /// <summary>The bait works after a few seconds sitting. The assassin comes anyway if nobody takes the hint.</summary>
        public static bool BaitSprung(int secondsSitting, int secondsWaited) => secondsSitting >= 3 || secondsWaited >= 90;

        /// <summary>The Shadow Reaver vanishes at two thirds and one third of his health.</summary>
        public static bool ReaverVanishes(int healthPercent, int vanished) =>
            vanished == 0 && healthPercent <= 66 || vanished == 1 && healthPercent <= 33;

        public static string NextPiece(IEnumerable<string> standing)
        {
            List<string> pieces = standing.ToList();
            return ChessOrder.FirstOrDefault(pieces.Contains);
        }

        /// <summary>Eidolons blast harder the longer they live.</summary>
        public static int EidolonDamage(int stage) => Math.Min(60 + 30 * stage, 240);

        /// <summary>Three on Runihura is safe. Four draws the spikes.</summary>
        public static bool SpikesFall(int crowded) => crowded >= 4;

        private static TrialPhase LeaveChamber(string announce, TrialPoint gate)
        {
            return new TrialPhase
            {
                Announce = announce,
                OnStart = run => Ml12Kit.MoveParty(run, gate),
                SurviveSeconds = 3,
            };
        }

        private static TrialMobSpec Shadow(TrialPoint at)
        {
            return new TrialMobSpec
            {
                Name = "Sobekite shadow",
                Model = RobedModel,
                Size = 50,
                Level = 57,
                Health = 3000,
                DamageFactor = 0.7,
                MeleeDamage = eDamageType.Thrust,
                At = at,
                Tag = "shadow",
            };
        }

        private static TrialDefinition DeathFromShadow()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 1,
                Name = "Death from Shadow",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Sobekite,
                Anchor = EastAlcove,
                StarterName = "Wounded Temple Keeper",
                StarterModel = PriestModel,
                Intro = "They come out of the walls, stranger. They will not show themselves to a crowd, but they cannot pass by one who looks helpless. " +
                    "Sit here in the alcove with your back to the stone, and keep your friends close by. When Ka'a comes for you, make him regret it. Ata will follow him.",
                Victory = "Ata dies in the alcove he crept out of. The keepers can breathe again, for now.",
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Sit down here in the alcove and wait.",
                        OnTick = WatchTheBait,
                        Done = run => run.Get<bool>("sprung"),
                    },
                    new TrialPhase
                    {
                        Announce = "The wall grinds open behind you!",
                        OnStart = KaaStrikes,
                        Done = run => !run.Mobs("kaa").Any() && !run.Mobs("shadow").Any(),
                    },
                    new TrialPhase
                    {
                        Announce = "Something else moves in the tunnel. Ata is here!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Ata",
                                Model = RobedModel,
                                Size = 55,
                                Level = 65,
                                Health = 45000,
                                DamageFactor = 1.1,
                                MeleeDamage = eDamageType.Thrust,
                                At = Ml12Kit.Ring(EastAlcove, 300, 1, 4),
                                Tag = "ata",
                            },
                        },
                        OnTick = AtaPoison,
                    },
                },
            };
        }

        private static void WatchTheBait(TrialRun run)
        {
            int waited = run.Get("waited", 0) + 1;
            run.Set("waited", waited);

            bool baiting = run.Leader.IsSitting && Ml12Kit.Near(run.Leader.X, run.Leader.Y, run.Definition.Anchor, 600);
            int sitting = baiting ? run.Get("sitting", 0) + 1 : 0;
            run.Set("sitting", sitting);

            if (BaitSprung(sitting, waited))
                run.Set("sprung", true);
        }

        private static void KaaStrikes(TrialRun run)
        {
            TrialPoint behind = new(run.Leader.X, run.Leader.Y + 150, run.Leader.Z);
            TrialMob kaa = run.Spawn(new TrialMobSpec
            {
                Name = "Ka'a",
                Model = RobedModel,
                Size = 52,
                Level = 62,
                Health = 8000,
                DamageFactor = 1.0,
                MeleeDamage = eDamageType.Thrust,
                At = behind,
                Tag = "kaa",
            });
            run.Spawn(Shadow(Ml12Kit.Ring(behind, 300, 1, 4)));
            run.Spawn(Shadow(Ml12Kit.Ring(behind, 300, 3, 4)));
            Ml12Kit.Strike(run, kaa, run.Leader, 250, eDamageType.Thrust);
        }

        private static void AtaPoison(TrialRun run)
        {
            TrialMob ata = run.Mobs("ata").FirstOrDefault();
            if (ata == null || !Ml12Kit.Every(run, "venom", 8))
                return;
            GameLiving target = Ml12Kit.RandomHostile(run, ata, 800);
            if (target != null)
                Ml12Kit.Strike(run, ata, target, 130, eDamageType.Body);
        }

        private static TrialDefinition StalkingTerror()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 2,
                Name = "Stalking Terror",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Sobekite,
                Anchor = WestAlcove,
                StarterName = "Frightened Temple Keeper",
                StarterModel = PriestModel,
                Intro = "The imposter's reaver is killing us one by one. He sends his shadows ahead of him and slips back into the walls when he is hurt. " +
                    "Stay with him. When he vanishes he has only gone to the next alcove up the hall.",
                Victory = "The Shadow Reaver lies dead. No more keepers will be found in the alcoves.",
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Shadows peel away from the walls!",
                        Mobs = Ml12Kit.Circle(WestAlcove, 350, 4, Shadow).ToList(),
                    },
                    new TrialPhase
                    {
                        Announce = "The Shadow Reaver steps out of the stone!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Shadow Reaver",
                                Model = RobedModel,
                                Size = 55,
                                Level = 65,
                                Health = 46000,
                                DamageFactor = 1.2,
                                MeleeDamage = eDamageType.Slash,
                                At = WestAlcove,
                                Tag = "reaver",
                            },
                        },
                        OnTick = ReaverHunts,
                    },
                },
            };
        }

        private static void ReaverHunts(TrialRun run)
        {
            TrialMob reaver = run.Mobs("reaver").FirstOrDefault();
            if (reaver == null)
                return;

            int vanished = run.Get("vanished", 0);
            if (!ReaverVanishes(reaver.HealthPercent, vanished))
                return;

            run.Set("vanished", vanished + 1);
            TrialPoint spot = vanished == 0 ? WestAlcoveFar : WestAlcove;
            reaver.MoveTo(reaver.CurrentRegionID, spot.X, spot.Y, spot.Z, spot.Heading);
            run.Tell("The Shadow Reaver melts into the wall! Find the next alcove!");
        }

        private static TrialDefinition TritonHoards()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 3,
                Name = "Triton Hoards",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Sobekite,
                Anchor = DepthsCamp[0],
                StarterName = "Antron Diplomat",
                StarterModel = TritonMageModel,
                Intro = "My people and the Speos fight over what they stole from this temple, and the Speos are winning. Break their camp here in the flooded depths and kill their chieftain. " +
                    "Whatever you find you may keep: finishing this stands for the Cracked, Stone and Cellar keys, and for the four old relics Onuris will ask after.",
                Victory = "The Speos chieftain is dead. You take a ring of old keys and four battered relics from his hoard.",
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The Speos camp boils up out of the dark water!",
                        Mobs =
                        {
                            Speos("Speos warrior", TritonModel, 3000, 0.7, DepthsCamp[1]),
                            Speos("Speos warrior", TritonModel, 3000, 0.7, DepthsCamp[2]),
                            Speos("Speos treasure hunter", TritonGuardModel, 3500, 0.8, DepthsCamp[3]),
                            Speos("Speos arch mage", TritonMageModel, 3000, 0.5, DepthsCamp[4]),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "The Speos chieftain comes down from his hoard with his guard about him!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Speos Chieftain",
                                Model = TritonChiefModel,
                                Size = 65,
                                Level = 62,
                                Health = 42000,
                                DamageFactor = 1.1,
                                MeleeDamage = eDamageType.Thrust,
                                At = DepthsCamp[5],
                                Tag = "chieftain",
                            },
                            Speos("Speos warrior", TritonModel, 3000, 0.7, DepthsCamp[3], false),
                            Speos("Speos arch mage", TritonMageModel, 3000, 0.5, DepthsCamp[4], false),
                        },
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 9, Damage = 130, Radius = 450, SourceTag = "chieftain", DamageType = eDamageType.Cold },
                        },
                    },
                },
            };
        }

        private static TrialMobSpec Speos(string name, ushort model, int health, double damage, TrialPoint at, bool required = true)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = model,
                Size = 54,
                Level = 57,
                Health = health,
                DamageFactor = damage,
                MeleeDamage = eDamageType.Thrust,
                At = at,
                Required = required,
            };
        }

        private static TrialDefinition RrionnesReflection()
        {
            TrialPoint nook = new(27402, 20117, 16097, 4061);
            return new TrialDefinition
            {
                ML = 2,
                Step = 4,
                Name = "Rrionne's Reflection",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Sobekite,
                Anchor = nook,
                StarterName = "Keeper of the Water",
                StarterModel = PriestModel,
                Intro = "Rrionne cannot be hurt while her reflection walks. Break the reflection first, and take care, for it throws back what it is given. " +
                    "Then she can be killed. Keep your healers away from her when she does. The Key to the North Gate is on her, though finishing this is all the key you will need.",
                Victory = "Rrionne falls, and the North Gate key is yours.",
                Replaces = new[] { "Rrionne", "Rrionne's Reflection" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Rrionne turns, and something steps out of the water behind her.",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Rrionne's Reflection",
                                Model = LadyModel,
                                Size = 50,
                                Level = 66,
                                Health = 15000,
                                DamageFactor = 0.9,
                                MeleeDamage = eDamageType.Cold,
                                At = Ml12Kit.Ring(nook, 250, 0, 2),
                                Reflect = 0.1,
                                Tag = "reflection",
                            },
                            new TrialMobSpec
                            {
                                Name = "Rrionne",
                                Model = LadyModel,
                                Size = 50,
                                Level = 65,
                                Health = 44000,
                                DamageFactor = 1.1,
                                MeleeDamage = eDamageType.Slash,
                                At = Ml12Kit.Ring(nook, 250, 1, 2),
                                AggroRange = 0,
                                Immune = true,
                                Tag = "rrionne",
                            },
                        },
                        Done = run => !run.Mobs("reflection").Any(),
                    },
                    new TrialPhase
                    {
                        Announce = "The reflection shatters, and Rrionne screams!",
                        OnStart = run =>
                        {
                            run.SetImmune("rrionne", false);
                            Ml12Kit.Wake(run, "rrionne", 1500);
                        },
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 7, Damage = 170, Radius = 450, SourceTag = "rrionne", DamageType = eDamageType.Cold },
                        },
                        Done = run => !run.Mobs("rrionne").Any(),
                    },
                },
            };
        }

        private static TrialDefinition TestOfStrategy()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 5,
                Name = "Chath's Test of Strategy",
                Scope = TrialScope.Group,
                Zone = TrialZone.Sobekite,
                Anchor = NorthGate,
                StarterName = "Chaths",
                StarterModel = PriestModel,
                Intro = "You carry the North Gate key, so you may come in and play. My pieces stand against yours in the hall above. Set yours by touching each one, the king, the queen, the rook, " +
                    "the bishop, the knight and a pawn. Then stand back and let them fight. Do not lift a hand: strategy is not fought, it is arranged.",
                Victory = "Chaths bows over his fallen king. Your strategy has beaten his.",
                RequiresSteps = new[] { 4 },
                Replaces = new[]
                {
                    "Chaths", "King", "Queen", "Rook", "Bishop", "Knight", "Pawn",
                    "Chaths's King", "Chaths's Queen", "Chaths's Rook", "Chaths's Bishop", "Chaths's Knight", "Chaths's Pawn",
                },
                TimeLimitSeconds = 900,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The gate opens onto the board. Touch each of your pieces to set it.",
                        Mobs =
                        {
                            Piece("King", 993, 62, new TrialPoint(32124, 13693, 17413), "You set the King to COMMAND."),
                            Piece("Queen", 984, 62, new TrialPoint(31890, 13690, 17413), "You set the Queen to DRAIN."),
                            Piece("Rook", 993, 75, new TrialPoint(32354, 13696, 17413), "You set the Rook to DEFEND."),
                            Piece("Bishop", 993, 50, new TrialPoint(31666, 13687, 17413), "You set the Bishop to HEAL."),
                            Piece("Knight", 993, 55, new TrialPoint(32127, 13508, 17413), "You set the Knight to WEAKEN."),
                            Piece("Pawn", 993, 37, new TrialPoint(31887, 13504, 17413), "You set the Pawns to STUN."),
                        },
                        OnStart = run => Ml12Kit.MoveParty(run, ChessHall),
                    },
                    new TrialPhase
                    {
                        Announce = "Your pieces are set. Chaths moves first!",
                        Mobs = BuildEnemyPieces(),
                        OnTick = PlayTheBoard,
                        Done = run => !run.Mobs("enemy").Any(),
                    },
                    LeaveChamber("Chaths sweeps the board clear and shows you out.", NorthGate),
                },
            };
        }

        private static TrialMobSpec Piece(string name, ushort model, byte size, TrialPoint at, string text)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = model,
                Size = size,
                Level = 55,
                At = at,
                Objective = true,
                ObjectiveText = text,
            };
        }

        private static List<TrialMobSpec> BuildEnemyPieces()
        {
            (string Name, ushort Model, byte Size, TrialPoint At)[] pieces =
            {
                ("Chaths's King", 994, 62, new TrialPoint(32121, 11763, 17413)),
                ("Chaths's Queen", 985, 62, new TrialPoint(31885, 11763, 17413)),
                ("Chaths's Rook", 994, 75, new TrialPoint(32350, 11763, 17413)),
                ("Chaths's Bishop", 994, 50, new TrialPoint(31659, 11764, 17413)),
                ("Chaths's Knight", 994, 55, new TrialPoint(31888, 11955, 17413)),
                ("Chaths's Pawn", 994, 37, new TrialPoint(31662, 11955, 17413)),
                ("Chaths's Pawn", 994, 37, new TrialPoint(32125, 11954, 17413)),
                ("Chaths's Pawn", 994, 37, new TrialPoint(32355, 11954, 17413)),
            };
            return pieces.Select(piece => new TrialMobSpec
            {
                Name = piece.Name,
                Model = piece.Model,
                Size = piece.Size,
                Level = 55,
                Health = 3000,
                DamageFactor = 0.5,
                At = piece.At,
                AggroRange = 0,
                Tag = "enemy",
            }).ToList();
        }

        private static void PlayTheBoard(TrialRun run)
        {
            if (!Ml12Kit.Every(run, "move", 4))
                return;
            List<TrialMob> enemies = run.Mobs("enemy").ToList();
            string next = NextPiece(enemies.Select(enemy => enemy.Name));
            TrialMob target = enemies.FirstOrDefault(enemy => enemy.Name == next);
            if (target == null)
                return;
            run.Tell($"Your pieces close on {target.Name}.");
            Ml12Kit.Wound(run, target, 0.34);
        }

        private static TrialDefinition TestOfTactics()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 6,
                Name = "Kanahkt Test of Tactics",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Sobekite,
                Anchor = CrackedGate,
                StarterName = "Kanakht",
                StarterModel = RobedModel,
                Intro = "The Cracked Key opens my amphitheater, and you hold that right by your deeds in the depths. Four statues stand around my floor. They wake one at a time, and each brings eidolons that grow while they live. " +
                    "The statue cannot be harmed until its eidolons are gone, so learn that first. I will let you breathe between each one.",
                Victory = "The fourth statue falls, and Kanakht inclines his head. Your tactics will do.",
                RequiresSteps = new[] { 3 },
                Replaces = new[] { "Kanakht", "Marble Statue", "Slate Statue", "Stone Statue" },
                TimeLimitSeconds = 2100,
                Phases =
                {
                    Statue("The first Stone Statue grinds awake!", "Stone Statue", 997, new TrialPoint(31749, 25358, 16234), 10000),
                    Rest(),
                    Statue("The second Stone Statue grinds awake!", "Stone Statue", 997, new TrialPoint(33799, 25356, 16234), 12000),
                    Rest(),
                    Statue("The Slate Statue turns its head!", "Slate Statue", 994, new TrialPoint(33304, 24219, 16490), 15000),
                    Rest(),
                    Statue("The Marble Statue steps down!", "Marble Statue", StatueModel, new TrialPoint(32236, 24291, 16482), 18000),
                    LeaveChamber("Kanakht opens the cracked door for you.", CrackedGate),
                },
            };
        }

        private static TrialPhase Rest()
        {
            return new TrialPhase
            {
                Announce = "Kanakht says: Catch your breath. The next one wakes soon.",
                SurviveSeconds = 20,
            };
        }

        private static TrialPhase Statue(string announce, string name, ushort model, TrialPoint at, int health)
        {
            List<TrialMobSpec> mobs = Ml12Kit.Circle(Amphitheater, 500, 4, spot => new TrialMobSpec
            {
                Name = "sobekite eidolon",
                Model = OrbModel,
                Size = 30,
                Level = 55,
                Health = 2000,
                DamageFactor = 0.3,
                MeleeDamage = eDamageType.Energy,
                At = spot,
                Tag = "eidolon",
            }).ToList();
            mobs.Add(new TrialMobSpec
            {
                Name = name,
                Model = model,
                Size = 100,
                Level = 65,
                Health = health,
                DamageFactor = 1.0,
                At = at,
                Immune = true,
                Tag = "statue",
            });

            return new TrialPhase
            {
                Announce = announce,
                Mobs = mobs,
                OnStart = run =>
                {
                    if (run.Get<bool>("inside"))
                    {
                        run.Set("stage", 0);
                        return;
                    }
                    run.Set("inside", true);
                    Ml12Kit.MoveParty(run, Amphitheater);
                },
                OnTick = GrowEidolons,
            };
        }

        private static void GrowEidolons(TrialRun run)
        {
            List<TrialMob> eidolons = run.Mobs("eidolon").ToList();
            run.SetImmune("statue", eidolons.Count > 0);

            if (eidolons.Count == 0 || !Ml12Kit.Every(run, "grow", 10))
                return;

            int stage = run.Get("stage", 0) + 1;
            run.Set("stage", stage);
            foreach (TrialMob eidolon in eidolons)
            {
                eidolon.Level = (byte)Math.Min(eidolon.Level + 3, 65);
                Ml12Kit.Burst(run, eidolon, eidolon, 400, EidolonDamage(stage), eDamageType.Energy);
            }
        }

        private static TrialDefinition PickYourPoison()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 7,
                Name = "Pick Your Poison",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Sobekite,
                Anchor = CellarStair,
                StarterName = "Djedkare",
                StarterModel = PriestModel,
                Intro = "You hold the Cellar Key by right of your deeds in the depths. Below, three vials wait. Touch Fear and you need only reach a chest past what walks there. " +
                    "Touch Terror and she will come for you. Touch Horror if you bring an army, for it is the same road, and worse. Only one, mind.",
                Victory = "Djedkare nods. You have chosen your poison and swallowed it.",
                RequiresSteps = new[] { 3 },
                Replaces = new[] { "Djedkare" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The cellar is cold. Three vials stand before you. Touch one.",
                        Mobs = BuildVials(),
                        OnStart = run => Ml12Kit.MoveParty(run, Cellar),
                        Done = run => run.Get<string>("poison") != null,
                    },
                    new TrialPhase
                    {
                        Announce = "The vial is empty, and the cellar answers.",
                        OnStart = SwallowPoison,
                        OnTick = PoisonWorks,
                        Done = run => !run.Mobs("test").Any(),
                    },
                    LeaveChamber("Djedkare leads you back up the stairs.", CellarStair),
                },
            };
        }

        private static List<TrialMobSpec> BuildVials()
        {
            List<TrialMobSpec> vials = new();
            for (int i = 0; i < Poisons.Length; i++)
            {
                string poison = Poisons[i];
                vials.Add(new TrialMobSpec
                {
                    Name = $"vial of {poison}",
                    Model = OrbModel,
                    Size = 25,
                    Level = 55,
                    At = Ml12Kit.Ring(Cellar, 200, i, Poisons.Length),
                    Objective = true,
                    ObjectiveText = $"You choose {poison}.",
                    Required = false,
                    Tag = "vial",
                    OnDeath = (run, _) =>
                    {
                        if (run.Get<string>("poison") == null)
                            run.Set("poison", poison);
                    },
                });
            }
            return vials;
        }

        private static void SwallowPoison(TrialRun run)
        {
            Ml12Kit.Clear(run, "vial");
            switch (run.Get<string>("poison"))
            {
                case "Fear":
                    run.Spawn(new TrialMobSpec
                    {
                        Name = "chest of Fear",
                        Model = OrbModel,
                        Size = 40,
                        Level = 55,
                        At = FearChest,
                        Objective = true,
                        ObjectiveText = "You lay your hand on the chest, and the fear lifts.",
                        Tag = "test",
                    });
                    foreach (TrialMobSpec spec in Ml12Kit.Circle(FearChest, 400, 4, at => new TrialMobSpec
                    {
                        Name = "fear shade",
                        Model = BruteModel,
                        Size = 50,
                        Level = 58,
                        Health = 4000,
                        DamageFactor = 0.8,
                        At = at,
                        Required = false,
                    }))
                    {
                        run.Spawn(spec);
                    }
                    break;
                case "Terror":
                    run.Spawn(Poison("Terror", 60, 62, 40000, 1.0));
                    break;
                default:
                    run.Spawn(Poison("Horror", 75, 65, 60000, 1.25));
                    break;
            }
        }

        private static TrialMobSpec Poison(string name, byte size, byte level, int health, double damage)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = LadyModel,
                Size = size,
                Level = level,
                Health = health,
                DamageFactor = damage,
                MeleeDamage = eDamageType.Slash,
                At = Ml12Kit.Ring(Cellar, 500, 0, 4),
                Tag = "test",
            };
        }

        private static void PoisonWorks(TrialRun run)
        {
            TrialMob foe = run.Mobs("test").FirstOrDefault(mob => !mob.Spec.Objective);
            if (foe == null || !Ml12Kit.Every(run, "dread", 8))
                return;
            Ml12Kit.Burst(run, foe, foe, 500, foe.Name == "Horror" ? 170 : 120, eDamageType.Spirit);
        }

        private static TrialDefinition StandFast()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 8,
                Name = "Stand Fast",
                Scope = TrialScope.Solo,
                Zone = TrialZone.Sobekite,
                Anchor = SouthGate,
                StarterName = "Amenemhat",
                StarterModel = PriestModel,
                Intro = "No key opens this way, and no friend may walk it with you. I will meet you on the platform at the head of the great stair, one blade against one. " +
                    "If you beat me, do not expect a dry way down.",
                Victory = "You have stood fast, alone.",
                TimeLimitSeconds = 900,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The South Hall falls away beneath you. Amenemhat waits at the head of the stair.",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Amenemhat",
                                Model = PriestModel,
                                Size = 50,
                                Level = 58,
                                Health = 3000,
                                DamageFactor = 0.5,
                                MeleeDamage = eDamageType.Slash,
                                At = new TrialPoint(27403, 32010, 18337),
                                Tag = "amenemhat",
                            },
                        },
                        OnStart = run => Ml12Kit.MoveParty(run, PlatformTop),
                        OnTick = run =>
                        {
                            TrialMob amenemhat = run.Mobs("amenemhat").FirstOrDefault();
                            if (amenemhat != null && Ml12Kit.Every(run, "smite", 8))
                                Ml12Kit.Strike(run, amenemhat, run.Leader, 70, eDamageType.Spirit);
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "The platform drops out from under you!",
                        OnStart = run =>
                        {
                            run.Leader.TakeDamage(run.Starter, eDamageType.Crush, run.Leader.MaxHealth / 8, 0);
                            Ml12Kit.MoveParty(run, SouthGate);
                        },
                        SurviveSeconds = 2,
                    },
                },
            };
        }

        private static TrialDefinition BattleMasters()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 9,
                Name = "Battle Masters",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Sobekite,
                Anchor = StoneGate,
                StarterName = "Onuris",
                StarterModel = PriestModel,
                Intro = "So you have the Stone Key, and the staff of Kaletor, the shield of Buliss, the sword of Dimitri and the staff of Thao. No, keep your hands still: I can smell them on you from the depths. " +
                    "Those four once beat this temple. Give me leave and I will call them back to test you. Kaletor's fire is the worst of it, so see to him first.",
                Victory = "The four Battle Masters lie still, and Onuris takes back the relics. He has things to tell you about an imposter.",
                RequiresSteps = new[] { 3 },
                Replaces = new[] { "Onuris" },
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Onuris raises the relics, and four shapes form in the hall!",
                        Mobs =
                        {
                            Master("Buliss", BruteModel, 66, 30000, 1.2, 0, eDamageType.Crush),
                            Master("Dimitri", BruteModel, 60, 12000, 0.9, 1, eDamageType.Slash),
                            Master("Kaletor", RobedModel, 63, 14000, 0.6, 2, eDamageType.Heat),
                            Master("Thao", RobedModel, 63, 14000, 0.6, 3, eDamageType.Cold),
                        },
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 7, Damage = 180, Radius = 500, SourceTag = "Kaletor", DamageType = eDamageType.Heat },
                        },
                        OnStart = run => Ml12Kit.MoveParty(run, OnurisHall),
                        OnTick = ThaoBolts,
                    },
                    LeaveChamber("Onuris gathers up the relics and walks you back to the Stone Gate.", StoneGate),
                },
            };
        }

        private static TrialMobSpec Master(string name, ushort model, byte level, int health, double damage, int seat, eDamageType type)
        {
            return new TrialMobSpec
            {
                Name = name,
                Model = model,
                Size = 55,
                Level = level,
                Health = health,
                DamageFactor = damage,
                MeleeDamage = type,
                At = Ml12Kit.Ring(OnurisHall, 500, seat, 4),
                Tag = name,
            };
        }

        private static void ThaoBolts(TrialRun run)
        {
            TrialMob thao = run.Mobs("Thao").FirstOrDefault();
            if (thao == null || !Ml12Kit.Every(run, "bolt", 6))
                return;
            GameLiving target = Ml12Kit.RandomHostile(run, thao, 1500);
            if (target != null)
                Ml12Kit.Strike(run, thao, target, 140, eDamageType.Cold);
        }

        private static TrialDefinition ImmortalImposter()
        {
            return new TrialDefinition
            {
                ML = 2,
                Step = 10,
                Name = "Immortal Imposter",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Oceanus,
                Anchor = new TrialPoint(334744, 465762, 10734, 2305),
                StarterName = "Shade of the Temple",
                StarterModel = PriestModel,
                Intro = "Above the Sobekite Eternal the imposter Runihura sits with the stolen Ankh of Life. His spitting cobras guard the door. Kill them and go in. " +
                    "Then spread out and stay spread out: no more than three of you close to him, or the spikes will find you. He calls vipers, and his breath is poison. " +
                    "The Ankh will try once to save him. Do not stop when it does.",
                Victory = "The Ankh falls from Runihura's hand. The imposter is dead, and the temple's keepers are free.",
                Replaces = new[] { "Runihura", "spitting cobra" },
                TimeLimitSeconds = 2400,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The cobras rear up at the temple door!",
                        Mobs =
                        {
                            Cobra(new TrialPoint(334666, 466759, 10762)),
                            Cobra(new TrialPoint(334664, 466029, 10730)),
                            Cobra(new TrialPoint(334700, 465474, 10764)),
                            Cobra(new TrialPoint(335263, 464895, 10766)),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "Runihura rises from his throne with the Ankh in his hand!",
                        Mobs =
                        {
                            new TrialMobSpec
                            {
                                Name = "Runihura",
                                Model = 1038,
                                Size = 45,
                                Level = 66,
                                Health = 60000,
                                DamageFactor = 1.2,
                                MeleeDamage = eDamageType.Crush,
                                At = Runihura,
                                Tag = "runihura",
                            },
                        },
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 8, Damage = 120, Radius = 450, SourceTag = "runihura", DamageType = eDamageType.Body },
                        },
                        OnTick = ImposterTricks,
                        Done = run => !run.Mobs("runihura").Any(),
                    },
                },
            };
        }

        private static TrialMobSpec Cobra(TrialPoint at)
        {
            return new TrialMobSpec
            {
                Name = "spitting cobra",
                Model = 1234,
                Size = 50,
                Level = 58,
                Health = 4500,
                DamageFactor = 0.8,
                MeleeDamage = eDamageType.Thrust,
                At = at,
            };
        }

        private static void ImposterTricks(TrialRun run)
        {
            TrialMob runihura = run.Mobs("runihura").FirstOrDefault();
            if (runihura == null)
                return;

            if (runihura.HealthPercent <= 15 && !run.Get<bool>("ankh"))
            {
                run.Set("ankh", true);
                run.Tell("The Ankh blazes in Runihura's hand and his wounds begin to close!");
                Ml12Kit.Heal(runihura, 0.2);
            }

            if (Ml12Kit.Every(run, "spikes", 6) && SpikesFall(run.Hostiles(runihura, 250).Count()))
            {
                run.Tell("Too many stand close to Runihura! Spikes burst from the floor!");
                Ml12Kit.Burst(run, runihura, runihura, 300, 260, eDamageType.Thrust);
            }

            if (Ml12Kit.Every(run, "vipers", 30) && run.Mobs("viper").Count() < 5)
            {
                run.Tell("Runihura calls his vipers!");
                run.Spawn(new TrialMobSpec
                {
                    Name = "bane viper",
                    Model = 30,
                    Size = 40,
                    Level = 55,
                    Health = 2000,
                    DamageFactor = 0.4,
                    MeleeDamage = eDamageType.Thrust,
                    At = Ml12Kit.Ring(Runihura, 400, Util.Random(0, 7), 8),
                    Required = false,
                    Tag = "viper",
                });
            }
        }
    }
}
