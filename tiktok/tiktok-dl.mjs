// Usage: node tiktok-dl.mjs <url>
import fs from 'fs';

const t0 = Date.now();
const url = process.argv[2];
if (!url) { console.error('bad url'); process.exit(1); }

const id = url.match(/\/video\/(\d+)/)?.[1];
if (!id) { console.error('no video id in url'); process.exit(1); }

fs.mkdirSync('tt-downloads', { recursive: true });
const file = `tt-downloads/${id}.mp4`;

console.log(`downloading ${id}...`);
try {
  const res = await fetch(`https://tikcdn.io/ssstik/${id}`, {
    headers: {
      'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
      'accept-encoding': 'gzip, deflate, br, zstd',
      'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
      'priority': 'u=0, i',
      'referer': 'https://ssstik.io/',
      'sec-ch-ua': '"Microsoft Edge";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
      'sec-ch-ua-mobile': '?0',
      'sec-ch-ua-platform': '"Windows"',
      'sec-fetch-dest': 'document',
      'sec-fetch-mode': 'navigate',
      'sec-fetch-site': 'cross-site',
      'sec-fetch-user': '?1',
      'upgrade-insecure-requests': '1',
      'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0',
    },
  });

  if (!res.ok) throw new Error(`tikcdn ${res.status}`);

  const buf = Buffer.from(await res.arrayBuffer());

  if (buf.length < 10000 || buf.slice(4, 8).toString() !== 'ftyp') {
    throw new Error(`tikcdn returned junk (${buf.length} bytes)`);
  }

  fs.writeFileSync(file, buf);
  const ms = Date.now() - t0;
  console.log(`saved ${file} (${buf.length} bytes)`);
  console.log(`took: ${ms} ms (${(ms / 1000).toFixed(2)}s)`);
  process.exit(0);
} catch (e) {
  console.warn(`tikcdn failed: ${e.message} — falling back to puppeteer`);
}

const { default: puppeteer } = await import('puppeteer');

const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
const page = await browser.newPage();
await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36');

let done = false;

page.on('response', r => {
  if (done) return;
  const u = r.url();
  if (/v\d+-webapp.*tiktok\.com/.test(u) && u.includes('mime_type=video_mp4')) {
    const len = parseInt(r.headers()['content-length'] || '0', 10);
    if (len > 1000) {
      done = true;
      r.buffer().then(b => {
        fs.writeFileSync(file, b);
        const ms = Date.now() - t0;
        console.log(`chunk: ${b.length} bytes`);
        console.log(`saved ${file}`);
        console.log(`took: ${ms} ms (${(ms / 1000).toFixed(2)}s)`);
        if (b.slice(4, 8).toString() !== 'ftyp') console.warn('⚠ not ftyp');
        process.exit(0);
      }).catch(e => { console.error(e); process.exit(1); });
    }
  }
});

page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
setTimeout(() => { console.error('no stream'); process.exit(1); }, 30000);
