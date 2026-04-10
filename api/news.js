export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');

  const { q = 'forex gold oil markets geopolitical' } = req.query;
  const key = process.env.MEDIASTACK_KEY;

  if (!key) {
    return res.status(500).json({ error: 'Clé Mediastack manquante' });
  }

  try {
    const url = `http://api.mediastack.com/v1/news?access_key=${key}&keywords=${encodeURIComponent(q)}&languages=en,fr&limit=10&sort=published_desc&categories=business,general`;
    const r = await fetch(url);
    const d = await r.json();

    if (d.error) {
      return res.status(400).json({ error: d.error.message });
    }

    const articles = (d.data || []).map(a => ({
      title: a.title,
      url: a.url,
      source: a.source,
      published: a.published_at,
      description: a.description,
    }));

    return res.status(200).json({ articles });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
