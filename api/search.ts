const COMMON_STOCKS = [
  { name: 'Reliance Industries', ticker: 'RELIANCE.NS', sector: 'Energy' },
  { name: 'Bharti Airtel', ticker: 'BHARTIARTL.NS', sector: 'Telecommunications' },
  { name: 'Hindustan Aeronautics', ticker: 'HAL.NS', sector: 'Industrials' },
  { name: 'Mazagon Dock Shipbuilders', ticker: 'MAZDOCK.NS', sector: 'Industrials' },
  { name: 'Bajaj Finserv', ticker: 'BAJAJFINSV.NS', sector: 'Financial Services' },
  { name: 'HDFC Bank', ticker: 'HDFCBANK.NS', sector: 'Financial Services' },
  { name: 'Titan Company', ticker: 'TITAN.NS', sector: 'Consumer Cyclical' },
  { name: 'Varun Beverages', ticker: 'VBL.NS', sector: 'Consumer Defensive' },
  { name: 'Coal India', ticker: 'COALINDIA.NS', sector: 'Utilities' },
  { name: 'Adani Power', ticker: 'ADANIPOWER.NS', sector: 'Utilities' },
  { name: 'TVS Motor Company', ticker: 'TVSMOTOR.NS', sector: 'Consumer Cyclical' },
  { name: 'Tata Motors', ticker: 'TATAMOTORS.NS', sector: 'Consumer Cyclical' },
  { name: 'Siemens India', ticker: 'SIEMENS.NS', sector: 'Industrials' },
  { name: 'Solar Industries', ticker: 'SOLARINDS.NS', sector: 'Basic Materials' },
  { name: 'Escorts Kubota', ticker: 'ESCORTS.NS', sector: 'Industrials' },
  { name: 'Bharat Forge', ticker: 'BHARATFORG.NS', sector: 'Industrials' },
  { name: 'DLF Limited', ticker: 'DLF.NS', sector: 'Real Estate' },
  { name: 'Godrej Properties', ticker: 'GODREJPROP.NS', sector: 'Real Estate' },
  { name: 'State Bank of India', ticker: 'SBIN.NS', sector: 'Financial Services' },
  { name: 'Tata Consultancy Services', ticker: 'TCS.NS', sector: 'Technology' },
  { name: 'Infosys Limited', ticker: 'INFY.NS', sector: 'Technology' },
  { name: 'Apple Inc.', ticker: 'AAPL', sector: 'Technology' },
  { name: 'Microsoft Corporation', ticker: 'MSFT', sector: 'Technology' },
  { name: 'Alphabet Inc.', ticker: 'GOOGL', sector: 'Technology' },
  { name: 'Amazon.com Inc.', ticker: 'AMZN', sector: 'Consumer Cyclical' },
  { name: 'NVIDIA Corporation', ticker: 'NVDA', sector: 'Technology' },
  { name: 'Morgan Stanley', ticker: 'MS', sector: 'Financial Services' },
  { name: 'JPMorgan Chase & Co.', ticker: 'JPM', sector: 'Financial Services' },
  { name: 'Zomato Limited', ticker: 'ETERNAL.NS', sector: 'Consumer Cyclical' },
  { name: 'Swiggy Limited', ticker: 'SWIGGY.NS', sector: 'Consumer Cyclical' },
];

export default async function handler(req: any, res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const q = String(req.query.q || '').trim();
  if (!q) {
    return res.status(200).json({ results: [] });
  }

  const clean = q.toLowerCase();
  const matched = COMMON_STOCKS.filter(
    (s) =>
      s.name.toLowerCase().includes(clean) ||
      s.ticker.toLowerCase().includes(clean)
  );

  const results = matched.map((s) => ({
    name: s.name,
    ticker: s.ticker,
    display: `${s.name} (${s.ticker})`,
    sector: s.sector,
  }));

  // If query is not matched locally, query Yahoo Finance autocomplete
  if (results.length === 0) {
    try {
      const yRes = await fetch(
        `https://query2.finance.yahoo.com/v1/finance/search?q=${encodeURIComponent(q)}&quotesCount=6`,
        { headers: { 'User-Agent': 'Mozilla/5.0' } }
      );
      if (yRes.ok) {
        const yData = await yRes.json();
        const quotes = yData.quotes || [];
        for (const item of quotes) {
          if (item.symbol && (item.shortname || item.longname)) {
            const name = item.longname || item.shortname;
            results.push({
              name,
              ticker: item.symbol,
              display: `${name} (${item.symbol})`,
              sector: item.sector || 'Diversified',
            });
          }
        }
      }
    } catch {
      // Ignore network fallback errors
    }
  }

  return res.status(200).json({ results: results.slice(0, 10) });
}
