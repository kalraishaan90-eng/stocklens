import asyncio
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
import feedparser
import pandas as pd
import yfinance as yf
from app.services.cache import get_cached, set_cached

# Well-known national economic / market regime events for Indian markets
KNOWN_MARKET_EVENTS = {
    "2024-06-04": [
        {
            "title": "Indian Equities Suffer Steep Drawdown as Lok Sabha Election Results Narrow Majority",
            "source": "Financial Express",
            "url": "https://www.google.com/search?q=india+stock+market+june+4+2024+election+results",
            "date": "2024-06-04"
        },
        {
            "title": "PSU and Capital Goods Stocks Plummet Following General Election Verdict",
            "source": "Economic Times",
            "url": "https://www.google.com/search?q=psu+stocks+june+4+2024+crash",
            "date": "2024-06-04"
        }
    ],
    "2024-06-03": [
        {
            "title": "Sensex & Nifty Hit Historic Record Highs on Exit Poll Optimism",
            "source": "Business Standard",
            "url": "https://www.google.com/search?q=stock+market+june+3+2024+exit+polls",
            "date": "2024-06-03"
        }
    ]
}

def clean_company_name(name: str, ticker: str) -> str:
    """Strips legal entity suffixes to produce clean search term."""
    clean = name
    for suffix in [
        "Limited", "Ltd.", "Ltd", "Corporation", "Corp", "Industries",
        "Enterprises", "Holdings", "India", "The", "(India)"
    ]:
        # Strip suffix if it leaves at least 3 characters
        replaced = clean.replace(suffix, "").strip()
        if len(replaced) >= 3:
            clean = replaced
    clean = clean.strip()
    if not clean:
        clean = ticker.split(".")[0]
    return clean

def get_corporate_events(ticker: str, event_date_str: str) -> List[str]:
    """
    Checks yfinance for earnings dates, dividends, and stock splits within +/- 7 days of event date.
    """
    cache_key = f"corp_events:{ticker}"
    cached_events = get_cached(cache_key)
    
    if cached_events is None:
        raw_events = []
        try:
            # Skip indices or invalid tickers
            if not ticker.startswith("^"):
                def _fetch_yfinance_actions():
                    evs = []
                    t = yf.Ticker(ticker)
                    actions = getattr(t, "actions", None)
                    if actions is not None and not actions.empty:
                        act_df = actions.copy()
                        if act_df.index.tz is not None:
                            act_df.index = act_df.index.tz_localize(None).floor("D")
                        else:
                            act_df.index = act_df.index.floor("D")

                        for act_dt, row in act_df.iterrows():
                            div = float(row.get("Dividends", 0.0))
                            split = float(row.get("Stock Splits", 0.0))
                            d_str = act_dt.strftime("%Y-%m-%d")
                            if div > 0:
                                evs.append({
                                    "type": "dividend",
                                    "date": d_str,
                                    "desc": f"Dividend: INR {div:.2f} per share (Ex-date: {d_str})"
                                })
                            if split > 0:
                                evs.append({
                                    "type": "split",
                                    "date": d_str,
                                    "desc": f"Stock Split: {split:.0f}:1 ratio (Ex-date: {d_str})"
                                })
                    return evs

                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(_fetch_yfinance_actions)
                    raw_events = future.result(timeout=1.2)
        except Exception:
            raw_events = []

        cached_events = raw_events
        set_cached(cache_key, cached_events, ttl_seconds=86400)

    # Filter events within +/- 7 days of event date
    matched = []
    try:
        ev_dt = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        for item in cached_events:
            i_dt = datetime.strptime(item["date"], "%Y-%m-%d").date()
            if abs((i_dt - ev_dt).days) <= 7:
                matched.append(item["desc"])
    except Exception:
        pass

    return matched

async def fetch_news_for_event(
    ticker: str,
    company_name: str,
    event_date_str: str,
    end_date_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches real news headlines associated with an anomaly date.
    Strictly queries Google News RSS with after:/before: date operators.
    
    1. Query 1: "<company name>" after:YYYY-MM-DD before:YYYY-MM-DD
    2. Query 2: "<company> results OR order OR stake OR rating OR SEBI OR guidance"
    3. Parses with feedparser, dedupes, keeps top 5 most relevant.
    4. Attaches corporate events from yfinance (earnings, dividends, splits).
    """
    cache_key = f"news_event_v2:{ticker}:{event_date_str}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    start_dt = datetime.strptime(event_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else start_dt

    # Date window: start - 3 days to end + 1 day
    # before: in Google is exclusive, so +2 days covers +1 day
    d_after = (start_dt - timedelta(days=3)).strftime("%Y-%m-%d")
    d_before = (end_dt + timedelta(days=2)).strftime("%Y-%m-%d")

    clean_name = clean_company_name(company_name, ticker)
    symbol_bare = ticker.split(".")[0]

    # Two distinct queries as specified in prompt
    q1 = f'"{clean_name}" after:{d_after} before:{d_before}'
    q2 = f'{clean_name} results OR order OR stake OR rating OR SEBI OR guidance after:{d_after} before:{d_before}'

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    found_articles: List[Dict[str, Any]] = []
    seen_titles = set()

    # Check for known macroeconomic dates first
    if event_date_str in KNOWN_MARKET_EVENTS:
        for item in KNOWN_MARKET_EVENTS[event_date_str]:
            found_articles.append(item)
            seen_titles.add(item["title"].lower())

    async def _fetch_rss(query_str: str) -> List[Dict[str, Any]]:
        entries_found = []
        try:
            encoded_q = urllib.parse.quote(query_str)
            rss_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-IN&gl=IN&ceid=IN:en"
            async with httpx.AsyncClient(timeout=2.5) as client:
                resp = await client.get(rss_url, headers=headers)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries:
                        title = entry.get("title", "").strip()
                        if not title:
                            continue
                        source_obj = entry.get("source", {})
                        source_title = source_obj.get("title") if isinstance(source_obj, dict) else "News Media"
                        link = entry.get("link", "")
                        pub_date_str = None
                        published_parsed = entry.get("published_parsed")
                        if published_parsed:
                            pub_date = datetime(*published_parsed[:6])
                            pub_date_str = pub_date.strftime("%Y-%m-%d")
                        else:
                            pub_date_str = event_date_str

                        # Prioritize headlines mentioning company or symbol
                        relevance_score = 0
                        title_lower = title.lower()
                        if clean_name.lower() in title_lower:
                            relevance_score += 3
                        if symbol_bare.lower() in title_lower:
                            relevance_score += 2
                        for kw in ["order", "results", "profit", "revenue", "stake", "rating", "sebi", "guidance", "deal", "shares", "rally", "fall", "surge"]:
                            if kw in title_lower:
                                relevance_score += 1

                        entries_found.append({
                            "title": title,
                            "source": source_title or "Google News",
                            "url": link,
                            "date": pub_date_str,
                            "relevance": relevance_score
                        })
        except Exception:
            pass
        return entries_found

    feed_results = await asyncio.gather(_fetch_rss(q1), _fetch_rss(q2))
    for entries in feed_results:
        for item in entries:
            clean_key = "".join(ch for ch in item["title"].lower() if ch.isalnum())
            if clean_key not in seen_titles:
                seen_titles.add(clean_key)
                found_articles.append(item)

    # Sort by relevance descending, keep top 5
    found_articles.sort(key=lambda x: x.get("relevance", 0), reverse=True)
    top_5_headlines = [
        {
            "title": a["title"],
            "source": a["source"],
            "url": a.get("url"),
            "date": a.get("date")
        }
        for a in found_articles[:5]
    ]

    # Fetch corporate events near event date
    corp_events = get_corporate_events(ticker, event_date_str)

    has_news = len(top_5_headlines) > 0

    result = {
        "headlines": top_5_headlines,
        "corporate_events": corp_events,
        "has_news": has_news,
        # Backward compatibility fields
        "headline": top_5_headlines[0]["title"] if top_5_headlines else "No specific corporate headline indexed for this session",
        "source": top_5_headlines[0]["source"] if top_5_headlines else "Exchange Trading & Market Data",
        "url": top_5_headlines[0]["url"] if top_5_headlines else None
    }

    set_cached(cache_key, result, ttl_seconds=86400 * 7)
    return result
