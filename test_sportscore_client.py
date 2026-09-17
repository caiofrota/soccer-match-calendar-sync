import json
import unittest
from unittest.mock import Mock, call, patch

from curl_cffi import requests
from curl_cffi.requests.exceptions import HTTPError, RequestException

from sportscore_client import SportScoreProvider


class Response(requests.Response):
    def __init__(self, payload, status=200, headers=None):
        super().__init__()
        self.content = json.dumps(payload).encode()
        self.status_code = status
        self.headers = requests.Headers(headers or {"Content-Type": "application/json"})


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
    def test_uses_browser_transport_with_matching_default_headers(self):
        provider = SportScoreProvider()

        self.assertEqual(provider.session.impersonate, "chrome")
        self.assertTrue(provider.session.default_headers)
        self.assertNotIn("User-Agent", provider.session.headers)
        self.assertTrue(provider.session.verify)

    @patch("urllib3.util.retry.time.sleep")
    def test_retries_rate_limit_and_server_failure_before_returning_matches(self, sleep):
        provider = SportScoreProvider()
        provider.session.get = Mock(
            side_effect=[
                Response({}, status=429, headers={"Retry-After": "5"}),
                Response({}, status=503),
                Response({"team": {"slug": "ceara"}, "matches": [fixture()]}),
            ]
        )

        self.assertEqual(len(provider.team_schedule("ceara")), 1)
        self.assertEqual(provider.session.get.call_count, 3)
        self.assertEqual(sleep.call_args_list, [call(5), call(2)])

    def test_recovers_from_transport_timeout(self):
        provider = SportScoreProvider()
        provider.session.get = Mock(
            side_effect=[
                requests.exceptions.Timeout("timed out"),
                Response({"team": {"slug": "ceara"}, "matches": [fixture()]}),
            ]
        )

        self.assertEqual(len(provider.team_schedule("ceara")), 1)
        self.assertEqual(provider.session.get.call_count, 2)

    def test_stops_after_retry_budget_and_preserves_failure(self):
        for failure in (Response({}, status=503), requests.exceptions.Timeout("timed out")):
            with self.subTest(failure=failure):
                provider = SportScoreProvider(retries=2, backoff_factor=0)
                provider.session.get = Mock(side_effect=[failure] * 3)
                with self.assertRaises(RequestException):
                    provider.team_schedule("ceara")
                self.assertEqual(provider.session.get.call_count, 3)

    def test_retries_are_reset_for_each_request(self):
        provider = SportScoreProvider(retries=1)
        successful = Response({"team": {"slug": "ceara"}, "matches": []})
        provider.session.get = Mock(
            side_effect=[Response({}, status=502), successful, Response({}, status=502), successful]
        )

        self.assertEqual(provider.team_schedule("ceara"), [])
        self.assertEqual(provider.team_schedule("ceara"), [])
        self.assertEqual(provider.session.get.call_count, 4)

    def test_does_not_retry_permanent_http_errors(self):
        for status in (401, 403, 404):
            with self.subTest(status=status):
                provider = SportScoreProvider()
                provider.session.get = Mock(return_value=Response({}, status=status))
                with self.assertRaises(HTTPError):
                    provider.team_schedule("ceara")
                provider.session.get.assert_called_once()

    def test_reports_cloudflare_challenge_without_treating_it_as_empty_schedule(self):
        provider = SportScoreProvider()
        provider.session.get = Mock(
            return_value=Response(
                "<html>Just a moment...</html>",
                status=403,
                headers={"cf-mitigated": "challenge", "cf-ray": "diagnostic-ray"},
            )
        )

        with self.assertRaisesRegex(HTTPError, "Cloudflare.*diagnostic-ray"):
            provider.team_schedule("ceara")
        provider.session.get.assert_called_once()

    def test_rejects_non_object_payload(self):
        provider = SportScoreProvider()
        provider.session.get = Mock(return_value=Response([]))

        with self.assertRaisesRegex(ValueError, "non-object"):
            provider.team_schedule("ceara")

    def test_competition_reports_transport_failure_when_no_source_succeeds(self):
        provider = SportScoreProvider(retries=0)
        provider.session.get = Mock(side_effect=requests.exceptions.Timeout("timed out"))

        with self.assertRaisesRegex(RuntimeError, "returned no teams.*timed out"):
            provider.competition_schedule("fifa-world-cup")

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
