"""
Usage: python tiktok_dl.py <url>
pip install requests playwright
playwright install chromium
"""

import os
import re
import sys
import time
from pathlib import Path

import requests

t0 = time.time()
url = sys.argv[1] if len(sys.argv) > 1 else None
if not url:
    print("bad url", file=sys.stderr)
    sys.exit(1)

m = re.search(r"/video/(\d+)", url)
if not m:
    print("no video id in url", file=sys.stderr)
    sys.exit(1)
video_id = m.group(1)

Path("tt-downloads").mkdir(parents=True, exist_ok=True)
out_file = Path("tt-downloads") / f"{video_id}.mp4"

print(f"downloading {video_id}...")

TIKCDN_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
    "priority": "u=0, i",
    "referer": "https://ssstik.io/",
    "sec-ch-ua": '"Microsoft Edge";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "cross-site",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36 Edg/153.0.0.0"
    ),
}

try:
    res = requests.get(
        f"https://tikcdn.io/ssstik/{video_id}",
        headers=TIKCDN_HEADERS,
        timeout=30,
    )
    res.raise_for_status()
    buf = res.content

    if len(buf) < 10000 or buf[4:8] != b"ftyp":
        raise ValueError(f"tikcdn returned junk ({len(buf)} bytes)")

    out_file.write_bytes(buf)
    ms = int((time.time() - t0) * 1000)
    print(f"saved {out_file} ({len(buf)} bytes)")
    print(f"took: {ms} ms ({ms / 1000:.2f}s)")
    sys.exit(0)

except Exception as e:
    print(f"tikcdn failed: {e} — falling back to playwright", file=sys.stderr)


from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page()
    page.set_extra_http_headers({
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    })

    captured = {"done": False, "buf": None, "err": None}

    VIDEO_RE = re.compile(r"v\d+-webapp.*tiktok\.com")

    def on_response(response):
        if captured["done"]:
            return
        u = response.url
        if VIDEO_RE.search(u) and "mime_type=video_mp4" in u:
            cl = response.headers.get("content-length", "0")
            try:
                cl_int = int(cl)
            except ValueError:
                cl_int = 0
            if cl_int > 1000:
                captured["done"] = True
                try:
                    captured["buf"] = response.body()
                except Exception as e:
                    captured["err"] = e

    page.on("response", on_response)

    try:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass

        deadline = time.time() + 30
        while time.time() < deadline and not captured["done"]:
            page.wait_for_timeout(200)

        if not captured["done"]:
            print("no stream", file=sys.stderr)
            browser.close()
            sys.exit(1)

        if captured["err"]:
            print(captured["err"], file=sys.stderr)
            browser.close()
            sys.exit(1)

        buf = captured["buf"]
        out_file.write_bytes(buf)
        ms = int((time.time() - t0) * 1000)
        print(f"chunk: {len(buf)} bytes")
        print(f"saved {out_file}")
        print(f"took: {ms} ms ({ms / 1000:.2f}s)")
        if buf[4:8] != b"ftyp":
            print("⚠ not ftyp", file=sys.stderr)
        browser.close()
        sys.exit(0)

    except Exception as e:
        print(e, file=sys.stderr)
        browser.close()
        sys.exit(1)
