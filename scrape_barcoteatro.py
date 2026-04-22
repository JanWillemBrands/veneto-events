"""Scraper for Barco Teatro (Padua area) — concerts, exhibitions, theatre."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import dateparser


URL = "https://www.barcoteatro.it/"

HEADERS = {
    "User-Agent": "VenetoEventsDashboard/1.0 (+https://github.com/ShowMode)"
}


def scrape():
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    events = []

    for item in soup.select(".event-list-item"):
        # Title — prefer subtitle h3, fall back to title h2
        subtitle_el = item.select_one(".event-list-item-subtitle h3")
        title_el = item.select_one(".event-list-item-title h2")
        if not title_el:
            continue
        title = subtitle_el.get_text(strip=True) if subtitle_el else title_el.get_text(strip=True)

        # Link from image anchor or title anchor
        link_el = item.select_one("a.event-list-item-image") or item.select_one(".event-list-item-title a")
        event_url = ""
        if link_el:
            href = link_el.get("href", "")
            event_url = href if href.startswith("http") else "https://www.barcoteatro.it" + href

        # Date
        date_el = item.select_one(".event-list-item-date")
        date_str = date_el.get_text(strip=True) if date_el else ""

        # Category
        type_el = item.select_one(".event-list-item-type")
        category = type_el.get_text(strip=True) if type_el else ""

        # Image
        img_el = item.select_one("img")
        image_url = ""
        if img_el:
            src = img_el.get("src", "")
            image_url = src if src.startswith("http") else "https://www.barcoteatro.it" + src

        # Parse date — handle ranges like "19 marzo 2026 – 19 marzo 2027"
        # Use the first date in the range
        first_date_str = date_str.split("–")[0].strip() if "–" in date_str else date_str
        start_date = dateparser.parse(
            first_date_str,
            languages=["it"],
            settings={"DATE_ORDER": "DMY", "PREFER_DATES_FROM": "future"},
        )

        if start_date and start_date >= datetime.now():
            events.append({
                "title": title,
                "start": start_date.isoformat(),
                "type": category,
                "location": "Padua",
                "venue": "Barco Teatro",
                "url": event_url,
                "image": image_url,
                "source": "Barco Teatro",
            })

    return events


if __name__ == "__main__":
    for ev in scrape():
        print(f"{ev['start'][:10]}  {ev['title']}  ({ev['type']})")
