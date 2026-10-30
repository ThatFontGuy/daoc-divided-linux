using DOL.GS.ServerProperties;

namespace DOL.GS
{
    /// <summary>
    /// Which client class IDs the custom classes use. Unpatched clients have no slot past 62, so the
    /// custom classes borrow the Mauler slots (60 Albion, 61 Midgard, 62 Hibernia). The patched modern
    /// client (source/tools/classslots) has native slots 63-65, and the Mauler slots are real Maulers.
    /// </summary>
    public static class CustomClassSlots
    {
        public static bool IsNative(GameClient client) =>
            IsNative(Properties.NATIVE_CUSTOM_CLASS_SLOTS, client?.Version ?? GameClient.eClientVersion.VersionNotChecked);

        public static bool IsNative(bool enabled, GameClient.eClientVersion version) =>
            enabled && version >= GameClient.eClientVersion.Version1125;
    }
}
