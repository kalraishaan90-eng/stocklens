import { AnalysisResponse } from './types';

const PAIRS: Array<{ key: string; first: string[]; second: string[] }> = [
  { key: 'hal_mazdock', first: ['hal', 'hindustan aeronautics', 'hal ns', 'hal.ns'], second: ['mazagon dock', 'mazdock', 'mazagon dock shipbuilders', 'mazdock ns', 'mazdock.ns'] },
  { key: 'reliance_bhartiartl', first: ['reliance', 'reliance industries', 'ril', 'reliance ns', 'reliance.ns'], second: ['bharti airtel', 'airtel', 'bharti', 'bhartiartl ns', 'bhartiartl.ns'] },
  { key: 'bajajfinsv_hdfcbank', first: ['bajaj finserv', 'bajajfinsv', 'bajfinsv', 'bajajfinsv ns', 'bajajfinsv.ns'], second: ['hdfc bank', 'hdfcbank', 'hdfc', 'hdfcbank ns', 'hdfcbank.ns'] },
  { key: 'titan_vbl', first: ['titan', 'titan company', 'titan ns', 'titan.ns'], second: ['varun beverages', 'vbl', 'vbl ns', 'vbl.ns'] },
  { key: 'coalindia_adanipower', first: ['coal india', 'coalindia', 'cil', 'coalindia ns', 'coalindia.ns'], second: ['adani power', 'adanipower', 'adanipower ns', 'adanipower.ns'] },
  { key: 'tvsmotor_tmpv', first: ['tvs motor', 'tvs', 'tvsmotor', 'tvsmotor ns', 'tvsmotor.ns'], second: ['tata motors', 'tmpv', 'tata motors passenger vehicles', 'tatamotors', 'tatamotors ns', 'tatamotors.ns'] },
  { key: 'siemens_solarinds', first: ['siemens', 'siemens india', 'siemens ns', 'siemens.ns'], second: ['solar industries', 'solarinds', 'solar industries india', 'solarinds ns', 'solarinds.ns'] },
  { key: 'escorts_bharatforg', first: ['escorts kubota', 'escorts', 'escorts ns', 'escorts.ns'], second: ['bharat forge', 'bharatforg', 'bharatforg ns', 'bharatforg.ns'] },
  { key: 'dlf_godrejprop', first: ['dlf', 'dlf limited', 'dlf ns', 'dlf.ns'], second: ['godrej properties', 'godrejprop', 'godrej', 'godrejprop ns', 'godrejprop.ns'] },
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
