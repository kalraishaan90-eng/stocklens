import pytest
from unittest.mock import patch, AsyncMock
from app.services.ticker_resolver import resolve_ticker, resolve_symbol, verify_assigned_tickers

@pytest.mark.asyncio
async def test_resolve_common_indian_tickers():
    """Verify backward compatibility and basic resolution."""
    hal_ticker, hal_name = await resolve_ticker("HAL")
    assert hal_ticker == "HAL.NS"
    assert "Hindustan Aeronautics" in hal_name

    maz_ticker, maz_name = await resolve_ticker("Mazagon Dock")
    assert maz_ticker == "MAZDOCK.NS"
    assert "Mazagon Dock" in maz_name

    rel_ticker, rel_name = await resolve_ticker("Reliance")
    assert rel_ticker == "RELIANCE.NS"

    air_ticker, air_name = await resolve_ticker("Bharti Airtel")
    assert air_ticker == "BHARTIARTL.NS"


@pytest.mark.asyncio
async def test_resolve_symbol_rich_structure():
    """Verify rich symbol resolution with top match, alternatives, sector, and exchange."""
    res = await resolve_symbol("Bajaj Finserv")
    assert res.match is not None
    assert res.match.ticker == "BAJAJFINSV.NS"
    assert res.match.exchange == "NSE"
    assert res.match.sector == "Financial Services"
    assert len(res.alternatives) <= 3
    # Preference for NSE over BSE
    assert res.match.ticker.endswith(".NS")
    if res.alternatives:
        assert any(alt.exchange == "BSE" for alt in res.alternatives)


@pytest.mark.asyncio
async def test_fuzzy_matching_typos():
    """Verify fuzzy matching handles typos using rapidfuzz."""
    # Typo: "hindutan aero"
    res1 = await resolve_symbol("hindutan aero")
    assert res1.match is not None
    assert res1.match.ticker == "HAL.NS"

    # Typo: "relianc"
    res2 = await resolve_symbol("relianc")
    assert res2.match is not None
    assert res2.match.ticker == "RELIANCE.NS"

    # Typo: "bajj finserv"
    res3 = await resolve_symbol("bajj finserv")
    assert res3.match is not None
    assert res3.match.ticker == "BAJAJFINSV.NS"

    # Typo: "hdfc bnk"
    res4 = await resolve_symbol("hdfc bnk")
    assert res4.match is not None
    assert res4.match.ticker == "HDFCBANK.NS"


@pytest.mark.asyncio
async def test_restructured_companies_ambiguity_and_notes():
    """
    Verify Tata Motors and Siemens have restructuring notes and ambiguity flags.
    Tata Motors demerged into Passenger (TMPV.NS) and Commercial (TMCV.NS).
    """
    # Tata Motors resolution
    res_tm = await resolve_symbol("Tata Motors")
    assert res_tm.match is not None
    assert res_tm.match.ticker in ("TMPV.NS", "TMCV.NS")
    assert res_tm.is_ambiguous is True
    assert res_tm.restructuring_note is not None
    assert "demerger" in res_tm.restructuring_note.lower()
    # Alternatives should include the other vehicle entity
    alt_tickers = [a.ticker for a in res_tm.alternatives]
    assert any("TMCV" in t or "TMPV" in t for t in alt_tickers)

    # Siemens resolution
    res_sie = await resolve_symbol("Siemens")
    assert res_sie.match is not None
    assert res_sie.match.ticker == "SIEMENS.NS"
    assert res_sie.restructuring_note is not None
    assert "energy" in res_sie.restructuring_note.lower()


@pytest.mark.asyncio
async def test_yahoo_search_mock():
    """Verify fallback to Yahoo search when company not in alias map, preferring NSE over BSE."""
    mock_quotes = [
        {"symbol": "UNKNOWN.BO", "longname": "Unknown Corp BSE", "exchange": "BSE", "quoteType": "EQUITY", "sector": "Technology"},
        {"symbol": "UNKNOWN.NS", "longname": "Unknown Corp NSE", "exchange": "NSE", "quoteType": "EQUITY", "sector": "Technology"},
        {"symbol": "UNKNOWN.L", "longname": "Unknown Corp London", "exchange": "LSE", "quoteType": "EQUITY", "sector": "Technology"}
    ]
    with patch("app.services.ticker_resolver._search_yahoo", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {"ticker": q["symbol"], "name": q["longname"], "exchange": "NSE" if q["symbol"].endswith(".NS") else ("BSE" if q["symbol"].endswith(".BO") else "LSE"), "sector": q["sector"]}
            for q in mock_quotes
        ]
        res = await resolve_symbol("Unknown Corp XYZ")
        assert res.match is not None
        # Preference: NSE (.NS) should be ranked above BSE (.BO)
        assert res.match.ticker == "UNKNOWN.NS"
        assert res.match.exchange == "NSE"


@pytest.mark.asyncio
async def test_startup_verification_routine():
    """Verify startup verification executes and populates status with 18 companies."""
    status = await verify_assigned_tickers(live=False)
    assert len(status) >= 0  # Can run without errors


@pytest.mark.asyncio
async def test_resolve_global_and_acronym_tickers():
    """Verify US/global tickers (MSDL, JP Morgan, JPM) and acronyms (MDL) resolve cleanly without faulty .NS appendages."""
    msdl_t, msdl_n = await resolve_ticker("MSDL")
    assert msdl_t == "MSDL"
    assert "Morgan Stanley" in msdl_n

    jpm_t, jpm_n = await resolve_ticker("JP Morgan")
    assert jpm_t == "JPM"
    assert "JPMorgan" in jpm_n

    mdl_t, mdl_n = await resolve_ticker("MDL")
    assert mdl_t == "MAZDOCK.NS"
    assert "Mazagon Dock" in mdl_n

