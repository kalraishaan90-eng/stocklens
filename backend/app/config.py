import os
from pathlib import Path
from typing import List
from urllib.parse import urlsplit
from dotenv import load_dotenv

# Base backend directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "StockLens API"
    VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Exact origins only; wildcard origins are rejected because credentials are enabled.
    CORS_ORIGINS: List[str] = [origin.strip().rstrip("/") for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()]
    for origin in CORS_ORIGINS:
        parsed_origin = urlsplit(origin)
        if origin == "*" or parsed_origin.scheme not in {"http", "https"} or not parsed_origin.netloc or parsed_origin.path or parsed_origin.query or parsed_origin.fragment or parsed_origin.username:
            raise ValueError("CORS_ORIGINS must contain explicit http(s) origins without paths or wildcards")
    
    # Integration keys and flags
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    OFFLINE_DEMO_ENABLED: bool = os.getenv("OFFLINE_DEMO_ENABLED", "false").lower() in ("true", "1", "yes")
    ANALYZE_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("ANALYZE_RATE_LIMIT_PER_MINUTE", "60"))

    CACHE_DIR: Path = BASE_DIR / "cache"
    DB_PATH: Path = CACHE_DIR / "stocklens_cache.db"
    PRICES_CACHE_DIR: Path = CACHE_DIR / "prices"
    PRICE_CACHE_TTL_SECONDS: int = int(os.getenv("PRICE_CACHE_TTL_SECONDS", str(6 * 3600)))  # 6-hour TTL

    # Benchmark and Sector Index mapping for Indian markets
    BENCHMARK_INDEX: str = "^NSEI"
    SECTOR_INDEX_MAP: dict = {
        "Financial Services": "^NSEBANK",
        "Banking": "^NSEBANK",
        "Financial": "^NSEBANK",
        "Technology": "^CNXIT",
        "Information Technology": "^CNXIT",
        "Automobile": "^CNXAUTO",
        "Auto": "^CNXAUTO",
        "Consumer Cyclical": "^CNXAUTO",
        "Energy": "^CNXENERGY",
        "Oil & Gas": "^CNXENERGY",
        "Utilities": "^CNXENERGY",
        "Real Estate": "^CNXREALTY",
        "Consumer Defensive": "^CNXFMCG",
        "Consumer Goods": "^CNXFMCG",
        "FMCG": "^CNXFMCG",
        "Basic Materials": "^CNXMETAL",
        "Metals": "^CNXMETAL",
        "Metal": "^CNXMETAL",
        "Industrials": "^CNXINFRA",
        "Infrastructure": "^CNXINFRA",
        "Aerospace & Defense": "^CNXINFRA",
        "Capital Goods": "^CNXINFRA",
    }

    # Recommendation Weights (summing to target scale base 5.0)
    DEFAULT_RECOMMENDATION_WEIGHTS: dict = {
        "trend": 1.25,
        "momentum": 1.0,
        "risk": 1.0,
        "quality_of_returns": 1.0,
        "distance_52w": 0.75,
        "valuation": 0.5,
    }

    # Profile specific weighting regimes
    INVESTOR_PROFILE_WEIGHTS: dict = {
        "Conservative": {
            "trend": 0.75,
            "momentum": 0.5,
            "risk": 1.75,
            "quality_of_returns": 1.25,
            "distance_52w": 0.5,
            "valuation": 0.75,
        },
        "Balanced": {
            "trend": 1.25,
            "momentum": 1.0,
            "risk": 1.0,
            "quality_of_returns": 1.0,
            "distance_52w": 0.75,
            "valuation": 0.5,
        },
        "Aggressive": {
            "trend": 1.25,
            "momentum": 2.25,
            "risk": 0.25,
            "quality_of_returns": 0.75,
            "distance_52w": 0.75,
            "valuation": 0.25,
        }
    }

    # NIFTY 50 baseline for risk benchmarking
    NIFTY_BENCHMARK: dict = {
        "annualized_volatility_pct": 14.5,
        "max_drawdown_pct": 12.0,
    }

    # Sector Median P/E reference values
    SECTOR_PE_MEDIANS: dict = {
        "defence": 42.0,
        "shipbuilding": 40.0,
        "aerospace": 42.0,
        "technology": 28.0,
        "it": 28.0,
        "information technology": 28.0,
        "banking": 16.0,
        "financial": 18.0,
        "finance": 18.0,
        "auto": 24.0,
        "automobile": 24.0,
        "pharma": 32.0,
        "healthcare": 32.0,
        "fmcg": 48.0,
        "consumer": 45.0,
        "energy": 16.0,
        "power": 18.0,
        "metals": 12.0,
        "steel": 12.0,
        "general": 25.0,
        "diversified": 25.0,
    }

    # Risk-free rate for Sharpe ratio calculation (6.5% standard for Indian 10Y Sovereign benchmark)
    RISK_FREE_RATE_PCT: float = float(os.getenv("RISK_FREE_RATE_PCT", "6.5"))
    BENCHMARK_TICKER: str = os.getenv("BENCHMARK_TICKER", "^NSEI")

    # Stability Score Weights (Higher = More Stable, 0-100)
    STABILITY_WEIGHTS: dict = {
        "volatility": 0.40,   # 40% weight on lower annualized volatility
        "drawdown": 0.35,     # 35% weight on shallow max drawdown
        "consistency": 0.25   # 25% weight on trend consistency (% months above 3-month MA)
    }

    # Growth Score Weights (Higher = Stronger Growth, 0-100)
    GROWTH_WEIGHTS: dict = {
        "cagr": 0.45,         # 45% weight on compound annual growth rate
        "momentum": 0.30,     # 30% weight on trailing 3-month momentum
        "trend": 0.25         # 25% weight on trend signals (50-DMA position and 3M MA slope)
    }

settings = Settings()
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
settings.PRICES_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Direct exports for backward compatibility
GEMINI_API_KEY = settings.GEMINI_API_KEY
CACHE_TTL_SECONDS = settings.CACHE_TTL_SECONDS
OFFLINE_DEMO_ENABLED = settings.OFFLINE_DEMO_ENABLED
CACHE_DIR = settings.CACHE_DIR
DB_PATH = settings.DB_PATH
PRICES_CACHE_DIR = settings.PRICES_CACHE_DIR
PRICE_CACHE_TTL_SECONDS = settings.PRICE_CACHE_TTL_SECONDS
BENCHMARK_INDEX = settings.BENCHMARK_INDEX
SECTOR_INDEX_MAP = settings.SECTOR_INDEX_MAP
DEFAULT_RECOMMENDATION_WEIGHTS = settings.DEFAULT_RECOMMENDATION_WEIGHTS
INVESTOR_PROFILE_WEIGHTS = settings.INVESTOR_PROFILE_WEIGHTS
NIFTY_BENCHMARK = settings.NIFTY_BENCHMARK
SECTOR_PE_MEDIANS = settings.SECTOR_PE_MEDIANS
RISK_FREE_RATE_PCT = settings.RISK_FREE_RATE_PCT
BENCHMARK_TICKER = settings.BENCHMARK_TICKER
STABILITY_WEIGHTS = settings.STABILITY_WEIGHTS
GROWTH_WEIGHTS = settings.GROWTH_WEIGHTS
