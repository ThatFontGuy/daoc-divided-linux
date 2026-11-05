/*
* DAWN OF LIGHT - The first free open source DAoC server emulator
* 
* This program is free software; you can redistribute it and/or
* modify it under the terms of the GNU General Public License
* as published by the Free Software Foundation; either version 2
* of the License, or (at your option) any later version.
* 
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
* 
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*
*/

using System;
using DOL.Events;
using DOL.GS.Effects;
using DOL.GS.PacketHandler;
namespace DOL.GS.Spells
{
	public static class CostumeSpellHandlerRules
	{
		/// <summary>Shape potions are for the capitals and housing, not the open world.</summary>
		public static bool AllowedIn(ushort region) => region is 10 or 101 or 201 or 2 or 102 or 202;
	}

	/// Costume spell handler: Shape change on self
	/// <author>Luhz</author>
	[SpellHandler(eSpellType.Costume)]
	class CostumeSpellHandler : SpellHandler
	{
		// The work sits in OnEffectStart and OnEffectExpires: without this a potion gave an icon and no shape (playtest 2026-10-31).
		public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams)
		{
			return ECSGameEffectFactory.Create(initParams, static (in i) => new LegacySpellECSEffect(i));
		}

		public override bool StartSpell(GameLiving target, DOL.Database.DbInventoryItem item)
		{
			if (!CostumeSpellHandlerRules.AllowedIn(Caster.CurrentRegionID))
			{
				MessageToCaster("This only works in a capital city or a housing zone.", eChatType.CT_SpellResisted);
				return false;
			}
			return base.StartSpell(target, item);
		}

		public override bool CheckBeginCast(GameLiving selectedTarget, bool quiet) =>
			selectedTarget is GamePlayer && CostumeSpellHandlerRules.AllowedIn(selectedTarget.CurrentRegionID);

		/// Effect starting.
		/// <param name="effect"></param>
		public override void OnEffectStart(GameSpellEffect effect)
		{
			if (effect.Owner is not GamePlayer player)
				return;
			player.Model = (ushort)effect.Spell.Value;
			GameEventMgr.AddHandler(player, GamePlayerEvent.RegionChanged, new DOLEventHandler(OnZone));
		}

		private void OnZone(DOLEvent e, object sender, EventArgs arguments)
		{
			if (sender is GamePlayer player && !CostumeSpellHandlerRules.AllowedIn(player.CurrentRegionID))
				player.Model = player.CreationModel;
		}

		/// Effect expiring (duration spells only).
		/// <returns>Immunity duration in milliseconds.</returns>
		public override int OnEffectExpires(GameSpellEffect effect, bool noMessages)
		{
			if (effect.Owner is GamePlayer player)
			{
				player.Model = player.CreationModel;
				GameEventMgr.RemoveHandler(player, GamePlayerEvent.RegionChanged, new DOLEventHandler(OnZone));
			}
			return 0;
		}

		/// Creates a new Costume spell handler.
		public CostumeSpellHandler(GameLiving caster, Spell spell, SpellLine line)
			: base(caster, spell, line) { }
	}
}
