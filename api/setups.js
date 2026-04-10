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

  const prompt = `Tu es un analyste de marché expert en swing trading H4 pour un trader FTMO.

Prix actuels en temps réel :
- XAUUSD (Or spot) : ${prices.xau || 'N/A'}
- NAS100 (Nasdaq) : ${prices.nas || 'N/A'}
- WTICOUSD (Pétrole WTI) : ${prices.oil || 'N/A'}
- EURUSD : ${prices.eur || 'N/A'}
- BTCUSD : ${prices.btc || 'N/A'}
- USDJPY : ${prices.jpy || 'N/A'}
- VIX : ${prices.vix || 'N/A'}
- DXY : ${prices.dxy || 'N/A'}
- Date/heure : ${new Date().toLocaleString('fr-CA')}

Identifie les 3 MEILLEURS setups swing H4 disponibles MAINTENANT parmi : XAUUSD, NAS100, WTICOUSD, EURUSD, BTCUSD, USDJPY.

Réponds UNIQUEMENT en JSON valide, format exact :
{
  "setups": [
    {
      "symbol": "XAUUSD",
      "direction": "bull",
      "rating": 8.5,
      "why": "Explication courte en français (max 2 phrases)",
      "scalein1_zone": "4720–4730",
      "scalein1_note": "Raison du niveau",
      "scalein2_zone": "4700–4710",
      "scalein2_note": "Raison du niveau",
      "sl_zone": "4685",
      "tags": ["Setup actif", "Tendance intacte"]
    }
  ]
}

Règles :
- direction : "bull" pour long, "bear" pour short, "wait" si pas clair
- rating : entre 1 et 10, sois honnête
- Zones scale in basées sur les VRAIS prix fournis
- SL sous support significatif (long) ou au-dessus résistance (short)
- Trie par rating décroissant
- JSON uniquement, aucun texte avant ou après`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': key,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-20250514',
        max_tokens: 1000,
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
