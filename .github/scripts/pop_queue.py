#!/usr/bin/env python3
"""Publish the next approved, unposted queue item into social/feed.xml.

IFTTT watches that feed and posts to LinkedIn. Nothing reaches the feed unless
the item carries approved: true, so approval is the only gate that matters.

Deviation from LLM-SOC-013 §6: the reference implementation writes
    body = f"{title}\n\n{caption}"
Our captions already open with the title (GATE 1 requires the claim inside the
first 140 characters), so that would emit the title twice. The caption is used
verbatim instead.
"""

import datetime
import json
import pathlib
import xml.sax.saxutils as sx

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUEUE = ROOT / "social" / "queue.json"
FEED = ROOT / "social" / "feed.xml"

items = json.loads(QUEUE.read_text())
nxt = next((i for i in items if i.get("approved") and not i.get("posted")), None)

if nxt is None:
    pending = sum(1 for i in items if not i.get("approved"))
    print(f"nothing approved and unposted — feed unchanged "
          f"({pending} item(s) awaiting approval)")
    raise SystemExit(0)

unfilled = nxt["caption"].count("[ ")
if unfilled:
    print(f"REFUSING {nxt['id']}: {unfilled} unfilled [ ] blank(s) still in the "
          f"caption. Fill them before approving — publishing a bracket is worse "
          f"than publishing nothing.")
    raise SystemExit(1)

now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%a, %d %b %Y %H:%M:%S +0000"
)

FEED.write_text(
    f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
  <title>Hethusha Umanga — post queue</title>
  <link>https://unrealumanga.github.io/portfolio2/</link>
  <description>Scheduled posts awaiting publication</description>
  <item>
    <title>{sx.escape(nxt['title'])}</title>
    <description>{sx.escape(nxt['caption'])}</description>
    <link>https://unrealumanga.github.io/portfolio2/</link>
    <guid isPermaLink="false">{sx.escape(nxt['id'])}</guid>
    <pubDate>{now}</pubDate>
    <enclosure url="{sx.escape(nxt['image_url'])}" type="image/png" length="0"/>
    <media:content url="{sx.escape(nxt['image_url'])}" medium="image"/>
    <media:description>{sx.escape(nxt.get('alt', ''))}</media:description>
  </item>
</channel>
</rss>
""",
    encoding="utf-8",
)

nxt["posted"] = True
nxt["posted_at"] = now
QUEUE.write_text(json.dumps(items, indent=2) + "\n")

remaining = sum(1 for i in items if i.get("approved") and not i.get("posted"))
print(f"published to feed: {nxt['id']} ({remaining} approved item(s) still queued)")
