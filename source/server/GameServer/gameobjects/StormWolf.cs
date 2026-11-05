using System;
using System.Linq;
using System.Threading;
using DOL.AI.Brain;
using DOL.Events;
using DOL.GS.PacketHandler;
using DOL.GS.Spells;
using DOL.GS;

namespace DOL.GS
{
    public class StormWolf : GameSummonedPet
    {
        public const double NormalDamage=2.0, CrownDamage=3.0;
        public const int HealthSteal=30;
        private ushort _normalModel;
        private readonly Lock _controlledNpcListLock = new();
        public Lock ControlledNpcListLock => _controlledNpcListLock;
        public StormWolf(INpcTemplate template):base(template) { DamageFactor=NormalDamage; }
        public override double MaxHealthScalingFactor => 4.0;
        public override void DealDamage(AttackData ad)
        {
            int healthBefore=ad.Target?.Health??0;
            base.DealDamage(ad);
            int dealt=Math.Min(healthBefore,Math.Max(0,ad.Damage+ad.CriticalDamage));
            if(dealt>0 && IsAlive) ChangeHealth(this,eHealthChangeType.Spell,StormforgedRules.RestorePerHit(dealt,HealthSteal));
        }
        public override double GetSpellScalingFactor() => Level / 50.0;
        public override void SortSpells()
        {
            base.SortSpells();
            if(HarmfulSpells!=null) HarmfulSpells=HarmfulSpells.ConvertAll(GetScaledSpell);
            if(InstantHarmfulSpells!=null) InstantHarmfulSpells=InstantHarmfulSpells.ConvertAll(GetScaledSpell);
        }
        public override bool SetPetLevel() { SummonSpellDamage=-100; SummonSpellValue=50; return base.SetPetLevel(); }
        private bool _stealthHandlerAdded;
        public override bool AddToWorld()
        {
            if(!base.AddToWorld()) return false;
            _normalModel=Model;
            // Drengr's second/third wolf (SummonDrengrWolfCompanion) attach here as sub-pets, so
            // every Storm Wolf -- not just the first -- needs room for them regardless of which
            // one ends up as the player's direct pet.
            InitControlledBrainArray(2);
            // Player-only event: a /spawn or gamebot owner threw here and the casting service removed the bot.
            // Bot owners are kept in sync by StormWolfBrain.Think instead. RootOwner (not Owner) walks past
            // the first wolf for a sub-pet, to the real player at the top of the chain.
            if(RootOwner is GamePlayer rootPlayer)
            {
                GameEventMgr.AddHandler(rootPlayer,GamePlayerEvent.StealthStateChanged,OwnerStealthChanged);
                _stealthHandlerAdded=true;
            }
            SyncOwner();
            return true;
        }
        public override bool RemoveFromWorld()
        {
            // Guarded by _stealthHandlerAdded: a zero-health sub-pet deleted by
            // SummonStormWolf.OnPetReleased's cascade can have RemoveFromWorld called again by
            // the NPC service's own cleanup pass, and unsubscribing twice throws (the handler
            // chain is already gone after the first removal).
            if(_stealthHandlerAdded && RootOwner is GamePlayer rootPlayer)
            {
                GameEventMgr.RemoveHandler(rootPlayer,GamePlayerEvent.StealthStateChanged,OwnerStealthChanged);
                _stealthHandlerAdded=false;
            }
            return base.RemoveFromWorld();
        }
        private void OwnerStealthChanged(DOLEvent e,object sender,EventArgs args)=>SyncOwner();
        public void SyncOwner()
        {
            GameLiving rootOwner=RootOwner;
            if(rootOwner==null) return;
            SetPetLevel();
            Stealth(rootOwner.IsStealthed);
            bool empowered=StormforgedHeroicRules.HasAvatar(rootOwner);
            ushort model=empowered && PendragonRules.RealmOffset(rootOwner)==0?(ushort)650:_normalModel;
            if(Model!=model) Model=model;
            Size=empowered?(byte)70:(byte)50;
            DamageFactor=empowered?CrownDamage:NormalDamage;
            MaxSpeedBase = rootOwner.MaxSpeedBase;
        }
        public override void Stealth(bool hidden)
        {
            if(IsStealthed==hidden) return;
            if(hidden) { StopAttack(); StopCurrentSpellcast(); }
            Flags=hidden?Flags|eFlags.STEALTH:Flags&~eFlags.STEALTH;
            if(hidden && ObjectState==eObjectState.Active)
                foreach(var viewer in GetPlayersInRadius(WorldMgr.VISIBILITY_DISTANCE))
                    if(!IsVisibleTo(viewer)) viewer.Out.SendObjectRemove(this);
        }
        public override bool IsVisibleTo(GameObject viewer) => base.IsVisibleTo(viewer) &&
            (!IsStealthed || viewer==RootOwner || viewer is GamePlayer player && RootOwner!=null && player.CanDetect(RootOwner));

        // Multiple simultaneous sub-pets (Drengr's second/third wolf): the base GameNPC
        // implementation only ever holds one controlled brain in slot 0, same pattern as
        // DOL.GS.Bonedancer.CommanderPet.
        public override bool AddControlledBrain(IControlledBrain controlledBrain)
        {
            lock(ControlledNpcListLock)
            {
                if(ControlledNpcList==null) return false;
                for(int i=0;i<ControlledNpcList.Length;i++)
                {
                    if(ControlledNpcList[i]==null)
                    {
                        ControlledNpcList[i]=controlledBrain;
                        UpdatePetCount(controlledBrain.Body as GameSummonedPet,true);
                        return true;
                    }
                }
                return false;
            }
        }
        public override bool RemoveControlledBrain(IControlledBrain controlledBrain)
        {
            if(controlledBrain==null) return false;
            lock(ControlledNpcListLock)
            {
                if(ControlledNpcList==null) return false;
                for(int i=0;i<ControlledNpcList.Length;i++)
                {
                    if(ControlledNpcList[i]==controlledBrain)
                    {
                        ControlledNpcList[i]=null;
                        UpdatePetCount(controlledBrain.Body as GameSummonedPet,false);
                        return true;
                    }
                }
                return false;
            }
        }
    }
}

namespace DOL.AI.Brain
{
    public class StormWolfBrain : ControlledMobBrain
    {
        public StormWolfBrain(GameLiving owner):base(owner) { }
        public override void Think()
        {
            if(Body is StormWolf wolf) wolf.SyncOwner();
            // GetPlayerOwner() walks past an intermediate first-wolf owner (for the second/third
            // wolf) to the real player, so every wolf follows/attacks off the player's own state.
            GamePlayer rootPlayer=GetPlayerOwner();
            if(rootPlayer==null) return;
            if(rootPlayer.IsStealthed)
            {
                Body.StopAttack(); ClearAggroList();
                if(WalkState==eWalkState.Follow) Body.Follow(rootPlayer,MIN_OWNER_FOLLOW_DIST,MAX_OWNER_FOLLOW_DIST);
                return;
            }
            if(AggressionState!=eAggressionState.Passive && WalkState!=eWalkState.Stay && rootPlayer.IsAttacking && rootPlayer.TargetObject is GameLiving target &&
                GameServer.ServerRules.IsAllowedToAttack(rootPlayer,target,true)) base.Attack(target);
            base.Think();
        }
        public override void Attack(GameObject target)
        {
            GamePlayer rootPlayer=GetPlayerOwner();
            if(target is not GameLiving living || rootPlayer==null || !GameServer.ServerRules.IsAllowedToAttack(rootPlayer,living,true)) return;
            rootPlayer.Stealth(false); Body.Stealth(false);
            base.Attack(target);
        }
    }
}

namespace DOL.GS.Spells
{
    [SpellHandler(eSpellType.StormSovereignWolf)]
    public class SummonStormWolf : SummonSpellHandler
    {
        public SummonStormWolf(GameLiving caster,Spell spell,SpellLine line):base(caster,spell,line) { }
        public override bool IsSummoningSpell=>true;
        public override string ShortDescription=>Spell.Description;
        protected override IControlledBrain GetPetBrain(GameLiving owner)=>new StormWolfBrain(owner);
        protected override GameSummonedPet GetGamePet(INpcTemplate template)
        {
            // Named distinctly from the second/third wolf companions, since all three otherwise
            // share the same reused NPC template's name.
            var pet=new StormWolf(template);
            pet.Name="Male Wolf";
            return pet;
        }
        public override void OnPetReleased()
        {
            // Releasing the commander wolf (this one) otherwise leaves any Drengr second/third
            // wolf companions attached to it behind, since ending its own Pet effect only
            // despawns itself, not the sub-pets it holds. Delete them directly here (matching
            // what PetECSGameEffect.OnStopEffect does for the main pet) rather than cascading
            // through their own Pet effect, which depends on ECS tick timing we don't control
            // from inside this callback.
            if(Pet is StormWolf commander && commander.ControlledNpcList!=null)
            {
                foreach(IControlledBrain subBrain in commander.ControlledNpcList.Where(b=>b!=null).ToArray())
                {
                    commander.RemoveControlledBrain(subBrain);
                    if(subBrain.Body is GameSummonedPet subPet)
                    {
                        subPet.Health=0;
                        subPet.Delete();
                    }
                }
            }
            base.OnPetReleased();
        }
    }

    // Drengr's second/third wolf: attaches another Storm Wolf as a sub-pet of the player's first
    // Storm Wolf (same commander/sub-pet attachment as DOL.GS.Spells.SummonMinionHandler), capped
    // by StormWolf.ControlledNpcList's length (2). StormWolfBrain/StormWolf resolve all
    // player-facing behavior through the root player, so every wolf still acts like an
    // independent pet of the caster, not a hierarchy, despite the attachment.
    [SpellHandler(eSpellType.DrengrWolfCompanion)]
    public class SummonDrengrWolfCompanion : SummonSpellHandler
    {
        public SummonDrengrWolfCompanion(GameLiving caster,Spell spell,SpellLine line):base(caster,spell,line) { }
        public override bool IsSummoningSpell=>true;
        public override string ShortDescription=>Spell.Description;
        public override bool CheckBeginCast(GameLiving selectedTarget)
        {
            if(Caster.ControlledBrain?.Body is not StormWolf commander)
            {
                MessageToCaster("You must have your first Storm Wolf summoned before you can call another.",eChatType.CT_SpellResisted);
                return false;
            }
            if(commander.ControlledNpcList==null || commander.PetCount>=commander.ControlledNpcList.Length)
            {
                MessageToCaster("You already have as many wolves summoned as you can control.",eChatType.CT_SpellResisted);
                return false;
            }
            return base.CheckBeginCast(selectedTarget);
        }
        protected override IControlledBrain GetPetBrain(GameLiving owner)=>new StormWolfBrain(Caster.ControlledBrain.Body);
        protected override GameSummonedPet GetGamePet(INpcTemplate template)
        {
            var pet=new StormWolf(template);
            // Distinguish the companions from each other and from the first (Male) wolf, which
            // otherwise all share the same reused NPC template's name.
            pet.Name=Spell.ID==62652?"Wolf Youngling":"Female Wolf";
            return pet;
        }
        protected override void SetBrainToOwner(IControlledBrain brain)=>Caster.ControlledBrain.Body.AddControlledBrain(brain);
    }
}

