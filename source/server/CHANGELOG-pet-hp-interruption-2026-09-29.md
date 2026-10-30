# Player pet HP and priest interruption - Claude version only

- Player-owned Sluaghbinder pets now share the existing bot pet HP multipliers at every level. This is HP-only: player melee damage factors, spells, armor, and other classes are unchanged.
- Owner-level-50 unbuffed HP: walking dead 1,283; sturdy zombie 1,350; magician 960; guardian 1,714; priest 1,086; Dullahan 1,385.
- Priest spells 59037 (Miasma of Renewal) and 59038 (Priest's Mending) now have Uninterruptible=0, as requested. They obey the existing combat interruption rules; this does not change global interruption timing. A HoT already applied is not a cast and continues ticking.
- Updated tools/pet_spell_changes.py so rerunning it preserves the interruptible setting. Spell strengths and the 75%/50% AI priorities are unchanged.
- Regression coverage compares player/bot HP at several levels, protects other-class pets, and checks interruption of both priest spells for player and bot owners.

Restart and re-summon pets after deployment. Original new class test, multiplayer test, and GitHub are untouched. Live-client verification remains outstanding.
