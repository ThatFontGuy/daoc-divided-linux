using System;
using System.Collections;
using System.Reflection;
using DOL.GS.PacketHandler;
using DOL.GS.Effects;
using DOL.Events;

namespace DOL.GS.SkillHandler
{
	/// <summary>
	/// Handler for Vampiir Bolt clicks
	/// </summary>
	[SkillHandler(Abilities.VampiirBolt)]
	public class VampiirBoltAbilityHandler : SpellCastingAbilityHandler
	{
		public const int ModernBoltBase = 69000;

		/// <summary>The bolt rank cast at the given ability level: stock spell IDs first, then the modern test kit.</summary>
		public static int SpellIdFor(int level) => SkillBase.GetSpellByID(13200 + level) != null ? 13200 + level : ModernBoltBase + level;

		public override long Preconditions
		{
			get
			{
				return DEAD | SITTING | MEZZED | STUNNED | TARGET;
			}
		}

		public override int SpellID
		{
			get
			{
				return SpellIdFor(m_ability.Level);
			}
		}
	}
}
