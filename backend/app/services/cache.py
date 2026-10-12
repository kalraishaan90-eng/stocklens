import sqlite3
import json
import time
from typing import Optional, Any, Tuple, Dict
from app.config import DB_PATH, PRICES_CACHE_DIR, PRICE_CACHE_TTL_SECONDS

def init_db():
    """Initializes the SQLite cache table if not already present."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        conn.commit()

def get_cached(key: str) -> Optional[Any]:
    """Retrieve an item from cache if it exists and has not expired."""
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data, expires_at FROM api_cache WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                data_str, expires_at = row
                if expires_at > int(time.time()):
                    return json.loads(data_str)
                else:
                    # Clean up expired entry
                    cursor.execute("DELETE FROM api_cache WHERE key = ?", (key,))
                    conn.commit()
    except Exception:
        pass
    return None

def set_cached(key: str, data: Any, ttl_seconds: int = 3600) -> None:
    """Store an item in cache with a TTL (seconds)."""
    try:
        init_db()
        expires_at = int(time.time()) + ttl_seconds
        data_str = json.dumps(data)
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO api_cache (key, data, expires_at)
                VALUES (?, ?, ?)
            """, (key, data_str, expires_at))
            conn.commit()
    except Exception:
        pass

def _sanitize_ticker(ticker: str) -> str:
    """Creates a filesystem-safe filename from a stock or index ticker."""
    return ticker.replace("^", "_idx_").replace(".", "_").replace("/", "_").upper()

def get_disk_price_cache(ticker: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Retrieves price data from disk cache.
    Returns:
        (data, is_stale)
        - If no cache file exists: (None, False)
        - If fresh (< 6-hour TTL): (data, False)
        - If expired (> 6-hour TTL): (data, True) [stale cache available for fallback]
    """
    cache_file = PRICES_CACHE_DIR / f"{_sanitize_ticker(ticker)}.json"
    if not cache_file.exists():
        return None, False
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            content = json.load(f)
        expires_at = content.get("expires_at", 0)
        is_stale = time.time() > expires_at
        data = content.get("data", content)
        return data, is_stale
    except Exception:
        return None, False

def set_disk_price_cache(ticker: str, data: Dict[str, Any], ttl_seconds: int = PRICE_CACHE_TTL_SECONDS) -> None:
    """
    Stores price data on disk as JSON with a specified TTL (default: 6 hours = 21600s).
    """
    try:
        PRICES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = PRICES_CACHE_DIR / f"{_sanitize_ticker(ticker)}.json"
        now = time.time()
        container = {
            "ticker": ticker,
            "saved_at": now,
            "ttl_seconds": ttl_seconds,
            "expires_at": now + ttl_seconds,
            "data": data
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(container, f, indent=2)
    except Exception:
        pass
