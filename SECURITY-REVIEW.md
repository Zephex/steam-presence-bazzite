# Security review — Steam + Spotify presence bridge

**Date:** 2026-11-17
**Scope:** static review only. Nothing was executed, installed, or connected to `example.com`.
**Files reviewed:** `README.txt`, `install-steam-bridge.sh`, `personal-bio-steam-bridge.service`, `steam-presence-bridge.py`.
**Patched copies:** see `patched/`. The originals in this folder are unchanged.

## Summary

| # | Severity | Finding | File |
|---|----------|---------|------|
| 1 | Low–Medium | HTTPS check accepts userinfo URLs; token can be sent to an attacker host | `install-steam-bridge.sh:9` |
| 2 | Low | Connection token passed via child process environment | `install-steam-bridge.sh:35` |
| 3 | Low | Config permissions set after write | `install-steam-bridge.sh:43-46` |
| 4 | Low | `playerctl` resolved via user-writable `PATH` | `steam-presence-bridge.py:131` |
| 5 | Low | systemd unit has no sandboxing / hardening directives | `*.service` |
| 6 | Cosmetic | Duplicated "reboot to apply it" | `README.txt:11` |

No critical or high-severity issues found.

## Details

### 1. Low–Medium — HTTPS validation bypass leaks the token

```bash
if [[ "$BIO_SITE" != https://* ]]; then
```

A URL such as `https://example.com@evil.com` satisfies this prefix check. Python's `urllib` treats `evil.com` as the hostname and still sends our explicit `Authorization: Bearer <token>` header to it. A user only has to be convinced to paste that URL at the prompt.

**Fix:** parse with `urllib.parse.urlparse` and require `scheme == "https"`, `hostname == "example.com"`, and no `username`/`password`. Applied in `patched/install-steam-bridge.sh`.

### 2. Low — token in process environment

`BIO_SITE=... BIO_TOKEN=... python3 - ...` exposes the secret in `/proc/<pid>/environ` for the lifetime of that short-lived process, readable by other processes of the same user.

**Fix:** feed the token to the child on stdin (`python3 -c ...`) instead of in `env`. Applied in `patched/install-steam-bridge.sh`.

### 3. Low — permissions applied after write

`open(path, "w")` followed by `os.chmod(path, 0o600)`: new files are already 0600 because of `umask 077`, but a **pre-existing** world-readable config stays readable during the write.

**Fix:** `os.open(..., 0o600)` + `os.fchmod` before writing. Applied in `patched/install-steam-bridge.sh`. The patched Python bridge also refuses to load a config that is a symlink, not owned by the user, or group/world-accessible.

### 4. Low — `playerctl` from `PATH`

`shutil.which("playerctl")` then executing by bare name means a fake `playerctl` dropped in a `PATH` directory such as `~/.local/bin` would be executed by the long-running service.

**Fix:** pin to `/usr/bin/playerctl` (where Bazzite's layered Fedora package installs it), with an explicit executable check. Applied in `patched/steam-presence-bridge.py`. Adjust `PLAYERCTL` if you install it elsewhere.

### 5. Low — no systemd sandboxing

The unit runs with the full privileges of your user session, so a compromise of the Python process is uncontained.

**Fix:** add `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome=read-only`, `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`, `RestrictSUIDSGID`, `LockPersonality`. The bridge only reads files, so these do not break its function; `AF_UNIX` is needed for MPRIS/D-Bus. Applied in `patched/personal-bio-steam-bridge.service`.

### 6. Cosmetic

`README.txt` line 11 says "reboot to apply it, reboot to apply it". Fixed in `patched/README.txt`.

## Done well

- HTTPS is enforced and Python's default TLS certificate verification is active.
- Token is sent in an `Authorization` header, not in the URL or query string.
- Config is written with `umask 077` and mode 0600; token input is hidden with `read -s`.
- No `shell=True`; all subprocess calls use argument lists, so no command injection.
- MPRIS metadata is constrained before being sent (art URL must be on `i.scdn.co`; Spotify URL must match a track/episode pattern).
- Runs as a **user** service, not root.

## By design / operational notes (not flaws)

- The bridge intentionally transmits your current game and listening activity to `example.com` every 15 seconds. Anyone obtaining the bearer token can spoof your presence; revoke it in the admin panel to disconnect.
- `/proc/*/environ` is scanned, but only `SteamAppId`, `SteamGameId`, and `STEAM_COMPAT_APP_ID` are extracted.
- Source integrity: these files came from a ChatGPT-generated bundle. The patched copies are review artifacts; verify the bundle source before ever running the installer on a real machine.
