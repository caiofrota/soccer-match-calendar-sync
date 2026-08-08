from __future__ import annotations

import argparse
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from sportscore_client import SportScoreMatch, SportScoreProvider, normalize

PRODID = "//Caio Frota//Match Crawler v2.0//EN"
CALNAME = "Match Crawler"
CALDESC = "Calendário de partidas fornecido por SportScore"
TIMEZONE = "America/Fortaleza"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = "credentials.json"
SPORTSCORE_URL = "https://sportscore.com"


@dataclass(frozen=True)
class Target:
    kind: str
    slug: str

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.slug}"


def get_calendar_service():
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Credentials file '{CREDENTIALS_FILE}' not found.")
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials)


def load_matches(target: Target) -> list[SportScoreMatch]:
    provider = SportScoreProvider()
    if target.kind == "team":
        matches = provider.team_schedule(target.slug)
    else:
        matches = provider.competition_schedule(target.slug)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    return [match for match in matches if match.kickoff >= cutoff]


def display_summary(match: SportScoreMatch) -> str:
    prefix = {
        "postponed": "ADIADO — nova data a definir — ",
        "canceled": "CANCELADO — ",
    }.get(match.status, "")
    return f"{prefix}{match.home} x {match.away}"


def description(match: SportScoreMatch) -> str:
    lines = [match.competition]
    if match.round_name:
        lines.append(match.round_name)
    if match.status == "postponed":
        lines.extend(
            [
                "Partida adiada; a data exibida é o horário originalmente informado.",
                "Aguardando divulgação da nova data.",
            ]
        )
    elif match.status == "canceled":
        lines.append("Partida cancelada pelo fornecedor.")
    elif match.status_text:
        lines.append(f"Status: {match.status_text}")
    lines.extend([f"Partida: {SPORTSCORE_URL}{match.path}", "Dados por SportScore"])
    return "\n".join(line for line in lines if line)


def event_properties(match: SportScoreMatch, target: Target) -> dict[str, str]:
    return {
        "provider": "sportscore",
        "target": target.key,
        "matchSlug": match.slug,
        "occurrence": match.occurrence_key,
        "home": normalize(match.home),
        "away": normalize(match.away),
        "providerStatus": match.status,
    }


def event_body(match: SportScoreMatch, target: Target) -> dict:
    start = match.kickoff.astimezone(timezone.utc)
    end = start + timedelta(hours=2)
    return {
        "summary": display_summary(match),
        "description": description(match),
        "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
        "location": match.location,
        "extendedProperties": {"private": event_properties(match, target)},
    }


def stable_ical_uid(match: SportScoreMatch, target: Target) -> str:
    value = f"{target.key}|{match.occurrence_key}".encode()
    return f"{hashlib.sha256(value).hexdigest()}@match-crawler"


def should_create_event(match: SportScoreMatch, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return match.kickoff >= now or match.status in {"live", "postponed", "canceled"}


def list_calendar_events(service, calendar_id: str) -> list[dict]:
    events: list[dict] = []
    page_token = None
    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=(datetime.now(timezone.utc) - timedelta(days=400)).isoformat(),
                timeMax=(datetime.now(timezone.utc) + timedelta(days=1100)).isoformat(),
                singleEvents=True,
                showDeleted=False,
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return events


def event_start(event: dict) -> Optional[datetime]:
    value = (event.get("start") or {}).get("dateTime")
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def choose_existing(match: SportScoreMatch, target: Target, events: list[dict]) -> Optional[dict]:
    exact: list[dict] = []
    reschedule: list[dict] = []
    legacy: list[dict] = []
    expected_summary = normalize(f"{match.home} x {match.away}")
    for event in events:
        private = ((event.get("extendedProperties") or {}).get("private") or {})
        if private.get("provider") == "sportscore" and private.get("target") == target.key:
            if private.get("occurrence") == match.occurrence_key:
                exact.append(event)
            elif (
                private.get("matchSlug") == match.slug
                and private.get("home") == normalize(match.home)
                and private.get("away") == normalize(match.away)
            ):
                previous = event_start(event)
                old_status = private.get("providerStatus")
                if old_status == "postponed" or (
                    previous and abs((previous - match.kickoff).total_seconds()) <= 21 * 86400
                ):
                    reschedule.append(event)
        elif normalize(str(event.get("summary") or "")) == expected_summary:
            previous = event_start(event)
            if previous and abs((previous - match.kickoff).total_seconds()) <= 60:
                legacy.append(event)
    for candidates in (exact, reschedule, legacy):
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise RuntimeError(f"Ambiguous calendar occurrence for {match.home} x {match.away}")
    return None


def sync_to_google_calendar(target: Target, calendar_id: str) -> None:
    service = get_calendar_service()
    matches = load_matches(target)
    events = list_calendar_events(service, calendar_id)
    created = updated = 0
    for match in matches:
        existing = choose_existing(match, target, events)
        if not existing and not should_create_event(match):
            print(f"[GCAL][skipped-past] {display_summary(match)} — {match.kickoff.isoformat()}")
            continue
        body = event_body(match, target)
        if existing:
            service.events().patch(
                calendarId=calendar_id, eventId=existing["id"], body=body
            ).execute()
            updated += 1
            action = "updated"
        else:
            body["iCalUID"] = stable_ical_uid(match, target)
            created_event = service.events().insert(
                calendarId=calendar_id, body=body
            ).execute()
            events.append(created_event)
            created += 1
            action = "created"
        print(f"[GCAL][{action}] {display_summary(match)} — {match.kickoff.isoformat()}")
    print(f"[GCAL] target={target.key} matches={len(matches)} created={created} updated={updated}")


def ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def generate_ics(target: Target, output_file: str) -> None:
    matches = load_matches(target)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-{PRODID}",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{ics_escape(CALNAME)}",
        f"X-WR-TIMEZONE:{TIMEZONE}", f"X-WR-CALDESC:{ics_escape(CALDESC)}",
    ]
    for match in matches:
        if not should_create_event(match):
            continue
        start = match.kickoff.astimezone(timezone.utc)
        end = start + timedelta(hours=2)
        lines.extend([
            "BEGIN:VEVENT", f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}", f"DTSTAMP:{now}",
            f"UID:{stable_ical_uid(match, target)}", f"DESCRIPTION:{ics_escape(description(match))}",
            f"LOCATION:{ics_escape(match.location)}", f"SUMMARY:{ics_escape(display_summary(match))}",
            "STATUS:CONFIRMED", "TRANSP:OPAQUE", "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    with open(output_file, "w", encoding="utf-8", newline="") as output:
        output.write("\r\n".join(lines) + "\r\n")
    print(f"[ICS] target={target.key} matches={len(matches)} output={output_file}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SportScore soccer calendar crawler")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("ics", "gcalendar"):
        child = subparsers.add_parser(command)
        child.add_argument("--target-type", choices=("team", "competition"), required=True)
        child.add_argument("--slug", required=True)
        if command == "ics":
            child.add_argument("--output", "-o", default="calendar.ics")
        else:
            child.add_argument("--calendar-id", "-c", required=True)
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    args = build_parser().parse_args(argv)
    target = Target(args.target_type, args.slug)
    if args.command == "ics":
        generate_ics(target, args.output)
    else:
        sync_to_google_calendar(target, args.calendar_id)


if __name__ == "__main__":
    main()
