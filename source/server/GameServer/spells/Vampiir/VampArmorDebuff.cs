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
using System.Collections.Generic;
using DOL.GS.Effects;
using DOL.GS.PacketHandler;

namespace DOL.GS.Spells
{
	[SpellHandler(eSpellType.VampiirArmorDebuff)]
	public class VampiirArmorDebuff : SpellHandler
	{
		private static eArmorSlot[] slots = new eArmorSlot[] { eArmorSlot.HEAD, eArmorSlot.TORSO, eArmorSlot.LEGS,  };
		private eArmorSlot m_slot = eArmorSlot.NOTSET;
		public eArmorSlot Slot { get { return m_slot; } }

		// The debuff lives on the player, not on the armor: nothing here can reach a saved item.
		private static string AfKey(eArmorSlot slot) => "VampiirArmorDebuffAF" + (int)slot;
		private static string AbsorbKey(eArmorSlot slot) => "VampiirArmorDebuffABS" + (int)slot;

		public static int AfPenalty(GamePlayer player, eArmorSlot slot) => player.TempProperties.GetProperty<int>(AfKey(slot));
		public static int AbsorbPenalty(GamePlayer player, eArmorSlot slot) => player.TempProperties.GetProperty<int>(AbsorbKey(slot));

		public override ECSGameSpellEffect CreateECSEffect(in ECSGameEffectInitParams initParams)
		{
			return ECSGameEffectFactory.Create(initParams, static (in i) => new LegacySpellECSEffect(i));
		}

		public override void FinishSpellCast(GameLiving target)
		{
			m_caster.Mana -= PowerCost(target);
			base.FinishSpellCast(target);
		}

		public override void OnEffectStart(GameSpellEffect effect)
		{
			effect.Owner.StartInterruptTimer(effect.Owner.SpellInterruptDuration, AttackData.eAttackType.Spell, Caster);
			GamePlayer player = effect.Owner as GamePlayer;
			if (player == null) return;
			int slot=Util.Random(0, 2);
			m_slot = slots[slot];
			string msg = GlobalConstants.SlotToName((int)m_slot);
			MessageToCaster("You debuff " + effect.Owner.Name + "'s " + msg+"", eChatType.CT_Spell);
			foreach (GamePlayer visPlayer in player.GetPlayersInRadius((ushort)WorldMgr.VISIBILITY_DISTANCE))
				visPlayer.Out.SendSpellEffectAnimation(player, player, (ushort)(13180+slot), 0, false, 0x01);

			ChangePenalty(player, (int)Spell.Value, (int)Spell.ResurrectMana);
			base.OnEffectStart(effect);
		}

		public override int OnEffectExpires(GameSpellEffect effect, bool noMessages)
		{
			if (m_slot != eArmorSlot.NOTSET && effect.Owner is GamePlayer player)
				ChangePenalty(player, -(int)Spell.Value, -(int)Spell.ResurrectMana);
			return base.OnEffectExpires(effect,noMessages);
		}

		private void ChangePenalty(GamePlayer player, int af, int absorb)
		{
			player.TempProperties.SetProperty(AfKey(m_slot), AfPenalty(player, m_slot) + af);
			player.TempProperties.SetProperty(AbsorbKey(m_slot), AbsorbPenalty(player, m_slot) + absorb);
			player.Out.SendCharStatsUpdate();
			player.UpdatePlayerStatus();
			player.Out.SendUpdatePlayer();
			player.Out.SendUpdateWeaponAndArmorStats();
			player.Out.SendCharResistsUpdate();
		}

		public override IList<string> DelveInfo 
		{
			get 
			{
				var list = new List<string>(16);
				list.Add("Name: " + Spell.Name+"\n");
				list.Add("Description: " + ShortDescription+"\n");
				list.Add("Target: " + Spell.Target);
				list.Add("Casting time: " + (Spell.CastTime*0.001).ToString("0.0## sec;-0.0## sec;'instant'"));
				if (Spell.Duration >= ushort.MaxValue*1000)
					list.Add("Duration: Permanent.");
				else if (Spell.Duration > 60000)
					list.Add(string.Format("Duration: {0}:{1} min", Spell.Duration/60000, (Spell.Duration%60000/1000).ToString("00")));
				else if (Spell.Duration != 0)
					list.Add("Duration: " + (Spell.Duration/1000).ToString("0' sec';'Permanent.';'Permanent.'"));
				if (Spell.RecastDelay > 60000)
					list.Add("Recast time: " + (Spell.RecastDelay/60000).ToString() + ":" + (Spell.RecastDelay%60000/1000).ToString("00") + " min");
				else if (Spell.RecastDelay > 0)
					list.Add("Recast time: " + (Spell.RecastDelay/1000).ToString() + " sec");
				if(Spell.Range != 0) list.Add("Range: " + Spell.Range);
				if(Spell.Power != 0) list.Add("Power cost: " + Spell.Power.ToString("0;0'%'"));
				list.Add("Debuff Absorption : " + Spell.ResurrectMana);
				list.Add("Debuff Armor Factor : " + Spell.Value);
				return list;
			}
		}
		
		public VampiirArmorDebuff(GameLiving caster, Spell spell, SpellLine line) : base(caster, spell, line) { }
	}
}