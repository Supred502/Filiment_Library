#!/usr/bin/env python3
"""Pull the Bambu Filament Manager spool list from your Bambu account and save it as filaments.json.

Run: python3 bambu_sync.py          (first run asks for your Bambu login)
     python3 bambu_sync.py --push   (also commits and pushes filaments.json to GitHub)

The login token is kept in ~/.config/filament-sync/token (only readable by you), never in this repo.
Bambu has no official API for this; the address comes from Bambu Studio's source (`/my/filament/v2`).
"""
import getpass, json, subprocess, sys, urllib.error, urllib.request
from pathlib import Path

API = "https://api.bambulab.com"
SPOOLS_PATH = "/v1/design-user-service/my/filament/v2"
TOKEN_FILE = Path.home() / ".config/filament-sync/token"
DEBUG_FILE = Path.home() / ".cache/filament-sync/last_response.json"
# Colour names live in Bambu Studio's own table (the API only returns hex codes).
COLOR_TABLES = [
    Path("/var/lib/flatpak/app/com.bambulab.BambuStudio/current/active/files/share/BambuStudio/profiles/BBL/filament/filaments_color_codes.json"),
    Path.home() / ".local/share/flatpak/app/com.bambulab.BambuStudio/current/active/files/share/BambuStudio/profiles/BBL/filament/filaments_color_codes.json",
    Path.home() / ".config/BambuStudio/system/BBL/filament/filaments_color_codes.json",
]
OUT = Path(__file__).resolve().parent / "filaments.json"


def call(method, path, body=None, token=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "bambu_network_agent/01.09.05.01")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


def login():
    if not sys.stdin.isatty():  # running from the daily timer: nobody can type a code
        msg = "Bambu login expired. Run: python3 bambu_sync.py --push in a terminal."
        subprocess.run(["notify-send", "Filament library", msg])
        sys.exit(msg)
    email = input("Bambu account email: ").strip()
    password = getpass.getpass("Password (leave empty if you sign in with Google/Apple — a code will be emailed): ")
    status, d = call("POST", "/v1/user-service/user/login", {"account": email, "password": password}) if password else (0, {"loginType": "verifyCode"})
    if not d.get("accessToken") and d.get("loginType") == "verifyCode":
        sent, _ = call("POST", "/v1/user-service/user/sendemail/code", {"email": email, "type": "codeLogin"})
        if sent != 200:
            sys.exit(f"Bambu would not send a login code (HTTP {sent}). Tell Claude.")
        status, d = call("POST", "/v1/user-service/user/login", {"account": email, "code": input("Code from your email: ").strip()})
    if not d.get("accessToken"):
        sys.exit(f"Login failed (HTTP {status}). If your account uses two-step verification or Google/Apple sign-in, tell Claude.")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.touch(mode=0o600)
    TOKEN_FILE.write_text(d["accessToken"])
    return d["accessToken"]


def fetch_spools(token):
    spools, offset = [], 0
    while True:
        status, d = call("GET", f"{SPOOLS_PATH}?offset={offset}&limit=50", token=token)
        if status == 401:
            return None
        DEBUG_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEBUG_FILE.write_text(json.dumps(d, indent=2))
        if status != 200 or not isinstance(d.get("hits"), list):
            sys.exit(f"Bambu answered HTTP {status} in an unexpected shape; saved to {DEBUG_FILE} — show it to Claude.")
        spools += d["hits"]
        if len(d["hits"]) < 50:
            return spools
        offset += 50


def color_names():
    table = next((p for p in COLOR_TABLES if p.exists()), None)
    if not table:
        print("Bambu Studio colour table not found; using material names instead of colour names.")
        return {}
    data = json.loads(table.read_text())["data"]
    return {(e["fila_id"], c.upper()): e["fila_color_name"]["en"] for e in data for c in e["fila_color"]}


def to_public(s, names):
    # The output file is public: only what the page shows, never printer/tag/account IDs.
    return {
        "name": names.get((s["filamentId"], s["color"].upper())) or s.get("displayName") or s["filamentName"],
        "brand": s["filamentVendor"],
        "material": s["filamentName"],
        "type": s["filamentType"],
        "color": s["color"],
        "remain": s["netWeight"],
        "total": s["totalNetWeight"],
    }


def main():
    token = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else login()
    spools = fetch_spools(token)
    if spools is None:  # token expired
        spools = fetch_spools(login())
        if spools is None:
            sys.exit("Bambu rejected the new login token.")
    names = color_names()
    spools = [to_public(s, names) for s in spools if not s.get("depleted")]
    if not spools:
        sys.exit("Bambu returned no spools; not overwriting filaments.json.")
    OUT.write_text(json.dumps({"spools": spools}, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {len(spools)} spools to {OUT.name}")
    if "--push" in sys.argv:
        repo = OUT.parent
        subprocess.run(["git", "-C", repo, "add", OUT.name], check=True)
        if subprocess.run(["git", "-C", repo, "diff", "--cached", "--quiet"]).returncode:
            subprocess.run(["git", "-C", repo, "commit", "-qm", "Update filament list"], check=True)
            subprocess.run(["git", "-C", repo, "push", "-q"], check=True)
            print("Pushed — the page updates in a minute or two.")
        else:
            print("No changes since last time.")


if __name__ == "__main__":
    main()
