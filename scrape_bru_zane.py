"""Scraper for Palazzetto Bru Zane (Venice) — classical music events."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import dateparser


URL = "https://bru-zane.com/en/"

HEADERS = {
    "User-Agent": "VenetoEventsDashboard/1.0 (+https://github.com/ShowMode)"
}


def scrape():
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    events = []

    for item in soup.select(".single-evento"):
        # Title in h4.event-title > a
        title_tag = item.select_one("h4.event-title a, .event-title a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        event_url = title_tag.get("href", "")

        # Date in .date-evento
        date_tag = item.select_one(".date-evento")
        date_str = date_tag.get_text(strip=True) if date_tag else ""

        # Type from data attribute or .tipologia-evento spans
        event_type = item.get("data-event-type", "")
        if not event_type:
            type_tags = item.select(".tipologia-evento")
            event_type = " ".join(t.get_text(strip=True) for t in type_tags)

        # Venue city from data attribute or .venue-evento
        city = item.get("data-venue-city", "Venice")

        # Image from the event preview
        img_tag = item.select_one("img")
        image_url = img_tag.get("src", "") if img_tag else ""

        start_date = dateparser.parse(
            date_str,
            languages=["en", "it"],
            settings={"DATE_ORDER": "DMY", "PREFER_DATES_FROM": "future"},
        )

        if start_date and start_date >= datetime.now():
            events.append({
                "title": title,
                "start": start_date.isoformat(),
                "date_display": date_str,
                "type": event_type or "Concert",
                "location": city,
                "venue": "Palazzetto Bru Zane",
                "url": event_url,
                "image": image_url,
                "source": "Bru Zane",
            })

    return events


if __name__ == "__main__":
    for ev in scrape():
        print(f"{ev['start'][:10]}  {ev['title']}  ({ev['type']})")
