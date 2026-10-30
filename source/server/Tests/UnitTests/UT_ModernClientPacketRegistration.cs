using System.Linq;
using System.Reflection;
using DOL.GS;
using DOL.GS.PacketHandler;
using NUnit.Framework;

namespace DOL.UnitTests;

[TestFixture]
public sealed class UT_ModernClientPacketRegistration
{
    [TestCase(1129, typeof(PacketLib1129), GameClient.eClientVersion.Version1129)]
    [TestCase(1130, typeof(PacketLib1130), GameClient.eClientVersion.Version1130)]
    public void VersionHasExactlyOneConcreteRegistration(int rawVersion, System.Type expected,
        GameClient.eClientVersion version)
    {
        var registrations = typeof(PacketLib1130).Assembly.GetTypes()
            .SelectMany(type => type.GetCustomAttributes<PacketLibAttribute>(false)
                .Where(attribute => attribute.RawVersion == rawVersion)
                .Select(attribute => (Type: type, Attribute: attribute))).ToArray();

        Assert.That(registrations, Has.Length.EqualTo(1));
        Assert.Multiple(() =>
        {
            Assert.That(registrations[0].Type, Is.EqualTo(expected));
            Assert.That(registrations[0].Attribute.ClientVersion, Is.EqualTo(version));
            Assert.That(System.Activator.CreateInstance(expected, new object[] { null }), Is.InstanceOf<IPacketLib>());
        });
    }

    [Test]
    public void UninvestigatedVersion1131IsNotRegistered()
    {
        var registered = typeof(PacketLib1130).Assembly.GetTypes()
            .SelectMany(type => type.GetCustomAttributes<PacketLibAttribute>(false));
        Assert.That(registered.Any(attribute => attribute.RawVersion == 1131), Is.False);
    }
}
