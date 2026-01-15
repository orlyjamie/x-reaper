#!/usr/bin/env python3
"""
X-REAPER: Hunt down deleted/protected tweets from the grave
"""

import os
import sys
import time
import re
import json
import asyncio
import io
from urllib.parse import quote
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

try:
    import aiohttp
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("pip install aiohttp requests beautifulsoup4 warcio")
    sys.exit(1)

try:
    from warcio.archiveiterator import ArchiveIterator
    HAS_WARCIO = True
except ImportError:
    HAS_WARCIO = False

BASE_URL = "https://ghostarchive.org"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

R = "\033[91m"
G = "\033[92m"
Y = "\033[93m"
B = "\033[94m"
C = "\033[96m"
W = "\033[97m"
D = "\033[90m"
X = "\033[0m"

BANNER = f"""{R}
 ██╗  ██╗      ██████╗ ███████╗ █████╗ ██████╗ ███████╗██████╗
 ╚██╗██╔╝      ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝██╔══██╗
  ╚███╔╝ █████╗██████╔╝█████╗  ███████║██████╔╝█████╗  ██████╔╝
  ██╔██╗ ╚════╝██╔══██╗██╔══╝  ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
 ██╔╝ ██╗      ██║  ██║███████╗██║  ██║██║     ███████╗██║  ██║
 ╚═╝  ╚═╝      ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
{Y}            ☠  HUNT DOWN THE DEAD TWEETS  ☠{X}
"""

REAPER = r"""
⠀⠀⣿⠲⠤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⣸⡏⠀⠀⠀⠉⠳⢄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⣿⠀⠀⠀⠀⠀⠀⠀⠉⠲⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢰⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠲⣄⠀⠀⠀⡰⠋⢙⣿⣦⡀⠀⠀⠀⠀⠀
⠸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣙⣦⣮⣤⡀⣸⣿⣿⣿⣆⠀⠀⠀⠀
⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⣿⣿⠀⣿⢟⣫⠟⠋⠀⠀⠀⠀
⠀⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⣿⣿⣷⣷⣿⡁⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⢸⣿⣿⣧⣿⣿⣆⠙⢆⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢾⣿⣤⣿⣿⣿⡟⠹⣿⣿⣿⣿⣷⡀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣿⣿⣿⣿⣧⣴⣿⣿⣿⣿⠏⢧⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⠀⠈⢳⡀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡏⣸⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⠀⠀⢳
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⢀⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠸⣿⣿⣿⣿⣿⣿⣿⣿⠏⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⡇⢠⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠃⢸⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣼⢸⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣾⣿⢸⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⣿⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠛⠻⠿⣿⣿⣿⡿⠿⠿⠿⠿⠿⢿⣿⣿⠏⠀⠀⠀⠀⠀⠀
"""

X_LOGO = r"""
██╗  ██╗
╚██╗██╔╝
 ╚███╔╝
 ██╔██╗
██╔╝ ██╗
╚═╝  ╚═╝
"""

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def animate_hunt(username):
    """Full reaper chasing X logo."""
    reaper_lines = [l for l in REAPER.strip().split('\n') if l]
    x_lines = [l for l in X_LOGO.strip().split('\n') if l]

    for frame in range(18):
        clear()
        print(BANNER)
        print(f"\n{Y}  ☠ HUNTING: @{username}{X}\n")

        gap = max(5, 45 - frame * 3)

        # Print reaper with X logo beside it (X at middle height of reaper)
        x_start = 8  # Where X logo starts vertically relative to reaper

        for i, rline in enumerate(reaper_lines):
            x_idx = i - x_start
            xline = x_lines[x_idx] if 0 <= x_idx < len(x_lines) else ""
            print(f"  {R}{rline}{X}{' ' * gap}{B}{xline}{X}")

        time.sleep(0.07)

    # Caught frame
    clear()
    print(BANNER)
    print(f"\n{G}  ☠ CAUGHT @{username}! ☠{X}\n")

    for i, rline in enumerate(reaper_lines):
        x_idx = i - 8
        xline = x_lines[x_idx] if 0 <= x_idx < len(x_lines) else ""
        print(f"  {R}{rline}{X}  {B}{xline}{X}")

    print(f"\n{Y}  EXTRACTING SOULS...{X}")
    time.sleep(0.5)

def print_tweet(idx, tweet_id, date, text):
    """Print full tweet."""
    tid = tweet_id or '???'
    dt = date or ''
    txt = text if text else f'{D}[content in saved snapshot]{X}'

    print(f"{R}💀{X} {Y}#{idx}{X} | {C}Tweet:{X} {tid} | {D}{dt}{X}")
    print(f"   {W}{txt}{X}")
    print()

def show_reaper_spinning():
    """Show reaper with spinning scythe effect."""
    reaper_lines = [l for l in REAPER.strip().split('\n') if l]
    for line in reaper_lines:
        print(f"  {R}{line}{X}")

# ============ SCRAPING (ASYNC) ============

def parse_results(html: str, target: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    table = soup.find('table')
    if not table:
        return results

    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
        link = cells[1].find('a')
        if not link:
            continue

        href = link.get('href', '')
        orig = link.text.strip()

        m = re.search(r'/archive/([A-Za-z0-9]+)', href)
        if not m:
            continue

        aid = m.group(1)
        date = cells[2].text.strip()

        tid_m = re.search(r'/status/(\d+)', orig)
        tid = tid_m.group(1) if tid_m else None

        user_m = re.search(r'x\.com/([^/]+)', orig)
        user = user_m.group(1) if user_m else None

        if user and user.lower() == target.lower():
            results.append({'id': aid, 'tweet_id': tid, 'date': date, 'text': None})
    return results

def extract_text(data, tid=None):
    def find(obj, d=0):
        if d > 12 or not isinstance(obj, (dict, list)):
            return None
        if isinstance(obj, dict):
            if 'legacy' in obj and isinstance(obj['legacy'], dict):
                leg = obj['legacy']
                if tid:
                    if obj.get('rest_id') == tid and 'full_text' in leg:
                        return leg['full_text']
                elif 'full_text' in leg:
                    return leg['full_text']
            for v in obj.values():
                r = find(v, d+1)
                if r:
                    return r
        elif isinstance(obj, list):
            for i in obj[:25]:
                r = find(i, d+1)
                if r:
                    return r
        return None
    return find(data)

def fetch_tweet_sync(t: dict) -> dict:
    """Fetch single tweet content - sync with requests (more reliable for WARC)."""
    if not t.get('tweet_id') or not HAS_WARCIO:
        return t

    try:
        # Get archive page to find WARC URL
        r = requests.get(f"{BASE_URL}/archive/{t['id']}", headers=HEADERS, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        el = soup.find('replay-web-page')
        if not el:
            return t

        warc_url = el.get('source')
        if not warc_url:
            return t

        # Fetch and parse WARC with streaming
        r = requests.get(warc_url, headers=HEADERS, timeout=12, stream=True)
        for rec in ArchiveIterator(r.raw):
            if rec.rec_type == 'response':
                uri = rec.rec_headers.get_header('WARC-Target-URI', '')
                ct = rec.http_headers.get_header('Content-Type', '') if rec.http_headers else ''
                if ('TweetDetail' in uri or 'TweetResultByRestId' in uri) and 'json' in ct:
                    data = json.loads(rec.content_stream().read().decode('utf-8', errors='ignore'))
                    txt = extract_text(data, t['tweet_id'])
                    if txt:
                        t['text'] = txt
                        return t
    except:
        pass
    return t

async def search_page_async(session: aiohttp.ClientSession, username: str, page: int) -> list[dict]:
    """Search one page async."""
    try:
        url = f"{BASE_URL}/search?term={quote(f'https://x.com/{username}', safe='')}"
        if page > 0:
            url += f"&page={page}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            html = await resp.text()
        return parse_results(html, username)
    except:
        return []

async def scrape_async(username: str):
    """Hybrid scraper - async search, threaded WARC extraction."""
    seen = set()
    all_tweets = []
    counter = [0]
    import threading
    print_lock = threading.Lock()

    print(f"\n{D}  ☠ Scanning graves...{X}")

    connector = aiohttp.TCPConnector(limit=50, limit_per_host=15)
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        # Search all pages in parallel (async - fast)
        search_tasks = [search_page_async(session, username, p) for p in range(10)]
        page_results = await asyncio.gather(*search_tasks)

        # Dedupe by tweet_id
        for results in page_results:
            for t in results:
                tid = t.get('tweet_id') or t['id']
                if tid not in seen:
                    seen.add(tid)
                    all_tweets.append(t)

        if not all_tweets:
            return []

    print(f"{G}  ☠ Found {len(all_tweets)} souls!{X}\n")
    print(f"{G}{'─'*70}{X}\n")

    # Animated skull spinner
    skulls = ['💀', '☠️ ', '🦴', '☠️ ']
    spinner_active = [True]
    extracted = [0]

    def spinner():
        i = 0
        while spinner_active[0]:
            frame = skulls[i % len(skulls)]
            sys.stdout.write(f"\r{Y}  {frame} REAPING... [{extracted[0]}/{len(all_tweets)}]{X}    ")
            sys.stdout.flush()
            time.sleep(0.12)
            i += 1

    spinner_thread = threading.Thread(target=spinner, daemon=True)
    spinner_thread.start()

    # Extract and print IMMEDIATELY as each completes
    def fetch_and_print(t):
        result = fetch_tweet_sync(t)
        with print_lock:
            extracted[0] += 1
            counter[0] += 1
            # Clear spinner line, print tweet, spinner continues on next iteration
            sys.stdout.write("\r" + " " * 50 + "\r")
            print_tweet(counter[0], result.get('tweet_id'), result.get('date'), result.get('text'))
        return result

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=15) as pool:
        completed = await asyncio.gather(*[
            loop.run_in_executor(pool, fetch_and_print, t) for t in all_tweets
        ])

    spinner_active[0] = False
    spinner_thread.join(timeout=0.3)
    sys.stdout.write("\r" + " " * 50 + "\r")
    print(f"{G}  ☠ REAPING COMPLETE!{X}\n")

    return list(completed)

def scrape_and_stream(username: str):
    """Wrapper to run async scraper."""
    return asyncio.run(scrape_async(username))

def main():
    print(BANNER)

    print(f"{C}  Enter username to hunt:{X}")
    try:
        username = input(f"{Y}  ☠ @{X}").strip().lstrip('@')
    except KeyboardInterrupt:
        print(f"\n{R}  ☠ Aborted{X}\n")
        sys.exit(0)

    if not username:
        print(f"{R}  No target!{X}")
        sys.exit(1)

    # Animate
    animate_hunt(username)

    # Header
    clear()
    print(BANNER)
    print(f"\n{G}{'═'*70}{X}")
    print(f"{G}  ☠ DEAD TWEETS FOR @{username.upper()} ☠{X}")
    print(f"{G}{'═'*70}{X}")

    # Scrape and stream
    tweets = scrape_and_stream(username)

    if not tweets:
        print(f"\n{R}  ☠ No dead tweets found!{X}\n")
        return

    # Summary
    with_text = sum(1 for t in tweets if t.get('text'))
    print(f"{G}{'─'*70}{X}")
    print(f"""{Y}
  ╔════════════════════════════════════╗
  ║      ☠ REAPING COMPLETE ☠          ║
  ╠════════════════════════════════════╣
  ║  Dead tweets:         {len(tweets):>5}        ║
  ║  With content:        {with_text:>5}        ║
  ╚════════════════════════════════════╝{X}
""")

    # Save
    print(f"{C}  Save to JSON? [y/N]:{X}")
    try:
        if input(f"{Y}  ☠ {X}").strip().lower() == 'y':
            fn = f"{username}_reaped.json"
            with open(fn, 'w') as f:
                json.dump(tweets, f, indent=2, ensure_ascii=False)
            print(f"{G}  ✓ Saved: {fn}{X}")
    except:
        pass

    print(f"\n{R}  ☠ THE REAPER DEPARTS ☠{X}\n")

if __name__ == '__main__':
    main()
