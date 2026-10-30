# Helmet shows no face: how to fix it

**Symptom:** a character or bot wears a helmet, and the helmet floats with no face or head inside
it. Only some *extension* variants of a helmet model do this. `/gminfo` on the wearer shows the
helmet's model and extension, for example `amber cailiocht helm | model 827 | extension 2`.

**Cause:** old client helmet meshes have several variants chosen by the item's extension number.
On some meshes, certain variants hide the whole face. The same model with extension 0 renders
correctly.

## How it's fixed (display only)

The server sends the client a different extension **for display only**. Item templates, stats,
drops and saved inventories keep their real extension.

- **Code:** `source/server/GameServer/packets/Server/HelmetAppearanceCompatibility.cs`. The method
  `VisibleExtension(slot, model, extension)` uses a set of helmet models and the extensions to show
  as 0.
- **Where it's used:** two places in `PacketLib1124.cs`:
  - `SendLivingEquipmentUpdate`: how others, bots and NPCs are shown to you.
  - `WriteItemData`: your own character's worn helmet.
- **Tests:** `source/server/Tests/UnitTests/UT_HelmetAppearanceCompatibility.cs`.

**Already fixed:** the "Hib Helm 3" mesh (`items.csv` 407 `H_helm3`, Head # 4, alternates
398/404). Extensions 2 and 3 show as 0 on all 15 models that use it:

440, 827, 837, 840, 1203, 1207, 1211, 2769, 2775, 2781, 2787, 2831, 2837, 2843, 2849

Extensions 0, 1, 5 and 7 are left alone.

Also fixed: the "Hib Helm 1" mesh (`items.csv` 409 `H_helm1`, Head # 2, alternates 400/406), for
example the Celtic scale helm 838 (Animalbound Osnadur Tha Coif). Only extension 2 shows as 0, on
all 6 models that use it:

438, 835, 838, 1201, 1205, 1209

Also fixed: the Norse "NHelm3" mesh (`items.csv` 389, Head # 4, alternates 395/392), for example
the leather cap 337 (rawhide starklaedar cap), which was invisible on a Shaman companion. Only
extension 2 shows as 0, on all 11 models that use it:

337, 831, 834, 1216, 1219, 1223, 1227, 2862, 2868, 2874, 2880

## Fixing a new one

1. **Find the helmet's family.** Run `python tools/claude-version/helmet_face_check.py <model>`.
   It prints the mesh and every helmet model that shares it; they all have the same broken
   variants. It also counts the helmet items using each extension.
2. **Update the code.**
   - If the family is already covered but the extension isn't, add the extension to that family.
   - If it's a new mesh, add a new model set with its own list of broken extensions. Every mesh
     can differ.
3. **Only change what's confirmed.** Remap only extensions seen broken in game, to 0 or another
   extension confirmed to show the face.
4. **Test.** Add `TestCase` rows (broken → 0, and good extensions unchanged), then run
   `dotnet test source/server/Tests/Tests.csproj -c Release`.
5. **Deploy.** Close the launcher, the game and the server, then build `GameServer.dll` and copy it
   to `runtime/server`, `runtime/server/lib` and `runtime/server/win-x64`. Back up the old file
   first.
