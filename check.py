"""Check Premiere Cinemas for bookable movies and alert on Telegram.

Runs one check and exits; GitHub Actions runs it every 15 minutes.
"""
import json
import os
import re
import sys

import requests

URL = "https://www.premiere-cinemas.com/en/now-showing"
STATE_FILE = "notified.json"

# keyword (lowercase, matched inside the title) -> friendly name
WATCH = {
    "doomsday": "Avengers: Doomsday",
    "dune": "Dune: Part Three",
    "clayface": "Clayface",  # TEST ONLY: already bookable, remove after the Telegram test
}


def fetch_page():
    r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    r.raise_for_status()
    return r.text


def parse_movies(html):
    """Return {title: show_dates} for every movie entry on the page.

    The movie list is embedded as escaped JSON in the page's Next.js data,
    e.g. \\"movie_title\\":\\"Clayface\\", ... \\"show_dates\\":\\"2026-10-28,...\\"
    """
    data = html.replace('\\"', '"')
    matches = list(re.finditer(r'"movie_title":"([^"]+)"', data))
    movies = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(data)
        dates = re.search(r'"show_dates":"([^"]*)"', data[m.end():end])
        title = m.group(1).strip()
        if dates and dates.group(1).strip():
            movies[title] = dates.group(1).strip()
        else:
            movies.setdefault(title, "")
    return movies


def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[dry run, no Telegram secrets]", text)
        return
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"notified": [], "broken_alerted": False}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def main():
    state = load_state()
    movies = parse_movies(fetch_page())
    bookable = {t: d for t, d in movies.items() if d}
    print(f"Found {len(movies)} movies, {len(bookable)} with show dates")

    # If nothing parses, the site layout probably changed: warn once.
    if not bookable:
        if not state.get("broken_alerted"):
            send_telegram("⚠️ Movie notifier found no movies on Premiere Cinemas. "
                          "The site may have changed; the script needs a look.")
            state["broken_alerted"] = True
            save_state(state)
        return
    state["broken_alerted"] = False

    for keyword, name in WATCH.items():
        if keyword in state["notified"]:
            continue
        for title, dates in bookable.items():
            if keyword in title.lower():
                first = dates.split(",")[0]
                send_telegram(f"🎬 {title} is bookable at Premiere Cinemas!\n"
                              f"First show date: {first}\n{URL}")
                state["notified"].append(keyword)
                print(f"Notified: {title}")
                break
        else:
            print(f"Not yet: {name}")

    save_state(state)


if __name__ == "__main__":
    sys.exit(main())
