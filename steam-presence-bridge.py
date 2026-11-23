#!/usr/bin/env python3
"""Send Steam and Spotify presence from Bazzite to the Personal Bio page."""

import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = Path.home() / ".config/personal-bio/steam-bridge.json"
INTERVAL = 15


def read_config():
    config = json.loads(CONFIG.read_text())
    base_url = config.get("site", "").rstrip("/")
    token = config.get("token", "")
    if not base_url.startswith("https://") or not token:
        raise RuntimeError("Config must contain an HTTPS site URL and connection token.")
    return base_url, token


def steam_roots():
    home = Path.home()
    candidates = [
        home / ".steam/steam",
        home / ".local/share/Steam",
        home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    ]
    found = []
    for path in candidates:
        try:
            resolved = path.resolve(strict=True)
            if resolved not in found and (resolved / "steamapps").is_dir():
                found.append(resolved)
        except OSError:
            pass
    return found


def library_paths():
    libraries = []
    for root in steam_roots():
        for path in [root, root / "steamapps"]:
            if path.name == "steamapps":
                libraries.append(path)
        vdf = root / "steamapps/libraryfolders.vdf"
        try:
            contents = vdf.read_text(errors="replace")
            for raw in re.findall(r'"path"\s+"((?:\\.|[^"])*)"', contents):
                decoded = raw.replace('\\\\', '\\').replace('\\"', '"')
                libraries.append(Path(decoded) / "steamapps")
        except OSError:
            pass
    return list(dict.fromkeys(path for path in libraries if path.is_dir()))


def installed_games():
    games = {}
    for library in library_paths():
        for manifest in library.glob("appmanifest_*.acf"):
            app_id = manifest.stem.removeprefix("appmanifest_")
            try:
                contents = manifest.read_text(errors="replace")
            except OSError:
                continue
            name = re.search(r'"name"\s+"((?:\\.|[^"])*)"', contents)
            if name:
                games[app_id] = name.group(1).replace('\\"', '"').replace('\\\\', '\\')
    return games


def running_game(games):
    candidates = []
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            values = {}
            for entry in (proc / "environ").read_bytes().split(b"\0"):
                if b"=" in entry:
                    key, value = entry.split(b"=", 1)
                    if key in (b"SteamAppId", b"SteamGameId", b"STEAM_COMPAT_APP_ID"):
                        values[key.decode()] = value.decode(errors="ignore")
            app_id = values.get("SteamGameId") or values.get("SteamAppId") or values.get("STEAM_COMPAT_APP_ID") or ""
            if not app_id.isdigit() or int(app_id) <= 0:
                command_line = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
                match = re.search(r"(?:^|\s)(?:AppId=|--appid[= ])(\d+)", command_line, re.IGNORECASE)
                app_id = match.group(1) if match else ""
            if not app_id.isdigit() or int(app_id) <= 0:
                continue
            stat = (proc / "stat").read_text()
            start_ticks = int(stat[stat.rfind(")") + 2:].split()[19])
            candidates.append((start_ticks, app_id))
        except (OSError, ValueError, IndexError, PermissionError):
            continue
    if not candidates:
        return None
    _, app_id = max(candidates)
    return {"gameId": app_id, "game": games.get(app_id, f"Steam game {app_id}")}


def steam_client_running():
    """Report whether the Steam client process is open in this user session."""
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            name = (proc / "comm").read_text().strip().lower()
            if name in {"steam", "steamwebhelper"}:
                return True
        except (OSError, PermissionError):
            continue
    return False


def send_presence(site, token, game):
    payload = {"online": steam_client_running(), "playing": bool(game), "game": game["game"] if game else "", "gameId": game["gameId"] if game else ""}
    request = urllib.request.Request(
        site + "/api/steam/presence",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def spotify_track():
    """Read the Spotify desktop player's current track through MPRIS/playerctl."""
    if not shutil.which("playerctl"):
        raise RuntimeError("playerctl is missing; install it on Bazzite to enable Spotify presence.")
    try:
        status = subprocess.run(
            ["playerctl", "--player=spotify", "status"],
            capture_output=True, text=True, timeout=4, check=True,
        ).stdout.strip().lower()
        if status != "playing":
            return None
        output = subprocess.run(
            ["playerctl", "--player=spotify", "--format",
             "{{title}}\t{{artist}}\t{{album}}\t{{mpris:artUrl}}\t{{xesam:url}}", "metadata"],
            capture_output=True, text=True, timeout=4, check=True,
        ).stdout.strip()
        fields = (output.split("\t", 4) + [""] * 5)[:5]
        title, artist, album, art_url, media_url = (value.strip() for value in fields)
        if not title:
            return None
        if not re.match(r"^https://i\.scdn\.co/", art_url, re.IGNORECASE):
            art_url = ""
        spotify_url = ""
        match = re.match(r"^(?:https://open\.spotify\.com/|spotify:)(track|episode)[/:]([A-Za-z0-9]+)", media_url, re.IGNORECASE)
        if match:
            spotify_url = f"https://open.spotify.com/{match.group(1).lower()}/{match.group(2)}"
        return {"playing": True, "song": title, "artist": artist, "album": album, "albumArtUrl": art_url, "spotifyUrl": spotify_url}
    except subprocess.CalledProcessError:
        return None
    except subprocess.TimeoutExpired:
        return None


def send_spotify_presence(site, token, track):
    payload = track or {"playing": False}
    request = urllib.request.Request(
        site + "/api/spotify/presence",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()


def main():
    site, token = read_config()
    print("Steam and Spotify presence bridge is running.", flush=True)
    last_error = ""
    while True:
        try:
            game = running_game(installed_games())
            send_presence(site, token, game)
            send_spotify_presence(site, token, spotify_track())
            last_error = ""
        except (OSError, ValueError, urllib.error.URLError, RuntimeError) as error:
            message = str(error)
            if message != last_error:
                print(f"Could not update presence: {message}", flush=True)
                last_error = message
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
