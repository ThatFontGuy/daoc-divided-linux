using System;
using System.Collections.Generic;
using System.Linq;
using DOL.Database;
using DOL.Events;
using DOL.GS.PacketHandler;
using DOL.GS.Styles;

namespace DOL.GS
{
    /// <summary>
    /// A character from the player's own account, summoned as a party bot. It behaves like a
    /// /spawn companion in the party (follow, assist, heal, BAF) but wears its real equipment,
    /// earns real experience and loot, trains its own specializations, and writes all of it back
    /// to its character so it can be logged in and played as normal.
    /// </summary>
    public partial class GameBot
    {
        private const int CompanionAutosaveMilliseconds = 120_000;

        private ECSGameTimer _companionAutosaveTimer;
        private bool _companionDirty;
        private bool _companionFinished;
        // Set once the companion has joined the owner's group. A summon that fails before then
        // is released without writing anything to the character.
        private bool _companionJoined;

        public bool IsAccountCompanion { get; private set; }
        public DbCoreCharacter CompanionCharacter { get; private set; }
        internal AccountCompanionRecord CompanionRecord { get; private set; }
        public string CompanionCharacterId => CompanionCharacter?.ObjectId;

        public GameBot(GamePlayer owner, DbCoreCharacter character, AccountCompanionRecord record)
        {
            Owner = owner ?? throw new ArgumentNullException(nameof(owner));
            CompanionCharacter = character ?? throw new ArgumentNullException(nameof(character));
            CompanionRecord = record ?? throw new ArgumentNullException(nameof(record));
            IsAccountCompanion = true;
            // Party behavior (follow, assist, healing priorities, BAF, stable travel) is the
            // /spawn companion's. Every place that would discard or regenerate a /spawn
            // helper checks IsAccountCompanion first.
            IsTemporaryGroupHelper = true;
            ClassId = (byte)character.Class;
            RaceId = (byte)character.Race;
            GenderId = (byte)character.Gender;
            ClassName = BotManager.GetClassNameById(ClassId);
            InternalID = AccountCompanionManager.InternalIdFor(character.ObjectId);
            _dummyClient = new BotDummyClient();
            _dummyLib = new BotDummyPacketLib();

            if (!SetCharacterClass(ClassId))
                throw new InvalidOperationException($"Failed to set character class {ClassId} for companion {character.Name}.");
            SetRaceAndRealm(owner);
            // The character's own identity always wins over the bot's random choices.
            Race = (short)character.Race;
            Gender = character.Gender == (int)eGender.Female ? eGender.Female : eGender.Male;
            int model = character.CurrentModel > 0 ? character.CurrentModel : character.CreationModel;
            if (AccountCompanionRules.NpcModel(model) > 0)
                Model = AccountCompanionRules.NpcModel(model);
            Realm = (eRealm)character.Realm;
            Size = AccountCompanionRules.NpcSize(model);
            Level = (byte)Math.Clamp(character.Level, 1, AccountCompanionRules.MaxLevel);
            _creationModel = Model;
            Name = character.Name;
            MaxSpeedBase = GamePlayer.PLAYER_BASE_SPEED;

            InitializeBotStats();
            LoadClassSpecializations(false);
            LoadPersistedSpecs(character.SerializedSpecs);
            BotSpec = ResolveCompanionBuild();
            Experience = Math.Max(0, character.Experience);
            RefreshSpecDependantSkills(false);
            SetBotSpells();
            SortStyles();
            SortSpells();

            // The character's own inventory rows: equipment, backpack and vault. No item is
            // generated for an account companion.
            var inventory = new BotInventory(character.ObjectId);
            inventory.LoadFromDatabase(character.ObjectId);
            Inventory = inventory;
            RefreshItemBonuses();

            Health = character.Health > 0 ? Math.Min(character.Health, MaxHealth) : MaxHealth;
            Mana = Math.Clamp(character.Mana, 0, MaxMana);
            Endurance = character.Endurance > 0 ? Math.Min(character.Endurance, MaxEndurance) : MaxEndurance;
            RespawnInterval = -1;

            var brain = new DOL.AI.Brain.BotBrain();
            brain.IsHealer = IsHealerClass();
            SetOwnBrain(brain);
            InitControlledBrainArray(1);

            GameEventMgr.AddHandler(Owner, GamePlayerEvent.Quit, new DOLEventHandler(OnOwnerQuit));
            GameEventMgr.AddHandler(Owner, GamePlayerEvent.RegionChanged, new DOLEventHandler(OnOwnerRegionChanged));
        }

        /// <summary>
        /// Keeps the saved plan if there is one; otherwise picks, from the class's normal bot
        /// builds, the one closest to what the character already trained, and remembers it.
        /// </summary>
        private BotSpec ResolveCompanionBuild()
        {
            eCharacterClass characterClass = (eCharacterClass)ClassId;
            IReadOnlyList<eSpecType> choices = BotSpec.GetSpecializationChoices(characterClass);
            BotSpec saved = BotSpec.GetSpec(characterClass, choices[0]);
            if (saved != null && BotLifetimeBuild.Restore(saved, CompanionRecord.BuildPlan))
                return saved;

            bool hasStyle = Enum.TryParse(CompanionRecord.Style, true, out eSpecType wanted) && choices.Contains(wanted);
            BotSpec best = null;
            int bestFit = -1;
            foreach (eSpecType choice in choices)
            {
                if (hasStyle && choice != wanted)
                    continue;
                // Builds include random weapon and variance rolls. Several rolls give the
                // best match a fair chance to appear.
                for (int roll = 0; roll < 8; roll++)
                {
                    BotSpec candidate = BotSpec.GetSpec(characterClass, choice);
                    if (candidate == null)
                        continue;
                    BotLifetimeBuild.AlignWithInvestedWeapons(candidate, GetBaseSpecLevel);
                    int fit = AccountCompanionRules.PlanFit(PlanLines(candidate), GetBaseSpecLevel);
                    if (fit > bestFit)
                    {
                        best = candidate;
                        bestFit = fit;
                    }
                }
            }

            if (best != null)
            {
                CompanionRecord.BuildPlan = BotLifetimeBuild.Encode(best);
                CompanionRecord.Dirty = true;
            }
            return best;
        }

        private static IEnumerable<AccountCompanionRules.PlanLine> PlanLines(BotSpec plan) =>
            plan?.SpecLines?.Select(line => new AccountCompanionRules.PlanLine(line.Spec, (int)line.SpecCap, line.levelRatio))
            ?? Enumerable.Empty<AccountCompanionRules.PlanLine>();

        private bool CompanionSecondStage =>
            AccountCompanionRules.IsSecondStage(Level, Experience, GamePlayer.GetExperienceAmountForLevel);

        /// <summary>Points the character has earned but not spent, counted the way the player's own sheet counts them.</summary>
        internal int CompanionUnspentSpecPoints()
        {
            if (CharacterClass == null)
                return 0;
            var autotrain = new HashSet<string>(CharacterClass.GetAutotrainableSkills() ?? new List<string>(), StringComparer.OrdinalIgnoreCase);
            int earned = AccountCompanionRules.EarnedSpecPoints(Level, CompanionSecondStage, CharacterClass.SpecPointsMultiplier);
            int spent = AccountCompanionRules.SpentSpecPoints(
                GetSpecList().Where(spec => spec.Trainable).Select(spec => (spec.Level, autotrain.Contains(spec.KeyName))), Level);
            return earned - spent;
        }

        /// <summary>Spends free specialization points along the companion's build. Never lowers a line.</summary>
        internal bool AutoTrainCompanion()
        {
            if (!IsAccountCompanion || BotSpec == null || CharacterClass == null)
                return false;
            int available = CompanionUnspentSpecPoints();
            if (available <= 0)
                return false;

            List<Specialization> trainable = GetSpecList().Where(spec => spec.Trainable).ToList();
            var current = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            foreach (Specialization spec in trainable)
                current[spec.KeyName] = spec.Level;
            var autotrain = CharacterClass.GetAutotrainableSkills()?.ToList() ?? new List<string>();
            Dictionary<string, int> trained = AccountCompanionRules.Spend(current, autotrain, PlanLines(BotSpec), Level, available, out _);

            var raised = new List<string>();
            foreach (Specialization spec in trainable)
            {
                if (trained.TryGetValue(spec.KeyName, out int level) && level > spec.Level)
                {
                    raised.Add($"{spec.Name} {level}");
                    spec.Level = level;
                }
            }
            if (raised.Count == 0)
                return false;

            RefreshSpecDependantSkills(false);
            SetBotSpells();
            SortStyles();
            SortSpells();
            _companionDirty = true;
            Owner?.Out.SendMessage($"{Name} trains: {string.Join(", ", raised)}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            return true;
        }

        /// <summary>On: free points are spent along the build at every level. Off (the default): the owner trains by hand.</summary>
        internal bool CompanionAutoSpend => CompanionRecord?.AutoTrain == true;

        internal void SetCompanionAutoSpend(bool on)
        {
            if (CompanionRecord == null || CompanionRecord.AutoTrain == on)
                return;
            CompanionRecord.AutoTrain = on;
            CompanionRecord.Dirty = true;
            _companionDirty = true;
            if (on)
                AutoTrainCompanion();
            SaveAccountCompanion("autospend");
        }

        /// <summary>The lines the owner can train, in the class's own order.</summary>
        internal List<Specialization> CompanionTrainableLines() =>
            GetSpecList().Where(spec => spec.Trainable).ToList();

        internal bool IsCompanionAutotrainLine(Specialization spec) =>
            CharacterClass?.GetAutotrainableSkills()?.Any(key => string.Equals(key, spec.KeyName, StringComparison.OrdinalIgnoreCase)) == true;

        /// <summary>Raises one line by up to <paramref name="steps"/> levels with free points, as at a trainer.</summary>
        internal string TrainCompanionLine(string lineName, int steps)
        {
            if (!IsAccountCompanion || CharacterClass == null)
                return "Only an account companion can be trained this way.";
            Specialization spec = CompanionTrainableLines().FirstOrDefault(line =>
                string.Equals(line.Name, lineName?.Trim(), StringComparison.OrdinalIgnoreCase) ||
                string.Equals(line.KeyName, lineName?.Trim(), StringComparison.OrdinalIgnoreCase));
            if (spec == null)
                return $"{Name} has no line called '{lineName}'.";

            int limit = AccountCompanionRules.LineLimit(Level);
            if (spec.Level >= limit)
                return $"{Name}'s {spec.Name} is already {spec.Level}, the most at level {Level}.";

            int available = CompanionUnspentSpecPoints();
            bool autotrain = IsCompanionAutotrainLine(spec);
            int trained = AccountCompanionRules.TrainLine(spec.Level, Math.Max(1, steps), autotrain, Level, available, out int cost);
            if (trained == spec.Level)
                return $"{Name} needs {AccountCompanionRules.NextLevelCost(spec.Level, autotrain, Level)} points for {spec.Name} {spec.Level + 1} and has {available}.";

            spec.Level = trained;
            RefreshSpecDependantSkills(false);
            SetBotSpells();
            SortStyles();
            SortSpells();
            _companionDirty = true;
            SaveAccountCompanion("train");
            if (log.IsInfoEnabled)
                log.Info($"ACCOUNT_COMPANION_TRAINED companion=\"{Name}\" line=\"{spec.KeyName}\" level={trained} cost={cost}");
            return $"{Name} trains {spec.Name} to {trained} ({cost} points). {available - cost} points left.";
        }

        /// <summary>Lines a respec would lower: above 1, or above an autotrain line's free levels.</summary>
        internal bool CanRespecCompanionLine(Specialization spec) =>
            spec.Level > AccountCompanionRules.RespecLevel(IsCompanionAutotrainLine(spec), Level);

        /// <summary>Why a respec has to wait, or null. Changing lines mid-fight or mid-cast could leave a stale spell or style in use.</summary>
        internal string CompanionRespecRefusal()
        {
            if (!IsAccountCompanion || CharacterClass == null)
                return "Only an account companion can be respecced this way.";
            if (!IsAlive)
                return $"{Name} must be alive to respec.";
            if (InCombat || IsCasting || IsAttacking)
                return $"{Name} is fighting. Respec it once the fight is over.";
            return null;
        }

        /// <summary>
        /// Free respec of one line or every line ("all"), as /respec at a trainer: each line goes back to 1
        /// (an autotrain line to its free levels) and the points become free to spend again.
        /// </summary>
        internal string RespecCompanion(string lineName)
        {
            string refusal = CompanionRespecRefusal();
            if (refusal != null)
                return refusal;

            bool all = string.Equals(lineName?.Trim(), "all", StringComparison.OrdinalIgnoreCase);
            List<Specialization> lines = CompanionTrainableLines()
                .Where(spec => all ||
                               string.Equals(spec.Name, lineName?.Trim(), StringComparison.OrdinalIgnoreCase) ||
                               string.Equals(spec.KeyName, lineName?.Trim(), StringComparison.OrdinalIgnoreCase))
                .ToList();
            if (lines.Count == 0)
                return $"{Name} has no line called '{lineName}'.";
            lines = lines.Where(CanRespecCompanionLine).ToList();
            if (lines.Count == 0)
                return all ? $"{Name} has nothing to respec." : $"{Name}'s {lineName} has no trained levels to give back.";

            int refunded = 0;
            foreach (Specialization spec in lines)
                refunded += LowerCompanionLine(spec);

            // Re-adds what the remaining levels still grant, then rebuilds the spell and style choices.
            RefreshSpecDependantSkills(false);
            GetAllUsableSkills(true);
            GetAllUsableListSpells(true);
            SetBotSpells();
            SortStyles();
            SortSpells();
            _companionDirty = true;
            SaveAccountCompanion("respec");
            if (log.IsInfoEnabled)
                log.Info($"ACCOUNT_COMPANION_RESPEC companion=\"{Name}\" lines=\"{string.Join(",", lines.Select(spec => spec.KeyName))}\" refunded={refunded}");
            string what = all ? "every line" : lines[0].Name;
            return $"{Name} respecs {what}: {refunded} points back, {CompanionUnspentSpecPoints()} free to spend.";
        }

        /// <summary>
        /// Lowers one line and takes away what only its lost levels granted. The bot's skill refresh
        /// only ever adds, so abilities and styles of the line are removed here and re-added by the
        /// caller's refresh at the levels still trained.
        /// </summary>
        private int LowerCompanionLine(Specialization spec)
        {
            bool autotrain = IsCompanionAutotrainLine(spec);
            int target = AccountCompanionRules.RespecLevel(autotrain, Level);
            int refund = AccountCompanionRules.RespecRefund(spec.Level, autotrain, Level);
            List<Ability> oldAbilities = spec.GetAbilitiesForLiving(this) ?? new List<Ability>();
            List<Style> oldStyles = spec.GetStylesForLiving(this) ?? new List<Style>();

            spec.Level = target;

            var lostStyles = new HashSet<int>(oldStyles.Select(style => style.ID));
            lostStyles.ExceptWith((spec.GetStylesForLiving(this) ?? new List<Style>()).Select(style => style.ID));
            foreach (Ability ability in oldAbilities)
                RemoveAbility(ability.KeyName);
            lock (Styles)
                Styles.RemoveAll(style => style != null && lostStyles.Contains(style.ID));
            return refund;
        }

        /// <summary>Tells the owner about unspent points when the companion does not spend them itself.</summary>
        internal void RemindCompanionUnspentPoints()
        {
            if (CompanionAutoSpend || Owner?.Client?.ClientState is not GameClient.eClientState.Playing)
                return;
            int available = CompanionUnspentSpecPoints();
            if (available > 0)
                Owner.Out.SendMessage($"{Name} has {available} specialization points to spend. Type /companion spec {Name} to train.",
                    eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        private void GainAccountCompanionExperience(GainedExperienceEventArgs arguments)
        {
            if (Level >= AccountCompanionRules.MaxLevel)
                return;

            long gained = arguments.ExpTotal;
            if (arguments.AllowMultiply)
            {
                // The same multipliers a player character gets for the same kill.
                long baseExperience = arguments.ExpBase;
                gained -= baseExperience;
                double rate = ServerProperties.Properties.XP_RATE;
                if (CurrentRegion?.IsRvR == true || CurrentZone?.IsRvR == true)
                    rate *= ServerProperties.Properties.RvR_XP_RATE;
                baseExperience = (long)(baseExperience * rate);
                long itemBonus = GetModified(eProperty.XpPoints);
                if (itemBonus != 0)
                    baseExperience += baseExperience * itemBonus / 100;
                gained += baseExperience;
            }
            if (gained <= 0)
                return;

            byte previousLevel = Level;
            Experience += gained;
            _companionDirty = true;
            int newLevel = AccountCompanionRules.LevelForExperience(Level, Experience, GamePlayer.GetExperienceAmountForLevel);
            if (newLevel == previousLevel)
                return;

            Level = (byte)newLevel;
            ApplyLevelStatGrowth(Level);
            LoadClassSpecializations(false);
            RefreshSpecDependantSkills(false);
            if (CompanionAutoSpend)
                AutoTrainCompanion();
            SetBotSpells();
            SortStyles();
            SortSpells();
            Health = MaxHealth;
            Mana = MaxMana;
            Endurance = MaxEndurance;
            ShowCompanionLevelUp();
            RemindCompanionUnspentPoints();
            SaveAccountCompanion("level");
        }

        /// <summary>
        /// What a player's level-up shows: the new level on the nameplate and group window, the
        /// level-up sparkle for everyone nearby, the chime and the screen-center message.
        /// </summary>
        private void ShowCompanionLevelUp()
        {
            if (ObjectState is eObjectState.Active)
            {
                // The client reads an NPC's level only from its create packet.
                ClientService.CreateObjectForPlayers(this);
                foreach (GamePlayer player in GetPlayersInRadius(WorldMgr.VISIBILITY_DISTANCE))
                    player?.Out.SendEmoteAnimation(this, eEmote.LvlUp);
            }

            Group?.UpdateMember(this, false, false);
            Group?.UpdateGroupWindow();

            if (Owner?.Client?.ClientState is not GameClient.eClientState.Playing)
                return;
            // The only level-up sound packet plays on the owner's own character, who stands beside
            // the companion; it also refreshes the owner's monster con colors.
            Owner.Out.SendLevelUpSound();
            Owner.Out.SendMessage($"{Name} has reached level {Level}!", eChatType.CT_Important, eChatLoc.CL_SystemWindow);
            Owner.Out.SendMessage($"{Name} has reached level {Level}!", eChatType.CT_ScreenCenter, eChatLoc.CL_SystemWindow);
        }

        internal void StartCompanionAutosave()
        {
            _companionAutosaveTimer?.Stop();
            _companionAutosaveTimer = new ECSGameTimer(this, _ =>
            {
                if (_companionFinished || ObjectState is not eObjectState.Active)
                    return 0;
                if (_companionDirty)
                    SaveAccountCompanion("autosave");
                return CompanionAutosaveMilliseconds;
            }, CompanionAutosaveMilliseconds);
        }

        internal void MarkCompanionDirty() => _companionDirty = true;

        internal void MarkCompanionJoined() => _companionJoined = true;

        /// <summary>Called once from Delete: the last save, then the companion is released.</summary>
        private void FinishAccountCompanion()
        {
            if (_companionFinished)
                return;
            _companionFinished = true;
            _companionAutosaveTimer?.Stop();
            _companionAutosaveTimer = null;
            try
            {
                if (_companionJoined)
                    SaveAccountCompanion("dismiss");
            }
            finally
            {
                AccountCompanionManager.Unregister(this);
            }
        }

        /// <summary>
        /// Writes level, experience, stats, specializations, class, position and resources into
        /// the character row the login screen uses, then saves the character's inventory.
        /// </summary>
        internal bool SaveAccountCompanion(string reason)
        {
            if (!IsAccountCompanion || CompanionCharacter == null)
                return false;

            try
            {
                // The login screen plays the DbCoreCharacter cached on the account. Writing into
                // that same object means picking the character later never loads stale data.
                var targets = new List<DbCoreCharacter> { CompanionCharacter };
                DbCoreCharacter cached = Owner?.Client?.Account?.Characters?
                    .FirstOrDefault(character => character != null && character.ObjectId == CompanionCharacter.ObjectId);
                if (cached != null && !ReferenceEquals(cached, CompanionCharacter))
                    targets.Add(cached);

                foreach (DbCoreCharacter target in targets)
                    ApplyCompanionStateTo(target);

                bool saved;
                lock (AutonomousBotStatusPersistence.DatabaseWriteLock)
                {
                    saved = GameServer.Database.SaveObject(cached ?? CompanionCharacter);
                    if (Inventory is BotInventory inventory)
                        saved &= inventory.SaveIntoDatabase(CompanionCharacter.ObjectId);
                    if (CompanionRecord != null)
                    {
                        CompanionRecord.Dirty = true;
                        saved &= CompanionRecord.IsPersisted
                            ? GameServer.Database.SaveObject(CompanionRecord)
                            : GameServer.Database.AddObject(CompanionRecord);
                    }
                }

                if (saved)
                    _companionDirty = false;
                else if (log.IsWarnEnabled)
                    log.Warn($"ACCOUNT_COMPANION_SAVE_INCOMPLETE companion=\"{Name}\" reason={reason}");
                return saved;
            }
            catch (Exception exception)
            {
                if (log.IsErrorEnabled)
                    log.Error($"ACCOUNT_COMPANION_SAVE_FAILED companion=\"{Name}\" reason={reason}", exception);
                return false;
            }
        }

        private void ApplyCompanionStateTo(DbCoreCharacter target)
        {
            int previousLevel = target.Level;
            if (Level > previousLevel && CharacterClass != null)
            {
                (int primary, int secondary, int tertiary) = AccountCompanionRules.StatGains(previousLevel, Level);
                AddCharacterStat(target, CharacterClass.PrimaryStat, primary);
                AddCharacterStat(target, CharacterClass.SecondaryStat, secondary);
                AddCharacterStat(target, CharacterClass.TertiaryStat, tertiary);
            }

            target.Class = ClassId;
            target.Level = Level;
            target.Experience = Experience;
            target.IsLevelSecondStage = CompanionSecondStage;
            target.SerializedSpecs = AccountCompanionRules.MergeSerializedSpecs(target.SerializedSpecs,
                GetSpecList().Where(spec => spec.Trainable && spec.AllowSave).Select(spec => (spec.KeyName, spec.Level)));

            if (IsAlive && CurrentRegion != null && !CurrentRegion.IsInstance)
            {
                target.Region = CurrentRegionID;
                target.Xpos = X;
                target.Ypos = Y;
                target.Zpos = Z;
                target.Direction = Heading;
                target.Health = Math.Max(1, Health);
                target.Mana = Math.Max(0, Mana);
                target.Endurance = Math.Max(0, Endurance);
            }
            else if (!IsAlive && target.BindRegion > 0)
            {
                // A companion dismissed while dead is released, as a player logging out dead.
                target.Region = target.BindRegion;
                target.Xpos = target.BindXpos;
                target.Ypos = target.BindYpos;
                target.Zpos = target.BindZpos;
                target.Direction = target.BindHeading;
                target.Health = Math.Max(1, MaxHealth / 4);
            }
        }

        private static void AddCharacterStat(DbCoreCharacter character, eStat stat, int amount)
        {
            if (amount <= 0)
                return;
            switch (stat)
            {
                case eStat.STR: character.Strength += amount; break;
                case eStat.DEX: character.Dexterity += amount; break;
                case eStat.CON: character.Constitution += amount; break;
                case eStat.QUI: character.Quickness += amount; break;
                case eStat.INT: character.Intelligence += amount; break;
                case eStat.PIE: character.Piety += amount; break;
                case eStat.EMP: character.Empathy += amount; break;
                case eStat.CHR: character.Charisma += amount; break;
            }
        }

        /// <summary>
        /// Takes a dropped item only when it is a real upgrade for this companion, and wears it.
        /// The item it replaces goes into its backpack. Nothing is taken when the backpack is full.
        /// </summary>
        internal bool TryTakeCompanionUpgrade(DbInventoryItem item)
        {
            if (!IsAccountCompanion || !IsAlive || Inventory == null || item == null || item.IsStackable ||
                !AutonomousBotEconomy.TryGetEquipmentUpgrade(this, item, out eInventorySlot equipSlot))
                return false;

            eInventorySlot backpack = Inventory.FindFirstEmptySlot(eInventorySlot.FirstBackpack, eInventorySlot.LastBackpack);
            if (backpack == eInventorySlot.Invalid || !Inventory.AddItem(backpack, item))
                return false;
            if (!Inventory.MoveItem(backpack, equipSlot, 1))
            {
                // Kept in the backpack: still the companion's loot, saved with its character.
                _companionDirty = true;
                return true;
            }

            RefreshItemBonuses();
            if (CharacterClass?.ID == (int)eCharacterClass.Savage &&
                BotWeaponStats.IsMeleeWeapon((eObjectType)item.Object_Type))
                EnsureBotWeaponReady();
            _companionDirty = true;
            return true;
        }

        internal static int CompanionUpgradeValue(GameBot bot, DbInventoryItem item)
        {
            if (!AutonomousBotEconomy.TryGetEquipmentUpgrade(bot, item, out eInventorySlot slot))
                return int.MinValue;
            return AutonomousBotEconomy.EquipmentValue(item) - AutonomousBotEconomy.EquipmentValue(bot.Inventory.GetItem(slot));
        }
    }
}
