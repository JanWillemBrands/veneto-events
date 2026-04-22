"""Scraper for Orchestra di Padova e del Veneto — concerts and performances."""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import dateparser


URL = "https://www.opvorchestra.it/calendario/"

HEADERS = {
    "User-Agent": "VenetoEventsDashboard/1.0 (+https://github.com/ShowMode)"
}


def scrape():
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    events = []

    for card in soup.select(".evento-card"):
        # Skip past events
        if "past" in card.get("class", []):
            continue

        # Date from span.data-evento
        date_el = card.select_one("span.data-evento")
        date_str = date_el.get_text(strip=True) if date_el else ""

        # Link
        link_el = card.select_one("a[href*='/calendario/']")
        event_url = ""
        if link_el:
            href = link_el.get("href", "")
            event_url = href if href.startswith("http") else "https://www.opvorchestra.it" + href

        # Venue from h6.clannews
        venue_el = card.select_one("h6.clannews")
        venue = venue_el.get_text(strip=True) if venue_el else "Padova"

        # Title — prefer h4.clannews (named concert), fall back to first performer
        title_el = card.select_one("h4.clannews")
        if title_el:
            title = title_el.get_text(strip=True)
        else:
            # Use first performer as title
            performer_el = card.select_one("strong.clanbold")
            title = performer_el.get_text(strip=True) if performer_el else ""

        if not title:
            continue

        # Image from background-image style
        img_div = card.select_one("div.image-evento-card")
        image_url = ""
        if img_div:
            style = img_div.get("style", "")
            match = re.search(r"url\(['\"]?([^'\")\s]+)['\"]?\)", style)
            if match:
                src = match.group(1)
                image_url = src if src.startswith("http") else "https://www.opvorchestra.it" + src

        # Parse date
        start_date = dateparser.parse(
            date_str,
            languages=["it", "en"],
            settings={"DATE_ORDER": "DMY", "PREFER_DATES_FROM": "future"},
        )

        if start_date and start_date >= datetime.now():
            events.append({
                "title": title,
                "start": start_date.isoformat(),
                "type": "Concert",
                "location": "Padova",
                "venue": venue,
                "url": event_url,
                "image": image_url,
                "source": "OPV",
            })

    events.sort(key=lambda e: e["start"])
    return events


if __name__ == "__main__":
    for ev in scrape():
        print(f"{ev['start'][:10]}  {ev['title']}  — {ev['venue']}")
