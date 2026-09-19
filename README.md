downloads videos from tiktok and other sites (more coming soon)

# tiktok downloader

## usage

`node tiktok/tiktok-dl.mjs <tiktok-url>`

example:

`node tiktok/tiktok-dl.mjs https://www.tiktok.com/@user/video/1234567890123456789`

output lands in tt-downloads/<videoid>.mp4. folder is created automatically.

## install

`npm install puppeteer`

that's it. no config, no api keys, no account.

## layout
```
downloader/
├── tiktok/
│   └── tiktok-dl.mjs      <- the tiktok downloader
└── tt-downloads/          <- output (created on first run)
```

each platform gets its own folder under the project root. tiktok is the first one. more will slot in alongside it (e.g. youtube/, instagram/, twitter/) as they're added.

## how it works

two strategies, tried in order:

### 1. tikcdn fast path
hits https://tikcdn.io/ssstik/<videoid> with a pile of browser-ish headers (referer ssstik.io, sec-ch-ua, edge user-agent, etc.) to look like a real browser coming from ssstik. if it returns a real mp4 (checked by size > 10kb and the ftyp magic bytes at offset 4), we write it to disk and exit. this is fast (usually under a few seconds) and doesn't need a browser.

### 2. puppeteer fallback
if tikcdn 404s, rate-limits, or hands back junk, we launch headless chromium, navigate to the actual tiktok page, and listen for the network response whose url matches /v\d+-webapp.*tiktok\.com/ and contains mime_type=video_mp4. when we see one with a real content-length, we buffer it, write it, and exit.

## timing / limits
- overall start time is captured at the top (t0) and printed as took: X ms on success.
- tikcdn: no explicit timeout, relies on fetch defaults.
- puppeteer path: 30 second hard timeout. if no matching stream is seen by then, it prints no stream and exits 1.
- navigation itself has a 60s timeout, but errors from page.goto are swallowed (catch(() => {})) because we expect to exit before navigation finishes anyway.

## what it validates
the mp4 is only accepted if:
- buf.length >= 10000
- bytes 4-8 equal ftyp (the ISO base media file format magic)

if tikcdn fails this check, it falls through to puppeteer. if puppeteer's chunk fails the ftyp check it still saves it but prints not ftyp, puppeteer path is more trusting because we matched the URL pattern directly.

## exit codes
- 0 - saved successfully
- 1 - no url arg, no video id in url, no stream captured in 30s, or an unexpected error

## files
- tt-downloads/ - created on run if missing
- tt-downloads/<id>.mp4 - the downloaded video

## caveats
- tiktok changes their video URL structure and CDN hosts regularly. the regex /v\d+-webapp.*tiktok\.com/ may need updating when it stops matching.
- tikcdn.io is a third-party proxy. it can disappear, rate-limit, or serve garbage at any time. the puppeteer fallback exists precisely because of that.
- headless chromium via puppeteer will get flagged by some anti-bot systems sooner or later. if both paths start failing consistently, that's probably why.
- this is for personal use on videos you have the right to download.
