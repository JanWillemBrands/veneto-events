#!/usr/bin/env python3
"""
Generate a combined RSS feed from all Veneto event scrapers.
Output: docs/events.rss (served via GitHub Pages)
"""

import os
import sys
from datetime import datetime
import feedgenerator

from scrape_bru_zane import scrape as scrape_bru_zane
from scrape_la_fenice import scrape as scrape_la_fenice

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "events.rss")


def main():
    print("Scraping Bru Zane...")
    bru_zane_events = scrape_bru_zane()
    print(f"  Found {len(bru_zane_events)} events")

    print("Scraping La Fenice...")
    la_fenice_events = scrape_la_fenice()
    print(f"  Found {len(la_fenice_events)} events")

    all_events = bru_zane_events + la_fenice_events
    all_events.sort(key=lambda e: e["start"])

    print(f"Total: {len(all_events)} upcoming events")

    feed = feedgenerator.Rss201rev2Feed(
        title="Veneto Events — Concerts & Opera in Venice",
        link="https://www.teatrolafenice.it/en/whats-on/",
        description="Upcoming concerts, opera, and cultural events in Venice and the Veneto region. "
                    "Sources: Teatro La Fenice, Palazzetto Bru Zane.",
        language="en",
    )

    for ev in all_events:
        # Build description with venue, type, and source
        desc_parts = []
        if ev.get("type"):
            desc_parts.append(ev["type"])
        if ev.get("venue"):
            desc_parts.append(ev["venue"])
        if ev.get("date_display"):
            desc_parts.append(ev["date_display"])
        desc_parts.append(ev.get("source", ""))
        description = " — ".join(p for p in desc_parts if p)

        # Include thumbnail via enclosure if available
        enclosures = []
        if ev.get("image"):
            enclosures.append(feedgenerator.Enclosure(
                url=ev["image"],
                length="0",
                mime_type="image/jpeg",
            ))

        start_dt = datetime.fromisoformat(ev["start"])

        feed.add_item(
            title=f"{ev['title']} — {ev.get('venue', ev.get('location', 'Venice'))}",
            link=ev["url"],
            description=description,
            pubdate=start_dt,
            unique_id=f"{ev['url']}#{ev['start']}",
            enclosures=enclosures if enclosures else None,
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        feed.write(f, "utf-8")

    print(f"RSS feed written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
