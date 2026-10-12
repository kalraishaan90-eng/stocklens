import re
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
import yfinance as yf
from typing import Tuple, List, Dict, Any, Optional
from rapidfuzz import process, fuzz

from app.models.schemas import ResolvedSymbolMatch, ResolveResponse
from app.services.cache import get_cached, set_cached

logger = logging.getLogger("stocklens.ticker_resolver")

# Metadata and corporate restructuring notes for the 18 assigned companies
ASSIGNED_COMPANIES_META = {
    "Hindustan Aeronautics": {
        "ticker": "HAL.NS",
        "alt_ticker": "HAL.BO",
        "name": "Hindustan Aeronautics Limited",
        "exchange": "NSE",
        "sector": "Industrials",
        "aliases": ["hal", "hindustan aeronautics", "hindustan aeronautics limited", "hindustan aero", "hind aero"],
        "restructuring_note": None
    },
    "Mazagon Dock Shipbuilders": {
        "ticker": "MAZDOCK.NS",
        "alt_ticker": "MAZDOCK.BO",
        "name": "Mazagon Dock Shipbuilders Limited",
        "exchange": "NSE",
        "sector": "Industrials",
        "aliases": ["mazdock", "mazagon dock", "mazagon dock shipbuilders", "mazagon", "mazgon", "mdl"],
        "restructuring_note": None
    },
    "Bajaj Finserv": {
        "ticker": "BAJAJFINSV.NS",
        "alt_ticker": "BAJAJFINSV.BO",
        "name": "Bajaj Finserv Limited",
        "exchange": "NSE",
        "sector": "Financial Services",
        "aliases": ["bajaj finserv", "bajfinsv", "bajaj fin serv", "bajaj finserv limited"],
        "restructuring_note": None
    },
    "HDFC Bank": {
        "ticker": "HDFCBANK.NS",
        "alt_ticker": "HDFCBANK.BO",
        "name": "HDFC Bank Limited",
        "exchange": "NSE",
        "sector": "Financial Services",
        "aliases": ["hdfc bank", "hdfc", "hdfcbank", "housing development finance corporation"],
        "restructuring_note": None
    },
    "Titan Company": {
        "ticker": "TITAN.NS",
        "alt_ticker": "TITAN.BO",
        "name": "Titan Company Limited",
        "exchange": "NSE",
        "sector": "Consumer Cyclical",
        "aliases": ["titan", "titan company", "titan company limited", "titan industries"],
        "restructuring_note": None
    },
    "Varun Beverages": {
        "ticker": "VBL.NS",
        "alt_ticker": "VBL.BO",
        "name": "Varun Beverages Limited",
        "exchange": "NSE",
        "sector": "Consumer Defensive",
        "aliases": ["varun beverages", "vbl", "varun beverages limited", "varun bev"],
        "restructuring_note": None
    },
    "Coal India": {
        "ticker": "COALINDIA.NS",
        "alt_ticker": "COALINDIA.BO",
        "name": "Coal India Limited",
        "exchange": "NSE",
        "sector": "Energy",
        "aliases": ["coal india", "cil", "coal india limited", "coalindia"],
        "restructuring_note": None
    },
    "Adani Power": {
        "ticker": "ADANIPOWER.NS",
        "alt_ticker": "ADANIPOWER.BO",
        "name": "Adani Power Limited",
        "exchange": "NSE",
        "sector": "Utilities",
        "aliases": ["adani power", "adani power limited", "adanipower"],
        "restructuring_note": None
    },
    "TVS Motor": {
        "ticker": "TVSMOTOR.NS",
        "alt_ticker": "TVSMOTOR.BO",
        "name": "TVS Motor Company Limited",
        "exchange": "NSE",
        "sector": "Consumer Cyclical",
        "aliases": ["tvs motor", "tvs", "tvsmotor", "tvs motor company"],
        "restructuring_note": None
    },
    "Tata Motors": {
        "ticker": "TMPV.NS",
        "alt_ticker": "TMCV.NS",
        "name": "Tata Motors Passenger Vehicles Limited",
        "exchange": "NSE",
        "sector": "Consumer Cyclical",
        "aliases": ["tata motors", "tatamotors", "tata motor", "tata motors passenger", "tata motors commercial", "tmcv", "tmpv"],
        "restructuring_note": (
            "Tata Motors underwent a corporate demerger separating its Commercial Vehicles (TMCV.NS) "
            "and Passenger Vehicles (TMPV.NS) operations. The legacy symbol TATAMOTORS.NS is delisted. "
            "Note: Commercial Vehicles (TMCV.NS) has a shorter historical trading series."
        )
    },
    "Siemens": {
        "ticker": "SIEMENS.NS",
        "alt_ticker": "SIEMENS.BO",
        "name": "Siemens Limited",
        "exchange": "NSE",
        "sector": "Industrials",
        "aliases": ["siemens", "siemens india", "siemens limited"],
        "restructuring_note": (
            "Siemens Ltd approved the demerger of its Energy business into Siemens Energy India Limited. "
            "SIEMENS.NS reflects continuing core industrial, digital enterprise, and mobility operations."
        )
    },
    "Solar Industries India": {
        "ticker": "SOLARINDS.NS",
        "alt_ticker": "SOLARINDS.BO",
        "name": "Solar Industries India Limited",
        "exchange": "NSE",
        "sector": "Basic Materials",
        "aliases": ["solar industries", "solar industries india", "solarinds", "solar industries limited"],
        "restructuring_note": None
    },
    "Escorts Kubota": {
        "ticker": "ESCORTS.NS",
        "alt_ticker": "ESCORTS.BO",
        "name": "Escorts Kubota Limited",
        "exchange": "NSE",
        "sector": "Industrials",
        "aliases": ["escorts", "escorts kubota", "escorts limited", "escorts kubota limited"],
        "restructuring_note": None
    },
    "Bharat Forge": {
        "ticker": "BHARATFORG.NS",
        "alt_ticker": "BHARATFORG.BO",
        "name": "Bharat Forge Limited",
        "exchange": "NSE",
        "sector": "Industrials",
        "aliases": ["bharat forge", "bharatforge", "bharat forge limited"],
        "restructuring_note": None
    },
    "DLF": {
        "ticker": "DLF.NS",
        "alt_ticker": "DLF.BO",
        "name": "DLF Limited",
        "exchange": "NSE",
        "sector": "Real Estate",
        "aliases": ["dlf", "dlf limited"],
        "restructuring_note": None
    },
    "Godrej Properties": {
        "ticker": "GODREJPROP.NS",
        "alt_ticker": "GODREJPROP.BO",
        "name": "Godrej Properties Limited",
        "exchange": "NSE",
        "sector": "Real Estate",
        "aliases": ["godrej properties", "godrej prop", "godrej properties limited"],
        "restructuring_note": None
    },
    "Bharti Airtel": {
        "ticker": "BHARTIARTL.NS",
        "alt_ticker": "BHARTIARTL.BO",
        "name": "Bharti Airtel Limited",
        "exchange": "NSE",
        "sector": "Communication Services",
        "aliases": ["bharti airtel", "airtel", "bharti", "bharti airtel limited"],
        "restructuring_note": None
    },
    "Reliance Industries": {
        "ticker": "RELIANCE.NS",
        "alt_ticker": "RELIANCE.BO",
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "sector": "Energy",
        "aliases": ["reliance", "reliance industries", "ril", "reliance industries limited"],
        "restructuring_note": None
    }
}

# Pre-load full alias dictionary
COMMON_TICKER_MAP: Dict[str, Tuple[str, str]] = {}
RICH_ALIAS_MAP: Dict[str, Dict[str, Any]] = {}

for c_name, meta in ASSIGNED_COMPANIES_META.items():
    primary = {
        "ticker": meta["ticker"],
        "name": meta["name"],
        "exchange": meta["exchange"],
        "sector": meta["sector"],
        "restructuring_note": meta["restructuring_note"]
    }
    for alias in meta["aliases"]:
        key = alias.lower().strip()
        COMMON_TICKER_MAP[key] = (meta["ticker"], meta["name"])
        RICH_ALIAS_MAP[key] = primary

# Additional common Indian names
ADDITIONAL_INDIAN_MAP = {
    "bajaj finance": ("BAJFINANCE.NS", "Bajaj Finance Limited", "Financial Services"),
    "tcs": ("TCS.NS", "Tata Consultancy Services Limited", "Technology"),
    "tata consultancy": ("TCS.NS", "Tata Consultancy Services Limited", "Technology"),
    "infosys": ("INFY.NS", "Infosys Limited", "Technology"),
    "infy": ("INFY.NS", "Infosys Limited", "Technology"),
    "wipro": ("WIPRO.NS", "Wipro Limited", "Technology"),
    "hcl tech": ("HCLTECH.NS", "HCL Technologies Limited", "Technology"),
    "tech mahindra": ("TECHM.NS", "Tech Mahindra Limited", "Technology"),
    "icici bank": ("ICICIBANK.NS", "ICICI Bank Limited", "Financial Services"),
    "icici": ("ICICIBANK.NS", "ICICI Bank Limited", "Financial Services"),
    "state bank of india": ("SBIN.NS", "State Bank of India", "Financial Services"),
    "sbi": ("SBIN.NS", "State Bank of India", "Financial Services"),
    "kotak bank": ("KOTAKBANK.NS", "Kotak Mahindra Bank Limited", "Financial Services"),
    "kotak": ("KOTAKBANK.NS", "Kotak Mahindra Bank Limited", "Financial Services"),
    "axis bank": ("AXISBANK.NS", "Axis Bank Limited", "Financial Services"),
    "axis": ("AXISBANK.NS", "Axis Bank Limited", "Financial Services"),
    "bank of baroda": ("BANKBARODA.NS", "Bank of Baroda", "Financial Services"),
    "bob": ("BANKBARODA.NS", "Bank of Baroda", "Financial Services"),
    "punjab national bank": ("PNB.NS", "Punjab National Bank", "Financial Services"),
    "pnb": ("PNB.NS", "Punjab National Bank", "Financial Services"),
    "canara bank": ("CANBK.NS", "Canara Bank", "Financial Services"),
    "canbk": ("CANBK.NS", "Canara Bank", "Financial Services"),
    "indusind bank": ("INDUSINDBK.NS", "IndusInd Bank Limited", "Financial Services"),
    "indusind": ("INDUSINDBK.NS", "IndusInd Bank Limited", "Financial Services"),
    "yes bank": ("YESBANK.NS", "Yes Bank Limited", "Financial Services"),
    "idfc first bank": ("IDFCFIRSTB.NS", "IDFC First Bank Limited", "Financial Services"),
    "federal bank": ("FEDERALBNK.NS", "The Federal Bank Limited", "Financial Services"),
    "maruti": ("MARUTI.NS", "Maruti Suzuki India Limited", "Consumer Cyclical"),
    "maruti suzuki": ("MARUTI.NS", "Maruti Suzuki India Limited", "Consumer Cyclical"),
    "itc": ("ITC.NS", "ITC Limited", "Consumer Defensive"),
    "hindustan unilever": ("HINDUNILVR.NS", "Hindustan Unilever Limited", "Consumer Defensive"),
    "hul": ("HINDUNILVR.NS", "Hindustan Unilever Limited", "Consumer Defensive"),
    "larsen and toubro": ("LT.NS", "Larsen & Toubro Limited", "Industrials"),
    "l&t": ("LT.NS", "Larsen & Toubro Limited", "Industrials"),
    "zomato": ("ETERNAL.NS", "Zomato (Eternal Limited)", "Consumer Cyclical"),
    "zomato limited": ("ETERNAL.NS", "Zomato (Eternal Limited)", "Consumer Cyclical"),
    "eternal": ("ETERNAL.NS", "Eternal Limited (Zomato)", "Consumer Cyclical"),
    "swiggy": ("SWIGGY.NS", "Swiggy Limited", "Consumer Cyclical"),
    "swiggy limited": ("SWIGGY.NS", "Swiggy Limited", "Consumer Cyclical"),
    "paytm": ("PAYTM.NS", "One97 Communications (Paytm)", "Technology"),
    "one97": ("PAYTM.NS", "One97 Communications (Paytm)", "Technology"),
    "nykaa": ("NYKAA.NS", "FSN E-Commerce Ventures (Nykaa)", "Consumer Cyclical"),
    "fsn": ("NYKAA.NS", "FSN E-Commerce Ventures (Nykaa)", "Consumer Cyclical"),
    "ola electric": ("OLAELEC.NS", "Ola Electric Mobility Limited", "Consumer Cyclical"),
    "ola": ("OLAELEC.NS", "Ola Electric Mobility Limited", "Consumer Cyclical"),
    "tata steel": ("TATASTEEL.NS", "Tata Steel Limited", "Basic Materials"),
    "sun pharma": ("SUNPHARMA.NS", "Sun Pharmaceutical Industries Limited", "Healthcare"),
    "dr reddy": ("DRREDDY.NS", "Dr. Reddy's Laboratories Limited", "Healthcare"),
    "cipla": ("CIPLA.NS", "Cipla Limited", "Healthcare"),
    "apollo hospitals": ("APOLLOHOSP.NS", "Apollo Hospitals Enterprise Limited", "Healthcare"),
    "adani enterprises": ("ADANIENT.NS", "Adani Enterprises Limited", "Energy"),
    "adani ports": ("ADANIPORTS.NS", "Adani Ports and Special Economic Zone Limited", "Industrials"),
    "irctc": ("IRCTC.NS", "Indian Railway Catering and Tourism Corp", "Industrials"),
    "rvnl": ("RVNL.NS", "Rail Vikas Nigam Limited", "Industrials"),
    "irfc": ("IRFC.NS", "Indian Railway Finance Corporation", "Financial Services"),
    "suzlon": ("SUZLON.NS", "Suzlon Energy Limited", "Utilities"),
    "trent": ("TRENT.NS", "Trent Limited", "Consumer Cyclical"),
    "cdsl": ("CDSL.NS", "Central Depository Services (India) Limited", "Financial Services"),
    "bse": ("BSE.NS", "BSE Limited", "Financial Services"),
    "coforge": ("COFORGE.NS", "Coforge Limited", "Technology"),
    "cochin shipyard": ("COCHINSHIP.NS", "Cochin Shipyard Limited", "Industrials"),
    "bel": ("BEL.NS", "Bharat Electronics Limited", "Industrials"),
    "bhel": ("BHEL.NS", "Bharat Heavy Electricals Limited", "Industrials"),
    "ntpc": ("NTPC.NS", "NTPC Limited", "Utilities"),
    "ongc": ("ONGC.NS", "Oil and Natural Gas Corporation", "Energy"),
    "tatatech": ("TATATECH.NS", "Tata Technologies Limited", "Technology"),
    "tata tech": ("TATATECH.NS", "Tata Technologies Limited", "Technology"),
    "tata technologies": ("TATATECH.NS", "Tata Technologies Limited", "Technology"),
    "ireda": ("IREDA.NS", "Indian Renewable Energy Development Agency Limited", "Financial Services"),
    "jiofin": ("JIOFIN.NS", "Jio Financial Services Limited", "Financial Services"),
    "jio financial": ("JIOFIN.NS", "Jio Financial Services Limited", "Financial Services"),
    "jio financial services": ("JIOFIN.NS", "Jio Financial Services Limited", "Financial Services"),
}

# Major Global / US stocks
GLOBAL_MAP = {
    "aapl": ("AAPL", "Apple Inc.", "Technology", "NASDAQ"),
    "apple": ("AAPL", "Apple Inc.", "Technology", "NASDAQ"),
    "msft": ("MSFT", "Microsoft Corporation", "Technology", "NASDAQ"),
    "microsoft": ("MSFT", "Microsoft Corporation", "Technology", "NASDAQ"),
    "googl": ("GOOGL", "Alphabet Inc. (Class A)", "Communication Services", "NASDAQ"),
    "google": ("GOOGL", "Alphabet Inc.", "Communication Services", "NASDAQ"),
    "goog": ("GOOG", "Alphabet Inc. (Class C)", "Communication Services", "NASDAQ"),
    "amzn": ("AMZN", "Amazon.com Inc.", "Consumer Cyclical", "NASDAQ"),
    "amazon": ("AMZN", "Amazon.com Inc.", "Consumer Cyclical", "NASDAQ"),
    "nvda": ("NVDA", "NVIDIA Corporation", "Technology", "NASDAQ"),
    "nvidia": ("NVDA", "NVIDIA Corporation", "Technology", "NASDAQ"),
    "meta": ("META", "Meta Platforms Inc.", "Communication Services", "NASDAQ"),
    "facebook": ("META", "Meta Platforms Inc.", "Communication Services", "NASDAQ"),
    "tsla": ("TSLA", "Tesla Inc.", "Consumer Cyclical", "NASDAQ"),
    "tesla": ("TSLA", "Tesla Inc.", "Consumer Cyclical", "NASDAQ"),
    "nflx": ("NFLX", "Netflix Inc.", "Communication Services", "NASDAQ"),
    "netflix": ("NFLX", "Netflix Inc.", "Communication Services", "NASDAQ"),
    "amd": ("AMD", "Advanced Micro Devices Inc.", "Technology", "NASDAQ"),
    "intc": ("INTC", "Intel Corporation", "Technology", "NASDAQ"),
    "intel": ("INTC", "Intel Corporation", "Technology", "NASDAQ"),
    "spy": ("SPY", "SPDR S&P 500 ETF Trust", "Financial Services", "NYSE Arca"),
    "qqq": ("QQQ", "Invesco QQQ Trust", "Financial Services", "NASDAQ"),
    "jpm": ("JPM", "JPMorgan Chase & Co.", "Financial Services", "NYSE"),
    "jp morgan": ("JPM", "JPMorgan Chase & Co.", "Financial Services", "NYSE"),
    "jpmorgan": ("JPM", "JPMorgan Chase & Co.", "Financial Services", "NYSE"),
    "jpmorgan chase": ("JPM", "JPMorgan Chase & Co.", "Financial Services", "NYSE"),
    "ms": ("MS", "Morgan Stanley", "Financial Services", "NYSE"),
    "morgan stanley": ("MS", "Morgan Stanley", "Financial Services", "NYSE"),
    "msdl": ("MSDL", "Morgan Stanley Direct Lending Fund", "Financial Services", "NYSE"),
    "morgan stanley direct lending": ("MSDL", "Morgan Stanley Direct Lending Fund", "Financial Services", "NYSE"),
    "morgan stanley direct lending fund": ("MSDL", "Morgan Stanley Direct Lending Fund", "Financial Services", "NYSE"),
    "gs": ("GS", "Goldman Sachs Group Inc.", "Financial Services", "NYSE"),
    "goldman": ("GS", "Goldman Sachs Group Inc.", "Financial Services", "NYSE"),
    "goldman sachs": ("GS", "Goldman Sachs Group Inc.", "Financial Services", "NYSE"),
    "bac": ("BAC", "Bank of America Corporation", "Financial Services", "NYSE"),
    "bank of america": ("BAC", "Bank of America Corporation", "Financial Services", "NYSE"),
    "c": ("C", "Citigroup Inc.", "Financial Services", "NYSE"),
    "citi": ("C", "Citigroup Inc.", "Financial Services", "NYSE"),
    "citigroup": ("C", "Citigroup Inc.", "Financial Services", "NYSE"),
    "wfc": ("WFC", "Wells Fargo & Company", "Financial Services", "NYSE"),
    "wells fargo": ("WFC", "Wells Fargo & Company", "Financial Services", "NYSE"),
    "v": ("V", "Visa Inc.", "Financial Services", "NYSE"),
    "visa": ("V", "Visa Inc.", "Financial Services", "NYSE"),
    "ma": ("MA", "Mastercard Incorporated", "Financial Services", "NYSE"),
    "mastercard": ("MA", "Mastercard Incorporated", "Financial Services", "NYSE"),
    "blk": ("BLK", "BlackRock, Inc.", "Financial Services", "NYSE"),
    "blackrock": ("BLK", "BlackRock, Inc.", "Financial Services", "NYSE"),
    "ko": ("KO", "The Coca-Cola Company", "Consumer Defensive", "NYSE"),
    "coca cola": ("KO", "The Coca-Cola Company", "Consumer Defensive", "NYSE"),
    "pep": ("PEP", "PepsiCo, Inc.", "Consumer Defensive", "NASDAQ"),
    "pepsi": ("PEP", "PepsiCo, Inc.", "Consumer Defensive", "NASDAQ"),
    "baba": ("BABA", "Alibaba Group Holding Limited", "Consumer Cyclical", "NYSE"),
    "alibaba": ("BABA", "Alibaba Group Holding Limited", "Consumer Cyclical", "NYSE"),
    "cost": ("COST", "Costco Wholesale Corporation", "Consumer Defensive", "NASDAQ"),
    "costco": ("COST", "Costco Wholesale Corporation", "Consumer Defensive", "NASDAQ"),
    "wmt": ("WMT", "Walmart Inc.", "Consumer Defensive", "NYSE"),
    "walmart": ("WMT", "Walmart Inc.", "Consumer Defensive", "NYSE"),
    "dis": ("DIS", "Walt Disney Company", "Communication Services", "NYSE"),
    "disney": ("DIS", "Walt Disney Company", "Communication Services", "NYSE"),
}

for k, val in ADDITIONAL_INDIAN_MAP.items():
    COMMON_TICKER_MAP[k] = (val[0], val[1])
    RICH_ALIAS_MAP[k] = {
        "ticker": val[0],
        "name": val[1],
        "exchange": "NSE",
        "sector": val[2],
        "restructuring_note": None
    }

for k, val in GLOBAL_MAP.items():
    COMMON_TICKER_MAP[k] = (val[0], val[1])
    RICH_ALIAS_MAP[k] = {
        "ticker": val[0],
        "name": val[1],
        "exchange": val[3],
        "sector": val[2],
        "restructuring_note": None
    }

# Startup verification results store
STARTUP_VERIFIED_STATUS: Dict[str, Dict[str, Any]] = {}

def _verify_single_ticker(c_name: str, meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Verifies one assigned company's ticker via a live Yahoo Finance lookup.

    Checks ticker accessibility and history length (2-year window) and logs a
    warning when the history is empty, short (< 350 trading days), or the
    company has a known corporate restructuring/demerger.
    """
    ticker = meta["ticker"]
    warning = None
    short_history = False
    row_count = 0

    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2y")
        row_count = len(hist)
        if row_count == 0:
            warning = f"Warning: No price data returned for {ticker}. Symbol may be delisted or inactive."
            logger.warning(warning)
        elif row_count < 350:
            short_history = True
            warning = (
                f"Warning: {ticker} has a short trading history ({row_count} trading days over 2 years, "
                f"expected ~490). The symbol may be recently listed, demerged or restructured."
            )
            logger.warning(warning)
    except Exception as e:
        warning = f"Live verification error for {ticker}: {str(e)}"
        logger.warning(warning)

    # Restructuring inspection (e.g. Tata Motors demerger, Siemens Energy split)
    if meta["restructuring_note"]:
        logger.warning(f"Restructuring Alert [{c_name} -> {ticker}]: {meta['restructuring_note']}")
        if warning is None:
            warning = meta["restructuring_note"]

    status_entry = {
        "company_name": c_name,
        "ticker": ticker,
        "alt_ticker": meta.get("alt_ticker"),
        "verified": row_count > 0,
        "rows_2y": row_count,
        "short_history": short_history,
        "warning": warning,
        "restructuring_note": meta["restructuring_note"]
    }
    return ticker, status_entry


def verify_assigned_tickers_sync() -> Dict[str, Dict[str, Any]]:
    """
    Synchronous live verification of the 18 assigned tickers:
    Checks ticker accessibility, history length, and corporate restructuring flags.
    Logs warnings for short history or restructured companies.
    Runs lookups in parallel (bounded thread pool) so startup stays fast.
    """
    logger.info("Verifying 18 assigned company tickers via live Yahoo Finance lookup...")
    results: Dict[str, Dict[str, Any]] = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(_verify_single_ticker, c_name, meta)
            for c_name, meta in ASSIGNED_COMPANIES_META.items()
        ]
        for future in as_completed(futures):
            try:
                ticker, status_entry = future.result()
                results[ticker] = status_entry
                STARTUP_VERIFIED_STATUS[ticker] = status_entry
            except Exception as e:  # pragma: no cover - defensive
                logger.warning(f"Ticker verification worker failed: {e}")

    verified_count = sum(1 for v in results.values() if v.get("verified"))
    flagged = [v["ticker"] for v in results.values() if v.get("warning")]
    logger.info(
        f"Assigned company verification completed: {verified_count}/{len(ASSIGNED_COMPANIES_META)} tickers live-verified."
        + (f" Flagged: {', '.join(flagged)}" if flagged else "")
    )
    return results

async def verify_assigned_tickers(live: bool = True) -> Dict[str, Dict[str, Any]]:
    """Async wrapper around verification routine."""
    if not live:
        return STARTUP_VERIFIED_STATUS
    return await asyncio.to_thread(verify_assigned_tickers_sync)


async def _search_yahoo(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Searches Yahoo Finance API for ticker quotes matching query."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount={limit}&newsCount=0"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get("quotes", [])
                results = []
                for q in quotes:
                    sym = q.get("symbol", "")
                    qtype = q.get("quoteType", "")
                    if not sym or qtype in ("FUTURE", "OPTION", "CURRENCY"):
                        continue
                    name = q.get("longname") or q.get("shortname") or sym
                    exchange = q.get("exchange", "")
                    sector = q.get("sector") or None
                    results.append({
                        "ticker": sym,
                        "name": name,
                        "exchange": "NSE" if sym.endswith(".NS") else ("BSE" if sym.endswith(".BO") else exchange),
                        "sector": sector
                    })
                return results
    except Exception as e:
        logger.debug(f"Yahoo search error: {e}")
    return []


async def resolve_symbol(query: str) -> ResolveResponse:
    """
    Primary symbol resolver:
    1. Direct exact alias match (0ms).
    2. Fuzzy match with RapidFuzz for typos against pre-loaded alias catalog.
    3. Yahoo Finance Search API fallback preferring NSE (.NS), then BSE (.BO).
    4. Attaches corporate restructuring notes (e.g. Tata Motors, Siemens) and flags ambiguity.
    5. Returns top match plus up to 3 alternatives.
    """
    clean_query = query.strip()
    norm = clean_query.lower()
    
    candidates: List[ResolvedSymbolMatch] = []
    restructure_note: Optional[str] = None
    is_ambiguous: bool = False

    # Check startup status note if exists
    def _get_restructure_note(ticker: str) -> Optional[str]:
        if ticker in STARTUP_VERIFIED_STATUS and STARTUP_VERIFIED_STATUS[ticker].get("restructuring_note"):
            return STARTUP_VERIFIED_STATUS[ticker]["restructuring_note"]
        # Check in ASSIGNED_COMPANIES_META
        for meta in ASSIGNED_COMPANIES_META.values():
            if meta["ticker"] == ticker or meta.get("alt_ticker") == ticker:
                return meta.get("restructuring_note")
        return None

    # Special handling for Tata Motors queries
    if "tata motor" in norm or norm in ("tatamotors", "tmcv", "tmpv"):
        restructure_note = ASSIGNED_COMPANIES_META["Tata Motors"]["restructuring_note"]
        candidates.append(
            ResolvedSymbolMatch(
                ticker="TMPV.NS",
                name="Tata Motors Passenger Vehicles Limited",
                exchange="NSE",
                sector="Consumer Cyclical",
                is_ambiguous=True,
                restructuring_note=restructure_note,
                confidence_score=95.0
            )
        )
        candidates.append(
            ResolvedSymbolMatch(
                ticker="TMCV.NS",
                name="Tata Motors Limited (Commercial Vehicles)",
                exchange="NSE",
                sector="Consumer Cyclical",
                is_ambiguous=True,
                restructuring_note="Demerged commercial vehicle entity. Short trading history (<1 year).",
                confidence_score=90.0
            )
        )
        candidates.append(
            ResolvedSymbolMatch(
                ticker="TMPV.BO",
                name="Tata Motors Passenger Vehicles Limited (BSE)",
                exchange="BSE",
                sector="Consumer Cyclical",
                is_ambiguous=True,
                restructuring_note=restructure_note,
                confidence_score=85.0
            )
        )
        return ResolveResponse(
            query=clean_query,
            match=candidates[0],
            alternatives=candidates[1:4],
            is_ambiguous=True,
            restructuring_note=restructure_note
        )

    # 1. Exact match in RICH_ALIAS_MAP
    if norm in RICH_ALIAS_MAP:
        item = RICH_ALIAS_MAP[norm]
        note = item.get("restructuring_note") or _get_restructure_note(item["ticker"])
        top_match = ResolvedSymbolMatch(
            ticker=item["ticker"],
            name=item["name"],
            exchange=item["exchange"],
            sector=item["sector"],
            is_ambiguous=bool(note),
            restructuring_note=note,
            confidence_score=100.0
        )
        candidates.append(top_match)
        
        # Add BSE counterpart if available
        base_sym = item["ticker"].replace(".NS", "")
        candidates.append(
            ResolvedSymbolMatch(
                ticker=f"{base_sym}.BO",
                name=item["name"],
                exchange="BSE",
                sector=item["sector"],
                is_ambiguous=False,
                confidence_score=90.0
            )
        )

    # 2. Fuzzy match against alias catalog using rapidfuzz (handling typos)
    if not candidates:
        all_keys = list(RICH_ALIAS_MAP.keys())
        fuzzy_matches = process.extract(
            norm,
            all_keys,
            scorer=fuzz.ratio,
            limit=4
        )
        
        # If best match is strong (score >= 70)
        for matched_key, score, _ in fuzzy_matches:
            if score >= 70:
                item = RICH_ALIAS_MAP[matched_key]
                if not any(c.ticker == item["ticker"] for c in candidates):
                    note = item.get("restructuring_note") or _get_restructure_note(item["ticker"])
                    candidates.append(
                        ResolvedSymbolMatch(
                            ticker=item["ticker"],
                            name=item["name"],
                            exchange=item["exchange"],
                            sector=item["sector"],
                            is_ambiguous=(score < 88 or bool(note)),
                            restructuring_note=note,
                            confidence_score=float(score)
                        )
                    )
                    # Add BSE alternative if available
                    if item["ticker"].endswith(".NS"):
                        bse_sym = item["ticker"].replace(".NS", ".BO")
                        if not any(c.ticker == bse_sym for c in candidates):
                            candidates.append(
                                ResolvedSymbolMatch(
                                    ticker=bse_sym,
                                    name=item["name"],
                                    exchange="BSE",
                                    sector=item["sector"],
                                    is_ambiguous=False,
                                    confidence_score=float(score) - 5.0
                                )
                            )

    upper_sym = clean_query.upper()

    # 3. Direct ticker format check for explicit exchange suffix or index (e.g. "RELIANCE.NS", "HAL.BO", "^NSEI")
    if not candidates and ("." in upper_sym or upper_sym.startswith("^")) and re.match(r"^[A-Z0-9\^]{1,12}(\.[A-Z]{2,4})?$", upper_sym):
        candidates.append(
            ResolvedSymbolMatch(
                ticker=upper_sym,
                name=upper_sym,
                exchange="NSE" if upper_sym.endswith(".NS") else ("BSE" if upper_sym.endswith(".BO") else "GLOBAL"),
                sector=None,
                is_ambiguous=False,
                confidence_score=95.0
            )
        )

    # 4. Search Yahoo Finance API
    if len(candidates) < 2:
        try:
            yahoo_results = await _search_yahoo(clean_query, limit=6)
            for yr in yahoo_results:
                sym = yr["ticker"]
                if not any(c.ticker == sym for c in candidates):
                    note = _get_restructure_note(sym)
                    is_exact_sym = (sym.upper() == upper_sym)
                    is_stem_sym = (sym.replace(".NS", "").replace(".BO", "").upper() == upper_sym)
                    conf = 95.0 if (is_exact_sym or is_stem_sym) else 80.0
                    candidates.append(
                        ResolvedSymbolMatch(
                            ticker=sym,
                            name=yr["name"],
                            exchange=yr["exchange"],
                            sector=yr["sector"],
                            is_ambiguous=bool(note),
                            restructuring_note=note,
                            confidence_score=conf
                        )
                    )
        except Exception:
            pass

    # 5. Fallback if no candidates found (offline, unknown symbol, or junk query)
    if not candidates:
        if re.match(r"^[A-Z0-9]{1,12}$", upper_sym):
            candidates.append(
                ResolvedSymbolMatch(
                    ticker=f"{upper_sym}.NS",
                    name=clean_query,
                    exchange="NSE",
                    sector=None,
                    is_ambiguous=True,
                    confidence_score=60.0
                )
            )
            candidates.append(
                ResolvedSymbolMatch(
                    ticker=f"{upper_sym}.BO",
                    name=clean_query,
                    exchange="BSE",
                    sector=None,
                    is_ambiguous=True,
                    confidence_score=50.0
                )
            )
        else:
            default_ticker = f"{upper_sym[:12]}.NS"
            candidates.append(
                ResolvedSymbolMatch(
                    ticker=default_ticker,
                    name=clean_query,
                    exchange="NSE",
                    sector=None,
                    is_ambiguous=True,
                    confidence_score=40.0
                )
            )

    # 5. Sort candidates preferring NSE (.NS) then BSE (.BO)
    def _exchange_priority(match: ResolvedSymbolMatch) -> int:
        score = match.confidence_score or 50.0
        if match.ticker.endswith(".NS"):
            return int(score * 10) + 20
        elif match.ticker.endswith(".BO"):
            return int(score * 10) + 10
        return int(score * 10)

    candidates.sort(key=_exchange_priority, reverse=True)

    top_match = candidates[0]
    alternatives = candidates[1:4]

    # Determine if the query is ambiguous
    # If top match confidence is below 85, or top match note exists, or top 2 scores are within 5 points
    if top_match.restructuring_note:
        is_ambiguous = True
        restructure_note = top_match.restructuring_note
    elif alternatives and top_match.confidence_score and alternatives[0].confidence_score:
        if (top_match.confidence_score - alternatives[0].confidence_score) < 8.0:
            is_ambiguous = True
    elif (top_match.confidence_score or 100) < 85.0:
        is_ambiguous = True

    top_match.is_ambiguous = is_ambiguous

    return ResolveResponse(
        query=clean_query,
        match=top_match,
        alternatives=alternatives,
        is_ambiguous=is_ambiguous,
        restructuring_note=restructure_note
    )


async def resolve_ticker(query: str) -> Tuple[str, str]:
    """
    Backward-compatible resolver returning (ticker_symbol, company_display_name).
    """
    res = await resolve_symbol(query)
    if res.match:
        return res.match.ticker, res.match.name
    return f"{query.upper()}.NS", query
