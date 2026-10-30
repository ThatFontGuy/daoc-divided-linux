# Play with friends

One of you **hosts**: your server runs as usual and friends join your world. The others **join**: they start only
their game client, against your server. You connect in one of three ways:

| Way | Installs | Router | Works for |
|---|---|---|---|
| Home network | nothing | nothing | friends in your house |
| [Tailscale](https://tailscale.com) (a free private network between your PCs) | Tailscale on every PC | nothing | nearly everyone |
| Internet mode | nothing | opened by the server (UPnP) while it runs, for the friends you list | hosts whose internet address isn't shared (see [Internet mode](#internet-mode-no-tailscale)) |

You all need the same game: Classic with Classic, Stormforged with Stormforged, the modern 1.130 test with the modern
test. Join Friend does not support the new (Godot) client yet.

**Characters stay in the host's world.** A friend makes a new character on your server, and it is saved in your
world, not theirs. Taking your own character along and back is the next step:
[CHARACTER-PASSPORT.md](CHARACTER-PASSPORT.md).

## Once, on both PCs

1. Install Tailscale and sign in.
2. Make the host PC reachable to the friend: either both sign in to the same tailnet, or the host shares their PC
   with the friend (Tailscale admin console → the PC → Share).

Friends in the same house can skip Tailscale and use the host PC's home-network address (192.168.x.x or 10.x.x.x).

## Hosting

1. In your launcher, press **HOST FOR FRIENDS**.
2. **TURN ON**. The server will listen on Tailscale and your home network as well as this PC. Your previous settings
   are saved as `runtime\server\config\serverconfig.before-host-for-friends.xml`.
3. **ADD FIREWALL RULES** (once). Windows asks for permission. The rules let in TCP 10300 and UDP 10400 (the modern
   test uses its own login port) for this game's `CoreServer.exe` only, and only from Tailscale (100.64.0.0/10) and
   your local subnet. The script is kept as `runtime\host-for-friends-firewall.cmd` if you'd rather run it yourself.
4. Start the server (or stop and start it, if it was running).
5. **COPY ADDRESS** and send it to your friend.

Your own ENTER REALM works the same as before. To stop hosting, **TURN OFF** (the server listens on this PC only
again after its next start) and, if you like, **REMOVE FIREWALL RULES**.

## Internet mode (no Tailscale)

For friends who'd rather not install anything. Hosting must be on first.

1. **INTERNET: TURN ON**. The window asks your router for your internet address:
   - "Router OK (UPnP). Friends join at …": good, that's the address to send.
   - "Your provider shares addresses (CGNAT)": internet mode can't work on your connection. Use Tailscale.
   - "Your router did not answer UPnP": turn UPnP on in the router's settings, or forward the two ports to this PC
     by hand and put your internet address in `<PublicIP>` in `runtime\server\config\serverconfig.xml`.
2. Each friend searches "what is my IP" and sends you the address. Type them into the box, separated by commas.
3. **UPDATE FIREWALL RULES** (Windows asks). Only those addresses, Tailscale and your home network get in. When a
   friend's address changes (home addresses do, now and then), update the list and the rules again.
4. Start (or restart) the server. While it runs, it opens TCP 10300 / UDP 10400 on your router (the modern test:
   10330 / 10430), and it closes them when it stops normally.
5. **COPY ADDRESS** copies your internet address for your friend's JOIN FRIEND.

The game's login isn't encrypted the way Tailscale's tunnel is. Keep the friend list short and turn internet mode
off when you're done playing.

## Joining

1. Your own server doesn't need to run.
2. Press **JOIN FRIEND** in your launcher, or double-click `Join Friend.cmd` beside it.
3. Enter the host's address, then an account name and password **for their server**. The first time, their server
   creates the account. Use the same name and password each time to get back to your characters there.
4. **JOIN FRIEND**. The window checks the host can be reached before starting the client.

Tick "Remember my password" to skip typing it next time. It's stored encrypted for your Windows user, in
`%LOCALAPPDATA%\OfflineDAoC\join-friend.json`.

## If it doesn't connect

| Message | Check |
|---|---|
| Cannot reach the host | Tailscale is on for both of you, the host's server is running with hosting on, and the host added the firewall rules. |
| The client starts but login fails | The account name and password for the host's server. A different password from the first time is refused. |
| Internet mode: cannot reach the host | Your address is in the host's friend list and they updated the firewall rules; the host's server log shows `[UPNP] Router forwards …` at start. |
| Logged in, but stuck when entering the world or changing region | Tell us: the UDP side (port 10400) or the region address. Session details are in your `runtime\logs\client-diagnostics.log` (look for `remote10300`). |

## How it works (for developers)

- Hosting sets `IP` and `UdpIP` to `0.0.0.0` in `serverconfig.xml` and leaves `RegionIP` at `127.0.0.1`. The
  server then tells each client the address that client connected to (`RegionAddress.ForClient`, used by the
  packet libraries), so this PC gets 127.0.0.1 and a friend gets the Tailscale or home-network address.
- Internet mode sets `EnableUPnP` (and `PublicIP` to `auto`; `DetectRegionIP` stays off). At start the server maps
  its ports on the router to this PC's address on the router's network (`UpnpNat.LocalAddress`, not the first
  address the PC has), keeps the router's internet address as `PublicIP`, and removes the mapping in
  `BaseServer.Stop`. Only clients connecting from a public address are given `PublicIP` for the game connection.
  `UpnpNat` speaks both `WANIPConnection` and `WANPPPConnection` routers; the launcher compiles the same file for
  its router check. The friend list is `runtime\host-for-friends.json`.
- The firewall rules are tied to `CoreServer.exe` (`program=`), so Windows doesn't show its own unrestricted
  "allow access" prompt when the server first listens on the network.
- Code: `HostForFriends.cs` / `HostForFriendsForm.cs` (host), `JoinFriend.cs` / `JoinFriendForm.cs` /
  `JoinFriendProfile.cs` (guest), `Program.cs --join`. Join Friend comes from the
  [stefanrows/OfflineDAoC](https://github.com/stefanrows/OfflineDAoC) fork (its `docs/TAILSCALE_COOP.md`).
