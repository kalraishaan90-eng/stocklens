export default function handler(req: any, res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const geminiConfigured = Boolean(
    process.env.GEMINI_API_KEY || process.env.VITE_GEMINI_API_KEY
  );

  return res.status(200).json({
    status: 'ok',
    version: '1.0.0',
    mode: 'vercel_serverless',
    timestamp: new Date().toISOString(),
    gemini_enabled: geminiConfigured,
  });
}
