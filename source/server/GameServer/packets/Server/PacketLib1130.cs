namespace DOL.GS.PacketHandler
{
    // Reuses the 1.129 writers for the identified 1.130 client. Registration
    // enables compatibility testing; world/gameplay differences need validation.
    [PacketLib(1130, GameClient.eClientVersion.Version1130)]
    public class PacketLib1130 : PacketLib1129
    {
        public PacketLib1130(GameClient client) : base(client) { }
    }
}
