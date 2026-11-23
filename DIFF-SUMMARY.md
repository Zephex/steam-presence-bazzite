# Diff summary — originals vs `patched/`

This is a quick map of what changed. Full rationale is in `SECURITY-REVIEW.md`.
The originals in this folder are byte-identical to the downloaded bundle;
run `./verify-originals.sh` to confirm.

## `install-steam-bridge.sh`

| Location | Original | Patched | Why |
|---|---|---|---|
| line 9 | `[[ "$BIO_SITE" != https://* ]]` | `urlparse` check requiring scheme `https`, host `example.com`, no userinfo | Blocks `https://example.com@evil.com` token leak (finding 1) |
| line 35 | `BIO_SITE=... BIO_TOKEN=... python3 - ...` heredoc | token fed on stdin via `printf | python3 -c` | Keeps secret out of child `/proc/<pid>/environ` (finding 2) |
| lines 43-46 | `open(path,"w")` then `os.chmod(path,0o600)` | `os.open(...,0o600)` + `os.fchmod` before writing | Fixes permissive window on a pre-existing config (finding 3) |
| line 49 | `install -m 755` for the bridge | `install -m 700` | Minor least-privilege tightening |

## `steam-presence-bridge.py`

| Location | Original | Patched | Why |
|---|---|---|---|
| imports | `import shutil` | `import stat as statmod` | Supports config checks |
| constants | — | `PLAYERCTL = "/usr/bin/playerctl"` | Pins the executable path |
| `read_config()` | reads file directly | `lstat()` check: regular file, owned by you, no group/other bits | Rejects symlink / loose permissions (finding 3) |
| `spotify_track()` | `shutil.which("playerctl")`, calls by bare name | `isfile`/`access` check, calls use `PLAYERCTL` | Prevents PATH hijacking (finding 4) |

Network payloads, API endpoints, polling interval, game detection, and MPRIS
parsing are otherwise unchanged.

## `personal-bio-steam-bridge.service`

Added hardening only — no change to `ExecStart`, restart behavior, or install target:

`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome=read-only`,
`ProtectKernelTunables`, `ProtectKernelModules`, `ProtectControlGroups`,
`RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`, `RestrictSUIDSGID`,
`LockPersonality` (finding 5).

## `README.txt`

Line 11: removed the duplicated "reboot to apply it, reboot to apply it" (finding 6).

## Validation performed

- `bash -n` passed on both installer versions.
- Both Python files parsed cleanly with `ast.parse` (no execution).
- Patched scripts retain executable permissions (`755`).
- Nothing was installed or run against the live site.
