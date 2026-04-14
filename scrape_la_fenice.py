"""Scraper for Teatro La Fenice (Venice) — opera, concerts, ballet, jazz.

The calendar page renders all events in static HTML within
.sn_calendar_block_list_row containers. Each row has:
  - data-list-id="MM-DD-YYYY" (the date)
  - data-list-month, data-list-year
  - .sn_calendar_block_list_row_group_i child divs for each event
    containing .time, .title, .category, .place, figure>img, and a link.
"""

from datetime import datetime
import requests
from bs4 import BeautifulSoup


URL = "https://www.teatrolafenice.it/en/whats-on/"

HEADERS = {
    "User-Agent": "VenetoEventsDashboard/1.0 (+https://github.com/ShowMode)"
}


def scrape():
    response = requests.get(URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    events = []
    now = datetime.now()

    for row in soup.select(".sn_calendar_block_list_row"):
        # Parse date from data-list-id="MM-DD-YYYY"
        date_id = row.get("data-list-id", "")
        if not date_id:
            continue
        try:
            row_date = datetime.strptime(date_id, "%m-%d-%Y")
        except ValueError:
            continue

        if row_date.date() < now.date():
            continue

        for item in row.select(".sn_calendar_block_list_row_group_i"):
            title_el = item.select_one(".title")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)

            time_el = item.select_one(".time")
            time_str = time_el.get_text(strip=True) if time_el else "00:00"

            category_el = item.select_one(".category")
            category = category_el.get_text(strip=True) if category_el else ""

            place_el = item.select_one(".place")
            venue = place_el.get_text(strip=True) if place_el else "La Fenice"

            link_el = item.select_one(".link a[href]")
            event_url = link_el["href"] if link_el else ""

            img_el = item.select_one("figure img")
            image_url = img_el.get("src", "") if img_el else ""

            # Build full datetime
            try:
                hour, minute = time_str.split(":")
                event_dt = row_date.replace(hour=int(hour), minute=int(minute))
            except (ValueError, AttributeError):
                event_dt = row_date

            events.append({
                "title": title,
                "start": event_dt.isoformat(),
                "type": category,
                "location": "Venice",
                "venue": venue,
                "url": event_url,
                "image": image_url,
                "source": "La Fenice",
            })

    events.sort(key=lambda e: e["start"])
    return events


if __name__ == "__main__":
    for ev in scrape():
        print(f"{ev['start'][:16]}  {ev['title']}  ({ev['type']}) — {ev['venue']}")
