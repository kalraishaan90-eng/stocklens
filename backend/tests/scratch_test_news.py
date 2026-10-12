import asyncio
from datetime import datetime, timedelta
import feedparser
import urllib.parse
import httpx
import yfinance as yf

async def fetch_news(company: str, date_str: str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    d_after = (dt - timedelta(days=3)).strftime("%Y-%m-%d")
    # after: and before: in google search are exclusive/inclusive depending on query, so dt + 2 days covers +1 day nicely
    d_before = (dt + timedelta(days=2)).strftime("%Y-%m-%d")
    
    q1 = f'"{company}" after:{d_after} before:{d_before}'
    q2 = f'{company} results OR order OR stake OR rating OR SEBI OR guidance after:{d_after} before:{d_before}'
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    articles = []
    seen = set()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for q in [q1, q2]:
            url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
            try:
                res = await client.get(url, headers=headers)
                feed = feedparser.parse(res.text)
                for e in feed.entries:
                    t = e.get("title", "").strip()
                    if not t:
                        continue
                    # dedupe by simplified lowercase headline
                    simple_t = "".join(ch for ch in t.lower() if ch.isalnum())
                    if simple_t in seen:
                        continue
                    seen.add(simple_t)
                    source_obj = e.get("source", {})
                    source_title = source_obj.get("title") if isinstance(source_obj, dict) else "News Media"
                    articles.append({
                        "title": t,
                        "source": source_title or "Google News",
                        "link": e.get("link", ""),
                        "published": e.get("published", "")
                    })
            except Exception as exc:
                print(f"Error fetching for query '{q}': {exc}")
                
    return articles[:5]

def get_corporate_events(ticker: str, event_date_str: str) -> list[str]:
    events = []
    try:
        t = yf.Ticker(ticker)
        dt = datetime.strptime(event_date_str, "%Y-%m-%d")
        
        # Actions (dividends, splits)
        actions = t.actions
        if actions is not None and not actions.empty:
            actions_clean = actions.copy()
            if actions_clean.index.tz is not None:
                actions_clean.index = actions_clean.index.tz_convert(None).floor("D")
            else:
                actions_clean.index = actions_clean.index.floor("D")
                
            for act_dt, row in actions_clean.iterrows():
                diff_days = abs((act_dt - dt).days)
                if diff_days <= 7:
                    div = row.get("Dividends", 0.0)
                    split = row.get("Stock Splits", 0.0)
                    if div and div > 0:
                        events.append(f"Dividend: ₹{div:.2f} per share (Ex-date: {act_dt.strftime('%Y-%m-%d')})")
                    if split and split > 0:
                        events.append(f"Stock Split: {split:.0f}:1 ratio (Ex-date: {act_dt.strftime('%Y-%m-%d')})")
                        
        # Earnings dates
        earnings = getattr(t, "earnings_dates", None)
        if earnings is not None and not earnings.empty:
            e_clean = earnings.copy()
            if e_clean.index.tz is not None:
                e_clean.index = e_clean.index.tz_convert(None).floor("D")
            else:
                e_clean.index = e_clean.index.floor("D")
                
            for e_dt, row in e_clean.iterrows():
                diff_days = abs((e_dt - dt).days)
                if diff_days <= 7:
                    eps_rep = row.get("Reported EPS")
                    eps_est = row.get("EPS Estimate")
                    rep_str = f", Reported EPS: ₹{eps_rep:.2f}" if eps_rep and not pd.isna(eps_rep) else ""
                    est_str = f", Est EPS: ₹{eps_est:.2f}" if eps_est and not pd.isna(eps_est) else ""
                    events.append(f"Earnings Release: {e_dt.strftime('%Y-%m-%d')}{rep_str}{est_str}")
    except Exception as exc:
        print(f"Error fetching corporate events for {ticker}: {exc}")
    return events

async def main():
    test_cases = [
        ("ADANIPOWER.NS", "Adani Power", "2024-11-21"),
        ("TITAN.NS", "Titan Company", "2025-07-08"),
        ("RELIANCE.NS", "Reliance Industries", "2026-01-06")
    ]
    for ticker, comp, dt in test_cases:
        arts = await fetch_news(comp, dt)
        corp = get_corporate_events(ticker, dt)
        print(f"\n==========================================")
        print(f"Ticker: {ticker} ({comp}) on {dt}")
        print(f"Corporate Events ({len(corp)}): {corp}")
        print(f"Top {len(arts)} Headlines:")
        for a in arts:
            print(f"  [{a['source']}] {a['title']}")

if __name__ == "__main__":
    import pandas as pd
    asyncio.run(main())
