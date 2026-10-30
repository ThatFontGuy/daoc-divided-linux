using DOL.GS;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture]
public sealed class UT_CustomClassSlots
{
    [Test]
    public void NativeSlotsOnlyForEnabledModernClients()
    {
        Assert.That(CustomClassSlots.IsNative(true, GameClient.eClientVersion.Version1130), Is.True);
        Assert.That(CustomClassSlots.IsNative(true, GameClient.eClientVersion.Version1125), Is.True);
        Assert.That(CustomClassSlots.IsNative(false, GameClient.eClientVersion.Version1130), Is.False);
        Assert.That(CustomClassSlots.IsNative(true, GameClient.eClientVersion.Version1124), Is.False, "older clients keep borrowing the Mauler slots");
        Assert.That(CustomClassSlots.IsNative(true, GameClient.eClientVersion.VersionNotChecked), Is.False);
    }

    [Test]
    public void ClassicMappingStillBorrowsMaulerSlots()
    {
        Assert.That(StormforgedRules.CreationClass((int)eCharacterClass.MaulerMid, (int)eRealm.Midgard, true), Is.EqualTo((int)eCharacterClass.Stormforged));
        Assert.That(StormforgedRules.OverviewClass((int)eCharacterClass.PendragonSovereign, (int)eRealm.Albion), Is.EqualTo((byte)eCharacterClass.MaulerAlb));
    }

    [Test]
    public void ClientSlotNumbersMatchServerClassIds()
    {
        // source/tools/classslots/patch_class_slots.py registers these exact client IDs.
        Assert.That((int)eCharacterClass.Stormforged, Is.EqualTo(64));
        Assert.That((int)eCharacterClass.PendragonSovereign, Is.EqualTo(65));
    }
}
