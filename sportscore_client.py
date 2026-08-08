"""Client for SportScore's documented public football widgets."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def normalize_status(status: str, text: str = "") -> str:
    value = normalize(f"{status} {text}")
    if re.search(r"cancel+ed|abandon", value):
        return "canceled"
    if re.search(r"postpon|suspend|delay", value):
        return "postponed"
    if re.search(r"finish|full time|after extra time|after penalt|shootout|\baet\b|\bft\b", value):
        return "final"
    if re.search(r"\blive\b|in play|in progress|half time|first half|second half|paused|\bht\b", value):
        return "live"
    return "scheduled"


@dataclass(frozen=True)
class SportScoreMatch:
    slug: str
    path: str
    kickoff: datetime
    status: str
    status_text: str
    competition: str
    round_name: str
    home: str
    away: str
    location: str

    @property
    def occurrence_key(self) -> str:
        return f"{self.slug}|{normalize(self.home)}|{normalize(self.away)}|{self.kickoff.isoformat()}"


def parse_match(payload: dict[str, Any]) -> SportScoreMatch:
    for field in ("home", "away", "time", "status"):
        if not payload.get(field):
            raise ValueError(f"SportScore match is missing {field}")
    raw_slug = str(payload.get("slug") or payload.get("url") or "")
    if re.fullmatch(r"[a-z0-9-]+", raw_slug, re.I):
        slug = raw_slug.lower()
    else:
        parts = [part for part in urlparse(raw_slug).path.split("/") if part]
        if "match" not in parts or parts.index("match") + 1 >= len(parts):
            raise ValueError("SportScore match has no valid slug")
        slug = parts[parts.index("match") + 1].lower()
    kickoff = datetime.fromisoformat(str(payload["time"]).replace("Z", "+00:00"))
    if kickoff.tzinfo is None:
        raise ValueError("SportScore match time has no timezone")
    round_name = payload.get("round_name") or payload.get("round") or ""
    if isinstance(round_name, int):
        round_name = f"Rodada {round_name}"
    return SportScoreMatch(
        slug=slug,
        path=str(payload.get("url") or f"/football/match/{slug}/"),
        kickoff=kickoff,
        status=normalize_status(str(payload["status"]), str(payload.get("status_text") or "")),
        status_text=str(payload.get("status_text") or "").strip(),
        competition=str(payload.get("competition") or "").strip(),
        round_name=str(round_name).strip(),
        home=str(payload["home"]).strip(),
        away=str(payload["away"]).strip(),
        location=str(payload.get("venue") or payload.get("stadium") or "").strip(),
    )


class SportScoreProvider:
    def __init__(
        self,
        base_url: str = "https://sportscore.com",
        timeout: int = 10,
        retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "MatchCalendarSync/2.0"})
        retry_policy = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            allowed_methods=frozenset({"GET"}),
            status_forcelist=RETRYABLE_STATUS_CODES,
            backoff_factor=backoff_factor,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry_policy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _get(self, endpoint: str, slug: str, **extra: str) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/api/widget/{endpoint}/",
            params={"sport": "football", "slug": slug, **extra},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("SportScore returned a non-object payload")
        return payload

    def team_schedule(self, slug: str) -> list[SportScoreMatch]:
        payload = self._get("team", slug, limit="30")
        returned = str((payload.get("team") or {}).get("slug") or "").lower()
        if returned != slug.lower():
            raise ValueError(f'SportScore returned "{returned}" for team "{slug}"')
        if not isinstance(payload.get("matches"), list):
            raise ValueError("SportScore team payload has no matches list")
        return [parse_match(match) for match in payload["matches"]]

    def competition_schedule(self, slug: str) -> list[SportScoreMatch]:
        teams: set[str] = set()
        names: set[str] = set()
        errors: list[str] = []
        try:
            standings = self._get("standings", slug)
            returned = standings.get("competition_slug")
            if returned and str(returned).lower() != slug.lower():
                raise ValueError(f'SportScore returned competition "{returned}" for "{slug}"')
            names.add(normalize(str(standings.get("competition") or "")))
            for table in standings.get("tables") or []:
                teams.update(str(row["team_slug"]).lower() for row in table.get("rows") or [] if row.get("team_slug"))
        except (requests.RequestException, ValueError) as error:
            errors.append(str(error))
        try:
            bracket = self._get("bracket", slug)
            names.add(normalize(str(bracket.get("competition") or "")))
            for round_data in bracket.get("rounds") or []:
                for match in round_data.get("matchups") or []:
                    for side in ("home", "away"):
                        if match.get(side):
                            teams.add(normalize(str(match[side])).replace(" ", "-"))
        except (requests.RequestException, ValueError) as error:
            errors.append(str(error))
        names.discard("")
        if not teams:
            raise RuntimeError(f"SportScore returned no teams for {slug}: {'; '.join(errors)}")
        found: dict[str, SportScoreMatch] = {}
        successful = 0
        schedule_errors: list[str] = []
        for team in sorted(teams):
            try:
                matches = self.team_schedule(team)
                successful += 1
                for match in matches:
                    if normalize(match.competition) in names:
                        found.setdefault(match.occurrence_key, match)
            except (requests.RequestException, ValueError) as error:
                schedule_errors.append(f"{team}: {error}")
        if not successful:
            raise RuntimeError("Every team schedule failed: " + "; ".join(schedule_errors))
        return list(found.values())
