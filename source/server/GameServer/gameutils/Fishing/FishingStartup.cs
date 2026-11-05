using System;
using System.Linq;
using DOL.Database;
using DOL.Events;
using DOL.Logging;

namespace DOL.GS.Fishing;

/// <summary>
/// Adds the fishing item templates (fish, junk, the poles, camp kits and cooked food) to the database when the server starts.
/// Existing rows are left alone, so edits made in the database are kept, except the model, stack size and price of our own rows:
/// a model changed in FishingCatalog (the pole's look, say) is copied onto the existing row.
/// </summary>
public static class FishingStartup
{
    private static readonly Logger Log = LoggerManager.Create(typeof(FishingStartup));

    [GameServerStartedEvent]
    public static void OnServerStarted(DOLEvent e, object sender, EventArgs args)
    {
        int added = 0;
        int updated = 0;
        int failed = 0;

        foreach (DbItemTemplate template in FishingCatalog.AllTemplates().Concat(FishingCraft.AllTemplates()).Concat(FishingCooking.AllTemplates()))
        {
            // A client with the private rod (tools/pet-art/install_fishing_rod.py) gets it through fishing_pole_model.
            if (FishingCraft.FindPole(template.Id_nb) != null && ServerProperties.Properties.FISHING_POLE_MODEL > 0)
            {
                template.Model = ServerProperties.Properties.FISHING_POLE_MODEL;
            }

            DbItemTemplate existing = GameServer.Database.FindObjectByKey<DbItemTemplate>(template.Id_nb);

            if (existing != null)
            {
                // A template with our id but from another source (a stock quest item, say) would be handed out
                // in place of ours, so say so in the log rather than silently using it.
                if (existing.PackageID != FishingCatalog.PackageId)
                {
                    Log.Warn($"Fishing: item template '{template.Id_nb}' already exists from package '{existing.PackageID}' and is used as-is.");

                    continue;
                }

                // The client draws an item (hand mesh and bag icon) from its model alone, and inventory items read
                // the model and stack size through their template, so updating the cached row changes every existing
                // pole and fish too.
                if (existing.Model != template.Model || existing.MaxCount != template.MaxCount || existing.Price != template.Price)
                {
                    int oldModel = existing.Model;
                    int oldMaxCount = existing.MaxCount;
                    long oldPrice = existing.Price;

                    // DbItemTemplate ignores Dirty unless AllowUpdate is set, and SaveObject skips clean rows while
                    // still returning true, so without it the change would never reach the database.
                    existing.AllowUpdate = true;
                    existing.Model = template.Model;
                    existing.MaxCount = template.MaxCount;
                    existing.Price = template.Price;
                    bool saved = GameServer.Database.SaveObject(existing);
                    existing.AllowUpdate = false;

                    if (saved)
                    {
                        updated++;
                        Log.Info($"Fishing: item template '{template.Id_nb}' model {oldModel} -> {template.Model}, stack {oldMaxCount} -> {template.MaxCount}, price {oldPrice} -> {template.Price}.");
                    }
                    else
                    {
                        failed++;
                        Log.Error($"Fishing: could not save item template '{template.Id_nb}'.");
                    }
                }

                continue;
            }

            if (GameServer.Database.AddObject(template))
            {
                added++;
            }
            else
            {
                failed++;
                Log.Error($"Fishing: could not add item template '{template.Id_nb}'.");
            }
        }

        if (Log.IsInfoEnabled)
        {
            Log.Info($"Fishing: added {added} and updated {updated} item template(s) in the database ({failed} failed).");
        }
    }
}
