using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;

namespace DOL.GS.Trials
{
    /// <summary>Master Level 6 trials: Typhon's Reach and the Ashen Isles, ending with the Chimera.</summary>
    public static class Ml6
    {
        private const ushort UraeusModel = 1234;
        private const ushort SalamanderModel = 1261;
        private const ushort WarriorModel = 1045;
        private const ushort PriestModel = 1046;
        private const ushort TaurModel = 1190;
        private const ushort SmallTaurModel = 1191;
        private const ushort SphinxModel = 1177;
        private const ushort EfreetModel = 1199;
        private const ushort MauModel = 1040;
        private const ushort PartModel = 997;
        private const ushort GateModel = 998;
        private const ushort OrbModel = 1391;

        public const int GlandsNeeded = 8;
        public const int FlameSeconds = 60;
        public const int IncineratorReach = 400;
        public const int LateefSpeed = 120;
        public const int LateefPatienceSeconds = 420;
        public const int BridgeReach = 500;
        public const int AmbushSeconds = 900;
        public const int OrbSeconds = 600;
        public const int BrazierCount = 6;
        public const int GateAddLimit = 6;
        public const int OpenGateWaveSeconds = 25;
        public const int FailingGateWaveSeconds = 12;
        public const int FailingGatePercent = 30;

        private static readonly TrialPoint LateefRow = new(515919, 573893, 10336, 2635);
        private static readonly TrialPoint LateefBridge = new(486533, 574213, 10497, 1016);
        private static readonly TrialPoint OrbCentre = new(551166, 576515, 10769, 2048);

        private static readonly TrialPoint[] HatchlingRows =
        {
            new(477952, 554227, 9592), new(476445, 551307, 9592), new(477903, 550623, 9593),
            new(478320, 553268, 9592), new(474993, 555334, 9594), new(476685, 550226, 9602),
        };

        private static readonly TrialMobSpec[] Hatchlings = HatchlingRows.Select(Hatchling).ToArray();

        private static readonly TrialMobSpec Battler = new()
        {
            Name = "taur battler", Model = SmallTaurModel, Level = 60, Size = 60, Health = 4000, DamageFactor = 0.9,
            At = new TrialPoint(550925, 539420, 10796), Required = false, Tag = "adds", MeleeDamage = eDamageType.Slash,
        };

        private static readonly TrialMobSpec Lancer = new()
        {
            Name = "taur lancer", Model = TaurModel, Level = 63, Size = 60, Health = 6000, DamageFactor = 1.1,
            At = new TrialPoint(550567, 539088, 10734), Required = false, Tag = "adds", MeleeDamage = eDamageType.Thrust,
        };

        private static readonly TrialMobSpec ChimeraGuard = new()
        {
            Name = "elite taur defender", Model = SmallTaurModel, Level = 60, Size = 45, Health = 5000, DamageFactor = 0.9,
            At = new TrialPoint(550743, 559385, 10672), Required = false, Tag = "defender", MeleeDamage = eDamageType.Slash,
        };

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return Hunt();
            yield return Sacrifice();
            yield return Lateef();
            yield return Infestation();
            yield return Flames();
            yield return Siraadi();
            yield return Ankhkare();
            yield return Efreet();
            yield return Fortress();
            yield return Chimera();
        }

        private static TrialDefinition Hunt() => new()
        {
            ML = 6, Step = 1, Name = "Hunt for the Haje-Uraei", Scope = TrialScope.Group, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(468644, 537649, 10424),
            StarterName = "Scorched Snake Hunter", StarterModel = 381,
            Intro = "The rare one, the haje-uraei, is born from the death of its lesser kin. I have seen it rise from a corpse and slide off for the lava. Kill the uraeus around here and it will show itself. It spits fire from far off, so close with it quickly.",
            Victory = "The haje-uraei's coils go slack, and its venom is yours.",
            TimeLimitSeconds = 1200,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The uraeus nest uncoils around you.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "uraeus", Model = UraeusModel, Level = 58, Health = 3000, DamageFactor = 0.8, Count = 3, Spread = 500, MeleeDamage = eDamageType.Thrust },
                    },
                },
                new TrialPhase
                {
                    Announce = "A haje-uraei springs to life from the last body and turns toward you!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "haje-uraei", Model = UraeusModel, Level = 63, Size = 60, Health = 20000, DamageFactor = 1.1, Spread = 300, Tag = "haje", MeleeDamage = eDamageType.Thrust },
                    },
                    OnTick = HajeTick,
                },
            },
        };

        private static TrialDefinition Sacrifice() => new()
        {
            ML = 6, Step = 2, Name = "Sacrifice", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(464272, 561748, 10036, 2901),
            StarterName = "siam-he mau prisoner", StarterModel = MauModel,
            Intro = "They have dragged me here to feed the earth. If my blood is spilled, something terrible will climb out of it. Help me against my escort, if you can. And if you cannot, stay and kill what comes.",
            Victory = "The Anathemic Salamander falls, and the trembling stops. The prisoner's death is paid for.",
            Replaces = new[] { "Anathemic Salamander", "siam-he mau prisoner", "siam-he sacrificial escort" },
            TimeLimitSeconds = 1500,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The sacrificial escort closes around the prisoner.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "siam-he sacrificial escort", Model = WarriorModel, Level = 61, Health = 6000, DamageFactor = 1.0, Count = 4, Spread = 450, MeleeDamage = eDamageType.Slash },
                    },
                },
                new TrialPhase
                {
                    Announce = "Too late. The last escort's blade finds its mark. The earth trembles violently, and a curse climbs out of Volcanus!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Anathemic Salamander", Model = SalamanderModel, Level = 68, Size = 200, Health = 70000, DamageFactor = 0.9, Spread = 500, Tag = "anathemic" },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 14, Damage = 160, Radius = 700, SourceTag = "anathemic", DamageType = eDamageType.Heat, Message = "The Anathemic Salamander breathes out a wash of cinders." },
                    },
                },
            },
        };

        private static TrialDefinition Lateef() => new()
        {
            ML = 6, Step = 3, Name = "Lateef", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = LateefRow,
            StarterName = "Lateef", StarterModel = PriestModel,
            Intro = "I followed Am-he and I am sick of fire. I want the desert. There is a great arched bridge to the west. See me across and I will pay you with the dagger I stole from my masters. I walk slowly, and I may be watched, so stay close.",
            Victory = "Sutekh falls. You take back the dagger Lateef died for, and clean it.",
            Replaces = new[] { "Lateef", "Sutekh", "Fadil", "Udaji" },
            TimeLimitSeconds = 1800,
            LeashRange = 36000,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Lateef the Deserter sets off west for the bridge. Stay with him.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Lateef the Deserter", Model = PriestModel, Level = 60, Size = 49, Objective = true, Required = false, Spread = 200, Tag = "deserter", ObjectiveText = "Lateef waves you on. He has no breath to spare for talk." },
                    },
                    OnStart = run => run.Set("deserter", run.Mobs("deserter").First()),
                    OnTick = LateefTick,
                    Done = run => run.Get<bool>("atBridge"),
                },
                new TrialPhase
                {
                    Announce = "Three servants of Am-he appear on the bridge. Sutekh takes the dagger from Lateef, kills him with it and sheathes it. They will not stay long!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Fadil", Model = PriestModel, Level = 66, Health = 14000, DamageFactor = 0.9, At = new TrialPoint(486534, 574289, 10497, 1016), Tag = "fadil" },
                        new TrialMobSpec { Name = "Udaji", Model = PriestModel, Level = 66, Health = 14000, DamageFactor = 0.9, At = new TrialPoint(486532, 574139, 10498, 1016), Tag = "udaji" },
                        new TrialMobSpec { Name = "Sutekh", Model = PriestModel, Level = 68, Health = 60000, DamageFactor = 1.4, At = LateefBridge, Tag = "sutekh", MeleeDamage = eDamageType.Thrust },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 12, Damage = 180, Radius = 500, SourceTag = "fadil", DamageType = eDamageType.Spirit, Message = "Fadil's will lashes out across the bridge." },
                        new TrialPulse { IntervalSeconds = 6, Damage = 110, Radius = 600, SourceTag = "udaji", DamageType = eDamageType.Body },
                    },
                    OnStart = LateefFalls,
                    OnTick = AmbushTick,
                },
            },
        };

        private static TrialDefinition Infestation() => new()
        {
            ML = 6, Step = 4, Name = "Infestation", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(468740, 548123, 10136, 4009),
            StarterName = "Hissing Nest", StarterModel = UraeusModel,
            Intro = "The nest is seething. Kill what crawls out of it and the mother of them, Pallida-Uraei, will come looking. Bring her low and she will split in three, but the three share one life. Kill one and all are done. The tail you take from her will open the way to Ankhkare.",
            Victory = "Pallida-Uraei lies still, and you cut away her tail. Its keeping is recorded, and Ankhkare's guardian will know it.",
            Replaces = new[] { "Pallida-Uraei" },
            TimeLimitSeconds = 1500,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The uraeus pour out of the nest.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "uraeus", Model = UraeusModel, Level = 58, Health = 3500, DamageFactor = 0.8, Count = 4, Spread = 450, MeleeDamage = eDamageType.Thrust },
                    },
                },
                new TrialPhase
                {
                    Announce = "A hissing noise is heard throughout Volcanus.",
                    Mobs =
                    {
                        new TrialMobSpec
                        {
                            Name = "Pallida-Uraei", Model = UraeusModel, Level = 66, Size = 75, Health = 45000, DamageFactor = 1.2, Spread = 300, Tag = "pallida", MeleeDamage = eDamageType.Thrust,
                            OnDeath = (run, _) => run.Set("pallidaDead", true),
                        },
                    },
                    OnTick = PallidaTick,
                    Done = run => run.Get<bool>("pallidaDead"),
                },
            },
        };

        private static TrialDefinition Flames() => new()
        {
            ML = 6, Step = 5, Name = "Flames", Scope = TrialScope.Solo, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(476838, 552923, 9592, 2070),
            StarterName = "crazed adventurer", StarterModel = 381,
            Intro = "Cold! It's all about cold! Hatchlings carry frozen glands, glands cool the spouts, and under the spouts are the four pieces. Bring me eight glands. When the eighth is in my hand the flames go out for sixty seconds, no more! Get the cogwheel, the fastener, the handle and the lens, target the big salamander, walk right up to him, and watch him burn.",
            Victory = "The livid salamander collapses into ash, and the ash is yours to keep. Ankhkare's guardian will know it.",
            Replaces = new[] { "livid salamander", "crazed adventurer" },
            TimeLimitSeconds = 1500,
            Phases =
            {
                new TrialPhase
                {
                    Announce = $"Hunt the hatchlings around the spouts. The adventurer needs {GlandsNeeded} frozen glands.",
                    Mobs = { Hatchlings[0], Hatchlings[1], Hatchlings[2] },
                    OnTick = HatchlingTick,
                    Done = run => run.Get<int>("glands") >= GlandsNeeded,
                },
                new TrialPhase
                {
                    Announce = $"\"That's the last one! Run!\" The flame spouts die. You have {FlameSeconds} seconds to grab all four pieces!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Cogwheel", Model = PartModel, Size = 27, Objective = true, At = new TrialPoint(476034, 554496, 9592), ObjectiveText = "You snatch the cogwheel from the cold spout." },
                        new TrialMobSpec { Name = "Fastener", Model = PartModel, Size = 27, Objective = true, At = new TrialPoint(476035, 551937, 9592), ObjectiveText = "You snatch the fastener from the cold spout." },
                        new TrialMobSpec { Name = "Handle", Model = PartModel, Size = 27, Objective = true, At = new TrialPoint(477568, 554493, 9592), ObjectiveText = "You snatch the handle from the cold spout." },
                        new TrialMobSpec { Name = "Lens", Model = PartModel, Size = 27, Objective = true, At = new TrialPoint(477572, 551934, 9592), ObjectiveText = "You snatch the lens from the cold spout." },
                    },
                    OnTick = SpoutTick,
                },
                new TrialPhase
                {
                    Announce = "The four pieces lock together into a Salamander Incinerator. Target the livid salamander and get close. Nothing else will hurt him.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "livid salamander", Model = SalamanderModel, Level = 65, Size = 150, Health = 8000, DamageFactor = 0.8, At = new TrialPoint(474883, 550113, 9781, 1174), Immune = true, Tag = "livid", MeleeDamage = eDamageType.Slash },
                    },
                    OnTick = IncineratorTick,
                },
            },
        };

        private static TrialDefinition Siraadi() => new()
        {
            ML = 6, Step = 6, Name = "Siraadi", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(484358, 564268, 9592),
            StarterName = "Escaped Offering", StarterModel = MauModel,
            Intro = "Stay down here by the lava, well back from the pillars. They answer one another's calls, so draw them out and fight them away from the platform. Thin them enough and Siraadi himself will come to see why the rites have stopped. His head will open the way to Ankhkare.",
            Victory = "Siraadi falls, and you take his head. Its keeping is recorded, and Ankhkare's guardian will know it.",
            Replaces = new[] { "Siraadi" },
            TimeLimitSeconds = 1800,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Worshippers come down from the platform to see who has interrupted them.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "siam-he prema", Model = PriestModel, Level = 60, Health = 5000, DamageFactor = 1.0, Count = 2, At = new TrialPoint(485175, 562562, 9592), MeleeDamage = eDamageType.Slash },
                        new TrialMobSpec { Name = "siam-he chanter", Model = PriestModel, Level = 60, Health = 3500, DamageFactor = 0.7, Count = 2, At = new TrialPoint(485430, 562826, 9592), Tag = "chanter" },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 10, Damage = 120, Radius = 600, SourceTag = "chanter", DamageType = eDamageType.Heat },
                    },
                },
                new TrialPhase
                {
                    Announce = "A sacrificial escort marching for the ramp hears the fight and turns aside.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "siam-he sacrificial escort", Model = WarriorModel, Level = 61, Health = 6000, DamageFactor = 1.0, Count = 3, At = new TrialPoint(485175, 562562, 9592), MeleeDamage = eDamageType.Slash },
                    },
                },
                new TrialPhase
                {
                    Announce = "More worshippers run in from across Volcanus to refill the platform.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "siam-he prema", Model = PriestModel, Level = 60, Health = 5000, DamageFactor = 1.0, Count = 2, At = new TrialPoint(485175, 562562, 9592), MeleeDamage = eDamageType.Slash },
                        new TrialMobSpec { Name = "siam-he chanter", Model = PriestModel, Level = 60, Health = 3500, DamageFactor = 0.7, Count = 2, At = new TrialPoint(485430, 562826, 9592), Tag = "chanter" },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 10, Damage = 120, Radius = 600, SourceTag = "chanter", DamageType = eDamageType.Heat },
                    },
                },
                new TrialPhase
                {
                    Announce = "Siraadi the sacrificer descends from among the pillars.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Siraadi", Model = PriestModel, Level = 67, Size = 62, Health = 60000, DamageFactor = 1.2, At = new TrialPoint(485430, 562826, 9592), Tag = "siraadi", MeleeDamage = eDamageType.Slash },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 15, Damage = 200, Radius = 700, SourceTag = "siraadi", DamageType = eDamageType.Heat, Message = "Siraadi calls down Am-he's fire!" },
                    },
                },
            },
        };

        private static TrialDefinition Ankhkare() => new()
        {
            ML = 6, Step = 7, Name = "Ankhkare", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(536380, 575552, 10691, 2548),
            StarterName = "Ankhkare's Guardian", StarterModel = SphinxModel,
            Intro = "Three of us keep the burning way to Ankhkare. You have already paid the toll: the tail of Pallida-Uraei, the ash of the livid salamander and the head of Siraadi. I will lower my wall for the tail, but the fire was all that held the swarm back. When it is dead, go on to my sisters.",
            Victory = "Ankhkare falls, and the burning way goes dark.",
            RequiresSteps = new[] { 4, 5, 6 },
            Replaces = new[] { "Ankhkare's Guardian", "Ankhkare" },
            TimeLimitSeconds = 2100,
            LeashRange = 12000,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The guardian takes the tail of Pallida-Uraei and the fire falls. The uraeus behind it strike at once!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "uraeus", Model = UraeusModel, Level = 60, Health = 5000, DamageFactor = 1.0, Count = 4, At = new TrialPoint(535369, 576334, 10618), MeleeDamage = eDamageType.Thrust },
                    },
                },
                new TrialPhase
                {
                    Announce = "Go on to the second guardian, to the south-east.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Ankhkare's Guardian", Model = SphinxModel, Level = 60, Objective = true, At = new TrialPoint(539324, 578368, 10699, 2548), ObjectiveText = "You hold out your claim to the head of Siraadi. The guardian bows, and the fire falls." },
                    },
                },
                new TrialPhase
                {
                    Announce = "Siam-he and salamanders rush through the gap!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "siam-he plebian", Model = WarriorModel, Level = 60, Health = 5000, DamageFactor = 1.0, Count = 3, At = new TrialPoint(538380, 579653, 10579), MeleeDamage = eDamageType.Slash },
                        new TrialMobSpec { Name = "salamander", Model = SalamanderModel, Level = 60, Size = 100, Health = 6000, DamageFactor = 1.0, Count = 2, At = new TrialPoint(538646, 579172, 10587), MeleeDamage = eDamageType.Slash },
                    },
                },
                new TrialPhase
                {
                    Announce = "Go on to the third guardian, to the west.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Ankhkare's Guardian", Model = SphinxModel, Level = 60, Objective = true, At = new TrialPoint(535871, 578879, 10699, 2560), ObjectiveText = "You hold out your claim to the salamander ash. The guardian bows, and the last fire falls." },
                    },
                },
                new TrialPhase
                {
                    Announce = "Salamanders immune to fire and frost alike boil out of the last wall!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "salamander", Model = SalamanderModel, Level = 62, Size = 100, Health = 6000, DamageFactor = 1.0, Count = 5, At = new TrialPoint(535315, 578541, 10616), MeleeDamage = eDamageType.Slash },
                    },
                },
                new TrialPhase
                {
                    Announce = "Ankhkare rises to the north-west, and three more guardians with him. Keep your fighters bunched and go to him!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Ankhkare", Model = SphinxModel, Level = 69, Size = 150, Health = 90000, DamageFactor = 1.3, At = new TrialPoint(531684, 582548, 10831, 2586), Tag = "ankhkare", MeleeDamage = eDamageType.Slash },
                        new TrialMobSpec { Name = "Ankhkare's Guardian", Model = SphinxModel, Level = 62, Health = 8000, DamageFactor = 1.0, Count = 3, At = new TrialPoint(532184, 582248, 10831), MeleeDamage = eDamageType.Slash },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 11, Damage = 240, Radius = 900, SourceTag = "ankhkare", DamageType = eDamageType.Heat, Message = "Ankhkare's fire washes over the ground around him." },
                    },
                },
            },
        };

        private static TrialDefinition Efreet() => new()
        {
            ML = 6, Step = 8, Name = "Efreet", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = OrbCentre,
            StarterName = "efreeti overseer", StarterModel = EfreetModel,
            Intro = "Do you dare the braziers? Say the word and the Orb of Apollo will burn here, with an efreeti on every pillar. Destroy the orb within ten minutes. The efreeti cannot be hurt, and their bolts do not stop. Those near the orb will burn; the rest must spread out around the ring.",
            Victory = "The Orb of Apollo shatters. The braziers go out, and the efreeti go with them.",
            Replaces = new[] { "efreeti overseer" },
            TimeLimitSeconds = 900,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The Orb of Apollo blazes up, and the efreeti take their places on the pillars!",
                    Mobs = OrbMobs(),
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 5, Damage = 240, Radius = 500, SourceTag = "orb", DamageType = eDamageType.Heat },
                    },
                    OnStart = RootOrbMobs,
                    OnTick = OrbTick,
                },
            },
        };

        private static TrialDefinition Fortress() => new()
        {
            ML = 6, Step = 9, Name = "Fortress", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(551238, 539933, 10616),
            StarterName = "Taur Deserter", StarterModel = SmallTaurModel,
            Intro = "Vazul sits behind two gates, and I know how they are held. Breach them from here. Taurs will come the whole time, and faster when a gate is close to falling. When a gate is about to go, back away from it. Vazul sets traps. Break the second and he must come out, with his portalmasters. Kill those fast or the warping never stops.",
            Victory = "Vazul is dead and the fortress is breached.",
            Replaces = new[] { "Vazul" },
            TimeLimitSeconds = 2400,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The horns sound from the wall. Attack the outer gate!",
                    Mobs = { Gate("Outer Gate of Vazul's Fortress", new TrialPoint(550793, 539622, 10833)) },
                    OnStart = RootGate,
                    OnTick = GateTick,
                },
                new TrialPhase
                {
                    Announce = "The outer gate is down. Attack the inner gate!",
                    Mobs = { Gate("Inner Gate of Vazul's Fortress", new TrialPoint(550925, 539420, 10796)) },
                    OnStart = RootGate,
                    OnTick = GateTick,
                },
                new TrialPhase
                {
                    Announce = "Vazul strides out of the ruined gate with his portalmasters at his side!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Vazul", Model = TaurModel, Level = 68, Size = 75, Health = 80000, DamageFactor = 1.4, Spread = 300, Tag = "vazul", MeleeDamage = eDamageType.Crush },
                        new TrialMobSpec { Name = "taur portalmaster", Model = TaurModel, Level = 60, Size = 55, Health = 3500, DamageFactor = 0.6, Count = 2, Required = false, At = new TrialPoint(550567, 539088, 10734), Tag = "portal" },
                    },
                    OnTick = PortalTick,
                },
            },
        };

        private static TrialDefinition Chimera() => new()
        {
            ML = 6, Step = 10, Name = "Chimera's Fortification", Scope = TrialScope.Raid, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(549139, 558294, 10672),
            StarterName = "Taur Stonecutter", StarterModel = SmallTaurModel,
            Intro = "You have the ash, the tail, the head and the fall of the fortress behind you. Only she is left. Clear her defenders from the room first. Then keep spread out, because her gaze takes everyone standing near her, and a few of us will always come to her call.",
            Victory = "The Chimera falls, and the fire in the Ashen Isles sinks low.",
            Replaces = new[] { "Chimera" },
            TimeLimitSeconds = 2400,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The elite defenders turn on you. Clear the room!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "elite taur defender", Model = SmallTaurModel, Level = 60, Size = 45, Health = 5000, DamageFactor = 0.9, Count = 4, Spread = 500, MeleeDamage = eDamageType.Slash },
                        new TrialMobSpec { Name = "taur arieos", Model = SmallTaurModel, Level = 58, Size = 45, Health = 4000, DamageFactor = 0.9, Count = 2, Spread = 350, MeleeDamage = eDamageType.Slash },
                    },
                },
                new TrialPhase
                {
                    Announce = "The Chimera rises from her nest!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Chimera", Model = 1180, Level = 70, Size = 150, Health = 130000, DamageFactor = 1.4, At = new TrialPoint(550183, 558467, 10763, 329), Tag = "chimera", MeleeDamage = eDamageType.Slash },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 15, Damage = 200, Radius = 600, SourceTag = "chimera", DamageType = eDamageType.Spirit, Message = "The Chimera's gaze sweeps the room, and everything near her staggers!" },
                    },
                    OnTick = ChimeraTick,
                },
            },
        };

        /// <summary>An evenly spaced point on a circle, for monsters that need their own place.</summary>
        public static TrialPoint Ring(TrialPoint centre, int radius, int index, int count)
        {
            double angle = 2 * Math.PI * index / count;
            return new TrialPoint(centre.X + (int)Math.Round(radius * Math.Cos(angle)), centre.Y + (int)Math.Round(radius * Math.Sin(angle)), centre.Z, centre.Heading);
        }

        public static int GateWaveSeconds(int gateHealthPercent) => gateHealthPercent <= FailingGatePercent ? FailingGateWaveSeconds : OpenGateWaveSeconds;

        private static TrialMobSpec Hatchling(TrialPoint point) => new()
        {
            Name = "salamander hatchling", Model = SalamanderModel, Level = 55, Size = 50, Health = 700, DamageFactor = 0.3, At = point, Required = false, Tag = "hatchling",
            MeleeDamage = eDamageType.Slash,
            OnDeath = (run, _) =>
            {
                int glands = run.Get<int>("glands") + 1;
                run.Set("glands", glands);
                if (glands <= GlandsNeeded)
                    run.Tell($"A frozen cold gland: {glands} of {GlandsNeeded}.");
            },
        };

        private static List<TrialMobSpec> OrbMobs()
        {
            List<TrialMobSpec> mobs = new()
            {
                new TrialMobSpec { Name = "Orb of Apollo", Model = OrbModel, Level = 66, Size = 80, Health = 70000, DamageFactor = 0.5, Spread = 150, Tag = "orb", MeleeDamage = eDamageType.Heat },
            };
            for (int i = 0; i < BrazierCount; i++)
            {
                mobs.Add(new TrialMobSpec
                {
                    Name = "efreeti of the brazier", Model = EfreetModel, Level = 65, Health = 5000, DamageFactor = 0.5, Required = false, Immune = true,
                    At = Ring(OrbCentre, 1400, i, BrazierCount), AggroRange = 0, Tag = "brazier",
                });
            }
            return mobs;
        }

        private static TrialMobSpec Gate(string name, TrialPoint point) => new()
        {
            Name = name, Model = GateModel, Level = 60, Size = 120, Health = 25000, DamageFactor = 0.01, At = point, AggroRange = 0, Tag = "gate",
            OnDeath = GateTrap,
        };

        private static void HajeTick(TrialRun run)
        {
            TrialMob haje = run.Mobs("haje").FirstOrDefault();
            if (haje == null || !Ml5.Every(run, "spit", 6))
                return;
            GameLiving target = Ml5.RandomHostile(run, haje, 1800);
            if (target != null)
                Ml5.Strike(run, haje, target, 170, eDamageType.Heat);
        }

        private static void LateefTick(TrialRun run)
        {
            TrialMob deserter = run.Get<TrialMob>("deserter");
            if (Ml5.Near(deserter, LateefBridge, BridgeReach))
            {
                run.Set("atBridge", true);
                return;
            }

            int walked = run.Get<int>("walked") + 1;
            run.Set("walked", walked);
            if (walked >= LateefPatienceSeconds)
            {
                deserter.MoveTo(run.Starter.CurrentRegionID, LateefBridge.X, LateefBridge.Y, LateefBridge.Z, LateefBridge.Heading);
                run.Set("atBridge", true);
            }
            else if (!deserter.IsMoving)
            {
                deserter.PathTo(new Vector3(LateefBridge.X, LateefBridge.Y, LateefBridge.Z), LateefSpeed);
            }
        }

        private static void LateefFalls(TrialRun run)
        {
            run.Get<TrialMob>("deserter").Die(run.Mobs("sutekh").FirstOrDefault());
        }

        private static void AmbushTick(TrialRun run)
        {
            int age = run.Get<int>("ambushAge") + 1;
            run.Set("ambushAge", age);
            if (age >= AmbushSeconds)
            {
                run.End(false, "The servants of Am-he step back into the fire, and the dagger goes with them.");
                return;
            }

            TrialMob sutekh = run.Mobs("sutekh").FirstOrDefault();
            if (sutekh != null && run.Mobs("udaji").Any() && Ml5.Every(run, "mend", 3))
                sutekh.ChangeHealth(sutekh, eHealthChangeType.Regenerate, sutekh.MaxHealth / 100);
        }

        private static void PallidaTick(TrialRun run)
        {
            TrialMob pallida = run.Mobs("pallida").FirstOrDefault();
            if (pallida == null || pallida.HealthPercent > 25 || run.Get<bool>("pallidaSplit"))
                return;

            run.Set("pallidaSplit", true);
            run.Tell("Pallida-Uraei tears apart into three!");
            pallida.Delete();
            run.Spawn(new TrialMobSpec
            {
                Name = "Pallida-Uraei", Model = UraeusModel, Level = 64, Size = 60, Health = 5000, DamageFactor = 0.9, Count = 3, Spread = 350, Tag = "pallida", MeleeDamage = eDamageType.Thrust,
                OnDeath = (finished, _) =>
                {
                    Ml5.Clear(finished, "pallida");
                    finished.Set("pallidaDead", true);
                },
            });
        }

        private static void HatchlingTick(TrialRun run)
        {
            if (run.Mobs("hatchling").Count() < 3 && Ml5.Every(run, "hatch", 5))
                run.Spawn(Hatchlings[Util.Random(Hatchlings.Length - 1)]);
        }

        private static void SpoutTick(TrialRun run)
        {
            int age = run.Get<int>("flameAge") + 1;
            run.Set("flameAge", age);
            if (age >= FlameSeconds)
                run.End(false, "The spouts roar back to life. You were too slow, and the adventurer has no glands left.");
        }

        private static void IncineratorTick(TrialRun run)
        {
            TrialMob livid = run.Mobs("livid").FirstOrDefault();
            if (livid == null || run.Leader.TargetObject != livid || !run.Leader.IsWithinRadius(livid, IncineratorReach))
                return;
            run.Tell("The Salamander Incinerator spends itself in one white burst.");
            livid.Immune = false;
            livid.Die(run.Leader);
        }

        private static void RootOrbMobs(TrialRun run)
        {
            foreach (TrialMob mob in run.Mobs("orb").Concat(run.Mobs("brazier")))
                mob.MaxSpeedBase = 0;
        }

        private static void OrbTick(TrialRun run)
        {
            int age = run.Get<int>("orbAge") + 1;
            run.Set("orbAge", age);
            if (age >= OrbSeconds)
            {
                run.End(false, "The orb burns on untouched. The braziers gutter out and the efreeti wait for the next fool.");
                return;
            }

            if (!Ml5.Every(run, "bolts", 4))
                return;
            foreach (TrialMob brazier in run.Mobs("brazier").ToList())
            {
                GameLiving target = Ml5.RandomHostile(run, brazier, 3000);
                if (target != null)
                    Ml5.Strike(run, brazier, target, 100, eDamageType.Heat);
            }
        }

        private static void RootGate(TrialRun run)
        {
            run.Set("gateTrapWarned", false);
            foreach (TrialMob gate in run.Mobs("gate"))
                gate.MaxSpeedBase = 0;
        }

        private static void GateTick(TrialRun run)
        {
            TrialMob gate = run.Mobs("gate").FirstOrDefault();
            if (gate == null)
                return;

            if (gate.HealthPercent <= 10 && !run.Get<bool>("gateTrapWarned"))
            {
                run.Set("gateTrapWarned", true);
                run.Tell("The gate groans and begins to glow. Get back from it!");
            }

            if (!Ml5.Every(run, "gateWave", GateWaveSeconds(gate.HealthPercent)) || run.Mobs("adds").Count() >= GateAddLimit)
                return;

            int wave = run.Get<int>("wave") + 1;
            run.Set("wave", wave);
            run.Spawn(wave % 3 == 0 ? Lancer : Battler);
        }

        private static void GateTrap(TrialRun run, TrialMob gate)
        {
            switch (Util.Random(2))
            {
                case 0:
                    run.Tell("The fallen gate erupts in fire!");
                    foreach (GameLiving target in run.Hostiles(run.Starter, 1500))
                        Ml5.Strike(run, run.Starter, target, 300, eDamageType.Heat);
                    break;
                case 1:
                    run.Tell("The fallen gate reveals a line of lancers!");
                    run.Spawn(Lancer);
                    run.Spawn(Lancer);
                    break;
                default:
                    run.Tell("Battlers spill out through the gap!");
                    run.Spawn(Battler);
                    run.Spawn(Battler);
                    run.Spawn(Battler);
                    break;
            }
        }

        private static void PortalTick(TrialRun run)
        {
            if (run.Mobs("portal").Any() && Ml5.Every(run, "warp", 30) && run.Mobs("adds").Count() < GateAddLimit)
            {
                run.Tell("A portalmaster warps in another taur.");
                run.Spawn(Battler);
            }
        }

        private static void ChimeraTick(TrialRun run)
        {
            if (Ml5.Every(run, "defender", 60) && run.Mobs("defender").Count() < 4)
            {
                run.Tell("Defenders answer the Chimera's call.");
                run.Spawn(ChimeraGuard);
                run.Spawn(ChimeraGuard);
            }
        }
    }
}
