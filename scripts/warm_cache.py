#!/usr/bin/env python3
"""Fetch the nine exhibition pair histories plus benchmark/sector indexes."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.services.snapshot_service import ASSIGNED_PAIRS
from app.services.stock_data import fetch_benchmark_history, fetch_stock_history_with_retry
from app.config import settings


async def main() -> int:
    tickers = sorted({p[k] for p in ASSIGNED_PAIRS for k in ("ticker1", "ticker2")})
    outcomes = await asyncio.gather(
        *(fetch_stock_history_with_retry(ticker) for ticker in tickers),
        fetch_benchmark_history(),
        return_exceptions=True,
    )
    failures = [(ticker, result) for ticker, result in zip(tickers + [settings.BENCHMARK_TICKER], outcomes)
                if isinstance(result, BaseException)]
    print(f"Warmed {len(tickers) - sum(1 for ticker, _ in failures if ticker != settings.BENCHMARK_TICKER)}/{len(tickers)} stock histories")
    print("Benchmark: " + ("failed" if any(t == settings.BENCHMARK_TICKER for t, _ in failures) else "ready"))
    for ticker, error in failures:
        print(f"  ERROR {ticker}: {error}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
