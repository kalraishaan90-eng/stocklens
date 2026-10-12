export default async function handler(req: any, res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const endpoint = String(req.query.endpoint || 'csv').toLowerCase();
  const { company1, company2, student_name, roll_number } = req.body || {};

  const c1 = company1 || 'Company 1';
  const c2 = company2 || 'Company 2';

  if (endpoint === 'csv' || endpoint === 'sheets-csv') {
    const csvContent = [
      `# StockLens Quantitative Analysis Report`,
      `# Generated: ${new Date().toISOString()}`,
      `# Pair: ${c1} vs ${c2}`,
      ...(student_name ? [`# Student: ${student_name} (Roll: ${roll_number || 'N/A'})`] : []),
      ``,
      `Month-Year,${c1} Close,${c1} 3M-MA,${c2} Close,${c2} 3M-MA`,
      `2024-10,100.00,,100.00,`,
      `2024-11,104.50,,102.10,`,
      `2024-12,108.20,104.23,101.50,101.20`,
      `2025-01,112.40,108.37,105.80,103.13`,
      `2025-02,110.10,110.23,108.40,105.23`,
      `2025-03,115.60,112.70,111.20,108.47`,
    ].join('\r\n');

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="StockLens_${c1}_vs_${c2}_Template.csv"`);
    return res.status(200).send(csvContent);
  }

  return res.status(400).json({ error: `Unsupported report endpoint: ${endpoint}` });
}
