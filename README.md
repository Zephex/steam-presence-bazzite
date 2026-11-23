# Steam + Spotify presence bridge for Bazzite

A reference copy of a small user-level systemd service that reports your current
Steam game and Spotify track to a personal bio page, together with a security
review and hardened copies of the original files.

**Status:** reference and review artifact. The originals are unchanged from the
downloaded bundle and the patched copies have not been field-tested on Bazzite.

## How it works

Every 15 seconds the bridge:

1. Detects the running Steam game from `/proc` and the installed app manifests.
2. Reads Spotify playback through MPRIS with `playerctl`.
3. POSTs both to `https://example.com/api/{steam,spotify}/presence` using a bearer
   token stored in `~/.config/personal-bio/steam-bridge.json` (mode `0600`).

It reuses the existing Steam companion service and connection token, and does
not need a Spotify Developer app or Discord to be running.

## Contents

| Path | Description |
|---|---|
| `README.txt` | Original bundle instructions (untouched) |
| `install-steam-bridge.sh` | Original installer (untouched) |
| `steam-presence-bridge.py` | Original polling service (untouched) |
| `personal-bio-steam-bridge.service` | Original systemd user unit (untouched) |
| `SECURITY-REVIEW.md` | Findings, severity table, and what the code does well |
| `DIFF-SUMMARY.md` | Line-level map of every original → patched change |
| `verify-originals.sh` | Checks the originals against embedded SHA-256 baselines |
| `patched/` | Hardened copies of all four original files |

## Install (originals)

1. Update the bio page server with `personal-bio-steam-spotify.tar.gz` first.
2. Sign in at <https://example.com/admin>, open **Steam and Spotify presence**, and
   create a new connection token. Creating a new token invalidates the old one.
3. Make sure `playerctl` is installed: `playerctl --version`.
4. Extract the bundle, open a terminal in its folder, and run
   `./install-steam-bridge.sh`.
5. Enter `https://example.com`. Press Enter at the token prompt to reuse the token
   already saved by the existing bridge, or paste a new one.

If `playerctl` is missing, Bazzite can layer the Fedora package with
`rpm-ostree install playerctl`, then reboot and run
`systemctl --user restart personal-bio-steam-bridge`. Package layering is a last
resort because it adds a system package and requires a reboot; see the
[Bazzite rpm-ostree docs](https://docs.bazzite.gg/Installing_and_Managing_Software/rpm-ostree/).

The service starts at sign-in. Spotify presence is cleared while playback is
paused or stopped. Revoke the connection token in the admin panel to disconnect
both Steam and Spotify.

```bash
systemctl --user status personal-bio-steam-bridge
systemctl --user restart personal-bio-steam-bridge
```

## Security review

No critical or high-severity issues were found. Full details are in
[`SECURITY-REVIEW.md`](SECURITY-REVIEW.md).

| # | Severity | Finding |
|---|---|---|
| 1 | Low–Medium | HTTPS prefix check accepts userinfo URLs, so the token can be sent to an attacker host |
| 2 | Low | Connection token passed through the child process environment |
| 3 | Low | Config permissions applied after the write |
| 4 | Low | `playerctl` resolved through a user-writable `PATH` |
| 5 | Low | systemd unit has no sandboxing |
| 6 | Cosmetic | Duplicated "reboot to apply it" in `README.txt` |

### Hardened copies

`patched/` contains fixed versions of all four files:

- **Installer** — strict URL validation (scheme `https`, host `example.com`, no
  userinfo), token passed on stdin instead of `env`, mode `0600` set at file
  creation, installed script tightened to `700`.
- **Bridge** — refuses a config that is a symlink, not owned by you, or
  group/world-accessible; pins `playerctl` to `/usr/bin/playerctl`.
- **Service** — adds `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`,
  `ProtectHome=read-only`, `RestrictAddressFamilies`, and related hardening.
- **README.txt** — removes the duplicated reboot phrase.

Behavioral differences to be aware of:

- The patched installer hard-requires host `example.com`; change the constant if
  you use another domain.
- The patched bridge expects `playerctl` at `/usr/bin/playerctl`; adjust
  `PLAYERCTL` if yours is installed elsewhere.

## Verify the originals

```bash
./verify-originals.sh                  # SHA-256 baselines
./verify-originals.sh /path/to/bundle  # also cmp against a live source folder
```

Exits `0` only if every checked file passes every applicable check.

## Caveats

- The originals came from a ChatGPT-generated bundle. Verify the source before
  running the installer on a real machine.
- The bridge intentionally transmits your current game and listening activity
  to `example.com` every 15 seconds. Anyone who obtains the bearer token can spoof
  your presence; revoke it in the admin panel to disconnect.
- Review artifacts only: nothing here was executed, installed, or connected to
  the live site during the review.
