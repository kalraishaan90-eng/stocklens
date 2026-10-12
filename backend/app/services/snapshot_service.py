import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("stocklens.snapshot_service")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEMO_DATA_DIR = BACKEND_DIR / "demo_data"

# Curated 9 Exhibition Project Pairs
ASSIGNED_PAIRS: List[Dict[str, Any]] = [
    {
        "key": "hal_mazdock",
        "ticker1": "HAL.NS",
        "ticker2": "MAZDOCK.NS",
        "name1": "Hindustan Aeronautics Limited",
        "name2": "Mazagon Dock Shipbuilders Limited",
        "query1": "HAL",
        "query2": "Mazagon Dock",
        "sector": "Aerospace & Defence",
        "aliases1": ["hal", "hindustan aeronautics", "hindustan aeronautics limited", "hal.ns"],
        "aliases2": ["mazdock", "mazagon dock", "mazagon dock shipbuilders", "mazdock.ns", "mazagon"]
    },
    {
        "key": "reliance_bhartiartl",
        "ticker1": "RELIANCE.NS",
        "ticker2": "BHARTIARTL.NS",
        "name1": "Reliance Industries Limited",
        "name2": "Bharti Airtel Limited",
        "query1": "Reliance",
        "query2": "Bharti Airtel",
        "sector": "Telecom & Digital Conglomerate",
        "aliases1": ["reliance", "reliance industries", "ril", "reliance.ns"],
        "aliases2": ["airtel", "bharti airtel", "bharti", "bhartiartl.ns"]
    },
    {
        "key": "bajajfinsv_hdfcbank",
        "ticker1": "BAJAJFINSV.NS",
        "ticker2": "HDFCBANK.NS",
        "name1": "Bajaj Finserv Limited",
        "name2": "HDFC Bank Limited",
        "query1": "Bajaj Finserv",
        "query2": "HDFC Bank",
        "sector": "Financial Services & Banking",
        "aliases1": ["bajaj finserv", "bajfinsv", "bajajfin", "bajajfinsv.ns"],
        "aliases2": ["hdfc", "hdfc bank", "hdfcbank", "hdfcbank.ns"]
    },
    {
        "key": "titan_vbl",
        "ticker1": "TITAN.NS",
        "ticker2": "VBL.NS",
        "name1": "Titan Company Limited",
        "name2": "Varun Beverages Limited",
        "query1": "Titan",
        "query2": "Varun Beverages",
        "sector": "Consumer Discretionary & Beverages",
        "aliases1": ["titan", "titan company", "titan limited", "titan.ns"],
        "aliases2": ["vbl", "varun beverages", "varun bev", "vbl.ns"]
    },
    {
        "key": "coalindia_adanipower",
        "ticker1": "COALINDIA.NS",
        "ticker2": "ADANIPOWER.NS",
        "name1": "Coal India Limited",
        "name2": "Adani Power Limited",
        "query1": "Coal India",
        "query2": "Adani Power",
        "sector": "Energy, Mining & Utilities",
        "aliases1": ["coal india", "cil", "coalindia", "coalindia.ns"],
        "aliases2": ["adani power", "adanipower", "adani power limited", "adanipower.ns"]
    },
    {
        "key": "tvsmotor_tmpv",
        "ticker1": "TVSMOTOR.NS",
        "ticker2": "TMPV.NS",
        "name1": "TVS Motor Company Limited",
        "name2": "Tata Motors Passenger Vehicles Limited",
        "query1": "TVS Motor",
        "query2": "Tata Motors",
        "sector": "Automobile Leaders",
        "aliases1": ["tvs", "tvs motor", "tvsmotor", "tvsmotor.ns"],
        "aliases2": ["tata motors", "tatamotors", "tmpv", "tmcv", "tmpv.ns", "tatamotors.ns"]
    },
    {
        "key": "siemens_solarinds",
        "ticker1": "SIEMENS.NS",
        "ticker2": "SOLARINDS.NS",
        "name1": "Siemens Limited",
        "name2": "Solar Industries India Limited",
        "query1": "Siemens",
        "query2": "Solar Industries",
        "sector": "Capital Goods & Industrial Defense",
        "aliases1": ["siemens", "siemens india", "siemens.ns"],
        "aliases2": ["solar industries", "solar inds", "solar industries india", "solarinds.ns", "solarinds"]
    },
    {
        "key": "escorts_bharatforg",
        "ticker1": "ESCORTS.NS",
        "ticker2": "BHARATFORG.NS",
        "name1": "Escorts Kubota Limited",
        "name2": "Bharat Forge Limited",
        "query1": "Escorts Kubota",
        "query2": "Bharat Forge",
        "sector": "Engineering & Auto Ancillaries",
        "aliases1": ["escorts", "escorts kubota", "escorts limited", "escorts.ns"],
        "aliases2": ["bharat forge", "bharatforge", "bharat forge limited", "bharatforg.ns"]
    },
    {
        "key": "dlf_godrejprop",
        "ticker1": "DLF.NS",
        "ticker2": "GODREJPROP.NS",
        "name1": "DLF Limited",
        "name2": "Godrej Properties Limited",
        "query1": "DLF",
        "query2": "Godrej Properties",
        "sector": "Real Estate Development",
        "aliases1": ["dlf", "dlf limited", "dlf.ns"],
        "aliases2": ["godrej properties", "godrej prop", "godrej", "godrejprop.ns", "godrejprop"]
    }
]

def _clean_str(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())

def get_pair_key(c1: str, c2: str, ticker1: str = "", ticker2: str = "") -> Optional[str]:
    """
    Matches any user query pair or ticker pair (in either order) to one of the 9 canonical keys.
    """
    clean_c1 = _clean_str(c1)
    clean_c2 = _clean_str(c2)
    clean_t1 = _clean_str(ticker1)
    clean_t2 = _clean_str(ticker2)

    query_tokens_a = {clean_c1, clean_t1} - {""}
    query_tokens_b = {clean_c2, clean_t2} - {""}

    for pair in ASSIGNED_PAIRS:
        aliases_1 = set(_clean_str(a) for a in pair["aliases1"])
        aliases_2 = set(_clean_str(a) for a in pair["aliases2"])

        # Check forward orientation: (c1 matches pair1 AND c2 matches pair2)
        match_forward = (bool(query_tokens_a & aliases_1) and bool(query_tokens_b & aliases_2))
        # Check reverse orientation: (c1 matches pair2 AND c2 matches pair1)
        match_reverse = (bool(query_tokens_a & aliases_2) and bool(query_tokens_b & aliases_1))

        if match_forward or match_reverse:
            return pair["key"]

    return None

def load_demo_snapshot(pair_key: str) -> Optional[Dict[str, Any]]:
    """Loads pre-computed demo snapshot from disk if present."""
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = DEMO_DATA_DIR / f"{pair_key}.json"
    if not snapshot_file.exists():
        return None
    try:
        with open(snapshot_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as exc:
        logger.error(f"Error loading demo snapshot '{pair_key}': {exc}")
        return None

def save_demo_snapshot(pair_key: str, data: Dict[str, Any]) -> Path:
    """Saves serialized analysis response as an offline demo snapshot."""
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_file = DEMO_DATA_DIR / f"{pair_key}.json"
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    logger.info(f"Saved demo snapshot: {snapshot_file}")
    return snapshot_file

def list_available_snapshots() -> Dict[str, bool]:
    """Returns a dictionary indicating snapshot availability for each of the 9 pairs."""
    status = {}
    for pair in ASSIGNED_PAIRS:
        k = pair["key"]
        p = DEMO_DATA_DIR / f"{k}.json"
        status[k] = p.exists() and p.stat().st_size > 500
    return status
