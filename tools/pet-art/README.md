# Pet art, weapon and spell-effect pipeline

These scripts made the private Sluaghbinder pet models and skins, the pet weapons, and the Blood
Shield and void blast spell effects in 0.33. Stock game models, textures and effects are never
edited. Every change is a **private copy** with new IDs, and every install script makes a backup
and prints a one-command rollback.

## Setup

- **Python 3.10+** with `numpy`, `Pillow` and `pyffi` (`pip install numpy pillow pyffi`).
- **Where the scripts look:** they expect to sit inside a playable folder, at
  `<playable>/tools/pet-art`, with the repository's `tools/asset-tool` next to them. Otherwise set:
  - `OFFLINE_DAOC_CLIENT`: the game's `runtime/client-opendaoc/app` folder
  - `OFFLINE_DAOC_ARCHIVE_TOOL`: the folder containing `archive.py` (the MPK reader and writer)
  - `OFFLINE_DAOC_BLENDER`: `blender.exe`, for the optional headless preview renders
- **Close everything first:** the launcher, the game and the server must be closed before any
  `install` step.

## How the pieces fit

| Script | Purpose |
|---|---|
| `daoc_catalog.py`, `resolve_models.py` | Read `gamedata.mpk` catalogs and MPK archives; resolve a model ID to its NIF, skins and users |
| `nifmesh.py`, `texelmap.py`, `regions.py`, `armorpaint.py` | Load creature NIFs (pyffi), bake texel-to-3D maps, and paint in model space |
| `nif4_geom.py`, `weapon_texel.py` | Read old NetImmerse 4.x **item** NIFs (weapons and shields) that pyffi can't parse. Read-only |
| `paint_*.py` | Paint each pet skin; `paint_pet_weapons.py` paints the four pet weapons |
| `export_obj.py`, `blender_render.py`, `weapon_preview.py`, `blender_weapons.py` | Headless Blender preview renders (OBJ bridge; NIFs are never rewritten by Blender) |
| `install_pet_art.py`, `update_skins.py`, `install_walkingdead.py`, `install_vnext.py` | Install pet skins, models and NIFs |
| `install_void_sun.py`, `add_magician_combat_anims.py` | Zombie magician void blast effect and animation sets |
| `install_blood_shield.py`, `install_sluagh_visuals2.py` | Blood Shield effect for Cairn armor buffs; summon hand glows and cast times |
| `install_pet_weapons.py`, `install_pet_shield_skins.py` | Private Necroservant and Zombie Guardian weapons (objects/items rows, pskins for emblem shields) |
| `install_sluagh_armor.py` | The Dubh Sluagh set (Sluaghbinder level 50 reward): pskins, mskins and Mskins archive, objects/items/speffects rows, weapon NIFs. `plan`, `install`, `rollback` |
| `nif4_append.py` | Append a second shape to a NetImmerse 4.2 item NIF (the 3D skull on the Cairnfire Aegis); every parse is checked byte for byte |
| `work/sluagh-armor/` | The set's art: `extract_meshes.py` (copies the stock meshes it needs into `nif/`), `paint_set.py` (armor, helm, cloak), `shield_build.py`, `mace_build.py`, `weapons_build.py` (scythe), `views_game.py` (flat-lit previews like the game), `cloak_debug_grid.py` (labelled grid to learn a texture mapping) |

## Lessons learned

- **Model chains:**
  - Creatures: `monsters.csv` → `monnifs.csv` (NIF and animation set) → `skins.csv` (archive
    `skinNNN.mpk`).
  - Items: `objects.csv` model ID → `items.csv` row → `items/<nif>`.
- **Emblem shields** (NIFs with cloakpattern and symbol layers) get their base texture from a
  `pskins.csv` override. Without one they render pink.
- **Animation sets:** a new animation set needs a row in **both** `anims.csv` and `canims.csv`,
  otherwise the creature freezes in melee.
- **Private NIFs** are byte copies of stock NIFs with **same-length** texture-name renames.
  Undoing the rename must give back the original byte-for-byte.
- **Textures:** DDS files are DXT1 with a full mip chain (`install_pet_art.encode_dds`). Pad UV
  islands so mipmaps don't bleed pale seams.
- **Player armor:** see section 13 of `docs/CLIENT-MODDING-GUIDE.txt`. Catacombs armor skins load
  through `mskins.csv` (pskins col 6), every body variant shares one texture layout, and cloaks
  use UV set 1.
- **Rollback:** each `install` writes `install-backups/<name>-<time>/` with a `manifest.json`.
  Roll back newest-first.
