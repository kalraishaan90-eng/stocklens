import { 
  AnalyzeRequest, 
  AnalysisResponse, 
  HealthResponse, 
  ApiErrorResponse 
} from './types';
import { loadBundledDemo } from './demoSnapshots';

// Read API base URL from environment variables with safe localhost or same-origin fallback
export const API_BASE_URL = 
  import.meta.env.VITE_API_BASE_URL || 
  (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : '');

/**
 * Health check caller for backend status monitoring
 */
export async function checkHealth(): Promise<HealthResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (response.ok) {
      return response.json();
    }
  } catch {
    // Backend offline / not reached
  }

  // Graceful offline fallback health
  return {
    status: 'ok',
    version: '1.0.0',
    mode: 'demo_fallback',
    cache_entries: 0,
    timestamp: new Date().toISOString(),
    gemini_enabled: Boolean(import.meta.env.VITE_GEMINI_API_KEY),
  } as any;
}

/**
 * Executes comparative stock analysis between two companies.
 * Sends POST /api/analyze with payload { company1, company2, use_offline_demo }.
 * Seamlessly falls back to bundled demo snapshot when backend is offline.
 */
export async function analyzeStocks(
  request: AnalyzeRequest
): Promise<AnalysisResponse> {
  // If explicitly requested offline demo, try bundled data first
  if (request.use_offline_demo) {
    const bundled = await loadBundledDemo(request.company1, request.company2);
    if (bundled) return bundled;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout

  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        company1: request.company1.trim(),
        company2: request.company2.trim(),
        use_offline_demo: request.use_offline_demo ?? false,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      // Check if we have a bundled demo snapshot for this comparison pair
      const bundled = await loadBundledDemo(request.company1, request.company2);
      if (bundled) {
        return bundled;
      }

      let errorMessage = `Server error (${response.status})`;
      try {
        const errorData: ApiErrorResponse = await response.json();
        if (errorData && errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData && (errorData as any).detail) {
          errorMessage = typeof (errorData as any).detail === 'string'
            ? (errorData as any).detail
            : JSON.stringify((errorData as any).detail);
        }
      } catch {
        if (response.status === 405) {
          errorMessage = 'The analysis endpoint is currently updating or offline. Please retry in a few moments.';
        } else {
          errorMessage = response.statusText || errorMessage;
        }
      }
      throw new Error(errorMessage);
    }

    const data: AnalysisResponse = await response.json();
    return data;
  } catch (error: any) {
    clearTimeout(timeoutId);

    // If fetch failed or network was down, check for bundled demo snapshot
    const bundled = await loadBundledDemo(request.company1, request.company2);
    if (bundled) {
      return bundled;
    }

    if (error.name === 'AbortError') {
      throw new Error('Analysis request timed out. Please check your internet connection or backend server.');
    }
    throw error;
  }
}

/**
 * Alias for legacy components
 */
export async function fetchStockAnalysis(
  companyA: string,
  companyB: string,
  useOfflineDemo: boolean = false
): Promise<AnalysisResponse> {
  return analyzeStocks({ company1: companyA, company2: companyB, use_offline_demo: useOfflineDemo });
}

export const FALLBACK_STOCKS = [
  { name: 'Reliance Industries', ticker: 'RELIANCE.NS', display: 'Reliance Industries (RELIANCE.NS)', sector: 'Energy' },
  { name: 'Bharti Airtel', ticker: 'BHARTIARTL.NS', display: 'Bharti Airtel (BHARTIARTL.NS)', sector: 'Telecommunications' },
  { name: 'Hindustan Aeronautics', ticker: 'HAL.NS', display: 'Hindustan Aeronautics (HAL.NS)', sector: 'Industrials' },
  { name: 'Mazagon Dock Shipbuilders', ticker: 'MAZDOCK.NS', display: 'Mazagon Dock (MAZDOCK.NS)', sector: 'Industrials' },
  { name: 'Bajaj Finserv', ticker: 'BAJAJFINSV.NS', display: 'Bajaj Finserv (BAJAJFINSV.NS)', sector: 'Financial Services' },
  { name: 'HDFC Bank', ticker: 'HDFCBANK.NS', display: 'HDFC Bank (HDFCBANK.NS)', sector: 'Financial Services' },
  { name: 'Titan Company', ticker: 'TITAN.NS', display: 'Titan Company (TITAN.NS)', sector: 'Consumer Cyclical' },
  { name: 'Varun Beverages', ticker: 'VBL.NS', display: 'Varun Beverages (VBL.NS)', sector: 'Consumer Defensive' },
  { name: 'Coal India', ticker: 'COALINDIA.NS', display: 'Coal India (COALINDIA.NS)', sector: 'Utilities' },
  { name: 'Adani Power', ticker: 'ADANIPOWER.NS', display: 'Adani Power (ADANIPOWER.NS)', sector: 'Utilities' },
  { name: 'TVS Motor Company', ticker: 'TVSMOTOR.NS', display: 'TVS Motor (TVSMOTOR.NS)', sector: 'Consumer Cyclical' },
  { name: 'Tata Motors', ticker: 'TATAMOTORS.NS', display: 'Tata Motors (TATAMOTORS.NS)', sector: 'Consumer Cyclical' },
  { name: 'Siemens India', ticker: 'SIEMENS.NS', display: 'Siemens India (SIEMENS.NS)', sector: 'Industrials' },
  { name: 'Solar Industries', ticker: 'SOLARINDS.NS', display: 'Solar Industries (SOLARINDS.NS)', sector: 'Basic Materials' },
  { name: 'Escorts Kubota', ticker: 'ESCORTS.NS', display: 'Escorts Kubota (ESCORTS.NS)', sector: 'Industrials' },
  { name: 'Bharat Forge', ticker: 'BHARATFORG.NS', display: 'Bharat Forge (BHARATFORG.NS)', sector: 'Industrials' },
  { name: 'DLF Limited', ticker: 'DLF.NS', display: 'DLF Limited (DLF.NS)', sector: 'Real Estate' },
  { name: 'Godrej Properties', ticker: 'GODREJPROP.NS', display: 'Godrej Properties (GODREJPROP.NS)', sector: 'Real Estate' },
  { name: 'State Bank of India', ticker: 'SBIN.NS', display: 'State Bank of India (SBIN.NS)', sector: 'Financial Services' },
  { name: 'Tata Consultancy Services', ticker: 'TCS.NS', display: 'TCS (TCS.NS)', sector: 'Technology' },
  { name: 'Infosys Limited', ticker: 'INFY.NS', display: 'Infosys (INFY.NS)', sector: 'Technology' },
  { name: 'Apple Inc.', ticker: 'AAPL', display: 'Apple Inc. (AAPL)', sector: 'Technology' },
  { name: 'Microsoft Corporation', ticker: 'MSFT', display: 'Microsoft (MSFT)', sector: 'Technology' },
  { name: 'Alphabet Inc.', ticker: 'GOOGL', display: 'Alphabet Inc. (GOOGL)', sector: 'Technology' },
  { name: 'Amazon.com Inc.', ticker: 'AMZN', display: 'Amazon.com (AMZN)', sector: 'Consumer Cyclical' },
  { name: 'NVIDIA Corporation', ticker: 'NVDA', display: 'NVIDIA Corporation (NVDA)', sector: 'Technology' },
  { name: 'Morgan Stanley', ticker: 'MS', display: 'Morgan Stanley (MS)', sector: 'Financial Services' },
  { name: 'JPMorgan Chase & Co.', ticker: 'JPM', display: 'JPMorgan Chase (JPM)', sector: 'Financial Services' },
  { name: 'Zomato Limited', ticker: 'ETERNAL.NS', display: 'Zomato (ETERNAL.NS)', sector: 'Consumer Cyclical' },
  { name: 'Swiggy Limited', ticker: 'SWIGGY.NS', display: 'Swiggy (SWIGGY.NS)', sector: 'Consumer Cyclical' },
];

/**
 * Search ticker suggestions helper
 */
export async function searchTickerSuggestions(
  query: string
): Promise<Array<{ name: string; ticker: string; display: string }>> {
  if (!query || !query.trim()) return [];
  const cleanQ = query.trim().toLowerCase();

  try {
    const res = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(query.trim())}`);
    if (res.ok) {
      const data = await res.json();
      if (data.results && data.results.length > 0) {
        return data.results;
      }
    }
  } catch {
    // Ignore and fallback
  }

  // Offline fuzzy match
  return FALLBACK_STOCKS.filter(
    (s) =>
      s.name.toLowerCase().includes(cleanQ) ||
      s.ticker.toLowerCase().includes(cleanQ) ||
      s.display.toLowerCase().includes(cleanQ)
  );
}

export interface ReportExportOptions {
  company1: string;
  company2: string;
  use_offline_demo: boolean;
  student_name?: string;
  roll_number?: string;
  theme?: 'dark' | 'light';
}

async function downloadReportFile(endpoint: string, options: ReportExportOptions): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/report/${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });

  if (!response.ok) {
    let message = `Report export failed (${response.status})`;
    try {
      const detail = await response.json();
      message = detail.detail || detail.message || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || '';
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1]
    || `StockLens_${endpoint.replace(/-/g, '_')}.${endpoint === 'pdf' ? 'pdf' : 'csv'}`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadReportPdf(options: ReportExportOptions): Promise<void> {
  return downloadReportFile('pdf', options);
}

export function downloadTemplateCsv(options: ReportExportOptions): Promise<void> {
  return downloadReportFile('csv', options);
}

export function downloadGoogleSheetsCsv(options: ReportExportOptions): Promise<void> {
  return downloadReportFile('sheets-csv', options);
}
