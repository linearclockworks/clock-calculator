const OWNER = 'linearclockworks';
const REPO = 'clock-calculator';
const FILE = 'pricing.json';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  const token = process.env.GITHUB_TOKEN;
  try {
    const r = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/commits?path=${FILE}&per_page=20`, {
      headers: { Authorization: `token ${token}`, Accept: 'application/vnd.github.v3+json' }
    });
    const commits = await r.json();
    const history = commits.map(c => ({
      sha: c.sha,
      message: c.commit.message.replace('[pricing] ', ''),
      date: c.commit.author.date
    }));
    return res.status(200).json({ history });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
