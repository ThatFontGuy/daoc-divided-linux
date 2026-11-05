# Play with friends

One of you **hosts**: your server runs as usual and friends join your world. The others **join**: they start only
their game client, against your server. The host sends an **invite code**, and friends paste it in. Nothing extra
needs installing, and no outside service is involved: the code simply holds the host's addresses.

You all need the same game: Classic with Classic, Stormforged with Stormforged, the modern 1.130 test with the modern
test. A code made for another game is refused. Join Friend does not support the new (Godot) client yet.

**A friend can make a new character in your world, or bring their own.** A new character stays in the host's world.
A brought character is locked in its owner's save while it visits, and goes home with what it earned. See
[Bringing your own character](#bringing-your-own-character).

## Bringing your own character

You need your own copy of the same game, with your own server stopped.

1. In **JOIN FRIEND**, fill in the code, your account and password as usual.
2. Choose a character under **Bring a character from your own save**.
3. Press **JOIN FRIEND**. The character goes to your friend's world with all its gear and the coin in that realm's
   wallet, and the game starts. Pick it on the character screen.
4. To go back, close the game, wait a moment, and press **COME HOME** with that character chosen. It returns with what it
   earned, and its coin.

A character can only be in one world at a time, so nothing can be duplicated. While it is away you can't play or delete
it at home.

- **What stays behind:** your house, guild, shared account vault and companion bots, and anything for sale on the Realm
  Exchange or in a house. Your other characters in that realm keep nothing from the wallet while the coin is away.
- **In your friend's world** a visitor can't buy a house. Before coming home it must take back anything it has for sale
  there and collect its sale money.
- **Name taken?** Type another in **Visiting name**. Your character gets its own name back at home.
- **RECALL** is for a world that has gone for good. The character comes back as it left, with the coin it carried, and
  everything it earned on that trip is lost.

## Hosting

1. In your launcher, press **HOST FOR FRIENDS**.
2. Type a password for your friends, 6 to 20 characters. It may be empty only if the internet box is unticked, so
   only your home network can join.
3. Leave **Friends outside my home can join over the internet** ticked unless everyone is in your house.
4. **START HOSTING**. Windows asks for permission the first time, for the firewall rules. Your server then starts.
   If it was already running, stop and start it.
5. **COPY CODE**, and send your friends the code and the password.

Your own ENTER REALM works the same as before. **STOP HOSTING** takes effect at the server's next start, and it
clears the password. Your previous settings are saved as
`runtime\server\config\serverconfig.before-host-for-friends.xml`.

If the window shows a message about your router:

- "Router OK (UPnP)": good, the code works from the internet.
- "Your provider shares addresses (CGNAT)": friends outside your home can't reach you. The code still works for your
  home network, and over [Tailscale](https://tailscale.com) if you both run it.
- "Your router did not answer UPnP": turn UPnP on in the router's settings, or forward the two ports to this PC by
  hand and put your internet address in `<PublicIP>` in `runtime\server\config\serverconfig.xml`.

A new code is needed when your internet address changes. Home addresses do, now and then. If friends suddenly can't
reach you, open the window and send the code it shows.

While hosting over the internet, your game port is open to any address, so the password is what keeps strangers from
making accounts. Send the code only to people you want in your world, and stop hosting when you're done. The game's
login is not encrypted, so don't reuse a password from anywhere else.

## Joining

1. Your own server doesn't need to run.
2. Press **JOIN FRIEND** in your launcher, or double-click `Join Friend.cmd` beside it.
3. Paste the invite code. A plain host address works too.
4. Choose an account name for their server. The first time, use the password your friend gave you, and their server
   creates the account. Use the same name and password each time to get back to your characters there.
5. **JOIN FRIEND**. The window tries each address in the code and starts the client on the first that answers.

Tick "Remember my password" to skip typing it next time. It's stored encrypted for your Windows user, in
`%LOCALAPPDATA%\OfflineDAoC\join-friend.json`.

## If it doesn't connect

| Message | Check |
|---|---|
| That invite code isn't right | Copy the whole code, starting with DR. |
| This code is for a different game | You both need the same game. |
| Cannot reach your friend's server | Their server has finished starting and they are hosting. Ask for a new code; their internet address may have changed. |
| The client starts but login fails | First time: the host's password. After that: the password you used the first time. |
| Logged in, but stuck when entering the world or changing region | Tell us: the UDP side (port 10400) or the region address. Session details are in your `runtime\logs\client-diagnostics.log` (look for `remote10300`). |

## How it works (for developers)

- Hosting sets `IP` and `UdpIP` to `0.0.0.0` in `serverconfig.xml` and leaves `RegionIP` at `127.0.0.1`. The
  server then tells each client the address that client connected to (`RegionAddress.ForClient`, used by the
  packet libraries), so this PC gets 127.0.0.1 and a friend gets the Tailscale or home-network address.
- `InviteCode` packs up to three IPv4 addresses, the login port and a check into Crockford base 32. Addresses go in
  the order Tailscale, internet, home network, because a home address could be some other device on the friend's
  own network. It holds no password.
- The login packet has only an account and a password, so `HostPasswordHash` in `serverconfig.xml` guards account
  creation: a new account from another PC must use the host's password (`HostPassword`, `LoginRequestHandler`).
  Existing accounts and this PC are unaffected. `HostForFriends.HashHostPassword` is the launcher's copy of the hash.
- Internet mode sets `EnableUPnP` (and `PublicIP` to `auto`; `DetectRegionIP` stays off), and needs a host password.
  At start the server maps its ports on the router to this PC's address on the router's network
  (`UpnpNat.LocalAddress`, not the first address the PC has), keeps the router's internet address as `PublicIP`, and
  removes the mapping in `BaseServer.Stop`. Only clients connecting from a public address are given `PublicIP` for
  the game connection. `UpnpNat` speaks both `WANIPConnection` and `WANPPPConnection` routers; the launcher compiles
  the same file for its router check.
- The firewall rules are tied to `CoreServer.exe` (`program=`), so Windows doesn't show its own unrestricted
  "allow access" prompt when the server first listens on the network. They admit Tailscale (100.64.0.0/10) and the
  local subnet, or any address for internet hosting. `runtime\host-for-friends.json` records which, and the script
  is kept as `runtime\host-for-friends-firewall.cmd`. The rules stay when hosting stops; they only admit
  `CoreServer.exe`, which then listens on this PC alone.
- Code: `HostForFriends.cs` / `HostForFriendsForm.cs` (host), `InviteCode.cs`, `JoinFriend.cs` / `JoinFriendForm.cs` /
  `JoinFriendProfile.cs` (guest), `Program.cs --join`. Join Friend comes from the
  [stefanrows/OfflineDAoC](https://github.com/stefanrows/OfflineDAoC) fork (its `docs/TAILSCALE_COOP.md`).
