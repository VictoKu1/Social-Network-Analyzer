"""Regression tests for untrusted profile input and analysis admission."""
# Test method names describe their assertions.
# pylint: disable=missing-function-docstring,missing-class-docstring

import os
import base64
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app import app
from analyze import validate_social_link
from social_media_fetchers import (
    GenericFetcher, TwitterFetcher, LinkedInFetcher, FacebookFetcher, InstagramFetcher, RedditFetcher,
)
from request_security import WorkAdmission
from security_limits import SecurityError


class SecurityBoundaryTests(unittest.TestCase):
    def setUp(self):
        admission = patch("app.work_admission", WorkAdmission())
        admission.start()
        self.addCleanup(admission.stop)
        self.env = patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-test-key", "LLM_PROVIDER": "openai",
                                          "APP_ACCESS_TOKEN": "", "APP_ALLOWED_HOSTS": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = app.test_client()

    def test_validator_uses_hostname_not_substrings(self):
        for url in (
            "http://127.0.0.1:8080/?github.com",
            "https://github.com.evil.example/profile",
            "https://github.com@evil.example/profile",
            "https://github.com:444/profile",
            "https://github.com:0/profile",
            "https://github.com\\@evil.example/profile",
        ):
            with self.subTest(url=url):
                self.assertFalse(validate_social_link(url)[0])
        self.assertEqual(validate_social_link("https://gist.github.com/user"), (True, "GitHub"))

    @patch("analyze._get_client")
    @patch("analyze.fetch_social_media_data", return_value=None)
    def test_direct_analysis_rejects_untrusted_urls_before_fetch(self, fetch, client):
        client.return_value.chat.completions.create.return_value.choices = []
        response = self.client.post("/analyze", json={
            "links_info": [{"url": "http://127.0.0.1/?github.com", "platform": "GitHub"}],
            "personal_description": "A normal description.",
        })
        self.assertEqual(response.status_code, 400)
        fetch.assert_not_called()
        client.assert_not_called()

    @patch("analyze._get_client")
    @patch("analyze.fetch_social_media_data", return_value=None)
    def test_server_rejects_excess_links_before_fetch(self, fetch, client):
        response = self.client.post("/analyze", json={
            "links_info": [{"url": "https://github.com/user", "platform": "GitHub"}] * 6,
            "personal_description": "Description",
        })
        self.assertEqual(response.status_code, 400)
        fetch.assert_not_called()
        client.assert_not_called()

    def test_generic_library_entry_rejects_private_destination(self):
        fetcher = GenericFetcher()
        response = MagicMock(status_code=200, text="<h1>Private service</h1>")
        with patch.object(fetcher.session, "get", return_value=response) as get:
            with self.assertRaises(ValueError):
                fetcher.fetch_profile_data("http://127.0.0.1/")
            get.assert_not_called()

    def test_request_body_limit(self):
        response = self.client.post("/validate_links", json={"links": [], "padding": "x" * 40000})
        self.assertEqual(response.status_code, 413)

    def test_remote_caller_is_denied_by_default(self):
        response = self.client.get("/api/llm-config", environ_overrides={"REMOTE_ADDR": "203.0.113.2"})
        self.assertEqual(response.status_code, 403)

    def test_cross_origin_and_rebinding_hosts_are_denied(self):
        self.assertEqual(self.client.get("/api/llm-config", headers={"Host": "attacker.example"}).status_code, 403)
        self.assertEqual(self.client.post("/validate_links", json={"links": []},
                                         headers={"Origin": "https://attacker.example"}).status_code, 403)

    def test_shared_auth_is_required_even_on_loopback(self):
        token = "synthetic-operator-secret-for-tests-only"
        basic = base64.b64encode(("operator:" + token).encode()).decode()
        with patch.dict(os.environ, {"APP_ACCESS_TOKEN": token, "APP_ALLOWED_HOSTS": "analysis.example"}):
            denied = self.client.get("/")
            self.assertEqual(denied.status_code, 401)
            self.assertIn("Basic", denied.headers["WWW-Authenticate"])
            allowed = self.client.get("/api/llm-config", headers={"Authorization": "Basic " + basic})
            denied = self.client.get("/api/llm-config", headers={"Authorization": "Basic b3BlcmF0b3I6d3Jvbmc="})
            self.assertEqual(allowed.status_code, 200)
            self.assertEqual(denied.status_code, 401)
            options = {"base_url": "https://analysis.example", "headers": {"Authorization": "Basic " + basic},
                       "environ_overrides": {"REMOTE_ADDR": "203.0.113.2"}}
            self.assertEqual(self.client.get("/api/llm-config", **options).status_code, 200)
            options["base_url"] = "http://analysis.example"
            options["headers"]["X-Forwarded-Proto"] = "https"
            self.assertEqual(self.client.get("/api/llm-config", **options).status_code, 403)
        with patch.dict(os.environ, {"APP_ACCESS_TOKEN": "short"}):
            self.assertEqual(self.client.get("/").status_code, 503)

    def test_forwarded_headers_cannot_enable_local_only_service(self):
        for headers in ({"X-Forwarded-For": "127.0.0.1"}, {"Forwarded": "for=127.0.0.1"},
                        {"X-Forwarded-Proto": "https"}):
            self.assertEqual(self.client.get("/api/llm-config", headers=headers).status_code, 403)

    def test_work_quota_and_concurrency_release_after_failure(self):
        admission = WorkAdmission(per_minute=2, concurrent=1)
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            with admission.acquire():
                with self.assertRaises(SecurityError) as denied:
                    with admission.acquire():
                        self.fail("Concurrent request admitted")
                self.assertEqual(denied.exception.status, 429)
                raise RuntimeError("synthetic")
        self.assertEqual(admission.active, 0)
        with admission.acquire():
            pass
        with self.assertRaises(SecurityError):
            with admission.acquire():
                self.fail("Quota exceeded")
        with patch("request_security.time.monotonic", return_value=admission.calls[-1] + 61):
            with admission.acquire():
                pass

    @patch("analyze._get_client")
    @patch("analyze.fetch_social_media_data")
    def test_malformed_and_large_inputs_fail_before_work(self, fetch, client):
        for payload in (
            {"links_info": {}}, {"links_info": [None]}, {"links_info": [{"url": {}}]},
            {"personal_description": []}, {"personal_description": "x" * 10001},
        ):
            with self.subTest(payload=str(payload)[:70]):
                self.assertEqual(self.client.post("/analyze", json=payload).status_code, 400)
        fetch.assert_not_called()
        client.assert_not_called()

    @patch("analyze._get_client")
    @patch("analyze.format_social_media_data", return_value="x" * 50001)
    @patch("analyze.fetch_social_media_data", return_value=object())
    def test_aggregate_content_budget_precedes_generation(self, _fetch, _format, client):
        response = self.client.post("/analyze", json={"links_info": [{"url": "https://github.com/user"}]})
        self.assertEqual(response.status_code, 413)
        client.assert_not_called()

    def test_shared_mode_does_not_reuse_previously_authenticated_clients(self):
        for cls, attribute, url in (
            (TwitterFetcher, "api", "https://x.com/user"),
            (LinkedInFetcher, "api", "https://linkedin.com/in/user"),
            (FacebookFetcher, "graph", "https://facebook.com/user"),
            (InstagramFetcher, "loader", "https://instagram.com/user"),
            (RedditFetcher, "reddit", "https://reddit.com/user/user"),
        ):
            fetcher = object.__new__(cls)
            setattr(fetcher, attribute, MagicMock())
            fetcher._handle_rate_limit = MagicMock()
            with self.subTest(fetcher=cls.__name__), patch.dict(os.environ, {"APP_ACCESS_TOKEN": "x" * 32}), \
                    patch.object(fetcher, "_fallback_fetch", return_value="public") as fallback:
                self.assertEqual(fetcher.fetch_profile_data(url), "public")
                fallback.assert_called_once_with(url)
                fetcher._handle_rate_limit.assert_not_called()

    def test_private_instagram_rejected_before_post_access(self):
        fetcher = object.__new__(InstagramFetcher)
        fetcher.loader = MagicMock()
        profile = MagicMock(is_private=True)
        module = SimpleNamespace(Profile=SimpleNamespace(from_username=MagicMock(return_value=profile)))
        with patch.dict(sys.modules, {"instaloader": module}), \
                patch.object(fetcher, "_handle_rate_limit"), \
                patch.object(fetcher, "_fallback_fetch") as fallback, self.assertRaises(SecurityError):
            fetcher.fetch_profile_data("https://instagram.com/user")
        profile.get_posts.assert_not_called()
        fallback.assert_not_called()

    def test_shared_reddit_does_not_initialize_an_operator_session(self):
        module = SimpleNamespace(Reddit=MagicMock())
        with patch.dict(sys.modules, {"praw": module}), patch.dict(os.environ, {
            "APP_ACCESS_TOKEN": "x" * 32, "REDDIT_CLIENT_ID": "synthetic",
            "REDDIT_CLIENT_SECRET": "synthetic", "praw_refresh_token": "synthetic",
        }):
            fetcher = RedditFetcher()
        self.assertIsNone(fetcher.reddit)
        module.Reddit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
