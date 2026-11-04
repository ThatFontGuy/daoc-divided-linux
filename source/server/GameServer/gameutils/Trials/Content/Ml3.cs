using System;
using System.Collections.Generic;
using System.Linq;
using static DOL.GS.Trials.Ml34Kit;

namespace DOL.GS.Trials
{
    /// <summary>Master Level 3: the gorgons and sea beasts of the Temple of Twilight, ending with Medusa.</summary>
    public static class Ml3
    {
        private const ushort Gorgon = 1182;
        private const ushort GorgonQueen = 1183;
        private const ushort MedusaModel = 1188;
        private const ushort Cobra = 1234;
        private const ushort Hoplite = 997;
        private const ushort StonedBriton = 1315;
        private const ushort StonedSaracen = 1319;
        private const ushort StonedNorse = 1327;
        private const ushort Chest = 2362;
        private const ushort Barracuda = 33735;
        private const ushort RayModel = 33743;
        private const ushort EelModel = 33742;
        private const ushort WhaleShark = 33736;
        private const ushort Octopus = 33738;
        private const ushort Triton = 33745;
        private const ushort MoughartModel = 33744;

        private const int BarrierCharges = 6;
        private const int RayKillsNeeded = 3;

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return MoiraisDestruction();
            yield return KepasDownfall();
            yield return CastasAnnihilation();
            yield return LaodamediasFuriousEnd();
            yield return AntioosDeceptiveDeath();
            yield return GlowingBarracudasFading();
            yield return ShraoghsFearRemoved();
            yield return StingRaysPowerAbsorbed();
            yield return SinoviasPowerRelinquished();
            yield return ConqueringTwilight();
        }

        private static TrialDefinition MoiraisDestruction()
        {
            TrialPoint moirai = new(39695, 22801, 16178);
            TrialPoint[] minions = { new(39498, 22724, 16186), new(39520, 22916, 16186), new(39808, 22984, 16186) };
            TrialMobSpec Minion(TrialPoint at) => Mob("Minion of Moirai", Gorgon, 62, 57, 5000, 0.7, at, "minion", required: false, melee: eDamageType.Slash);

            void Burn(TrialRun run)
            {
                TrialMob boss = First(run, "moirai");
                if (boss == null)
                    return;
                if (Every(run, "fire", 12))
                {
                    Hurt(run, boss, Ring(run, Where(boss), 250, 1100), 180, eDamageType.Heat);
                    run.Tell("Fire races around the rim of Moirai's platform. Only its centre is safe.");
                }
                if (Every(run, "snakes", 20) && run.Mobs("snake").Count() < Scaled(4, run.HealthScale))
                    run.Spawn(At(Mob("cobra", Cobra, 58, 40, 1500, 0.6, tag: "snake", required: false, melee: eDamageType.Thrust), On(moirai, 500, Random.Shared.Next(6), 6)));
            }

            void Drain(TrialRun run)
            {
                foreach (TrialMob minion in run.Mobs("minion").Where(mob => HealthPercent(mob) < 50).ToList())
                {
                    minion.Health = minion.MaxHealth;
                    int left = run.Get<int>("barrier") - 1;
                    run.Set("barrier", left);
                    if (left > 0)
                        run.Tell($"{minion.Name} drinks from the barrier to mend herself. It flickers and shrinks.");
                }
                if (run.Mobs("minion").Count() < minions.Length && Every(run, "resummon", 30))
                {
                    run.Tell("Moirai calls another servant. Slain minions take nothing from her shield!");
                    run.Spawn(Minion(minions[Random.Shared.Next(minions.Length)]));
                }
            }

            return new TrialDefinition
            {
                ML = 3,
                Step = 1,
                Name = "Moirai's Destruction",
                Scope = TrialScope.Group,
                Zone = TrialZone.Twilight,
                Anchor = new TrialPoint(39873, 24169, 16186),
                StarterName = "Gorgon Turncoat",
                StarterModel = Gorgon,
                Intro = "I served Moirai until her shield began to feed on her own servants. Nothing you own will scratch her while it holds. " +
                    "Her three minions sip from it when they are hurt, so wound them, again and again, but do not kill them. " +
                    "When the shield is gone, get to the very centre of her platform. Her fire does not reach it.",
                Victory = "Moirai falls, and the runic power behind her shield passes to you.",
                Replaces = new[] { "Moirai", "Minion of Moirai", "Moirai Invisible Energy" },
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Moirai's barrier hums. Wound her minions so they drain it. Do not kill them!",
                        Mobs =
                        {
                            Mob("Moirai", GorgonQueen, 66, 75, 30000, 1.3, moirai, "moirai", immune: true),
                            Minion(minions[0]),
                            Minion(minions[1]),
                            Minion(minions[2]),
                        },
                        OnStart = run => run.Set("barrier", Scaled(BarrierCharges, run.HealthScale, 3)),
                        OnTick = run =>
                        {
                            Drain(run);
                            Burn(run);
                        },
                        Done = run => run.Get<int>("barrier") <= 0 || First(run, "moirai") == null,
                    },
                    new TrialPhase
                    {
                        Announce = "The barrier collapses! Moirai can be hurt!",
                        OnStart = run => run.SetImmune("moirai", false),
                        OnTick = Burn,
                        Done = Cleared("moirai"),
                    },
                },
            };
        }

        private static TrialDefinition KepasDownfall()
        {
            TrialPoint kepa = new(61186, 18776, 16938);
            TrialPoint moughart = new(61186, 19376, 16938);

            void AllFall(TrialRun run, TrialMob mob)
            {
                foreach (TrialMob other in run.Mobs("moughart").ToList())
                    other.Delete();
            }

            TrialMobSpec Bodyguard() => Mob("Moughart's bodyguard", Triton, 64, 52, 5000, 0.9, tag: "moughart");

            return new TrialDefinition
            {
                ML = 3,
                Step = 2,
                Name = "Kepa's Downfall",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Twilight,
                Anchor = kepa,
                StarterName = "Kepa",
                StarterModel = Gorgon,
                Intro = "My runic power is yours if you cure what ails me. The triton Moughart holds the only remedy. " +
                    "I will drag him here from Mesothalassa with what strength I have left, and his guards with him. " +
                    "They are bound together: strike one down and the rest go with it. Do this for me, and I shall keep my word, in a manner of speaking.",
                Victory = "Kepa's bargain is paid in full, though not as she intended. Her runic power is yours.",
                Replaces = new[] { "Kepa" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Kepa hisses a summons, and Moughart is torn out of the sea with his bodyguards!",
                        OnStart = run =>
                        {
                            TrialMobSpec chief = Mob("Moughart", MoughartModel, 66, 50, 8000, 1.0, moughart, "moughart");
                            chief.OnDeath = AllFall;
                            run.Spawn(chief);
                            TrialMobSpec guard = Bodyguard();
                            guard.OnDeath = AllFall;
                            Wave(run, guard, 4, moughart, 300);
                        },
                        Done = Cleared("moughart"),
                    },
                    new TrialPhase
                    {
                        Announce = "Cured and strong again, Kepa laughs and draws on you. Her promise only ever covered her power, not your life!",
                        Mobs = { Mob("Kepa", Gorgon, 66, 62, 60000, 1.3, kepa, "kepa", melee: eDamageType.Slash) },
                        OnStart = HideStarter,
                        Done = Cleared("kepa"),
                    },
                },
            };
        }

        private static TrialDefinition CastasAnnihilation()
        {
            TrialPoint casta = new(55046, 19623, 15392);

            Action<TrialRun> Bolts(int damage, bool turnsArrows = false) => run =>
            {
                TrialMob boss = First(run, "casta");
                if (boss == null)
                    return;
                foreach (TrialHit hit in TakeHits(run, "blows").Where(hit => turnsArrows && hit.AttackType == AttackData.eAttackType.Ranged))
                    boss.Health = Math.Min(boss.MaxHealth, boss.Health + hit.Damage);
                if (Every(run, "bolt", 8))
                    Hurt(run, boss, Ring(run, Where(boss), 450, 2500), damage, eDamageType.Energy);
            };

            Func<TrialRun, bool> Below(int percent) => run => First(run, "casta") is not { } boss || HealthPercent(boss) <= percent;

            return new TrialDefinition
            {
                ML = 3,
                Step = 3,
                Name = "Casta's Annihilation",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Twilight,
                Anchor = casta,
                StarterName = "Petrified Delver",
                StarterModel = StonedBriton,
                Intro = "The stone figure still clutches a rubbing of Casta's jewellery. Her necklace turns arrows and bolts for the first minute of a fight. " +
                    "Each piece she wears will break under punishment, and her reach weakens with it. Until then she strikes down anyone who stands off from her, " +
                    "so the last words scratched here say to stay in her face.",
                Victory = "The last of Casta's artifacts crumbles, and Casta with it. Her runic power is yours.",
                Replaces = new[] { "Casta" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Casta's necklace blazes. Arrows slide off her!",
                        Mobs = { Mob("Casta", GorgonQueen, 66, 82, 70000, 1.4, casta, "casta", melee: eDamageType.Slash) },
                        OnStart = run => WatchHits(run, First(run, "casta"), "blows"),
                        OnTick = Bolts(240, turnsArrows: true),
                        SurviveSeconds = 60,
                    },
                    new TrialPhase
                    {
                        Announce = "Casta's necklace shatters! Arrows bite now.",
                        OnTick = Bolts(180),
                        Done = Below(66),
                    },
                    new TrialPhase
                    {
                        Announce = "A bracelet snaps from Casta's arm, and her bolts falter.",
                        OnTick = Bolts(120),
                        Done = Below(33),
                    },
                    new TrialPhase
                    {
                        Announce = "Casta's last ring cracks. She has only her claws left!",
                        Done = Cleared("casta"),
                    },
                },
            };
        }

        private static TrialDefinition LaodamediasFuriousEnd()
        {
            TrialPoint lair = new(64261, 19713, 16946);
            const double RageMultiplier = 1.8;
            const int RageSeconds = 12;

            void Temper(TrialRun run)
            {
                TrialMob boss = First(run, "laodameia");
                if (boss == null)
                    return;
                RageMeter meter = run.Get<RageMeter>("meter");
                meter.Second();

                int raging = run.Get<int>("raging");
                if (raging > 0)
                {
                    run.Set("raging", raging - 1);
                    if (raging == 1)
                    {
                        boss.DamageFactor = run.Get<double>("calm");
                        run.Tell("Laodameia's fury burns out.");
                    }
                }

                bool enraged = false;
                foreach (TrialHit hit in TakeHits(run, "blows").Where(hit => hit.Damage > 0 && hit.AttackType != AttackData.eAttackType.Spell))
                    enraged |= meter.Hit(hit.DamageType);
                if (enraged && raging == 0)
                {
                    run.Set("raging", RageSeconds);
                    boss.DamageFactor = run.Get<double>("calm") * RageMultiplier;
                    run.Tell("One weapon too many! Laodameia ENRAGES. Back away from her!");
                }
            }

            TrialMobSpec Deidamia() => Mob("Deidamia", Gorgon, 65, 62, 9000, 1.0, On(lair, 400, 0, 3), "deidamia", melee: eDamageType.Slash);
            TrialMobSpec Prokne() => Mob("Prokne", Gorgon, 65, 62, 9000, 0.8, On(lair, 400, 1, 3), "prokne", melee: eDamageType.Thrust);
            TrialMobSpec Ioclaste() => Mob("Ioclaste", Gorgon, 66, 66, 12000, 1.2, On(lair, 400, 2, 3), "ioclaste", melee: eDamageType.Slash);

            return new TrialDefinition
            {
                ML = 3,
                Step = 4,
                Name = "Laodamedia's Furious End",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Twilight,
                Anchor = lair,
                StarterName = "Petrified Swordsman",
                StarterModel = StonedNorse,
                Intro = "A warning is cut into the stone at this one's feet: Laodameia tires of any one weapon. Vary your slashing, crushing and thrusting. " +
                    "Hit her too often the same way and she flies into a rage. While she rages, get clear of her. " +
                    "Her three attendants rise when she falls. Deidamia breeds snakes and should die first. Then Prokne, then Ioclaste.",
                Victory = "The lair falls silent. Laodameia and her attendants are gone.",
                Replaces = new[] { "Laodameia" },
                TimeLimitSeconds = 2100,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Laodameia turns on you. Mix your weapons!",
                        Mobs = { Mob("Laodameia", GorgonQueen, 67, 75, 90000, 1.6, lair, "laodameia", melee: eDamageType.Slash) },
                        OnStart = run =>
                        {
                            run.Set("meter", new RageMeter(8, 30));
                            run.Set("calm", First(run, "laodameia").DamageFactor);
                            WatchHits(run, First(run, "laodameia"), "blows");
                        },
                        OnTick = Temper,
                        Done = Cleared("laodameia"),
                    },
                    new TrialPhase
                    {
                        Announce = "Three gorgons rise at the doorway. Deidamia first, or her snakes will swamp you!",
                        Mobs = { Deidamia(), Prokne(), Ioclaste() },
                        Pulses =
                        {
                            new TrialPulse { IntervalSeconds = 15, Damage = 150, Radius = 700, SourceTag = "prokne", DamageType = eDamageType.Energy, Message = "Prokne's stare sweeps the room." },
                        },
                        OnTick = run =>
                        {
                            if (First(run, "deidamia") is { } deidamia && Every(run, "snakes", 12) && run.Mobs("snake").Count() < Scaled(5, run.HealthScale))
                                run.Spawn(At(Mob("lethal cobra", Cobra, 62, 45, 2000, 0.7, tag: "snake", required: false, melee: eDamageType.Thrust), On(Where(deidamia), 200, Random.Shared.Next(6), 6)));
                        },
                        Done = Cleared("deidamia", "prokne", "ioclaste"),
                    },
                },
            };
        }

        private static TrialDefinition AntioosDeceptiveDeath()
        {
            TrialPoint antioos = new(45823, 17245, 16170);

            return new TrialDefinition
            {
                ML = 3,
                Step = 5,
                Name = "Antioos' Deceptive Death",
                Scope = TrialScope.Group,
                Zone = TrialZone.Twilight,
                Anchor = antioos,
                StarterName = "Antioos",
                StarterModel = Gorgon,
                Intro = "Runic power for a small errand. Bring me a pregnant cobra's egg, a gorgon's sword and a triton shaman's necklace. " +
                    "Spare yourself the journey: I have had their owners driven to my door. Kill them, lay the three things before me, and we shall settle our bargain.",
                Victory = "Antioos dies still trying to haggle. Her runic power is yours.",
                Replaces = new[] { "Antioos" },
                TimeLimitSeconds = 1800,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "A cobra, a gorgon and a shaman are driven in. Take what Antioos asked for.",
                        Mobs =
                        {
                            Mob("pregnant cobra", 34002, 63, 47, 5000, 0.9, On(antioos, 400, 0, 3), melee: eDamageType.Thrust),
                            Mob("gorgon guardian", Gorgon, 63, 62, 6000, 1.0, On(antioos, 400, 1, 3), melee: eDamageType.Slash),
                            Mob("triton shaman", Triton, 63, 50, 5000, 0.8, On(antioos, 400, 2, 3)),
                        },
                    },
                    new TrialPhase
                    {
                        Announce = "You have the egg, the sword and the necklace. Lay them in the chest before Antioos.",
                        Mobs = { Clickable("Antioos' Offering Chest", Chest, 30, On(antioos, 150, 1, 4), "You set down the egg, the sword and the necklace. Antioos smiles.") },
                    },
                    new TrialPhase
                    {
                        Announce = "Antioos: I said I would take these from you. I said nothing of letting you leave. Run if you like. It will not help for long.",
                        SurviveSeconds = 15,
                    },
                    new TrialPhase
                    {
                        Announce = "Antioos looses her giant cobra. She cannot be touched while it lives!",
                        Mobs =
                        {
                            Mob("Antioos", Gorgon, 67, 62, 38000, 1.7, antioos, "antioos", immune: true, melee: eDamageType.Slash),
                            Mob("giant cobra", Cobra, 66, 90, 12000, 1.2, On(antioos, 300, 0, 4), "giant cobra", melee: eDamageType.Thrust),
                        },
                        OnStart = HideStarter,
                        Done = Cleared("giant cobra"),
                    },
                    new TrialPhase
                    {
                        Announce = "The cobra is dead! Now Antioos!",
                        OnStart = run => run.SetImmune("antioos", false),
                        Done = Cleared("antioos"),
                    },
                },
            };
        }

        private static TrialDefinition GlowingBarracudasFading()
        {
            TrialPoint shoal = new(27617, 30741, 14925);
            return new TrialDefinition
            {
                ML = 3,
                Step = 6,
                Name = "Glowing Barracuda's Fading",
                Scope = TrialScope.Group,
                Zone = TrialZone.Twilight,
                Anchor = new TrialPoint(28852, 32492, 15325),
                StarterName = "triton treasure hunter",
                StarterModel = Triton,
                Intro = "One of the barracuda down that passage has swallowed runic power, and it shines through its hide. " +
                    "The rest of the shoal will come at you in a wave. You only need the shining one, so put your whole party on it and let the others follow it into the dark.",
                Victory = "The glow fades from the great barracuda, and the power settles on you.",
                Replaces = new[] { "triton treasure hunter", "bonerending barracuda" },
                TimeLimitSeconds = 1200,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The shoal turns as one. The glowing barracuda is the one that matters!",
                        Mobs = { Mob("glowing barracuda", Barracuda, 66, 90, 22000, 1.2, shoal, "glowing", melee: eDamageType.Thrust) },
                        OnStart = run => Wave(run, Mob("bonerending barracuda", Barracuda, 62, 50, 2500, 0.6, tag: "shoal", required: false, melee: eDamageType.Thrust), 12, shoal, 500),
                        Done = Cleared("glowing"),
                    },
                },
            };
        }

        private static TrialDefinition ShraoghsFearRemoved()
        {
            TrialPoint hunter = new(345077, 650488, 5546);
            TrialPoint shark = new(345677, 650088, 5546);
            const int StomachPercent = 25;
            const int ExposedSeconds = 25;

            void Stomach(TrialRun run, TrialMob mob)
            {
                if (First(run, "shraogh") is not { } boss)
                    return;
                boss.Health = Math.Max(1, boss.Health - boss.MaxHealth * StomachPercent / 100);
                boss.Immune = false;
                run.Set("exposed", ExposedSeconds);
                run.Tell("The eel bile eats through Shraogh's hide. Strike while it burns!");
            }

            void Eel(TrialRun run, TrialMob mob)
            {
                TrialMobSpec stomach = Clickable("eel stomach", EelModel, 15, Where(mob), "You burst the stomach. Its bile clouds the water towards Shraogh.", required: false);
                stomach.Tag = "stomach";
                stomach.OnDeath = Stomach;
                run.Spawn(stomach);
            }

            TrialMobSpec Eels()
            {
                TrialMobSpec eel = Mob("darid gremna eel", EelModel, 63, 62, 3500, 0.8, tag: "eel", required: false, melee: eDamageType.Thrust);
                eel.OnDeath = Eel;
                return eel;
            }

            return new TrialDefinition
            {
                ML = 3,
                Step = 7,
                Name = "Shraogh's Fear Removed",
                Scope = TrialScope.Group,
                Zone = TrialZone.Oceanus,
                Anchor = hunter,
                StarterName = "triton treasure hunter",
                StarterModel = Triton,
                Intro = "Your blades will barely mark that whale shark. Its hide takes no harm from steel. But the bile of a darid gremna eel eats right through it. " +
                    "I netted a few of them from the temple for this very purpose. Kill one, burst its stomach, and Shraogh is yours to cut until the burn fades.",
                Victory = "Shraogh sinks into the deep, and the waters before the temple are safe.",
                Replaces = new[] { "Shraogh", "triton treasure hunter" },
                TimeLimitSeconds = 1500,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Shraogh comes for you, and the netted eels break loose! Kill the eels and burst their stomachs.",
                        Mobs = { Mob("Shraogh", WhaleShark, 67, 25, 32000, 1.4, shark, "shraogh", immune: true, melee: eDamageType.Crush) },
                        OnStart = run => Wave(run, Eels(), 3, hunter, 500),
                        OnTick = run =>
                        {
                            int exposed = run.Get<int>("exposed");
                            if (exposed > 0)
                            {
                                run.Set("exposed", exposed - 1);
                                if (exposed == 1)
                                {
                                    run.SetImmune("shraogh", true);
                                    run.Tell("The bile washes away, and Shraogh's hide closes again.");
                                }
                            }
                            if (!run.Mobs("eel").Any() && !run.Mobs("stomach").Any() && exposed == 0)
                                Wave(run, Eels(), 3, hunter, 500);
                        },
                        Done = Cleared("shraogh"),
                    },
                },
            };
        }

        private static TrialDefinition StingRaysPowerAbsorbed()
        {
            TrialPoint swarm = new(34424, 44121, 14799);

            TrialMobSpec Glowing(TrialPoint at)
            {
                TrialMobSpec ray = Mob("glowing sting ray", RayModel, 65, 40, 7000, 1.0, at, "glowing", required: false, melee: eDamageType.Thrust);
                ray.OnDeath = PowerJumps;
                return ray;
            }

            void PowerJumps(TrialRun run, TrialMob mob)
            {
                int caught = run.Get<int>("caught") + 1;
                run.Set("caught", caught);
                if (caught >= RayKillsNeeded)
                    return;
                run.Tell("The runic power leaps to another ray!");
                TrialMob next = First(run, "ray");
                if (next == null)
                {
                    run.Spawn(Glowing(swarm));
                    return;
                }
                TrialPoint at = Where(next);
                next.Delete();
                run.Spawn(Glowing(at));
            }

            return new TrialDefinition
            {
                ML = 3,
                Step = 8,
                Name = "Sting Ray's Power Absorbed",
                Scope = TrialScope.Group,
                Zone = TrialZone.Twilight,
                Anchor = swarm,
                StarterName = "triton ray hunter",
                StarterModel = Triton,
                Intro = "The rays here pass stolen runic power from one to another like a hot stone. Kill the one that glows and the light jumps to its neighbour. " +
                    $"Do that {RayKillsNeeded} times and it has nowhere left to run but into you. Ignore the dull ones if you can. They sting.",
                Victory = "The light of the rays gutters out, and the runic power is yours.",
                Replaces = new[] { "sting ray" },
                TimeLimitSeconds = 1200,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The swarm lifts from the sand. One of them glows!",
                        OnStart = run =>
                        {
                            Wave(run, Mob("sting ray", RayModel, 63, 22, 3000, 0.8, tag: "ray", required: false, melee: eDamageType.Thrust), 9, swarm, 450);
                            run.Spawn(Glowing(On(swarm, 200, 0, 1)));
                        },
                        Done = run => run.Get<int>("caught") >= RayKillsNeeded,
                    },
                },
            };
        }

        private static TrialDefinition SinoviasPowerRelinquished()
        {
            TrialPoint den = new(58117, 35070, 14982);
            return new TrialDefinition
            {
                ML = 3,
                Step = 9,
                Name = "Sinovia's Power Relinquished",
                Scope = TrialScope.Group,
                Zone = TrialZone.Twilight,
                Anchor = den,
                StarterName = "triton wreck-diver",
                StarterModel = Triton,
                Intro = "Sinovia sits at the end of this tunnel with a belly full of runic power. Stand close to her. She reaches anyone who hangs back with a slow poison, " +
                    "she drinks the life from whoever she fancies, and when a healer draws her eye she sends her young to fetch them.",
                Victory = "Sinovia goes limp, and the power she swallowed drifts free into your hands.",
                Replaces = new[] { "Sinovia" },
                TimeLimitSeconds = 1200,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "Sinovia uncoils from the wreckage of her meals.",
                        Mobs = { Mob("Sinovia", Octopus, 67, 32, 34000, 1.3, den, "sinovia") },
                        OnTick = run =>
                        {
                            if (First(run, "sinovia") is not { } boss)
                                return;
                            if (Every(run, "ink", 6))
                                Hurt(run, boss, Ring(run, Where(boss), 500, 2000), 90, eDamageType.Body);
                            if (Every(run, "drain", 15) && Ring(run, Where(boss), 0, 1000).OrderBy(_ => Random.Shared.Next()).FirstOrDefault() is { } victim)
                            {
                                Hurt(run, boss, new[] { victim }, 200, eDamageType.Spirit);
                                boss.Health = Math.Min(boss.MaxHealth, boss.Health + boss.MaxHealth / 100);
                                run.Tell($"Sinovia drinks the life from {victim.Name}.");
                            }
                            if (Every(run, "young", 40) && run.Mobs("young").Count() < Scaled(2, run.HealthScale, 1))
                            {
                                TrialMob young = run.Spawn(At(Mob("omrentae octopus", Octopus, 63, 50, 4000, 0.9, tag: "young", required: false), On(den, 250, Random.Shared.Next(6), 6)));
                                if (Ring(run, Where(boss), 400, 2000).OrderBy(_ => Random.Shared.Next()).FirstOrDefault() is { } prey)
                                    young.StartAttack(prey);
                            }
                        },
                        Done = Cleared("sinovia"),
                    },
                },
            };
        }

        private static TrialDefinition ConqueringTwilight()
        {
            TrialPoint medusa = new(68865, 19544, 17897);
            TrialPoint[] squares = { new(68700, 20521, 17897), new(69030, 20521, 17897), new(68700, 21000, 17897), new(69030, 21000, 17897) };
            TrialPoint[] guards =
            {
                new(68431, 19899, 17898), new(68432, 20035, 17898), new(68436, 20177, 17898),
                new(69290, 20380, 17898), new(69292, 20523, 17898), new(69300, 20663, 17898),
                new(68432, 20863, 17898), new(68432, 21004, 17898), new(68429, 21147, 17898),
            };
            const int TrapRearmSeconds = 20;

            void Traps(TrialRun run)
            {
                for (int i = 0; i < squares.Length; i++)
                {
                    string key = $"trap{i}";
                    int rearm = run.Get<int>(key);
                    if (rearm > 0)
                    {
                        run.Set(key, rearm - 1);
                        continue;
                    }
                    if (!Ring(run, squares[i], 0, 130).Any())
                        continue;
                    run.Set(key, TrapRearmSeconds);
                    if (i % 2 == 0)
                    {
                        run.Tell("A dark square sinks underfoot, and a snake pours out of it!");
                        run.Spawn(At(Mob("lethal cobra", Cobra, 62, 45, 2500, 0.8, tag: "snake", required: false, melee: eDamageType.Thrust), squares[i]));
                    }
                    else
                    {
                        run.Tell("A dark square sinks underfoot, and green light bursts up from it!");
                        Hurt(run, run.Starter, Ring(run, squares[i], 0, 350), 200, eDamageType.Cold);
                    }
                }
            }

            void Fight(TrialRun run)
            {
                Traps(run);
                if (First(run, "medusa") is not { } boss)
                    return;
                if (Every(run, "gaze", 20))
                {
                    Hurt(run, boss, Ring(run, Where(boss), 0, 1000), 150, eDamageType.Spirit);
                    run.Tell("Medusa's gaze passes over you, and your limbs grow heavy.");
                }
                if (Every(run, "shriek", 40))
                    Hurt(run, boss, Ring(run, Where(boss), 0, 700), 250, eDamageType.Energy);
                if (HealthPercent(boss) <= 50 && !run.Get<bool>("statues"))
                {
                    run.Set("statues", true);
                    run.Tell("Stone grinds on stone. Statues step down from the walls. They cannot be hurt, so run from them and finish Medusa!");
                    Wave(run, Mob("animated statue", Hoplite, 65, 47, 5000, 1.2, tag: "hall statue", required: false, immune: true), 4, medusa, 900);
                }
            }

            return new TrialDefinition
            {
                ML = 3,
                Step = 10,
                Name = "Conquering Twilight",
                Scope = TrialScope.Raid,
                Zone = TrialZone.Twilight,
                Anchor = new TrialPoint(69127, 20936, 17898),
                StarterName = "Petrified Champion",
                StarterModel = StonedSaracen,
                Intro = "This one got further than most. Scratched in the plinth: clear the living statues first. Then fight Medusa at the side of the hall, away from the dark squares in the floor. " +
                    "They set loose snakes and worse. When she calls the stone from the walls, do not stop to fight it. It falls when she falls.",
                Victory = "Medusa is dead. The Temple of Twilight is yours, and the stone in its halls is only stone.",
                Replaces = new[]
                {
                    "Medusa", "treasure protector", "minor lifebane statue", "minor magebane statue", "minor shieldbreaker statue",
                    "superior lifebane statue", "superior magebane statue", "superior shieldbreaker statue",
                },
                TimeLimitSeconds = 2100,
                Phases =
                {
                    new TrialPhase
                    {
                        Announce = "The statues of Medusa's hall turn their heads. Break them before she wakes.",
                        OnStart = run =>
                        {
                            int count = Scaled(guards.Length, run.HealthScale);
                            for (int i = 0; i < count; i++)
                                run.Spawn(Mob(StatueName(i), Hoplite, 64, i % 3 == 1 ? (byte)47 : (byte)32, 4000, 1.0, guards[i], "guard"));
                        },
                        OnTick = Traps,
                        Done = Cleared("guard"),
                    },
                    new TrialPhase
                    {
                        Announce = "Medusa uncoils from her throne. Keep her at the side of the hall!",
                        Mobs = { Mob("Medusa", MedusaModel, 68, 75, 110000, 1.6, medusa, "medusa", melee: eDamageType.Slash) },
                        OnTick = Fight,
                        Done = Cleared("medusa"),
                    },
                    new TrialPhase
                    {
                        Announce = "With her last breath the traps of the hall go off together!",
                        Pulses = { new TrialPulse { IntervalSeconds = 3, Damage = 120, Radius = 900, DamageType = eDamageType.Heat } },
                        SurviveSeconds = 4,
                    },
                },
            };
        }

        private static string StatueName(int index) => (index % 9) switch
        {
            0 or 2 => "minor shieldbreaker statue",
            1 => "superior shieldbreaker statue",
            3 or 5 => "minor lifebane statue",
            4 => "superior lifebane statue",
            6 or 8 => "minor magebane statue",
            _ => "superior magebane statue",
        };
    }
}
