"""Scraper for Conservatorio Pollini (Padua) — concerts and masterclasses."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import dateparser


URL = "https://www.conservatoriopollini.it/site/it/produzione-eventi/"

HEADERS = {
    "User-Agent": "VenetoEventsDashboard/1.0 (+https://github.com/ShowMode)"
}


def scrape():
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    events = []

    for item in soup.select("div.notizia"):
        # Title from .titolo a
        title_el = item.select_one(".titolo a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        # Link
        href = title_el.get("href", "")
        event_url = href if href.startswith("http") else "https://www.conservatoriopollini.it" + href

        # Date from .sopratitolo_size (e.g., "Mercoledi, 15 Aprile 2026")
        date_el = item.select_one(".sopratitolo_size")
        date_str = date_el.get_text(strip=True) if date_el else ""

        # Image
        img_el = item.select_one("img")
        image_url = ""
        if img_el:
            src = img_el.get("src", "")
            image_url = src if src.startswith("http") else "https://www.conservatoriopollini.it" + src

        # Parse date
        start_date = dateparser.parse(
            date_str,
            languages=["it"],
            settings={"DATE_ORDER": "DMY", "PREFER_DATES_FROM": "future"},
        )

        if start_date and start_date >= datetime.now():
            events.append({
                "title": title,
                "start": start_date.isoformat(),
                "type": "Concert",
                "location": "Padova",
                "venue": "Conservatorio Pollini",
                "url": event_url,
                "image": image_url,
                "source": "Pollini",
            })

    return events


if __name__ == "__main__":
    for ev in scrape():
        print(f"{ev['start'][:10]}  {ev['title']}")
