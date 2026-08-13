#!/usr/bin/env python3
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / "capacitor.config.json").read_text(encoding="utf-8"))
errors = []
if config.get("appId") != "de.aplussolution.smarbiz": errors.append("Unexpected appId")
if config.get("appName") != "Smarbiz": errors.append("Unexpected appName")
server_url = str((config.get("server") or {}).get("url") or "")
if not server_url.startswith("https://smarbiz.sbs/"): errors.append("Native app must load the HTTPS Smarbiz production origin")
for relative in ("www/index.html", "assets/icon.svg", "assets/splash.svg"):
    if not (ROOT / relative).exists(): errors.append(f"Missing {relative}")
local_bundle = " ".join((ROOT / p).read_text(encoding="utf-8", errors="ignore").lower() for p in ("www/index.html", "www/app.css"))
for forbidden in ("google play", "play store"):
    if forbidden in local_bundle: errors.append(f"iOS-shared native bundle contains distribution-platform reference: {forbidden}")
if not os.getenv("SMARBIZ_SKIP_LIVE"):
    for url in ("https://smarbiz.sbs/api/health", "https://smarbiz.sbs/de/privacy", "https://smarbiz.sbs/de/support", "https://smarbiz.sbs/de/account-deletion"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SmarbizStoreReadiness/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status >= 400: errors.append(f"{url} returned {response.status}")
        except Exception as exc: errors.append(f"{url} unavailable: {exc}")
if errors:
    print("Store readiness failed:", file=sys.stderr)
    for error in errors: print(f"- {error}", file=sys.stderr)
    raise SystemExit(2)
print("Smarbiz native/store readiness checks passed.")
