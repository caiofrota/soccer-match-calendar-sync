import unittest
from unittest.mock import Mock

from sportscore_client import RETRYABLE_STATUS_CODES, SportScoreProvider


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def fixture():
    return {
        "home": "Brazil",
        "away": "France",
        "time": "2027-07-01T19:00:00+00:00",
        "status": "upcoming",
        "competition": "FIFA Women's World Cup",
        "url": "/football/match/brazil-vs-france/",
    }


class ProviderContractTests(unittest.TestCase):
    def test_retries_transient_get_failures(self):
        provider = SportScoreProvider(retries=4, backoff_factor=0.5)

        retries = provider.session.get_adapter("https://").max_retries

        self.assertEqual(retries.total, 4)
        self.assertEqual(retries.connect, 4)
        self.assertEqual(retries.read, 4)
        self.assertEqual(retries.status, 4)
        self.assertEqual(retries.allowed_methods, frozenset({"GET"}))
        self.assertEqual(retries.status_forcelist, RETRYABLE_STATUS_CODES)
        self.assertEqual(retries.backoff_factor, 0.5)
        self.assertTrue(retries.respect_retry_after_header)

    def test_team_endpoint_and_returned_slug_are_validated(self):
        provider = SportScoreProvider(base_url="https://sportscore.test")
        provider.session.get = Mock(
            return_value=Response({"team": {"slug": "brazil-women"}, "matches": [fixture()]})
        )

        matches = provider.team_schedule("brazil-women")

        self.assertEqual(len(matches), 1)
        provider.session.get.assert_called_once_with(
            "https://sportscore.test/api/widget/team/",
            params={"sport": "football", "slug": "brazil-women", "limit": "30"},
            timeout=10,
        )

    def test_rejects_provider_fuzzy_match_for_wrong_team(self):
        provider = SportScoreProvider()
        provider.session.get = Mock(
            return_value=Response({"team": {"slug": "brazil"}, "matches": []})
        )
        with self.assertRaisesRegex(ValueError, "returned"):
            provider.team_schedule("brazil-w")

    def test_competition_discovers_teams_and_deduplicates_fixture(self):
        provider = SportScoreProvider()

        def get(_url, params, timeout):
            if "standings" in _url:
                return Response(
                    {
                        "competition": "FIFA Women's World Cup",
                        "competition_slug": "fifa-womens-world-cup",
                        "tables": [
                            {"rows": [{"team_slug": "brazil-women"}, {"team_slug": "france-women"}]}
                        ],
                    }
                )
            if "bracket" in _url:
                return Response({"competition": "FIFA Women's World Cup", "rounds": []})
            return Response({"team": {"slug": params["slug"]}, "matches": [fixture()]})

        provider.session.get = Mock(side_effect=get)
        matches = provider.competition_schedule("fifa-womens-world-cup")
        self.assertEqual(len(matches), 1)


if __name__ == "__main__":
    unittest.main()
