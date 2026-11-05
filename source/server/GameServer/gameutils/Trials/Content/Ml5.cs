using System;
using System.Collections.Generic;
using System.Linq;

namespace DOL.GS.Trials
{
    /// <summary>Master Level 5 trials: the Halls of Ma'ati, the crocodiles at its door, and Ammut.</summary>
    public static class Ml5
    {
        private const ushort MummyModel = 1048;
        private const ushort MauModel = 1040;
        private const ushort ItemModel = 997;
        private const ushort LightModel = 966;

        public const int ScarabCount = 6;
        public const int HapyCopyCount = 6;
        public const int HapyCopySeconds = 25;
        public const int JudgementSeconds = 40;
        public const int JudgementWarningSeconds = 8;
        public const int JarReturnSeconds = 90;
        public const int FountainReach = 300;

        public static readonly int[] DuamutefSplits = { 65, 35 };
        public static readonly int[] HapySplits = { 75, 50, 25 };

        private static readonly TrialPoint Fountain = new(32166, 28385, 15610);
        private static readonly TrialPoint Dock = new(37735, 30124, 15507, 750);
        private static readonly TrialPoint AmmutRow = new(50466, 36712, 17104, 1036);
        private static readonly TrialPoint TempleLanding = new(49766, 36712, 17104, 1024);

        private static readonly TrialMobSpec Scarab = new()
        {
            Name = "scarab of Duamutef", Model = 1205, Level = 58, Size = 40, Health = 1800, DamageFactor = 0.5,
            Count = ScarabCount, Spread = 350, Required = false, Tag = "scarab", MeleeDamage = eDamageType.Thrust,
        };

        private static readonly TrialMobSpec HapyCopy = new()
        {
            Name = "Echo of Hapy", Model = 1177, Level = 60, Size = 50, Health = 1200, DamageFactor = 0.6,
            Count = HapyCopyCount, Spread = 400, Required = false, Tag = "hapycopy", MeleeDamage = eDamageType.Slash,
        };

        private static readonly TrialMobSpec Lion = new()
        {
            Name = "lion of Imsety", Model = 1193, Level = 60, Size = 62, Health = 3000, DamageFactor = 0.8,
            Spread = 350, Required = false, Tag = "lion", MeleeDamage = eDamageType.Slash,
        };

        private static readonly TrialMobSpec Anubis = new()
        {
            Name = "anubite of the scales", Model = 1045, Level = 60, Health = 3000, DamageFactor = 0.8,
            At = new TrialPoint(50166, 36412, 17104), Required = false, Tag = "anubis", MeleeDamage = eDamageType.Slash,
        };

        private static readonly TrialMobSpec Crocodile = new()
        {
            Name = "crocodile of the scales", Model = 1259, Level = 60, Size = 100, Health = 3000, DamageFactor = 0.8,
            At = new TrialPoint(50166, 37012, 17104), Required = false, Tag = "croc", MeleeDamage = eDamageType.Crush,
        };

        private static readonly TrialMobSpec[] Jars =
        {
            Jar("Canopic Jar of the Liver", "jarLiver", new TrialPoint(49766, 36412, 17104), "The jar breaks and life floods back into your party.", MendParty),
            Jar("Canopic Jar of the Lungs", "jarLungs", new TrialPoint(49766, 37012, 17104), "The jar breathes out. The next judgement will find nothing to weigh.",
                (run, _) => run.Set("ward", true)),
            Jar("Canopic Jar of the Stomach", "jarStomach", new TrialPoint(49466, 36412, 17104), "The jar swallows the crocodiles around you.",
                (run, _) => Clear(run, "croc")),
            Jar("Canopic Jar of the Intestines", "jarIntestines", new TrialPoint(49466, 37012, 17104), "The jar coils tight and the anubites are dragged away.",
                (run, _) => Clear(run, "anubis")),
        };

        public static IEnumerable<TrialDefinition> Trials()
        {
            yield return Coil();
            yield return Hunger();
            yield return Breath();
            yield return Blood();
            yield return Reflection();
            yield return Preservation();
            yield return Mask();
            yield return Wrap();
            yield return Token();
            yield return Appetite();
        }

        private static TrialDefinition Coil() => new()
        {
            ML = 5, Step = 1, Name = "Ma'atis' Coil", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(27962, 33644, 14864, 1012),
            StarterName = "Embalmer of Qebehsenuef", StarterModel = MummyModel,
            Intro = "The jar of the intestines was never sealed. The echo of Qebehsenuef still clutches it, and everything near him burns. Keep your resistance to heat high and take it from him.",
            Victory = "The jar of the intestines is yours. Its keeping is recorded, and Ammut's chamber will know you carry it.",
            Replaces = new[] { "Echo of Qebehsenuef" },
            TimeLimitSeconds = 1200,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Two an-uat step out of the niches to bar the way.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "an-uat zetzaui", Model = 1046, Level = 58, Health = 4000, DamageFactor = 0.9, Count = 2, Spread = 400, MeleeDamage = eDamageType.Slash },
                    },
                },
                new TrialPhase
                {
                    Announce = "The Echo of Qebehsenuef wakes, and the air begins to scorch.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Echo of Qebehsenuef", Model = 1043, Level = 65, Size = 100, Health = 22000, DamageFactor = 1.1, Spread = 200, Tag = "qeb" },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 9, Damage = 220, Radius = 800, SourceTag = "qeb", DamageType = eDamageType.Heat, Message = "Waves of heat roll off the Echo of Qebehsenuef!" },
                    },
                },
            },
        };

        private static TrialDefinition Hunger() => new()
        {
            ML = 5, Step = 2, Name = "Ma'atis' Hunger", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(40877, 44376, 13328, 3072),
            StarterName = "Embalmer of Duamutef", StarterModel = MummyModel,
            Intro = "The echo of Duamutef guards the jar of the stomach and he is always hungry. Wound him and he will shrink away into a swarm of scarabs that feed him. Crush them quickly or he will return as whole as he began.",
            Victory = "The jar of the stomach is yours. Its keeping is recorded, and Ammut's chamber will know you carry it.",
            Replaces = new[] { "Echo of Duamutef" },
            TimeLimitSeconds = 1500,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The Echo of Duamutef turns toward you.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Echo of Duamutef", Model = 1047, Level = 65, Size = 100, Health = 28000, DamageFactor = 1.1, Spread = 200, Tag = "duamutef", MeleeDamage = eDamageType.Slash },
                    },
                    OnTick = DuamutefTick,
                },
            },
        };

        private static TrialDefinition Breath() => new()
        {
            ML = 5, Step = 3, Name = "Ma'atis' Breath", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(27973, 24449, 14864, 1001),
            StarterName = "Embalmer of Hapy", StarterModel = MummyModel,
            Intro = "The echo of Hapy keeps the jar of the lungs. When hurt she breaks into hollow copies of herself. They are weak, so cut them down. Each copy that outlasts its strength flows back into her.",
            Victory = "The jar of the lungs is yours. Its keeping is recorded, and Ammut's chamber will know you carry it.",
            Replaces = new[] { "Echo of Hapy" },
            TimeLimitSeconds = 1500,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The Echo of Hapy lowers her head to meet you.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Echo of Hapy", Model = 1177, Level = 65, Size = 50, Health = 24000, DamageFactor = 1.1, Spread = 200, Tag = "hapy", MeleeDamage = eDamageType.Slash },
                    },
                    OnTick = HapyTick,
                },
            },
        };

        private static TrialDefinition Blood() => new()
        {
            ML = 5, Step = 4, Name = "Ma'atis' Blood", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(35214, 46388, 13328, 1991),
            StarterName = "Embalmer of Imsety", StarterModel = MummyModel,
            Intro = "The echo of Imsety is frail, and he knows it. He keeps the jar of the liver by calling lions out of the walls for as long as he lives. Do not linger. The longer he stands, the more of them will hunt you.",
            Victory = "The jar of the liver is yours. Its keeping is recorded, and Ammut's chamber will know you carry it.",
            Replaces = new[] { "Echo of Imsety" },
            TimeLimitSeconds = 1200,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The Echo of Imsety calls out, and something answers from the walls.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Echo of Imsety", Model = 1172, Level = 65, Size = 50, Health = 16000, DamageFactor = 1.0, Spread = 200, Tag = "imsety" },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 5, Damage = 140, Radius = 400, SourceTag = "lion", DamageType = eDamageType.Heat },
                    },
                    OnTick = ImsetyTick,
                },
            },
        };

        private static TrialDefinition Reflection() => new()
        {
            ML = 5, Step = 5, Name = "Ma'ati's Reflection", Scope = TrialScope.Group, Zone = TrialZone.Oceanus,
            Anchor = new TrialPoint(234262, 400048, 9108, 3060),
            StarterName = "Mirror Seeker", StarterModel = MauModel,
            Intro = "Two great crocodiles lie either side of the Necropolis door. The mirror of Ra was fed to one of them long ago, and it still throws back what strikes it. Open up the first, then cross the entrance and find the second.",
            Victory = "The mirror of Ra comes free, and the light on the sand goes still.",
            Replaces = new[] { "Cau Surae" },
            TimeLimitSeconds = 1200,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Cau Surae rises from the sand.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Cau Surae", Model = 1260, Level = 64, Size = 200, Health = 15000, DamageFactor = 1.0, Spread = 400, MeleeDamage = eDamageType.Crush },
                    },
                },
                new TrialPhase
                {
                    Announce = "Nothing in its belly. The second crocodile stirs south of the door, and light glints between its teeth.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Cau Surae", Model = 1260, Level = 64, Size = 200, Health = 15000, DamageFactor = 1.0, At = new TrialPoint(234229, 403299, 9108, 3072), Reflect = 0.1, MeleeDamage = eDamageType.Crush },
                    },
                },
            },
        };

        private static TrialDefinition Preservation() => new()
        {
            ML = 5, Step = 6, Name = "Ma'atis' Preservation", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(31227, 55077, 8848),
            StarterName = "Keeper of the Resin", StarterModel = MummyModel,
            Intro = "The bound ones here were sealed with the resin that preserves. It passes from each that falls to the next, and whichever stands last holds all of it and fights with all of its strength. Finish them and the resin is yours.",
            Victory = "The last of the bound ones falls and you take up the Resin of the Ways. Its keeping is recorded, and Mahaf will know it.",
            TimeLimitSeconds = 1200,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The bound ones stir and turn their wrapped faces to you.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "bound zaubak", Model = MummyModel, Level = 65, Health = 5000, DamageFactor = 1.0, Count = 4, Spread = 250, Tag = "bound" },
                        new TrialMobSpec { Name = "bound zauemia ruinetu", Model = MummyModel, Level = 65, Health = 6000, DamageFactor = 1.0, Spread = 100, Tag = "bound" },
                    },
                    OnTick = ResinTick,
                },
            },
        };

        private static TrialDefinition Mask() => new()
        {
            ML = 5, Step = 7, Name = "Ma'atis' Mask", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(35213, 58989, 8848),
            StarterName = "Keeper of the Mask", StarterModel = MummyModel,
            Intro = "The one who wears the mask cannot be touched while the bound ones around it stand. Break the ring around it first. You will need that mask before you can face Ammut.",
            Victory = "The mask lifts away in your hands: the Mask of the Ways. Its keeping is recorded, and Mahaf will know it.",
            TimeLimitSeconds = 1200,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The masked one stands untouched while its circle closes on you.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "bound zaubak", Model = MummyModel, Level = 65, Health = 5000, DamageFactor = 1.0, Count = 4, Spread = 300, Tag = "bound" },
                        new TrialMobSpec { Name = "bound zauemia ruinetu", Model = MummyModel, Level = 66, Size = 60, Health = 8000, DamageFactor = 1.1, Spread = 100, Immune = true, Tag = "mask" },
                    },
                    OnTick = MaskTick,
                },
            },
        };

        private static TrialDefinition Wrap() => new()
        {
            ML = 5, Step = 8, Name = "Ma'atis' Wrap", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(39723, 55141, 8848),
            StarterName = "Keeper of the Wrap", StarterModel = MummyModel,
            Intro = "The wrappings you need are wound around the one at the back of this chamber, and the others will not let you reach it. They come in two waves. Hold together until it steps forward.",
            Victory = "You unwind the Wrap of the Ways from what is left. Its keeping is recorded, and Mahaf will know it.",
            TimeLimitSeconds = 1200,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The first of the bound ones lurch forward.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "bound zaubak", Model = MummyModel, Level = 65, Health = 4500, DamageFactor = 1.0, Count = 3, Spread = 250 },
                    },
                },
                new TrialPhase
                {
                    Announce = "More of them drag themselves out of the dark.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "bound zaubak", Model = MummyModel, Level = 65, Health = 4500, DamageFactor = 1.0, Count = 3, Spread = 250 },
                    },
                },
                new TrialPhase
                {
                    Announce = "The wrapped one comes forward at last, trailing its bandages.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "bound zauemia ruinetu", Model = MummyModel, Level = 66, Size = 60, Health = 9000, DamageFactor = 1.2, Spread = 100 },
                    },
                },
            },
        };

        private static TrialDefinition Token() => new()
        {
            ML = 5, Step = 9, Name = "Token", Scope = TrialScope.Group, Zone = TrialZone.Maati,
            Anchor = new TrialPoint(37560, 30208, 15493, 1137),
            StarterName = "Mahaf", StarterModel = MummyModel,
            Intro = "I ferry only the dead, or those who pass for them. You carry the resin, the mask and the wrap; your deeds speak for them. Go back past the Fire Guardian and the lost, down the stair of snakes, and lie on the bier. Then come and drink from my river, and carry the poison to the fountain before it finishes you.",
            Victory = "The fountain draws the poison out of you, and the token of the river is yours.",
            RequiresSteps = new[] { 6, 7, 8 },
            Replaces = new[] { "Mahaf" },
            TimeLimitSeconds = 2400,
            LeashRange = 12000,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "The Fire Guardian bars the way by the entrance.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Fire Guardian", Model = 1047, Level = 66, Size = 87, Health = 12000, DamageFactor = 1.1, At = new TrialPoint(32686, 30074, 15502), Tag = "guardian", MeleeDamage = eDamageType.Slash },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 12, Damage = 160, Radius = 600, SourceTag = "guardian", DamageType = eDamageType.Heat },
                    },
                },
                new TrialPhase
                {
                    Announce = "The fire dies. The eternal lost drift through the room, drawn to the fountain on the west wall. Lead them to it and it will take them.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32942, 28822, 15688), Tag = "lost" },
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32881, 29107, 15608), Tag = "lost" },
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32574, 28569, 15589), Tag = "lost" },
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32938, 28551, 15560), Tag = "lost" },
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32475, 29244, 15586), Tag = "lost" },
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32756, 28325, 15589), Tag = "lost" },
                        new TrialMobSpec { Name = "Fountain of the Lost", Model = LightModel, Size = 40, Objective = true, Required = false, ObjectiveText = "The water is cold and still. Bring the lost here.", At = Fountain, Tag = "well", OnDeath = (_, well) => well.Delete() },
                    },
                    OnTick = LostTick,
                },
                new TrialPhase
                {
                    Announce = "Beyond the room, jackal-headed guards hold the river bridge. Pull them east along the water.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "an-uat hesen neteri", Model = 1046, Level = 60, Health = 4000, DamageFactor = 0.9, At = new TrialPoint(36938, 28007, 15504), MeleeDamage = eDamageType.Slash },
                        new TrialMobSpec { Name = "an-uat hesen neteri", Model = 1046, Level = 60, Health = 4000, DamageFactor = 0.9, At = new TrialPoint(36939, 27885, 15487), MeleeDamage = eDamageType.Slash },
                        new TrialMobSpec { Name = "an-uat merzaue", Model = 1047, Level = 63, Health = 5000, DamageFactor = 1.0, At = new TrialPoint(36970, 27816, 15487), MeleeDamage = eDamageType.Slash },
                    },
                    OnStart = run => Clear(run, "well"),
                },
                new TrialPhase
                {
                    Announce = "The stairwell hisses. Snakes are summoned onto every step.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "summoned cobra", Model = 1234, Level = 60, Health = 2200, DamageFactor = 0.7, At = new TrialPoint(35348, 34189, 15012), Spread = 150, MeleeDamage = eDamageType.Thrust },
                        new TrialMobSpec { Name = "summoned cobra", Model = 1234, Level = 60, Health = 2200, DamageFactor = 0.7, At = new TrialPoint(35200, 34000, 15012), MeleeDamage = eDamageType.Thrust },
                        new TrialMobSpec { Name = "summoned cobra", Model = 1234, Level = 60, Health = 2200, DamageFactor = 0.7, At = new TrialPoint(35500, 34350, 15012), MeleeDamage = eDamageType.Thrust },
                        new TrialMobSpec { Name = "summoned cobra", Model = 1234, Level = 60, Health = 2200, DamageFactor = 0.7, At = new TrialPoint(35520, 37538, 13456), MeleeDamage = eDamageType.Thrust },
                    },
                },
                new TrialPhase
                {
                    Announce = "The stair is clear. Find the bier at its foot and lie down. One of you lying there speaks for all.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Bier of the Ways", Model = ItemModel, Size = 60, Objective = true, At = new TrialPoint(35520, 37538, 13456), ObjectiveText = "Resin, mask and wrap close around you, and you rise as one of the dead." },
                    },
                },
                new TrialPhase
                {
                    Announce = "You walk as the dead walk. Go back to the dock, and take the water Mahaf offers.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Poisoned Waters", Model = LightModel, Size = 40, Objective = true, At = Dock, ObjectiveText = "You drink. It tastes of rot, and then it starts to burn. Do not cure this." },
                    },
                },
                new TrialPhase
                {
                    Announce = "The poison is in you. Run back to the fountain of the lost and jump in before it kills you!",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Fountain of the Lost", Model = LightModel, Size = 40, Objective = true, At = Fountain, Tag = "fountain", ObjectiveText = "The fountain closes over you and the burning stops." },
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32942, 28822, 15688), Required = false, Tag = "lost" },
                        new TrialMobSpec { Name = "eternal lost", Model = MummyModel, Level = 62, Health = 2500, DamageFactor = 0.7, At = new TrialPoint(32574, 28569, 15589), Required = false, Tag = "lost" },
                    },
                    Pulses =
                    {
                        new TrialPulse { IntervalSeconds = 6, Damage = 60, Radius = 12000, SourceTag = "fountain", DamageType = eDamageType.Body, Message = "The river's poison burns in your blood." },
                    },
                    OnTick = LostTick,
                },
            },
        };

        private static TrialDefinition Appetite() => new()
        {
            ML = 5, Step = 10, Name = "Ammut's Appetite", Scope = TrialScope.Raid, Zone = TrialZone.Maati,
            Anchor = Dock,
            StarterName = "Aken", StarterModel = MummyModel,
            Intro = "You bear the river's token, so I will row you to the one who eats the unworthy. The four canopic jars you stole wait for you in her temple, for your deeds carried them there. Break the liver to heal, the lungs to turn aside her judgement, the stomach to clear crocodiles, the intestines to clear anubites. When she names someone, stand clear of them.",
            Victory = "Ammut falls, and the river carries you back in silence.",
            Replaces = new[] { "Ammut", "Aken" },
            TimeLimitSeconds = 2100,
            LeashRange = 20000,
            Phases =
            {
                new TrialPhase
                {
                    Announce = "Aken pushes off from the dock. The dark water carries you to the temple of Ammut.",
                    SurviveSeconds = 6,
                    OnStart = run => MoveParty(run, TempleLanding),
                },
                new TrialPhase
                {
                    Announce = "Ammut raises her head from the scales. Your jars stand ready beside you.",
                    Mobs =
                    {
                        new TrialMobSpec { Name = "Ammut", Model = 1049, Level = 70, Size = 90, Health = 110000, DamageFactor = 1.4, At = AmmutRow, Tag = "ammut", MeleeDamage = eDamageType.Crush },
                        Jars[0], Jars[1], Jars[2], Jars[3],
                    },
                    OnTick = AmmutTick,
                },
                new TrialPhase
                {
                    Announce = "Aken's boat bumps against the temple steps and carries you home.",
                    OnStart = run => MoveParty(run, Dock),
                    Done = run => true,
                },
            },
        };

        /// <summary>How many of the given health marks a monster has fallen to or past.</summary>
        public static int PassedThresholds(int healthPercent, int[] thresholds) => thresholds.Count(mark => healthPercent <= mark);

        /// <summary>Health a swarm feeds Duamutef each second.</summary>
        public static int ScarabHeal(int scarabs, int maxHealth) => scarabs * maxHealth / 400;

        /// <summary>Health each copy that outlasts its strength gives back to Hapy.</summary>
        public static int HapyCopyHeal(int maxHealth) => maxHealth * 4 / 100;

        public static bool Near(GameObject mob, TrialPoint point, int radius)
        {
            long x = mob.X - point.X;
            long y = mob.Y - point.Y;
            return x * x + y * y <= (long)radius * radius;
        }

        /// <summary>True once each <paramref name="seconds"/> calls. Hooks tick once a second, so this is a timer.</summary>
        public static bool Every(TrialRun run, string key, int seconds)
        {
            int count = run.Get<int>(key) + 1;
            run.Set(key, count >= seconds ? 0 : count);
            return count >= seconds;
        }

        public static IEnumerable<GameLiving> Party(TrialRun run) =>
            run.Players.Cast<GameLiving>().Concat(run.Leader.Group?.GetMembersInTheGroup() ?? Enumerable.Empty<GameLiving>()).Distinct().ToList();

        public static void MoveParty(TrialRun run, TrialPoint point)
        {
            foreach (GameLiving member in Party(run).Where(member => member.IsAlive))
                member.MoveTo(run.Starter.CurrentRegionID, point.X, point.Y, point.Z, point.Heading);
        }

        public static GameLiving RandomHostile(TrialRun run, GameObject center, int radius)
        {
            List<GameLiving> targets = run.Hostiles(center, radius).ToList();
            return targets.Count == 0 ? null : targets[Util.Random(targets.Count - 1)];
        }

        public static void Strike(TrialRun run, GameLiving source, GameLiving target, int damage, eDamageType type) =>
            target.TakeDamage(source, type, (int)(damage * run.DamageScale), 0);

        public static void Clear(TrialRun run, string tag)
        {
            foreach (TrialMob mob in run.Mobs(tag).ToList())
                mob.Delete();
        }

        private static TrialMobSpec Jar(string name, string tag, TrialPoint at, string text, Action<TrialRun, TrialMob> use) => new()
        {
            Name = name, Model = ItemModel, Size = 27, Objective = true, Required = false, At = at, Tag = tag, ObjectiveText = text,
            OnDeath = (run, jar) =>
            {
                use(run, jar);
                jar.Delete();
            },
        };

        private static void MendParty(TrialRun run, TrialMob jar)
        {
            foreach (GameLiving member in Party(run).Where(member => member.IsAlive))
                member.Health = member.MaxHealth;
        }

        private static void DuamutefTick(TrialRun run)
        {
            TrialMob echo = run.Mobs("duamutef").FirstOrDefault();
            if (echo == null)
                return;

            if (!run.Get<bool>("swarm"))
            {
                if (PassedThresholds(echo.HealthPercent, DuamutefSplits) <= run.Get<int>("splits"))
                    return;
                run.Set("swarm", true);
                echo.Immune = true;
                echo.Size = 30;
                run.Tell("The Echo of Duamutef shrinks away into a swarm of scarabs!");
                run.Spawn(Scarab);
                return;
            }

            int scarabs = run.Mobs("scarab").Count();
            if (scarabs > 0)
            {
                echo.ChangeHealth(echo, eHealthChangeType.Regenerate, ScarabHeal(scarabs, echo.MaxHealth));
                return;
            }

            run.Set("swarm", false);
            run.Set("splits", PassedThresholds(echo.HealthPercent, DuamutefSplits));
            echo.Immune = false;
            echo.Size = 100;
            run.Tell("With its swarm gone, the Echo of Duamutef swells back to full size.");
        }

        private static void HapyTick(TrialRun run)
        {
            TrialMob hapy = run.Mobs("hapy").FirstOrDefault();
            if (hapy == null)
                return;

            if (!run.Get<bool>("split"))
            {
                if (PassedThresholds(hapy.HealthPercent, HapySplits) <= run.Get<int>("splits"))
                    return;
                run.Set("split", true);
                run.Set("copyAge", 0);
                hapy.Immune = true;
                hapy.Flags |= GameNPC.eFlags.GHOST;
                run.Tell("The Echo of Hapy fades, and hollow copies of her step out of the air!");
                run.Spawn(HapyCopy);
                return;
            }

            List<TrialMob> copies = run.Mobs("hapycopy").ToList();
            int age = run.Get<int>("copyAge") + 1;
            run.Set("copyAge", age);
            if (copies.Count > 0 && age >= HapyCopySeconds)
            {
                hapy.ChangeHealth(hapy, eHealthChangeType.Regenerate, copies.Count * HapyCopyHeal(hapy.MaxHealth));
                Clear(run, "hapycopy");
                run.Tell("The last copies run out of strength and flow back into the Echo of Hapy.");
                copies.Clear();
            }

            if (copies.Count > 0)
                return;
            run.Set("split", false);
            run.Set("splits", PassedThresholds(hapy.HealthPercent, HapySplits));
            hapy.Immune = false;
            hapy.Flags &= ~GameNPC.eFlags.GHOST;
            run.Tell("The Echo of Hapy stands solid again.");
        }

        private static void ImsetyTick(TrialRun run)
        {
            if (Every(run, "lion", 18) && run.Mobs("lion").Count() < 4)
            {
                run.Tell("A lion pads out of the wall at the Echo of Imsety's call.");
                run.Spawn(Lion);
            }
        }

        private static void ResinTick(TrialRun run)
        {
            List<TrialMob> left = run.Mobs("bound").ToList();
            if (left.Count != 1 || run.Get<bool>("hardened"))
                return;
            run.Set("hardened", true);
            left[0].DamageFactor *= 1.4;
            run.Tell($"All of the resin flows into the last {left[0].Name}, and it hardens!");
        }

        private static void MaskTick(TrialRun run)
        {
            if (run.Get<bool>("unmasked") || run.Mobs("bound").Any())
                return;
            run.Set("unmasked", true);
            run.SetImmune("mask", false);
            run.Tell("The circle is broken. The masked one can be hurt!");
        }

        private static void LostTick(TrialRun run)
        {
            foreach (TrialMob lost in run.Mobs("lost").Where(mob => Near(mob, Fountain, FountainReach)).ToList())
            {
                run.Tell("The fountain takes one of the lost.");
                lost.Die(run.Leader);
            }
        }

        private static void AmmutTick(TrialRun run)
        {
            TrialMob ammut = run.Mobs("ammut").FirstOrDefault();
            if (ammut == null)
                return;

            int age = run.Get<int>("ammutAge") + 1;
            run.Set("ammutAge", age);
            if (age == run.Definition.TimeLimitSeconds - 20)
            {
                run.Tell("Time is short. Aken's boat comes to take you off the steps.");
                MoveParty(run, Dock);
                return;
            }

            if (Every(run, "adds", 20))
            {
                if (run.Mobs("anubis").Count() < 3)
                    run.Spawn(Anubis);
                if (run.Mobs("croc").Count() < 3)
                    run.Spawn(Crocodile);
            }

            foreach (TrialMobSpec jar in Jars)
            {
                if (!run.Mobs(jar.Tag).Any() && Every(run, jar.Tag, JarReturnSeconds))
                    run.Spawn(jar);
            }

            Judge(run, ammut);
        }

        private static void Judge(TrialRun run, TrialMob ammut)
        {
            GameLiving judged = run.Get<GameLiving>("judged");
            if (judged == null)
            {
                if (!Every(run, "judgement", JudgementSeconds))
                    return;
                judged = RandomHostile(run, ammut, 3000);
                if (judged == null)
                    return;
                run.Set("judged", judged);
                run.Set("sentence", JudgementWarningSeconds);
                run.Tell($"Ammut weighs {judged.Name} and finds them wanting! Stand clear of {judged.Name}!");
                return;
            }

            int sentence = run.Get<int>("sentence") - 1;
            run.Set("sentence", sentence);
            if (sentence > 0)
                return;

            run.Set("judged", null);
            if (run.Get<bool>("ward"))
            {
                run.Set("ward", false);
                run.Tell("The breath of the lungs jar turns Ammut's judgement aside.");
                return;
            }

            run.Tell($"Ammut's judgement falls on {judged.Name}!");
            foreach (GameLiving target in run.Hostiles(judged, 350))
                Strike(run, ammut, target, 300, eDamageType.Heat);
        }
    }
}
