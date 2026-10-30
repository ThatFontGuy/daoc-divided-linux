using System.Collections.Generic;

namespace DOL.GS.Effects
{
	/// <summary>
	/// Adrenaline Rush
	/// </summary>
	public class FerociousWillEffect : TimedEffect
	{

		private int m_currentBonus = 25;

		public FerociousWillEffect()
			: base(30000)
		{
			
		}

		private GameLiving owner;

		public override void Start(GameLiving target)
        {
            base.Start(target);
            owner = target;
            GamePlayer player = target as GamePlayer;
            if (player != null)
            {
                foreach (GamePlayer p in player.GetPlayersInRadius(WorldMgr.VISIBILITY_DISTANCE))
                {
                    p.Out.SendSpellEffectAnimation(player, player, Icon, 0, false, 1);
                }
            }
            owner.BaseBuffBonusCategory[eProperty.PhysicalAbsorption] += m_currentBonus;
            foreach (eProperty resist in Resists)
                owner.OtherBonus[resist] += RESIST_BONUS;
        }

        // Live 1.108: also +25% to all resistances and a 25% chance to shrug off crowd control.
        public const int RESIST_BONUS = 25;
        public const int CC_SHRUG = 25;
        private static readonly eProperty[] Resists = { eProperty.Resist_Body, eProperty.Resist_Cold, eProperty.Resist_Energy,
            eProperty.Resist_Heat, eProperty.Resist_Matter, eProperty.Resist_Spirit, eProperty.Resist_Crush,
            eProperty.Resist_Slash, eProperty.Resist_Thrust };

		public override string Name { get { return "Ferocious Will"; } }

		public override ushort Icon { get { return 3064; } }

		public override void Stop()
		{
			owner.BaseBuffBonusCategory[eProperty.PhysicalAbsorption] -= m_currentBonus;
			foreach (eProperty resist in Resists)
				owner.OtherBonus[resist] -= RESIST_BONUS;
			base.Stop();
		}

		public int SpellEffectiveness
		{
			get { return 100; }
		}

		public override IList<string> DelveInfo
		{
			get
			{
				var list = new List<string>();
				list.Add("Gives the Berzerker an ABS buff of 25%. Lasts 30 seconds total.");
				return list;
			}
		}
	}
}
