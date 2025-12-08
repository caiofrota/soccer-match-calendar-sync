from __future__ import annotations
import argparse
import os
import re
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build

DEFAULT_SOURCE = "https://www.placardefutebol.com.br/champions-league"
PRODID = "//Caio Frota//Match Crawler v1.0//EN"
CALNAME = "Match Crawler"
CALDESC = "Match Crawler"
TIMEZONE = "America/Fortaleza"

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = "credentials.json"

HTTP_TIMEOUT = 10  # segundos

@dataclass
class MatchDetails:
    league: str
    group: str
    home: str
    away: str
    date_str: str
    time_str: str
    comments: str
    location: str

    @property
    def uid(self) -> str:
        return f"{self.league}|{self.group}|{self.home}|{self.away}"

def local_str_to_utc(date_str: str, time_str: str, fmt: str) -> str:
    local_dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
    utc_dt = local_dt + timedelta(hours=3)
    return utc_dt.strftime(fmt)

def fetch_html(url: str) -> BeautifulSoup:
    resp = requests.get(
        url,
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": "Mozilla/5.0 (MatchCrawler/1.0)"},
    )
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")

def get_calendar_service():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Credentials file '{CREDENTIALS_FILE}' not found."
        )

    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials)

def parse_match_page(url: str) -> MatchDetails:
    soup = fetch_html(url)

    league = (
        soup.find("h2", {"class": "match__league-name"}).get_text(strip=True)
        if soup.find("h2", {"class": "match__league-name"})
        else ""
    )

    group_el = soup.find("p", {"class": "match-group"})
    group = (
        re.sub(r"\s+", " ", group_el.get_text().strip().replace("\n", ""))
        if group_el
        else ""
    )

    teams = soup.find_all("h4", {"class": "team_link"})
    if len(teams) < 2:
        raise ValueError(f"Não foi possível encontrar os times em {url}")

    home = teams[0].get_text(strip=True)
    away = teams[1].get_text(strip=True)

    details_container = soup.find("div", {"class": "match-details"})
    date_str = ""
    time_str = ""
    comments = ""
    location = ""

    if details_container:
        for p in details_container.find_all("p"):
            if p.find("img", title="Local da partida"):
                location = p.get_text(strip=True)
            if p.find("img", title="Transmissão"):
                comments = p.get_text(strip=True)
            if p.find("img", title="Data da partida"):
                parts = p.get_text(strip=True).split(" às ")
                if len(parts) == 2:
                    date_str, time_str = parts

    if not (date_str and time_str):
        raise ValueError(f"Data/horário não encontrados em {url}")

    return MatchDetails(
        league=league,
        group=group,
        home=home,
        away=away,
        date_str=date_str,
        time_str=time_str,
        comments=comments,
        location=location,
    )


def iter_match_links(list_url: str) -> Iterable[str]:
    soup = fetch_html(list_url)

    matches_container = soup.find("div", {"id": "next_matches"}) or soup.find(
        "div", {"id": "main"}
    )
    if not matches_container:
        raise ValueError("It was not possible to find the matches container.")

    for a in matches_container.find_all("a"):
        classes = a.get("class") or []
        if any(cls.startswith("match__") for cls in classes):
            href = a.get("href")
            if href:
                yield href

def generate_ics(url: str, output_file: str = "calendar.ics") -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write(f"PRODID:-{PRODID}\n")
        f.write("CALSCALE:GREGORIAN\n")
        f.write("METHOD:PUBLISH\n")
        f.write(f"X-WR-CALNAME:{CALNAME}\n")
        f.write(f"X-WR-TIMEZONE:{TIMEZONE}\n")
        f.write(f"X-WR-CALDESC:{CALDESC}\n")

        for match_url in iter_match_links(url):
            try:
                details = parse_match_page(match_url)

                start_utc = local_str_to_utc(
                    details.date_str, details.time_str, "%Y%m%dT%H%M%SZ"
                )
                end_utc = (
                    datetime.strptime(start_utc, "%Y%m%dT%H%M%SZ")
                    + timedelta(hours=2)
                ).strftime("%Y%m%dT%H%M%SZ")

                now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

                f.write("BEGIN:VEVENT\n")
                f.write(f"DTSTART:{start_utc}\n")
                f.write(f"DTEND:{end_utc}\n")
                f.write(f"DTSTAMP:{now_utc}\n")
                f.write(f"UID:{details.uid}\n")
                f.write(f"CREATED:{now_utc}\n")
                f.write(
                    f"DESCRIPTION:{details.league} - {details.group}<br/>{details.comments}\n"
                )
                f.write(f"LAST-MODIFIED:{now_utc}\n")
                f.write("SEQUENCE:0\n")
                f.write("STATUS:CONFIRMED\n")
                f.write(f"LOCATION:{details.location}\n")
                f.write(f"SUMMARY:{details.home} x {details.away}\n")
                f.write("TRANSP:OPAQUE\n")
                f.write("END:VEVENT\n")

                print(
                    f"[ICS] {details.league} | {details.group} | "
                    f"{details.home} x {details.away} - "
                    f"{details.date_str} às {details.time_str} | {details.comments}"
                )
            except Exception as e:
                print(f"[ICS] Fail processing {match_url}: {e}")

        f.write("END:VCALENDAR\n")

def sync_to_google_calendar(url: str, calendar_id: str) -> None:
    service = get_calendar_service()

    for match_url in iter_match_links(url):
        try:
            details = parse_match_page(match_url)

            start_iso = local_str_to_utc(
                details.date_str, details.time_str, "%Y-%m-%dT%H:%M:%S"
            )
            end_iso = (
                datetime.strptime(start_iso, "%Y-%m-%dT%H:%M:%S")
                + timedelta(hours=2)
            ).strftime("%Y-%m-%dT%H:%M:%S")

            start_dt = f"{start_iso}Z"
            end_dt = f"{end_iso}Z"

            ical_uid = details.uid

            existing = (
                service.events()
                .list(calendarId=calendar_id, iCalUID=ical_uid, showDeleted=True)
                .execute()
                .get("items", [])
            )

            event_body = {
                "summary": f"{details.home} x {details.away}",
                "description": f"{details.league} - {details.group}<br/>{details.comments}",
                "start": {"dateTime": start_dt, "timeZone": TIMEZONE},
                "end": {"dateTime": end_dt, "timeZone": TIMEZONE},
                "location": details.location,
                "iCalUID": ical_uid,
            }

            if existing:
                event_id = existing[0]["id"]
                service.events().update(
                    calendarId=calendar_id, eventId=event_id, body=event_body
                ).execute()
                status = "updated"
            else:
                service.events().insert(calendarId=calendar_id, body=event_body).execute()
                status = "created"

            print(
                f"[GCAL][{status}] {details.league} | {details.group} | "
                f"{details.home} x {details.away} - "
                f"{details.date_str} às {details.time_str} | {details.comments}"
            )
        except Exception as e:
            print(f"[GCAL] Fail processing {match_url}: {e}")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Web Soccer Match Crawler"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ics_parser = subparsers.add_parser("ics", help="Generate calendar.ics file.")
    ics_parser.add_argument(
        "--url",
        "-u",
        default=DEFAULT_SOURCE,
        help=f"Source URL (default: {DEFAULT_SOURCE})",
    )
    ics_parser.add_argument(
        "--output",
        "-o",
        default="calendar.ics",
        help="Name of the output ICS file (default: calendar.ics)",
    )

    gcal_parser = subparsers.add_parser(
        "gcalendar", help="Sync events with Google Calendar"
    )
    gcal_parser.add_argument(
        "--url",
        "-u",
        default=DEFAULT_SOURCE,
        help=f"Source URL (default: {DEFAULT_SOURCE})",
    )
    gcal_parser.add_argument(
        "--calendar-id",
        "-c",
        required=True,
        help="ID of the Google Calendar (ex.: something@group.calendar.google.com)",
    )

    return parser

def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ics":
        generate_ics(args.url, args.output)
    elif args.command == "gcalendar":
        sync_to_google_calendar(args.url, args.calendar_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
