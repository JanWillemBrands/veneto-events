#!/usr/bin/env python3
"""
Generate a combined RSS feed from all Veneto event scrapers.
Combines multi-date events (e.g. opera with 5 showings) into a single item.
Output: docs/events.rss (served via GitHub Pages)
"""

import os
import sys
from collections import OrderedDict
from datetime import datetime
import feedgenerator

from scrape_bru_zane import scrape as scrape_bru_zane
from scrape_la_fenice import scrape as scrape_la_fenice

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "events.rss")


def format_date(dt):
    """Format datetime as 'Wed 15 Apr 18:00'."""
    return dt.strftime("%a %d %b %H:%M")


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
        # Use earliest future date as the sort key
        item["first_date"] = item["dates"][0]
        # Format all dates into a readable string
        if len(item["dates"]) == 1:
            item["dates_display"] = format_date(item["dates"][0])
        else:
            item["dates_display"] = " | ".join(format_date(d) for d in item["dates"])
        combined.append(item)

    combined.sort(key=lambda e: e["first_date"])
    return combined


def main():
    print("Scraping Bru Zane...")
    bru_zane_events = scrape_bru_zane()
    print(f"  Found {len(bru_zane_events)} events")

    print("Scraping La Fenice...")
    la_fenice_events = scrape_la_fenice()
    print(f"  Found {len(la_fenice_events)} events")

    all_events = bru_zane_events + la_fenice_events
    all_events.sort(key=lambda e: e["start"])

    combined = combine_events(all_events)
    print(f"Total: {len(all_events)} showings → {len(combined)} unique events")

    feed = feedgenerator.Rss201rev2Feed(
        title="Veneto Events — Concerts & Opera in Venice",
        link="https://www.teatrolafenice.it/en/whats-on/",
        description="Upcoming concerts, opera, and cultural events in Venice and the Veneto region. "
                    "Sources: Teatro La Fenice, Palazzetto Bru Zane.",
        language="en",
    )

    for ev in combined:
        # Description: dates on first line, then type — venue — source
        desc_parts = [ev["dates_display"]]
        meta = []
        if ev.get("type"):
            meta.append(ev["type"])
        if ev.get("venue"):
            meta.append(ev["venue"])
        meta.append(ev.get("source", ""))
        desc_parts.append(" — ".join(p for p in meta if p))
        description = "\n".join(desc_parts)

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
