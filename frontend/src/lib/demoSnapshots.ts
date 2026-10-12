import { AnalysisResponse } from './types';

const PAIRS: Array<{ key: string; first: string[]; second: string[] }> = [
  { key: 'hal_mazdock', first: ['hal', 'hindustan aeronautics', 'hal ns'], second: ['mazagon dock', 'mazdock', 'mazagon dock shipbuilders'] },
  { key: 'reliance_bhartiartl', first: ['reliance', 'reliance industries', 'ril'], second: ['bharti airtel', 'airtel', 'bharti'] },
  { key: 'bajajfinsv_hdfcbank', first: ['bajaj finserv', 'bajajfinsv', 'bajfinsv'], second: ['hdfc bank', 'hdfcbank', 'hdfc'] },
  { key: 'titan_vbl', first: ['titan', 'titan company'], second: ['varun beverages', 'vbl'] },
  { key: 'coalindia_adanipower', first: ['coal india', 'coalindia', 'cil'], second: ['adani power', 'adanipower'] },
  { key: 'tvsmotor_tmpv', first: ['tvs motor', 'tvs', 'tvsmotor'], second: ['tata motors', 'tmpv', 'tata motors passenger vehicles'] },
  { key: 'siemens_solarinds', first: ['siemens', 'siemens india'], second: ['solar industries', 'solarinds', 'solar industries india'] },
  { key: 'escorts_bharatforg', first: ['escorts kubota', 'escorts'], second: ['bharat forge', 'bharatforg'] },
  { key: 'dlf_godrejprop', first: ['dlf', 'dlf limited'], second: ['godrej properties', 'godrejprop', 'godrej'] },
];

const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, '');

export function pairSnapshotKey(first: string, second: string): string | undefined {
  const a = normalize(first);
  const b = normalize(second);
  return PAIRS.find((pair) => {
    const left = pair.first.some((alias) => normalize(alias) === a);
    const right = pair.second.some((alias) => normalize(alias) === b);
    const reverseLeft = pair.second.some((alias) => normalize(alias) === a);
    const reverseRight = pair.first.some((alias) => normalize(alias) === b);
    return (left && right) || (reverseLeft && reverseRight);
  })?.key;
}

export async function loadBundledDemo(first: string, second: string): Promise<AnalysisResponse | null> {
  const key = pairSnapshotKey(first, second);
  if (!key) return null;
  try {
    const response = await fetch(`/demo-data/${key}.json`, { cache: 'force-cache' });
    if (!response.ok) return null;
    const result = await response.json() as AnalysisResponse;
    if (!result.is_offline_demo || !result.demo_captured_at || !result.metadata?.is_offline_demo) return null;
    return result;
  } catch {
    return null;
  }
}
