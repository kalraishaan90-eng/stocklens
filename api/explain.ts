export default async function handler(req: any, res: any) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const apiKey = process.env.GEMINI_API_KEY || process.env.VITE_GEMINI_API_KEY;
  if (!apiKey) {
    return res.status(400).json({
      error: 'GEMINI_API_KEY is not configured in Vercel environment variables.',
      gemini_enabled: false,
    });
  }

  const { prompt, raw_analysis } = req.body || {};
  const userPrompt = prompt || (raw_analysis ? `You are an academic financial editor reviewing a Senior Secondary School Science Exhibition Project. Please polish the provided comparative stock analysis into elegant, professional academic prose without inventing any new figures:\n\n${raw_analysis}` : '');

  if (!userPrompt) {
    return res.status(400).json({ error: 'Prompt or analysis text required' });
  }

  try {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
    const geminiRes = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: userPrompt }] }],
        generationConfig: { temperature: 0.2, maxOutputTokens: 600 }
      }),
    });

    if (!geminiRes.ok) {
      const errText = await geminiRes.text();
      return res.status(geminiRes.status).json({ error: `Gemini API error: ${errText}` });
    }

    const data = await geminiRes.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || '';

    return res.status(200).json({
      text,
      gemini_enabled: true,
      model: 'gemini-1.5-flash',
    });
  } catch (err: any) {
    return res.status(500).json({ error: err.message || 'Internal server error' });
  }
}
