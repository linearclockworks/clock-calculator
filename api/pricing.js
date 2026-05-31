const OWNER = 'linearclockworks';
const REPO = 'clock-calculator';
const FILE = 'pricing.json';
const BRANCH = 'main';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const token = process.env.GITHUB_TOKEN;

  // Parse query params from URL directly
  const url = new URL(req.url, 'http://localhost');
  const history = url.searchParams.get('history');
  const commitSha = url.searchParams.get('commitSha');

  if (req.method === 'GET') {

    // GET history
    if (history) {
      try {
        const r = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/commits?path=${FILE}&per_page=20`, {
          headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' }
        });
        const commits = await r.json();
        const hist = commits.map(c => ({
          sha: c.sha,
          message: c.commit.message.replace('[pricing] ', ''),
          date: c.commit.author.date
        }));
        return res.status(200).json({ history: hist });
      } catch (e) {
        return res.status(500).json({ error: e.message });
      }
    }

    // GET pricing at commit or current
    try {
      const ref = commitSha || BRANCH;
      const r = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE}?ref=${ref}`, {
        headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' }
      });
      if (r.status === 404) return res.status(200).json({ exists: false });
      const data = await r.json();
      const content = JSON.parse(Buffer.from(data.content, 'base64').toString('utf8'));
      return res.status(200).json({ exists: true, sha: data.sha, ...content });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  // POST — save
  if (req.method === 'POST') {
    const { password, clocks, message, sha } = req.body;
    if (password !== process.env.SAVE_PASSWORD) {
      return res.status(401).json({ error: 'Wrong password' });
    }
    const payload = {
      clocks,
      savedAt: new Date().toISOString(),
      message: message || 'Updated pricing'
    };
    const content = Buffer.from(JSON.stringify(payload, null, 2)).toString('base64');
    const body = {
      message: `[pricing] ${message || 'Updated pricing'}`,
      content,
      branch: BRANCH,
      ...(sha ? { sha } : {})
    };
    try {
      const r = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE}`, {
        method: 'PUT',
        headers: {
          Authorization: `token ${token}`,
          Accept: 'application/vnd.github.v3+json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });
      const data = await r.json();
      if (!r.ok) return res.status(500).json({ error: data.message });
      return res.status(200).json({ ok: true, sha: data.content.sha });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
