using System;
using System.Linq;
using DOL.Events;
using DOL.GS.Spells;

namespace DOL.GS
{
    public class StormSovereignEffect : MasterLevelEffect
    {
        private long _lastProc;
        private GameLiving _marked;
        private int Key => PendragonRules.IsRoyalRank(SpellHandler.Spell.ID) ? StormSovereignAbilities.Key(SpellHandler.Spell.ID) : -1;
        public StormSovereignEffect(in ECSGameEffectInitParams init) : base(init,StormSovereignAbilities.Toggle(init.SpellHandler.Spell.ID)) { }
        public override void OnStartEffect()
        {
            base.OnStartEffect();
            if(Key==17) _marked=SpellHandler.Target;
            if(Key is 15 or 17) GameEventMgr.AddHandler(Owner,GameLivingEvent.AttackFinished,OnAttack);
            if(Key is 15 or 18) GameEventMgr.AddHandler(Owner,GameLivingEvent.AttackedByEnemy,OnDefend);
        }
        public override void OnStopEffect()
        {
            GameEventMgr.RemoveHandler(Owner,GameLivingEvent.AttackFinished,OnAttack);
            GameEventMgr.RemoveHandler(Owner,GameLivingEvent.AttackedByEnemy,OnDefend);
            base.OnStopEffect();
        }
        public override DOL.Database.DbPlayerXEffect GetSavedEffect() => StormSovereignAbilities.Toggle(SpellHandler.Spell.ID)?base.GetSavedEffect():null;
        private MasterLevelAbilityHandler Handler => (MasterLevelAbilityHandler)SpellHandler;
        private void OnAttack(DOLEvent e,object sender,EventArgs args)
        {
            if(IsEnding || !IsActive || args is not AttackFinishedEventArgs { AttackData: var hit } ||
                !hit.IsMeleeAttack || hit.Damage<=0 || hit.Target==null || !hit.Target.IsAlive) return;
            if(Key==17)
            {
                if(hit.Target==_marked) { End(); StormSovereignAbilities.Strike(Handler,hit.Target,hit.Damage*0.3); }
                return;
            }
            if(GameLoop.GameLoopTime<_lastProc || !Owner.Chance(RandomDeckEvent.OffensiveProcChance,20)) return;
            _lastProc=GameLoop.GameLoopTime+2000;
            eObjectType weapon=(eObjectType)(Owner.ActiveWeapon?.Object_Type??0);
            if(weapon is eObjectType.Sword or eObjectType.SlashingWeapon) Handler.Heal(Owner,Math.Max(1,Owner.MaxHealth*2/100));
            else {
                StormSovereignAbilities.Strike(Handler,hit.Target,Owner.Level*1.5,weapon is eObjectType.Axe or eObjectType.ThrustWeapon?eDamageType.Cold:eDamageType.Energy);
                if(weapon is eObjectType.Spear or eObjectType.PolearmWeapon)
                    foreach(var enemy in Handler.Enemies(hit.Target,250).Where(t=>t!=hit.Target && t.InCombat).Take(1))
                        StormSovereignAbilities.Strike(Handler,enemy,Owner.Level);
            }
        }
        private void OnDefend(DOLEvent e,object sender,EventArgs args)
        {
            if(IsEnding || !IsActive || GameLoop.GameLoopTime<_lastProc || args is not AttackedByEnemyEventArgs { AttackData: var hit } ||
                !hit.IsMeleeAttack || hit.Attacker==null || !hit.Attacker.IsAlive) return;
            if(Key==18 && hit.AttackResult==eAttackResult.Parried) {
                _lastProc=GameLoop.GameLoopTime+1000;
                StormSovereignAbilities.Strike(Handler,hit.Attacker,Owner.Level*2);
            }
            else if(Key==15 && hit.AttackResult==eAttackResult.Blocked && Owner.Chance(RandomDeckEvent.DefensiveProcChance,20)) {
                _lastProc=GameLoop.GameLoopTime+5000;
                Handler.Cast(Owner,500+Owner.Level,eSpellType.BothAblativeArmor,db=>{db.Target="Self";db.Duration=8;db.Value=Owner.Level*3;db.Damage=50;});
            }
        }
    }
}
