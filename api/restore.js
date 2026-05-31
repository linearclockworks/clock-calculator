const OWNER = 'linearclockworks';
const REPO = 'clock-calculator';
const FILE = 'pricing.json';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const token = process.env.GITHUB_TOKEN;
  const url = new URL(req.url, 'http://localhost');
  const commitSha = url.searchParams.get('sha');
  if (!commitSha) return res.status(400).json({ error: 'sha required' });
  try {
    const r = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE}?ref=${commitSha}`, {
      headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' }
    });
    if (r.status === 404) return res.status(404).json({ error: 'not found' });
    const data = await r.json();
    const content = JSON.parse(Buffer.from(data.content, 'base64').toString('utf8'));
    return res.status(200).json(content);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
