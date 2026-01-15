# X-REAPER ☠️

```
 ██╗  ██╗      ██████╗ ███████╗ █████╗ ██████╗ ███████╗██████╗
 ╚██╗██╔╝      ██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝██╔══██╗
  ╚███╔╝ █████╗██████╔╝█████╗  ███████║██████╔╝█████╗  ██████╔╝
  ██╔██╗ ╚════╝██╔══██╗██╔══╝  ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
 ██╔╝ ██╗      ██║  ██║███████╗██║  ██║██║     ███████╗██║  ██║
 ╚═╝  ╚═╝      ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
```

**Hunt down deleted tweets from the grave.**

## Demo 

https://github.com/user-attachments/assets/fa337afc-7bd8-4de0-8b59-94bd0c2d06c6

X-REAPER finds and extracts deleted/protected tweets that were archived on [GhostArchive.org](https://ghostarchive.org) before they disappeared.

## Why This Exists

When someone deletes a tweet, it's not always gone forever. Services like GhostArchive automatically archive public tweets in [WARC format](https://en.wikipedia.org/wiki/Web_ARChive) - the same format used by the Internet Archive.

X-REAPER searches GhostArchive for any user's archived tweets and extracts the original tweet text from these WARC files.

## How It Works

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Search Ghost   │────▶│  Fetch WARC      │────▶│  Extract Tweet  │
│  Archive Pages  │     │  Archive Files   │     │  from GraphQL   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

1. **Search Phase** - Queries GhostArchive's search API for `x.com/{username}` URLs (async, parallel)
2. **WARC Fetch** - Downloads the WARC archive files for each result (15 concurrent threads)
3. **Extraction** - Parses Twitter's GraphQL API responses stored in the WARC to get `legacy.full_text`

The tool uses a hybrid async/threaded approach:
- **aiohttp** for fast parallel searching across 10 pages simultaneously
- **ThreadPoolExecutor** for WARC parsing (streaming requires sync I/O)
- **warcio** library to parse the Web Archive format

## Installation

```bash
pip install aiohttp requests beautifulsoup4 warcio
```

## Usage

```bash
python x_reaper.py
```

Then enter the username you want to hunt.

Results show:
- Tweet ID
- Archive date
- Full tweet text (when extractable)

Optionally save results to JSON.

## Technical Details

### Why WARC?

GhostArchive stores complete webpage snapshots in WARC format. This includes:
- The HTML page
- All API responses made during the snapshot
- Images and other assets

Twitter/X uses GraphQL APIs internally. When a tweet page loads, it fetches tweet data from endpoints like `TweetDetail` or `TweetResultByRestId`. These responses contain the full tweet object with `legacy.full_text`.

### Why Some Tweets Show "[content in saved snapshot]"?

Some archives may:
- Have been captured before the page fully loaded
- Not include the GraphQL response
- Be from a different Twitter/X page layout

The tweet still exists in the archive - just needs manual viewing at the archive URL.

## Legal

This tool only accesses publicly archived data from GhostArchive. It does not:
- Bypass any authentication
- Access private/protected accounts
- Scrape Twitter/X directly

Use responsibly.

## License

MIT
