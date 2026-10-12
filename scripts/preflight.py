#!/usr/bin/env python3
"""Exhibition readiness checks for StockLens."""
import asyncio
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from app.services.snapshot_service import ASSIGNED_PAIRS, DEMO_DATA_DIR

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(label: str, passed: bool, detail: str = "") -> bool:
    mark = "\033[32mPASS\033[0m" if passed else "\033[31mFAIL\033[0m"
    print(f"[{mark}] {label}" + (f" - {detail}" if detail else ""))
    return passed


def internet_ok() -> bool:
    try:
        with urllib.request.urlopen("https://www.google.com/generate_204", timeout=5) as response:
            return response.status < 500
    except Exception:
        return False


def yahoo_ok() -> bool:
    try:
        req = urllib.request.Request("https://query1.finance.yahoo.com/v8/finance/chart/HAL.NS?range=5d&interval=1d",
                                     headers={"User-Agent": "StockLens exhibition preflight"})
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.load(response)
            return bool(payload.get("chart", {}).get("result"))
    except Exception:
        return False


def gemini_ok() -> tuple[bool, str]:
    key = settings.GEMINI_API_KEY
    if not key:
        return False, "GEMINI_API_KEY is not configured"
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return response.status == 200, "key accepted" if response.status == 200 else f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code} (key rejected or unavailable)"
    except Exception as exc:
        return False, str(exc)


def caches_warm() -> tuple[bool, str]:
    from app.services.cache import get_disk_price_cache
    tickers = sorted({p[k] for p in ASSIGNED_PAIRS for k in ("ticker1", "ticker2")})
    missing = [t for t in tickers if (lambda value: value[0] is None or value[1])(get_disk_price_cache(t))]
    return not missing, f"{len(tickers) - len(missing)}/{len(tickers)} pair tickers fresh" + (f"; missing {', '.join(missing)}" if missing else "")


def snapshots_ok() -> tuple[bool, str]:
    missing = [p["key"] for p in ASSIGNED_PAIRS
               if not (DEMO_DATA_DIR / f"{p['key']}.json").is_file()
               or (DEMO_DATA_DIR / f"{p['key']}.json").stat().st_size < 500]
    return not missing, f"{len(ASSIGNED_PAIRS) - len(missing)}/{len(ASSIGNED_PAIRS)} snapshots present" + (f"; missing {', '.join(missing)}" if missing else "")


def ports_free() -> tuple[bool, str]:
    api_port = settings.PORT if settings.PORT > 0 else 8000
    ports = sorted({api_port, int(os.getenv("VITE_PORT", "5173"))})
    busy = []
    for port in ports:
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                busy.append(str(port))
    return not busy, f"ports {', '.join(map(str, ports))} free" if not busy else f"in use: {', '.join(busy)}"


async def main() -> int:
    results = []
    results.append(check("Internet connection", internet_ok()))
    results.append(check("Yahoo Finance reachable", yahoo_ok()))
    valid_key, key_detail = gemini_ok()
    results.append(check("Gemini API key", valid_key, key_detail))
    cache_ok, cache_detail = caches_warm()
    results.append(check("Price cache warm", cache_ok, cache_detail))
    demo_ok, demo_detail = snapshots_ok()
    results.append(check("Offline snapshots", demo_ok, demo_detail))
    port_ok, port_detail = ports_free()
    results.append(check("Required ports", port_ok, port_detail))
    print(f"\n{sum(results)}/{len(results)} checks passed")
    if not cache_ok:
        print("Warm cache: python scripts/warm_cache.py")
    if not demo_ok:
        print("Build snapshots: python scripts/build_demo_snapshots.py")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
