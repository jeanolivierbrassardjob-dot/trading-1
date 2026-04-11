export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const key = process.env.ANTHROPIC_KEY;
  if (!key) return res.status(500).json({ error: 'Clé Anthropic manquante' });

  const { prices } = req.body;
  if (!prices) return res.status(400).json({ error: 'Prix manquants' });

  const prompt = `Analyste swing trading H4 FTMO. Prix actuels: XAUUSD=${prices.xau}, NAS100=${prices.nas}, WTI=${prices.oil}, EURUSD=${prices.eur}, BTCUSD=${prices.btc}, USDJPY=${prices.jpy}, VIX=${prices.vix}, DXY=${prices.dxy}. Date: ${new Date().toLocaleString('fr-CA')}.

Donne les 3 meilleurs setups H4. JSON uniquement:
{"setups":[{"symbol":"XAUUSD","direction":"bull","rating":8.5,"why":"2 phrases max en français","scalein1_zone":"4720-4730","scalein1_note":"raison","scalein2_zone":"4700-4710","scalein2_note":"raison","sl_zone":"4685","tags":["tag1"]}]}

Règles: direction=bull/bear/wait, rating=1-10, zones basées sur prix réels, trier par rating desc, JSON seulement.`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': key,
        'anthropic-version': '2023-06-01'
      },
      signal: AbortSignal.timeout(8000),
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 600,
        messages: [{ role: 'user', content: prompt }]
      })
    });

    const d = await r.json();
    const text = d.content?.find(b => b.type === 'text')?.text || '';
    const clean = text.replace(/```json|```/g, '').trim();
    const parsed = JSON.parse(clean);
    return res.status(200).json(parsed);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
