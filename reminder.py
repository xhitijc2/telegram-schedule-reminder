#!/usr/bin/env python3
"""
Reads schedule.csv and, if any event starts or ends in the current minute
(IST), sends a Telegram message.

Runs in a GitHub Action triggered by cron-job.org every minute.
Bot token and chat_id come from environment variables so they can be
stored as GitHub Actions secrets.
"""

import csv
import datetime as dt
import os
import re
import sys
import urllib.parse
import urllib.request

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schedule.csv")
SCHEDULE_YEAR = 2026
SCHEDULE_START = dt.date(2026, 7, 6)   # D1
SCHEDULE_END = dt.date(2026, 7, 26)    # D21
TOTAL_DAYS = (SCHEDULE_END - SCHEDULE_START).days + 1  # 21
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        print(f"sent: {text!r} -> {body[:200]}")


def parse_time(raw: str):
    if not raw:
        return None
    s = raw.strip().lstrip("~").strip()
    if re.match(r"^\d+\s*min$", s, re.I):
        return None
    if s.lower() in {"full day", ""}:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", s, re.I)
    if not m:
        return None
    hour = int(m.group(1)) % 12
    minute = int(m.group(2))
    if m.group(3).upper() == "PM":
        hour += 12
    return (hour, minute)


def parse_dates(raw: str):
    raw = raw.strip()
    if "-" in raw:
        start_s, end_s = raw.split("-", 1)
        s_list = parse_dates(start_s)
        e_list = parse_dates(end_s)
        if not s_list or not e_list:
            return []
        s, e = s_list[0], e_list[0]
        out = []
        d = s
        while d <= e:
            out.append(d)
            d += dt.timedelta(days=1)
        return out
    parts = raw.split("/")
    if len(parts) == 2:
        day, month = int(parts[0]), int(parts[1])
        return [dt.date(SCHEDULE_YEAR, month, day)]
    if len(parts) == 3:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        return [dt.date(year, month, day)]
    return []


def load_events():
    events = []
    seen = set()
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for d in parse_dates(row["Date"]):
                start_hm = parse_time(row.get("Start", ""))
                end_hm = parse_time(row.get("End", ""))
                key = (d, row["Category"], row["Activity"], start_hm, end_hm)
                if key in seen:
                    continue
                seen.add(key)
                if start_hm is None and end_hm is None:
                    continue
                events.append({
                    "date": d,
                    "category": row["Category"],
                    "activity": row["Activity"],
                    "start": start_hm,
                    "end": end_hm,
                })
    return events


def format_hm(hm):
    return dt.time(hm[0], hm[1]).strftime("%I:%M %p").lstrip("0")


def day_header(d: dt.date) -> str:
    """Returns e.g. '📅 Monday, 06 Jul 2026 · Day 1/21'."""
    day_num = (d - SCHEDULE_START).days + 1
    return f"📅 {d.strftime('%A, %d %b %Y')} · Day {day_num}/{TOTAL_DAYS}"


def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set", file=sys.stderr)
        sys.exit(1)

    now = dt.datetime.now(IST)
    today = now.date()
    now_hm = (now.hour, now.minute)
    print(f"Now (IST): {now.isoformat(timespec='seconds')}")

    events = load_events()
    matches = 0
    for ev in events:
        if ev["date"] != today:
            continue

        activity = escape_html(ev["activity"])
        category = escape_html(ev["category"])
        header = day_header(ev["date"])

        if ev["start"] == now_hm:
            end_str = f" — ends {format_hm(ev['end'])}" if ev["end"] else ""
            msg = (
                f"🔔 <b>Starting now</b> — {format_hm(ev['start'])}\n"
                f"{header}\n\n"
                f"<b>{activity}</b>\n"
                f"<i>{category}</i>{end_str}"
            )
            send_telegram(token, chat_id, msg)
            matches += 1

        if ev["end"] == now_hm:
            msg = (
                f"✅ <b>Ending now</b> — {format_hm(ev['end'])}\n"
                f"{header}\n\n"
                f"<b>{activity}</b>\n"
                f"<i>{category}</i>"
            )
            send_telegram(token, chat_id, msg)
            matches += 1

    print(f"Matches this minute: {matches}")


if __name__ == "__main__":
    main()
