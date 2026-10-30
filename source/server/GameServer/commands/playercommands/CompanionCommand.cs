using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using DOL.Database;
using DOL.GS.PacketHandler;

namespace DOL.GS.Commands
{
    /// <summary>
    /// Clickable popup listing the account's other characters. Uses the same invisible
    /// conversation NPC trick as the /spawn class menu, because the classic client only
    /// turns [bracketed] text into links when an NPC owns the popup.
    /// </summary>
    public sealed class AccountCompanionMenu : GameNPC
    {
        private const string ActiveMenuProperty = "OfflineDAoC.ActiveCompanionMenu";
        private const int MenuLifetimeMilliseconds = 600_000;
        private const ushort InvisibleModel = 150;

        private static readonly Regex TrainLink = new(@"^(?<line>.+) \+(?<steps>\d+)$", RegexOptions.CultureInvariant);
        private static readonly int[] TrainSteps = { 1, 5, 10 };
        internal const string AutoSpendOnLink = "Auto-spend on";
        internal const string AutoSpendOffLink = "Auto-spend off";
        internal const string SpendByBuildLink = "Spend by build";
        internal const string BackLink = "Back";
        internal const string ResetPrefix = "Reset ";
        internal const string ResetAllName = "all lines";

        private readonly GamePlayer _owner;
        private ECSGameTimer _expirationTimer;
        private bool _closed;
        // The companion whose training page is showing; null shows the character list.
        private GameBot _specFor;

        private AccountCompanionMenu(GamePlayer owner)
        {
            _owner = owner;
            Name = "Companion Menu";
            Realm = owner.Realm;
            Level = 1;
            Model = InvisibleModel;
            Size = 1;
            Flags = eFlags.PEACE | eFlags.DONTSHOWNAME;
            X = owner.X;
            Y = owner.Y;
            Z = owner.Z;
            Heading = owner.Heading;
            CurrentRegionID = owner.CurrentRegionID;
        }

        public static string BuildMenuText(GamePlayer owner)
        {
            var lines = AccountCompanionManager.AccountCharacters(owner)
                .Where(character => character.Realm == (int)owner.Realm)
                .Select(character =>
                {
                    string className = ScriptMgr.FindCharacterClass(character.Class)?.Name ?? "Unknown";
                    string state = AccountCompanionManager.IsSummoned(character.ObjectId)
                        ? $" (with you) [Train {character.Name}]"
                        : string.Empty;
                    return $"[{character.Name}] level {character.Level} {className}{state}";
                })
                .ToArray();
            if (lines.Length == 0)
                return "You have no other characters in this realm. Create one on the character screen, then type /companion.";
            return "Click a character to bring it into your group, or click one that is with you to send it home. " +
                   "Click Train to spend its specialization points:\n\n" +
                   string.Join('\n', lines);
        }

        /// <summary>The training page: free points, the auto-spend switch and +1/+5/+10 links for every line.</summary>
        public static string BuildSpecText(GameBot companion)
        {
            int available = companion.CompanionUnspentSpecPoints();
            int limit = AccountCompanionRules.LineLimit(companion.Level);
            var text = new StringBuilder();
            text.Append($"{companion.Name}, level {companion.Level} {companion.ClassName}\n");
            text.Append($"Free specialization points: {available}\n");
            text.Append(companion.CompanionAutoSpend
                ? $"Auto-spend is on: it trains its build by itself at every level. [{AutoSpendOffLink}]\n"
                : $"Auto-spend is off: you choose where its points go. [{AutoSpendOnLink}]\n");
            text.Append($"[{SpendByBuildLink}] spends the free points now along its build, once.\n");
            text.Append($"[{ResetPrefix}{ResetAllName}] gives back every point (free, asks first).\n\n");
            foreach (Specialization spec in companion.CompanionTrainableLines())
            {
                string reset = companion.CanRespecCompanionLine(spec) ? $" [{ResetPrefix}{spec.Name}]" : string.Empty;
                if (spec.Level >= limit)
                {
                    text.Append($"{spec.Name} {spec.Level} (most at this level){reset}\n");
                    continue;
                }
                int cost = AccountCompanionRules.NextLevelCost(spec.Level, companion.IsCompanionAutotrainLine(spec), companion.Level);
                text.Append($"{spec.Name} {spec.Level}, next level {cost} points: ");
                text.Append(string.Join(' ', TrainSteps.Select(steps => $"[{spec.Name} +{steps}]")));
                text.Append(reset);
                text.Append('\n');
            }
            text.Append($"\n[{BackLink}]");
            return text.ToString();
        }

        /// <summary>Reads a training-page link. False for anything the page does not offer.</summary>
        public static bool TryParseTrainLink(string text, out string line, out int steps)
        {
            line = null;
            steps = 0;
            Match match = TrainLink.Match(text?.Trim() ?? string.Empty);
            if (!match.Success || !int.TryParse(match.Groups["steps"].Value, out steps) || !TrainSteps.Contains(steps))
                return false;
            line = match.Groups["line"].Value;
            return true;
        }

        private string CurrentText() =>
            _specFor != null ? BuildSpecText(_specFor) : BuildMenuText(_owner);

        internal static bool Open(GamePlayer player, GameBot specFor = null)
        {
            if (player?.CurrentRegion == null)
                return false;
            player.TempProperties.GetProperty<AccountCompanionMenu>(ActiveMenuProperty)?.Close();
            var menu = new AccountCompanionMenu(player) { _specFor = specFor };
            if (!menu.AddToWorld())
                return false;
            player.TempProperties.SetProperty(ActiveMenuProperty, menu);
            player.TargetObject = menu;
            player.Out.SendChangeTarget(menu);
            menu._expirationTimer = new ECSGameTimer(menu, _ =>
            {
                menu.Close();
                return 0;
            }, MenuLifetimeMilliseconds);
            player.Out.SendMessage(menu.CurrentText(), eChatType.CT_Say, eChatLoc.CL_PopupWindow);
            return true;
        }

        public override bool WhisperReceive(GameLiving source, string text)
        {
            if (!ReferenceEquals(source, _owner) || string.IsNullOrWhiteSpace(text))
                return false;
            // A companion sent home while its page was open: back to the list.
            if (_specFor != null && !AccountCompanionManager.ActiveFor(_owner).Contains(_specFor))
                _specFor = null;

            if (_specFor != null)
                HandleSpecClick(text.Trim());
            else if (text.StartsWith("Train ", StringComparison.OrdinalIgnoreCase))
            {
                string name = text.Substring("Train ".Length).Trim();
                _specFor = AccountCompanionManager.ActiveFor(_owner)
                    .FirstOrDefault(bot => string.Equals(bot.Name, name, StringComparison.OrdinalIgnoreCase));
                if (_specFor == null)
                    _owner.Out.SendMessage($"{name} is not with you. Summon it first.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            }
            else
                CompanionCommandHandler.Toggle(_owner, text);

            if (!_closed && _owner.ObjectState is eObjectState.Active && _owner.CurrentRegion == CurrentRegion)
            {
                _owner.TargetObject = this;
                _owner.Out.SendChangeTarget(this);
                _owner.Out.SendMessage(CurrentText(), eChatType.CT_Say, eChatLoc.CL_PopupWindow);
            }
            return true;
        }

        private void HandleSpecClick(string text)
        {
            string message;
            if (string.Equals(text, BackLink, StringComparison.OrdinalIgnoreCase))
            {
                _specFor = null;
                return;
            }
            if (string.Equals(text, AutoSpendOnLink, StringComparison.OrdinalIgnoreCase) ||
                string.Equals(text, AutoSpendOffLink, StringComparison.OrdinalIgnoreCase))
            {
                bool on = string.Equals(text, AutoSpendOnLink, StringComparison.OrdinalIgnoreCase);
                _specFor.SetCompanionAutoSpend(on);
                message = CompanionCommandHandler.AutoSpendMessage(_specFor);
            }
            else if (string.Equals(text, SpendByBuildLink, StringComparison.OrdinalIgnoreCase))
            {
                // A success lists what was trained itself.
                if (_specFor.AutoTrainCompanion())
                {
                    _specFor.SaveAccountCompanion("train");
                    return;
                }
                message = $"{_specFor.Name} has nothing to train along its build right now.";
            }
            else if (TryParseResetLink(text, out string resetLine))
            {
                GameBot companion = _specFor;
                CompanionCommandHandler.ConfirmRespec(_owner, companion, resetLine, () =>
                {
                    // Show the page again with the new levels, if it is still open on this companion.
                    if (!_closed && ReferenceEquals(_specFor, companion) && _owner.ObjectState is eObjectState.Active)
                        _owner.Out.SendMessage(CurrentText(), eChatType.CT_Say, eChatLoc.CL_PopupWindow);
                });
                return;
            }
            else if (TryParseTrainLink(text, out string line, out int steps))
                message = _specFor.TrainCompanionLine(line, steps);
            else
                return;
            _owner.Out.SendMessage(message, eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        /// <summary>Reads a reset link: a line name, or "all" for every line.</summary>
        public static bool TryParseResetLink(string text, out string line)
        {
            line = null;
            text = text?.Trim() ?? string.Empty;
            if (!text.StartsWith(ResetPrefix, StringComparison.OrdinalIgnoreCase) || text.Length <= ResetPrefix.Length)
                return false;
            line = text.Substring(ResetPrefix.Length).Trim();
            if (string.Equals(line, ResetAllName, StringComparison.OrdinalIgnoreCase))
                line = "all";
            return line.Length > 0;
        }

        private void Close()
        {
            if (_closed)
                return;
            _closed = true;
            _expirationTimer?.Stop();
            if (ReferenceEquals(_owner?.TempProperties.GetProperty<AccountCompanionMenu>(ActiveMenuProperty), this))
                _owner.TempProperties.RemoveProperty(ActiveMenuProperty);
            if (_owner?.ObjectState is eObjectState.Active && ReferenceEquals(_owner.TargetObject, this))
            {
                _owner.TargetObject = null;
                _owner.Out.SendChangeTarget(null);
            }
            Delete();
        }
    }

    [CmdAttribute("&companion", ePrivLevel.Player,
        "Brings characters from your own account into your group; they keep what they earn",
        "/companion - menu of your characters",
        "/companion <name> - summon or send home",
        "/companion <name> <class> - choose a class for a new character",
        "/companion build <name> [build] - choose its training build",
        "/companion spec <name> - training page: spend its points by hand",
        "/companion train <name> <line> [levels] | autospend <name> on|off",
        "/companion respec <name> <line|all> - free respec, asks first",
        "/companion list | dismiss <name|all>")]
    public sealed class CompanionCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            GamePlayer player = client.Player;
            if (player == null)
                return;

            if (args.Length < 2)
            {
                if (!AccountCompanionMenu.Open(player))
                    DisplayMessage(client, "The companion menu could not open here. Use /companion <name>.");
                return;
            }

            string first = args[1].ToLowerInvariant();
            switch (first)
            {
                case "list":
                    List(player);
                    return;
                case "dismiss":
                case "home":
                    Dismiss(player, args.Length > 2 ? string.Join(' ', args.Skip(2)) : "all");
                    return;
                case "build":
                case "style":
                    Build(player, args);
                    return;
                case "spec":
                case "specs":
                    Spec(player, args);
                    return;
                case "train":
                    Train(player, args);
                    return;
                case "respec":
                    Respec(player, args);
                    return;
                case "autospend":
                case "autotrain":
                    AutoSpend(player, args);
                    return;
            }

            DbCoreCharacter character = AccountCompanionManager.FindCharacter(player, args[1]);
            if (character == null)
            {
                DisplayMessage(client, $"You have no other character named '{args[1]}'. Type /companion list.");
                return;
            }

            if (args.Length > 2)
            {
                string wanted = string.Join(' ', args.Skip(2));
                eCharacterClass chosen = AccountCompanionManager.PromotionChoices(character)
                    .FirstOrDefault(choice => string.Equals(choice.ToString(), wanted.Replace(" ", string.Empty), StringComparison.OrdinalIgnoreCase));
                AccountCompanionManager.Promote(player, character, chosen, out string promoted);
                DisplayMessage(client, promoted);
                return;
            }

            Toggle(player, character.Name);
        }

        internal static void Toggle(GamePlayer player, string name)
        {
            DbCoreCharacter character = AccountCompanionManager.FindCharacter(player, name);
            if (character == null)
                return;

            GameBot active = AccountCompanionManager.ActiveFor(player)
                .FirstOrDefault(bot => bot.CompanionCharacterId == character.ObjectId);
            if (active != null)
            {
                AccountCompanionManager.Dismiss(active);
                player.Out.SendMessage($"{character.Name} heads home. Its progress is saved.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }

            GameBot summoned = AccountCompanionManager.Summon(player, character, out string message);
            player.Out.SendMessage(message, eChatType.CT_System, eChatLoc.CL_SystemWindow);
            summoned?.RemindCompanionUnspentPoints();
            if (AccountCompanionManager.Check(player, character) == AccountCompanionRules.SummonRefusal.NeedsPromotion)
            {
                string choices = string.Join(", ", AccountCompanionManager.PromotionChoices(character));
                if (choices.Length > 0)
                    player.Out.SendMessage($"{character.Name} can become: {choices}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            }
        }

        private static void List(GamePlayer player)
        {
            var characters = AccountCompanionManager.AccountCharacters(player);
            if (characters.Count == 0)
            {
                player.Out.SendMessage("You have no other characters on this account.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            foreach (DbCoreCharacter character in characters)
            {
                string className = ScriptMgr.FindCharacterClass(character.Class)?.Name ?? "Unknown";
                AccountCompanionRules.SummonRefusal refusal = AccountCompanionManager.Check(player, character);
                string state = AccountCompanionManager.IsSummoned(character.ObjectId) ? "with you"
                    : refusal == AccountCompanionRules.SummonRefusal.None ? "ready"
                    : refusal == AccountCompanionRules.SummonRefusal.GroupFull ? "group full"
                    : AccountCompanionRules.RefusalMessage(refusal, character.Name);
                player.Out.SendMessage($"{character.Name}: level {character.Level} {className} - {state}", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            }
        }

        private static void Dismiss(GamePlayer player, string name)
        {
            var active = AccountCompanionManager.ActiveFor(player)
                .Where(bot => name.Equals("all", StringComparison.OrdinalIgnoreCase) ||
                              string.Equals(bot.Name, name, StringComparison.OrdinalIgnoreCase))
                .ToList();
            if (active.Count == 0)
            {
                player.Out.SendMessage("No matching companion is with you.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            foreach (GameBot companion in active)
                AccountCompanionManager.Dismiss(companion);
            player.Out.SendMessage($"Sent home and saved: {string.Join(", ", active.Select(bot => bot.Name))}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        internal static string AutoSpendMessage(GameBot companion) => companion.CompanionAutoSpend
            ? $"{companion.Name} will spend its points along its build at every level."
            : $"{companion.Name} will keep its points for you to spend.";

        /// <summary>Asks with the client's Yes/No dialog, then respecs. Free, as player respecs are on this server.</summary>
        internal static void ConfirmRespec(GamePlayer player, GameBot companion, string line, Action afterRespec = null)
        {
            string refusal = companion.CompanionRespecRefusal();
            if (refusal != null)
            {
                player.Out.SendMessage(refusal, eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            string what = line == "all" ? "every line" : line;
            player.Out.SendCustomDialog($"Respec {companion.Name}'s {what}? The points come back to spend again.", (responder, response) =>
            {
                if (response != 0x01 || !AccountCompanionManager.ActiveFor(responder).Contains(companion))
                    return;
                responder.Out.SendMessage(companion.RespecCompanion(line), eChatType.CT_System, eChatLoc.CL_SystemWindow);
                afterRespec?.Invoke();
            });
        }

        private static void Respec(GamePlayer player, string[] args)
        {
            if (args.Length < 4)
            {
                player.Out.SendMessage("Usage: /companion respec <name> <line|all>", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            GameBot companion = ActiveCompanion(player, args[2]);
            string line = string.Join(' ', args.Skip(3)).Trim();
            if (companion != null)
                ConfirmRespec(player, companion, line.Equals("all", StringComparison.OrdinalIgnoreCase) ? "all" : line);
        }

        private static GameBot ActiveCompanion(GamePlayer player, string name)
        {
            GameBot companion = AccountCompanionManager.ActiveFor(player)
                .FirstOrDefault(bot => string.Equals(bot.Name, name, StringComparison.OrdinalIgnoreCase));
            if (companion == null)
                player.Out.SendMessage($"{name} is not with you. Summon it with /companion {name} first.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
            return companion;
        }

        private static void Spec(GamePlayer player, string[] args)
        {
            if (args.Length < 3)
            {
                player.Out.SendMessage("Usage: /companion spec <name>", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            GameBot companion = ActiveCompanion(player, args[2]);
            if (companion != null && !AccountCompanionMenu.Open(player, companion))
                player.Out.SendMessage("The training page could not open here. Use /companion train <name> <line> [levels].", eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        private static void Train(GamePlayer player, string[] args)
        {
            if (args.Length < 4)
            {
                player.Out.SendMessage("Usage: /companion train <name> <line> [levels]", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            GameBot companion = ActiveCompanion(player, args[2]);
            if (companion == null)
                return;
            // Line names can have spaces ("Two Handed"); a number at the end is how many levels.
            List<string> words = args.Skip(3).ToList();
            int steps = 1;
            if (words.Count > 1 && int.TryParse(words[^1], out int parsed))
            {
                steps = Math.Clamp(parsed, 1, AccountCompanionRules.MaxLevel);
                words.RemoveAt(words.Count - 1);
            }
            player.Out.SendMessage(companion.TrainCompanionLine(string.Join(' ', words), steps), eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        private static void AutoSpend(GamePlayer player, string[] args)
        {
            if (args.Length < 3)
            {
                player.Out.SendMessage("Usage: /companion autospend <name> on|off", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            GameBot companion = ActiveCompanion(player, args[2]);
            if (companion == null)
                return;
            if (args.Length < 4)
            {
                player.Out.SendMessage($"{companion.Name}'s auto-spend is {(companion.CompanionAutoSpend ? "on" : "off")}.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            bool on = args[3].Equals("on", StringComparison.OrdinalIgnoreCase);
            if (!on && !args[3].Equals("off", StringComparison.OrdinalIgnoreCase))
            {
                player.Out.SendMessage("Usage: /companion autospend <name> on|off", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            companion.SetCompanionAutoSpend(on);
            player.Out.SendMessage(AutoSpendMessage(companion), eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }

        private static void Build(GamePlayer player, string[] args)
        {
            if (args.Length < 3)
            {
                player.Out.SendMessage("Usage: /companion build <name> [build]", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            DbCoreCharacter character = AccountCompanionManager.FindCharacter(player, args[2]);
            if (character == null)
            {
                player.Out.SendMessage($"You have no other character named '{args[2]}'.", eChatType.CT_System, eChatLoc.CL_SystemWindow);
                return;
            }
            AccountCompanionManager.SetStyle(player, character, args.Length > 3 ? args[3] : null, out string message);
            player.Out.SendMessage(message, eChatType.CT_System, eChatLoc.CL_SystemWindow);
        }
    }
}
