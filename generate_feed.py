#!/usr/bin/env python3
"""
Generate a combined RSS feed from all Veneto event scrapers.
Combines multi-date events (e.g. opera with 5 showings) into a single item.
Output: docs/events.rss (served via GitHub Pages)
"""

import json
import os
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from collections import OrderedDict
from datetime import datetime
from email.utils import parsedate_to_datetime
import feedgenerator

from scrape_bru_zane import scrape as scrape_bru_zane
from scrape_barcoteatro import scrape as scrape_barcoteatro
from scrape_opv import scrape as scrape_opv
from scrape_pollini import scrape as scrape_pollini

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "events.rss")

# La Fenice is scraped directly by the iPad app (Cloudflare blocks GitHub IPs)
SCRAPERS = [
    ("Bru Zane", scrape_bru_zane),
    ("Barco Teatro", scrape_barcoteatro),
    ("OPV", scrape_opv),
    ("Pollini", scrape_pollini),
]


def format_dates_by_month(dates):
    """Format dates grouped by month, e.g. 'Apr: 15, 19, 22 | May: 3, 10'."""
    if len(dates) == 1:
        return dates[0].strftime("%d %b")

    by_month = OrderedDict()
    for dt in sorted(dates):
        month_key = dt.strftime("%b")
        by_month.setdefault(month_key, []).append(dt.strftime("%d").lstrip("0"))

    parts = []
    for month, days in by_month.items():
        parts.append(f"{month}: {', '.join(days)}")
    return " | ".join(parts)


SOURCE_NAMES = [name for name, _ in SCRAPERS] + ["La Fenice"]


def load_existing_items_for_sources(sources):
    """Read the existing RSS feed and return items whose source is in the given set."""
    if not os.path.exists(OUTPUT_FILE) or not sources:
        return []
    try:
        tree = ET.parse(OUTPUT_FILE)
        items = []
        for item_el in tree.findall(".//item"):
            desc = (item_el.findtext("description") or "")
            source = None
            for s in SOURCE_NAMES:
                if s in desc:
                    source = s
                    break
            if source not in sources:
                continue
            pub_str = item_el.findtext("pubDate") or ""
            try:
                pub_dt = parsedate_to_datetime(pub_str)
            except Exception:
                continue
            if pub_dt.replace(tzinfo=None) < datetime.now():
                continue
            enc_el = item_el.find("enclosure")
            image = enc_el.get("url", "") if enc_el is not None else ""
            items.append({
                "title": item_el.findtext("title") or "",
                "start": pub_dt.replace(tzinfo=None).isoformat(),
                "url": item_el.findtext("link") or "",
                "description_raw": desc,
                "image": image,
                "source": source,
                "_preserved": True,
            })
        print(f"  Preserved {len(items)} items from existing feed for: {', '.join(sources)}")
        return items
    except Exception as e:
        print(f"  WARNING: Could not read existing feed: {e}")
        return []


def combine_events(events):
    """Group events by URL (same production = same URL) and merge dates."""
    grouped = OrderedDict()
    for ev in events:
        url = ev["url"]
        if url in grouped:
            grouped[url]["dates"].append(datetime.fromisoformat(ev["start"]))
        else:
            grouped[url] = {
                **ev,
                "dates": [datetime.fromisoformat(ev["start"])],
            }

    combined = []
    for item in grouped.values():
        item["dates"].sort()
        item["first_date"] = item["dates"][0]
        item["dates_display"] = format_dates_by_month(item["dates"])
        combined.append(item)

    combined.sort(key=lambda e: e["first_date"])
    return combined


EXCLUDE_KEYWORDS = [
    "seminario", "masterclass", "workshop", "convegno", "lezione",
    "conferenza", "musicoterapia", "degustazione", "tavola rotonda",
]


def is_excluded(event):
    title = event.get("title", "").lower()
    etype = event.get("type", "").lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in title or kw in etype:
            return True
    if etype == "altro":
        return True
    return False


def load_fenice_events():
    """Load La Fenice events uploaded by the iPad app via GitHub API."""
    fenice_file = os.path.join(OUTPUT_DIR, "fenice.json")
    if not os.path.exists(fenice_file):
        return []
    try:
        with open(fenice_file, "r") as f:
            data = json.load(f)
        events = []
        for ev in data.get("events", []):
            start = ev.get("start", "")
            if not start:
                continue
            try:
                dt = datetime.fromisoformat(start)
            except Exception:
                continue
            if dt < datetime.now():
                continue
            events.append({
                "title": ev.get("title", ""),
                "start": start,
                "url": ev.get("url", ""),
                "venue": ev.get("venue", "La Fenice"),
                "type": ev.get("type", ""),
                "source": "La Fenice",
                "image": ev.get("image", ""),
            })
        print(f"  Loaded {len(events)} La Fenice events from fenice.json")
        return events
    except Exception as e:
        print(f"  WARNING: Could not read fenice.json: {e}")
        return []


def main():
    all_events = []
    errors = []

    for name, scraper in SCRAPERS:
        for attempt in range(1, 3):
            try:
                print(f"Scraping {name}..." if attempt == 1 else f"  Retry {name}...")
                events = scraper()
                before = len(events)
                events = [e for e in events if not is_excluded(e)]
                excluded = before - len(events)
                if excluded:
                    print(f"  Found {before} events, excluded {excluded} (talks/workshops)")
                else:
                    print(f"  Found {len(events)} events")
                all_events.extend(events)
                break
            except Exception as e:
                print(f"  ERROR scraping {name} (attempt {attempt}): {e}")
                if attempt == 1:
                    time.sleep(5)
                else:
                    traceback.print_exc()
                    errors.append(name)

    # Load La Fenice events uploaded by the iPad app
    fenice_events = load_fenice_events()
    all_events.extend(fenice_events)

    # Preserve events from failed scrapers
    scraped_sources = set(name for name, _ in SCRAPERS) - set(errors)
    preserve_sources = set(errors)
    if os.path.exists(OUTPUT_FILE):
        try:
            tree = ET.parse(OUTPUT_FILE)
            for item_el in tree.findall(".//item"):
                desc = (item_el.findtext("description") or "")
                for s in SOURCE_NAMES:
                    if s in desc and s not in scraped_sources:
                        preserve_sources.add(s)
                        break
        except Exception:
            pass
    if preserve_sources:
        preserved = load_existing_items_for_sources(preserve_sources)
        all_events.extend(preserved)

    if not all_events:
        print("WARNING: No events found from any source.")
        if os.path.exists(OUTPUT_FILE):
            print(f"Keeping existing feed at {OUTPUT_FILE}")
            return 0
        else:
            print("No existing feed to fall back on.")
            return 1

    all_events.sort(key=lambda e: e["start"])
    combined = combine_events(all_events)
    print(f"Total: {len(all_events)} showings -> {len(combined)} unique events")
    if errors:
        print(f"Failed scrapers (using cached data): {', '.join(errors)}")

    sources = SOURCE_NAMES
    feed = feedgenerator.Rss201rev2Feed(
        title="Veneto Events",
        link="https://janwillembrands.github.io/veneto-events/",
        description="Upcoming concerts, opera, and cultural events in Venice and the Veneto region. "
                    f"Sources: {', '.join(sources)}.",
        language="en",
    )

    for ev in combined:
        if ev.get("_preserved"):
            description = ev["description_raw"]
        else:
            venue = ev.get("venue", "")
            desc_line1 = f"{venue} \u2022 {ev['dates_display']}" if venue else ev["dates_display"]
            meta = []
            if ev.get("type"):
                meta.append(ev["type"])
            meta.append(ev.get("source", ""))
            desc_line2 = " \u2014 ".join(p for p in meta if p)
            description = f"{desc_line1}\n{desc_line2}"

        enclosures = []
        if ev.get("image"):
            enclosures.append(feedgenerator.Enclosure(
                url=ev["image"],
                length="0",
                mime_type="image/jpeg",
            ))

        feed.add_item(
            title=ev["title"],
            link=ev["url"],
            description=description,
            pubdate=ev["first_date"],
            unique_id=ev["url"],
            enclosures=enclosures if enclosures else None,
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        feed.write(f, "utf-8")

    print(f"RSS feed written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
