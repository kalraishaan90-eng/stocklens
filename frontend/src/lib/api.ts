import { 
  AnalyzeRequest, 
  AnalysisResponse, 
  HealthResponse, 
  ApiErrorResponse 
} from './types';
import { loadBundledDemo } from './demoSnapshots';

// Read API base URL from environment variables with safe localhost fallback
export const API_BASE_URL = 
  import.meta.env.VITE_API_BASE_URL || 
  'http://localhost:8000';

/**
 * Health check caller for backend status monitoring
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }

  return response.json();
}

/**
 * Executes comparative stock analysis between two companies.
 * Sends POST /api/analyze with payload { company1, company2, use_offline_demo }.
 */
export async function analyzeStocks(
  request: AnalyzeRequest
): Promise<AnalysisResponse> {
  const controller = new AbortController();
  // Live analyses fetch two tickers, benchmark + sector indices, and news
  // headlines; cold-cache runs can take 10-25s on first use.
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
        use_offline_demo: false,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
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
        // Fallback to response status text
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data: AnalysisResponse = await response.json();
    return data;
  } catch (error: any) {
    clearTimeout(timeoutId);
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

/**
 * Search ticker suggestions helper
 */
export async function searchTickerSuggestions(
  query: string
): Promise<Array<{ name: string; ticker: string; display: string }>> {
  if (!query || !query.trim()) return [];
  try {
    const res = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(query.trim())}`);
    if (res.ok) {
      const data = await res.json();
      return data.results || [];
    }
  } catch {
    // Ignore fallback
  }
  return [];
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
