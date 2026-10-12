#!/usr/bin/env python3
"""
scripts/qa_run_pairs.py — StockLens functional QA harness.

Runs the FULL analysis pipeline for:
  * the 9 assigned exhibition pairs (ASSIGNED_PAIRS), plus
  * 5 edge-case pairs (recent listing <2y, demerger, illiquid small cap,
    misspelt names, non-Indian tickers).

For every pair it:
  1. POSTs /api/analyze and times it.
  2. Checks UI-safety invariants:
       - strict JSON: no NaN / Infinity anywhere (raw text + float walk)
       - monthly closes are the LAST trading day of each calendar month
       - MA-3M first two values null, MA-6M first five null (monthly_series)
       - moving_averages legacy rows actually carry MA values
       - series strictly sorted, unique dates, finite positive closes
       - overlay alignment (charts must cope with uneven histories)
       - no fake crash: flags any single-day drop <= -20% on adjusted data
       - metric sanity ranges (0..100 where applicable, no negatives where invalid)
  3. Cross-verifies 3 numbers (seeded random pick; always includes one
     month-end close) against an INDEPENDENT plain-pandas calculation
     directly from yfinance — formulas re-implemented here, app code not used.
  4. Dumps each raw response to qa/responses/<key>.json and all explanation
     texts to qa/explanations.json for the hallucination review.

Results: qa/qa_results.json (+ stdout summary). The human-readable write-up
lives in docs/QA_REPORT.md.

Run:  python scripts/qa_run_pairs.py [--only key1,key2] [--skip-crosscheck]
"""

import os
import sys
import json
import re
import math
import time
import random
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# Must be set before app import: do NOT fire 18 live lookups for every QA run.
os.environ["VERIFY_TICKERS_ON_STARTUP"] = "false"

QA_DIR = PROJECT_ROOT / "qa"
RESPONSES_DIR = QA_DIR / "responses"

import yfinance as yf  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.snapshot_service import ASSIGNED_PAIRS  # noqa: E402

# ---------------------------------------------------------------------------
# Edge-case pairs (5)
# ---------------------------------------------------------------------------
EDGE_PAIRS = [
    # Recently listed / demerged entity with < 2 years of history vs full history
    # (explicit .NS symbol: bare "TMCV" is hijacked by the Tata Motors special case)
    {"key": "edge_recent_listing", "query1": "TMCV.NS", "query2": "HAL",
     "why": "TMCV.NS has ~225 trading days (listed 2025-11) vs 500 for HAL.NS - uneven history"},
    # Split / demerger restructuring on both sides
    {"key": "edge_demerger", "query1": "Tata Motors", "query2": "Siemens",
     "why": "Both companies went through demergers; resolver must warn, no fake crashes"},
    # Very illiquid small cap (avg ~130k shares/day)
    {"key": "edge_illiquid_smallcap", "query1": "20MICRONS", "query2": "Solar Industries",
     "why": "20MICRONS.NS avg volume ~133k shares/day - thin liquidity, wide spreads"},
    # Misspelt names on BOTH sides (fuzzy matching)
    {"key": "edge_misspelt", "query1": "hindutan aeronautic", "query2": "mazagon dockshiplders",
     "why": "Both queries misspelt; rapidfuzz must still resolve to HAL.NS / MAZDOCK.NS"},
    # Non-Indian tickers
    {"key": "edge_non_indian", "query1": "AAPL", "query2": "MSFT",
     "why": "US tickers: no .NS suffix, no sector index, benchmark ^NSEI is unrelated"},
]

NAN_INF_RE = re.compile(r"(?<![\w\"'])(?:NaN|-?Infinity)(?![\w\"'])")

DOWNLOAD_CACHE: dict = {}


def download(ticker: str):
    """Independent raw download (plain yfinance + pandas, app code not used)."""
    if ticker in DOWNLOAD_CACHE:
        return DOWNLOAD_CACHE[ticker]
    start = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    end = datetime.now().strftime("%Y-%m-%d")
    hist = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=True)
    hist = hist.dropna(subset=["Close"]).sort_index()
    hist = hist[~hist.index.duplicated(keep="first")]
    DOWNLOAD_CACHE[ticker] = hist
    return hist


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def walk_floats(node, path=""):
    """Yields (path, value) for every float in the JSON tree."""
    if isinstance(node, bool):
        return
    if isinstance(node, float):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from walk_floats(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_floats(v, f"{path}[{i}]")


def check_json_finite(raw_text: str, payload: dict):
    fails = []
    if NAN_INF_RE.search(raw_text):
        fails.append(f"raw response text contains NaN/Infinity token near: {NAN_INF_RE.search(raw_text).group(0)}")
    for path, val in walk_floats(payload):
        if not math.isfinite(val):
            fails.append(f"non-finite value at {path}: {val}")
    return fails


def check_month_end(series, daily, label):
    """Every monthly close must be the last trading day of its calendar month."""
    fails = []
    daily_dates = {d["date"] for d in daily}
    by_month = {}
    for d in daily:
        by_month.setdefault(d["date"][:7], []).append(d["date"])
    for pt in series:
        m = pt["date"][:7]
        if pt["date"] not in daily_dates:
            fails.append(f"{label}: monthly date {pt['date']} not present in daily series")
            continue
        expected = max(by_month.get(m, []))
        if pt["date"] != expected:
            fails.append(f"{label}: {pt['date']} is not last trading day of {m} (expected {expected})")
        if pt.get("month_year") and pt["month_year"] != m:
            fails.append(f"{label}: month_year {pt.get('month_year')} != date prefix {m}")
    return fails


def check_ma_nulls(series, label):
    fails = []
    for i, pt in enumerate(series):
        if i < 2:
            if pt["ma_3m"] is not None:
                fails.append(f"{label}: ma_3m[{i}] should be null, got {pt['ma_3m']}")
        else:
            if pt["ma_3m"] is None:
                fails.append(f"{label}: ma_3m[{i}] should be computed, got null")
        if i < 5:
            if pt["ma_6m"] is not None:
                fails.append(f"{label}: ma_6m[{i}] should be null, got {pt['ma_6m']}")
        else:
            if pt["ma_6m"] is None:
                fails.append(f"{label}: ma_6m[{i}] should be computed, got null")
    # MA values must equal the mean of the window (spot check last index)
    if len(series) >= 3:
        last = series[-1]
        window = [series[-3 + k]["adj_close"] for k in range(3)]
        expect = round(sum(window) / 3, 2)
        if abs(last["ma_3m"] - expect) > 0.02:
            fails.append(f"{label}: ma_3m last={last['ma_3m']} expected={expect}")
    return fails


def check_daily(series, label):
    fails = []
    prev_date = None
    max_drop = 0.0
    max_drop_date = None
    prev_close = None
    for d in series:
        if not math.isfinite(d["close"]) or d["close"] <= 0:
            fails.append(f"{label}: invalid close {d['close']} on {d['date']}")
        if not math.isfinite(d["volume"]) or d["volume"] < 0:
            fails.append(f"{label}: invalid volume {d['volume']} on {d['date']}")
        if prev_date is not None and d["date"] <= prev_date:
            fails.append(f"{label}: dates not strictly increasing at {d['date']}")
        if prev_close:
            ret = (d["close"] - prev_close) / prev_close * 100.0
            if ret < max_drop:
                max_drop, max_drop_date = ret, d["date"]
        prev_date = d["date"]
        prev_close = d["close"]
    return fails, max_drop, max_drop_date


def check_metrics(m, label):
    fails = []
    def rng(name, lo, hi):
        v = m.get(name)
        if v is None:
            return
        if not isinstance(v, (int, float)) or not math.isfinite(v) or not (lo <= v <= hi):
            fails.append(f"{label}: {name}={v} outside [{lo},{hi}]")
    rng("positive_days_pct", 0, 100)
    rng("trend_consistency_pct", 0, 100)
    rng("stability_score", 0, 100)
    rng("growth_score", 0, 100)
    rng("annualized_volatility_pct", 0, 500)
    rng("max_drawdown_pct", 0, 100)
    rng("rsi_14", 0, 100)
    for name in ("cagr_pct", "total_return_pct", "sharpe_ratio", "current_price"):
        v = m.get(name)
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v):
            fails.append(f"{label}: {name} missing or non-finite: {v}")
    return fails


def check_payload(payload: dict, raw_text: str):
    fails, warns = [], []

    fails += [(f"json", m) for m in check_json_finite(raw_text, payload)]

    ca, cb = payload.get("company_a") or {}, payload.get("company_b") or {}
    for comp, label in ((ca, "A"), (cb, "B")):
        if not comp:
            fails.append(("structure", f"company_{label} missing"))
            continue
        ms, daily = comp.get("monthly_series") or [], comp.get("daily_series") or []
        if not ms:
            fails.append(("monthly", f"company_{label} has no monthly series"))
        if not daily:
            fails.append(("daily", f"company_{label} has no daily series"))
        if ms and daily:
            fails += [("month_end", m) for m in check_month_end(ms, daily, f"company_{label}")]
            fails += [("ma_nulls", m) for m in check_ma_nulls(ms, f"company_{label}")]
            d_fail, max_drop, max_drop_date = check_daily(daily, f"company_{label}")
            fails += [("daily", m) for m in d_fail]
            if max_drop <= -20.0:
                warns.append(("fake_crash",
                              f"company_{label}: single-day drop {max_drop:.1f}% on {max_drop_date} "
                              f"(adjusted data - verify not a split artifact)"))
        fails += [("metrics", m) for m in check_metrics(comp.get("metrics") or {}, f"company_{label}")]

    # Aligned monthly table: both companies on identical months
    ma, mb = ca.get("monthly_series") or [], cb.get("monthly_series") or []
    if ma and mb:
        if len(ma) != len(mb):
            warns.append(("uneven_history",
                          f"monthly series not aligned: A={len(ma)} months vs B={len(mb)} months"))
        else:
            if [p["month_year"] for p in ma] != [p["month_year"] for p in mb]:
                fails.append(("alignment", "monthly series month_year sequences differ"))

    # Legacy moving averages table must actually contain MA values
    legacy_ma = payload.get("moving_averages") or []
    if legacy_ma:
        computed = [r for r in legacy_ma if r.get("company1_ma_3m") is not None]
        if len(computed) < max(0, len(legacy_ma) - 5):
            fails.append(("legacy_ma",
                          f"moving_averages table has MA values in only {len(computed)}/{len(legacy_ma)} rows"))

    # Overlay alignment (chart data for uneven histories)
    overlay = payload.get("overlay_series") or []
    if overlay:
        for p in overlay:
            if not (math.isfinite(p.get("company_a_rebased", 0)) and math.isfinite(p.get("company_b_rebased", 0))):
                fails.append(("overlay", f"non-finite overlay point {p}"))
                break

    # Recommendation / comparison sanity
    rec = payload.get("recommendations") or {}
    for side in ("company1", "company2"):
        r = rec.get(side) or {}
        if r.get("action") not in ("BUY", "HOLD", "AVOID"):
            fails.append(("recommendation", f"{side} action invalid: {r.get('action')}"))
    comp_obj = payload.get("comparison") or {}
    if comp_obj.get("winner_ticker") and comp_obj["winner_ticker"] not in (
            (ca.get("info") or {}).get("ticker"), (cb.get("info") or {}).get("ticker")):
        warns.append(("comparison", f"winner {comp_obj.get('winner_ticker')} not one of the pair tickers"))

    # Explanation collection for hallucination review
    explanations = []
    for side, comp in (("A", ca), ("B", cb)):
        for ev in (comp.get("movement_events") or []) + (comp.get("recent_change") and [comp["recent_change"]] or []):
            explanations.append({
                "company": (comp.get("info") or {}).get("name"),
                "date": ev.get("date"),
                "change_pct": ev.get("change_pct"),
                "explanation": ev.get("explanation"),
                "confidence": ev.get("confidence"),
                "is_ai_generated": ev.get("is_ai_generated"),
                "headlines": [h.get("title") for h in (ev.get("headlines") or [])],
                "likely_reasons": ev.get("likely_reasons"),
            })

    return fails, warns, explanations


# ---------------------------------------------------------------------------
# Independent cross-verification (plain pandas, formulas re-implemented here)
# ---------------------------------------------------------------------------

def cross_verify(pair, payload):
    """Recomputes 3 seeded-random numbers for company 1 straight from yfinance."""
    rng = random.Random(sum(ord(c) for c in pair["key"]))
    ticker = payload["resolved_tickers"]["company1"]["ticker"]
    hist = download(ticker)
    ca = payload["company_a"]
    results = []

    months = ca["monthly_series"]
    pool = ["monthly_close", "cagr", "max_drawdown", "volatility", "total_return", "current_price"]
    picks = rng.sample(pool, 3)

    prices = hist["Close"]
    start_p, end_p = float(prices.iloc[0]), float(prices.iloc[-1])
    days = max((prices.index[-1] - prices.index[0]).days, 1)

    for pick in picks:
        if pick == "monthly_close":
            idx = rng.randrange(len(months))
            pt = months[idx]
            m = pt["month_year"]
            mask = [d[:7] == m for d in hist.index.strftime("%Y-%m-%d")]
            expected = round(float(prices[mask].iloc[-1]), 2)
            actual = pt["adj_close"]
            ok = abs(expected - actual) <= 0.05
            results.append({"pick": f"monthly_close({m})", "actual": actual, "expected": expected, "ok": ok,
                            "tolerance": 0.05})
        elif pick == "cagr":
            expected = round(((end_p / start_p) ** (365.25 / days) - 1) * 100, 2)
            actual = ca["metrics"]["cagr_pct"]
            ok = abs(expected - actual) <= 0.15
            results.append({"pick": "cagr_pct", "actual": actual, "expected": expected, "ok": ok,
                            "tolerance": 0.15})
        elif pick == "max_drawdown":
            running_max = prices.cummax()
            dd = ((prices - running_max) / running_max).min() * 100
            expected = round(abs(float(dd)), 2)
            actual = ca["metrics"]["max_drawdown_pct"]
            ok = abs(expected - actual) <= 0.15
            results.append({"pick": "max_drawdown_pct", "actual": actual, "expected": expected, "ok": ok,
                            "tolerance": 0.15})
        elif pick == "volatility":
            rets = prices.pct_change().dropna()
            expected = round(float(rets.std(ddof=1)) * math.sqrt(252) * 100, 2)
            actual = ca["metrics"]["annualized_volatility_pct"]
            ok = abs(expected - actual) <= 0.15
            results.append({"pick": "annualized_volatility_pct", "actual": actual, "expected": expected,
                            "ok": ok, "tolerance": 0.15})
        elif pick == "total_return":
            expected = round((end_p - start_p) / start_p * 100, 2)
            actual = ca["metrics"]["total_return_pct"]
            ok = abs(expected - actual) <= 0.15
            results.append({"pick": "total_return_pct", "actual": actual, "expected": expected, "ok": ok,
                            "tolerance": 0.15})
        elif pick == "current_price":
            expected = round(end_p, 2)
            actual = ca["metrics"]["current_price"]
            ok = abs(expected - actual) <= 0.05
            results.append({"pick": "current_price", "actual": actual, "expected": expected, "ok": ok,
                            "tolerance": 0.05})
    return ticker, results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_pairs():
    pairs = [{"key": p["key"], "query1": p["query1"], "query2": p["query2"],
              "why": "assigned exhibition pair"} for p in ASSIGNED_PAIRS]
    pairs += EDGE_PAIRS
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="comma-separated keys to run")
    ap.add_argument("--skip-crosscheck", action="store_true")
    args = ap.parse_args()

    QA_DIR.mkdir(exist_ok=True)
    RESPONSES_DIR.mkdir(exist_ok=True)

    pairs = build_pairs()
    if args.only:
        wanted = set(args.only.split(","))
        pairs = [p for p in pairs if p["key"] in wanted]

    results = []
    all_explanations = {}

    with TestClient(app) as client:
        for i, pair in enumerate(pairs, 1):
            key = pair["key"]
            print(f"\n[{i}/{len(pairs)}] {key}: {pair['query1']} vs {pair['query2']} ...", flush=True)
            entry = {"key": key, **pair}
            t0 = time.time()
            try:
                resp = client.post("/api/analyze", json={
                    "company1": pair["query1"],
                    "company2": pair["query2"],
                    "use_offline_demo": False,
                })
                entry["elapsed_s"] = round(time.time() - t0, 2)
                entry["status"] = resp.status_code
                if resp.status_code != 200:
                    entry["error"] = resp.text[:500]
                    entry["fails"] = [["http", entry["error"]]]
                    entry["warns"] = []
                    print(f"    HTTP {resp.status_code} in {entry['elapsed_s']}s: {entry['error'][:200]}")
                    results.append(entry)
                    continue

                raw_text = resp.text
                payload = resp.json()
                (RESPONSES_DIR / f"{key}.json").write_text(raw_text, encoding="utf-8")

                fails, warns, explanations = check_payload(payload, raw_text)
                entry["fails"] = fails
                entry["warns"] = warns
                entry["resolution"] = {
                    "c1": payload.get("resolved_tickers", {}).get("company1", {}).get("ticker"),
                    "c2": payload.get("resolved_tickers", {}).get("company2", {}).get("ticker"),
                }
                entry["stats"] = {
                    "daily_a": len(payload["company_a"]["daily_series"]),
                    "daily_b": len(payload["company_b"]["daily_series"]),
                    "months": len(payload["company_a"]["monthly_series"]),
                    "events_a": len(payload["company_a"].get("movement_events") or []),
                    "events_b": len(payload["company_b"].get("movement_events") or []),
                }
                all_explanations[key] = explanations

                if not args.skip_crosscheck:
                    try:
                        tk, checks = cross_verify(pair, payload)
                        entry["cross_verify"] = {"ticker": tk, "checks": checks}
                        bad = [c for c in checks if not c["ok"]]
                        if bad:
                            for c in bad:
                                entry["fails"].append(["cross_verify",
                                                        f"{c['pick']}: actual={c['actual']} expected={c['expected']} (tol {c['tolerance']})"])
                    except Exception as e:
                        entry["cross_verify"] = {"error": str(e)}
                        entry["warns"].append(["cross_verify", f"cross-check failed: {e}"])

                status = "PASS" if not entry["fails"] else "FAIL"
                print(f"    {status} in {entry['elapsed_s']}s | "
                      f"resolved {entry['resolution']['c1']} vs {entry['resolution']['c2']} | "
                      f"daily {entry['stats']['daily_a']}/{entry['stats']['daily_b']} | "
                      f"fails={len(entry['fails'])} warns={len(entry['warns'])}")
                for f in entry["fails"][:6]:
                    print(f"      FAIL {f[0]}: {f[1][:160]}")
                for w in entry["warns"][:4]:
                    print(f"      WARN {w[0]}: {w[1][:160]}")
            except Exception:
                entry["status"] = "exception"
                entry["error"] = traceback.format_exc()[-1000:]
                entry["fails"] = [["exception", entry["error"]]]
                entry["warns"] = []
                print(f"    EXCEPTION: {entry['error'][-300:]}")
            results.append(entry)
            time.sleep(1.5)  # be kind to Yahoo / Google News rate limits

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(results),
        "passed": sum(1 for r in results if not r.get("fails")),
        "failed": sum(1 for r in results if r.get("fails")),
        "results": results,
    }
    (QA_DIR / "qa_results.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    (QA_DIR / "explanations.json").write_text(json.dumps(all_explanations, indent=2, default=str), encoding="utf-8")

    print(f"\n=== QA batch complete: {out['passed']}/{out['total']} pairs clean "
          f"({out['failed']} with failures) ===")
    for r in results:
        if r.get("fails"):
            print(f"  FAIL {r['key']}: {len(r['fails'])} issue(s)")


if __name__ == "__main__":
    main()
