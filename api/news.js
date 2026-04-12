export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');

  const { q = 'forex trading financial markets' } = req.query;
  const key = process.env.MEDIASTACK_KEY;

  if (!key) {
    return res.status(500).json({ error: 'Clé Mediastack manquante' });
  }

  try {
    // Date d'aujourd'hui et d'hier pour filtrer les nouvelles récentes
    const today = new Date();
    const twoDaysAgo = new Date(today);
    twoDaysAgo.setDate(today.getDate() - 2);
    const dateFrom = twoDaysAgo.toISOString().split('T')[0];

    const url = `http://api.mediastack.com/v1/news?access_key=${key}&keywords=${encodeURIComponent(q)}&languages=en&limit=10&sort=published_desc&categories=business&date=${dateFrom},${today.toISOString().split('T')[0]}`;
    const r = await fetch(url);
    const d = await r.json();

    if (d.error) {
      return res.status(400).json({ error: d.error.message });
    }

    const articles = (d.data || [])
      .filter(a => a.title && a.title.length > 10)
      .map(a => ({
        title: a.title,
        url: a.url || '#',
        source: a.source,
        published: a.published_at || new Date().toISOString(),
        description: a.description || '',
      }));

    return res.status(200).json({ articles });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
