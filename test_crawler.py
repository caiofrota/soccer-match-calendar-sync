import sys
import types
import unittest
from datetime import datetime, timezone

# Unit tests exercise pure calendar logic without requiring Google SDK installation.
google = types.ModuleType("google")
oauth2 = types.ModuleType("google.oauth2")
oauth2.service_account = types.SimpleNamespace()
google.oauth2 = oauth2
api = types.ModuleType("googleapiclient")
discovery = types.ModuleType("googleapiclient.discovery")
discovery.build = lambda *args, **kwargs: None
api.discovery = discovery
sys.modules.setdefault("google", google)
sys.modules.setdefault("google.oauth2", oauth2)
sys.modules.setdefault("googleapiclient", api)
sys.modules.setdefault("googleapiclient.discovery", discovery)

from crawler import Target, choose_existing, display_summary, event_body, should_create_event
from sportscore_client import SportScoreMatch, normalize_status, parse_match


def match(**overrides):
    values = {
        "slug": "ceara-vs-fortaleza",
        "path": "/football/match/ceara-vs-fortaleza/",
        "kickoff": datetime(2026, 8, 10, 23, 30, tzinfo=timezone.utc),
        "status": "scheduled",
        "status_text": "Not started",
        "competition": "Brazilian Serie A",
        "round_name": "Rodada 19",
        "home": "Ceará",
        "away": "Fortaleza",
        "location": "Castelão",
    }
    values.update(overrides)
    return SportScoreMatch(**values)


class SportScoreParsingTests(unittest.TestCase):
    def test_normalizes_provider_statuses(self):
        self.assertEqual(normalize_status("upcoming", "Delayed"), "postponed")
        self.assertEqual(normalize_status("finished", "Full time"), "final")
        self.assertEqual(normalize_status("canceled"), "canceled")

    def test_parses_timezone_and_round(self):
        parsed = parse_match({
            "home": "Ceará", "away": "Fortaleza",
            "time": "2026-08-10T23:30:00+00:00", "status": "upcoming",
            "round": 19, "url": "/football/match/ceara-vs-fortaleza/",
        })
        self.assertEqual(parsed.slug, "ceara-vs-fortaleza")
        self.assertEqual(parsed.round_name, "Rodada 19")
        self.assertIsNotNone(parsed.kickoff.tzinfo)


class CalendarReconciliationTests(unittest.TestCase):
    def test_postponed_match_stays_visible(self):
        postponed = match(status="postponed")
        self.assertTrue(display_summary(postponed).startswith("ADIADO"))
        self.assertIn("horário originalmente", event_body(postponed, Target("team", "ceara"))["description"])

    def test_canceled_match_stays_visible(self):
        self.assertTrue(display_summary(match(status="canceled")).startswith("CANCELADO"))

    def test_reschedule_reuses_one_existing_event(self):
        old = match(status="postponed")
        target = Target("team", "ceara")
        event = event_body(old, target)
        event["id"] = "event-1"
        moved = match(kickoff=datetime(2026, 8, 24, 22, 0, tzinfo=timezone.utc))
        self.assertEqual(choose_existing(moved, target, [event])["id"], "event-1")

    def test_missing_match_does_not_cancel_an_event(self):
        self.assertIsNone(choose_existing(match(), Target("team", "ceara"), []))

    def test_does_not_create_past_final_or_scheduled_matches(self):
        now = datetime(2026, 8, 20, tzinfo=timezone.utc)
        self.assertFalse(should_create_event(match(status="final"), now))
        self.assertFalse(should_create_event(match(status="scheduled"), now))

    def test_keeps_actionable_past_statuses_visible(self):
        now = datetime(2026, 8, 20, tzinfo=timezone.utc)
        for status in ("live", "postponed", "canceled"):
            with self.subTest(status=status):
                self.assertTrue(should_create_event(match(status=status), now))


if __name__ == "__main__":
    unittest.main()
