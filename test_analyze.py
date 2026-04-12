"""
Unit tests for the analyze module.
"""

import unittest
from unittest.mock import patch, MagicMock
from analyze import validate_social_link, analyze_personality


class TestAnalyze(unittest.TestCase):
    """
    Test cases for the analyze module.
    """

    def test_validate_social_link_valid(self):
        """
        Test validate_social_link with a valid social media link.
        """
        link = "https://twitter.com/elonmusk"
        is_valid, platform = validate_social_link(link)
        self.assertTrue(is_valid)
        self.assertEqual(platform, "Twitter")

    def test_validate_social_link_invalid_prefix(self):
        """
        Test validate_social_link with an invalid prefix.
        """
        link = "ftp://facebook.com/page"
        is_valid, platform = validate_social_link(link)
        self.assertFalse(is_valid)
        self.assertIsNone(platform)

    def test_validate_social_link_unknown_domain(self):
        """
        Test validate_social_link with an unknown domain.
        """
        link = "https://example.com/user"
        is_valid, platform = validate_social_link(link)
        self.assertFalse(is_valid)
        self.assertIsNone(platform)

    @patch("openai.resources.Completions.create")
    def test_analyze_personality(self, mock_openai_create):
        """
        Test analyze_personality with mocked OpenAI API call.
        """
        mock_openai_create.return_value = MagicMock(
            choices=[MagicMock(text="Mocked analysis text")]
        )

        links_info = [
            {"url": "https://twitter.com/elonmusk", "platform": "Twitter"},
            {"url": "https://instagram.com/janedoe", "platform": "Instagram"},
        ]
        personal_description = "Jane loves travel and technology."

        result = analyze_personality(links_info, personal_description)

        # Check that we got back the mocked text
        self.assertIn("Mocked analysis text", result)

        # Verify the OpenAI API was called once
        mock_openai_create.assert_called_once()

    def test_analyze_personality_empty(self):
        """
        Test analyze_personality with empty input.
        """
        result = analyze_personality([], "")
        self.assertEqual(result, "No data provided for analysis.")


class TestGitHubFetcher(unittest.TestCase):
    """Unit tests for GitHubFetcher."""

    def setUp(self):
        from social_media_fetchers import GitHubFetcher
        self.fetcher = GitHubFetcher()

    def test_can_handle_url(self):
        self.assertTrue(self.fetcher.can_handle_url("https://github.com/torvalds"))
        self.assertFalse(self.fetcher.can_handle_url("https://twitter.com/user"))

    def test_extract_username_from_url(self):
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://github.com/torvalds"),
            "torvalds",
        )
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://github.com/octocat/Hello-World"),
            "octocat",
        )

    @patch("requests.Session.get")
    def test_fetch_profile_data_success(self, mock_get):
        """Fetch profile data when the GitHub API returns a valid response."""
        profile_payload = {
            "login": "torvalds",
            "name": "Linus Torvalds",
            "bio": "Just a guy",
            "followers": 200000,
            "following": 0,
            "avatar_url": "https://avatars.githubusercontent.com/u/1",
            "created_at": "2011-09-03T15:26:22Z",
            "location": "Portland, OR",
            "blog": "https://www.linuxfoundation.org",
        }
        repos_payload = [
            {
                "name": "linux",
                "description": "Linux kernel source tree",
                "stargazers_count": 170000,
                "language": "C",
                "html_url": "https://github.com/torvalds/linux",
            }
        ]

        mock_profile_resp = MagicMock()
        mock_profile_resp.status_code = 200
        mock_profile_resp.json.return_value = profile_payload

        mock_repos_resp = MagicMock()
        mock_repos_resp.status_code = 200
        mock_repos_resp.json.return_value = repos_payload

        mock_get.side_effect = [mock_profile_resp, mock_repos_resp]

        data = self.fetcher.fetch_profile_data("https://github.com/torvalds")
        self.assertIsNotNone(data)
        self.assertEqual(data.platform, "GitHub")
        self.assertEqual(data.username, "torvalds")
        self.assertEqual(data.display_name, "Linus Torvalds")
        self.assertEqual(data.followers_count, 200000)
        self.assertEqual(len(data.posts), 1)
        self.assertEqual(data.posts[0]["title"], "linux")

    @patch("requests.Session.get")
    def test_fetch_profile_data_not_found(self, mock_get):
        """Returns None when the GitHub API reports 404."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        data = self.fetcher.fetch_profile_data("https://github.com/nonexistentuser12345")
        self.assertIsNone(data)


class TestYouTubeFetcher(unittest.TestCase):
    """Unit tests for YouTubeFetcher."""

    def setUp(self):
        from social_media_fetchers import YouTubeFetcher
        self.fetcher = YouTubeFetcher()

    def test_can_handle_url(self):
        self.assertTrue(self.fetcher.can_handle_url("https://youtube.com/@PewDiePie"))
        self.assertFalse(self.fetcher.can_handle_url("https://twitter.com/user"))

    def test_extract_username_from_url(self):
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://youtube.com/@PewDiePie"),
            "PewDiePie",
        )
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://youtube.com/user/PewDiePie"),
            "PewDiePie",
        )
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://youtube.com/c/PewDiePie"),
            "PewDiePie",
        )

    @patch("requests.Session.get")
    def test_fallback_fetch(self, mock_get):
        """Uses Open Graph meta tags when no API key is available."""
        html = (
            '<html><head>'
            '<meta property="og:title" content="PewDiePie"/>'
            '<meta property="og:description" content="YouTube channel"/>'
            '</head></html>'
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_get.return_value = mock_resp

        data = self.fetcher._fallback_fetch("https://youtube.com/@PewDiePie")
        self.assertIsNotNone(data)
        self.assertEqual(data.platform, "YouTube")
        self.assertEqual(data.display_name, "PewDiePie")
        self.assertEqual(data.bio, "YouTube channel")


class TestTikTokFetcher(unittest.TestCase):
    """Unit tests for TikTokFetcher."""

    def setUp(self):
        from social_media_fetchers import TikTokFetcher
        self.fetcher = TikTokFetcher()

    def test_can_handle_url(self):
        self.assertTrue(self.fetcher.can_handle_url("https://tiktok.com/@charlidamelio"))
        self.assertFalse(self.fetcher.can_handle_url("https://instagram.com/user"))

    def test_extract_username_from_url(self):
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://tiktok.com/@charlidamelio"),
            "charlidamelio",
        )

    @patch("requests.Session.get")
    def test_fetch_profile_data(self, mock_get):
        """Parses Open Graph meta tags from a TikTok profile page."""
        html = (
            '<html><head>'
            '<meta property="og:title" content="charli d\'amelio"/>'
            '<meta property="og:description" content="TikTok star"/>'
            '<meta property="og:image" content="https://example.com/img.jpg"/>'
            '</head></html>'
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_get.return_value = mock_resp

        data = self.fetcher.fetch_profile_data("https://tiktok.com/@charlidamelio")
        self.assertIsNotNone(data)
        self.assertEqual(data.platform, "TikTok")
        self.assertEqual(data.username, "charlidamelio")
        self.assertIn("charli", data.display_name)
        self.assertEqual(data.profile_picture, "https://example.com/img.jpg")


class TestTumblrFetcher(unittest.TestCase):
    """Unit tests for TumblrFetcher."""

    def setUp(self):
        from social_media_fetchers import TumblrFetcher
        self.fetcher = TumblrFetcher()

    def test_can_handle_url(self):
        self.assertTrue(self.fetcher.can_handle_url("https://staff.tumblr.com"))
        self.assertTrue(self.fetcher.can_handle_url("https://www.tumblr.com/staff"))
        self.assertFalse(self.fetcher.can_handle_url("https://twitter.com/user"))

    def test_extract_username_subdomain(self):
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://staff.tumblr.com"),
            "staff",
        )

    def test_extract_username_path(self):
        self.assertEqual(
            self.fetcher.extract_username_from_url("https://www.tumblr.com/staff"),
            "staff",
        )

    @patch("requests.Session.get")
    def test_fetch_profile_data_api(self, mock_get):
        """Fetches blog info and posts via the Tumblr API."""
        self.fetcher.api_key = "fake_api_key"

        info_payload = {
            "response": {
                "blog": {
                    "title": "Tumblr Staff",
                    "description": "The Tumblr team",
                    "followers": 5000,
                    "url": "https://staff.tumblr.com",
                    "avatar": [{"url": "https://example.com/avatar.jpg"}],
                }
            }
        }
        posts_payload = {
            "response": {
                "posts": [
                    {
                        "title": "Hello",
                        "body": "Welcome to Tumblr",
                        "tags": ["intro"],
                        "date": "2024-01-01 12:00:00 GMT",
                        "type": "text",
                    }
                ]
            }
        }

        mock_info_resp = MagicMock()
        mock_info_resp.status_code = 200
        mock_info_resp.json.return_value = info_payload

        mock_posts_resp = MagicMock()
        mock_posts_resp.status_code = 200
        mock_posts_resp.json.return_value = posts_payload

        mock_get.side_effect = [mock_info_resp, mock_posts_resp]

        data = self.fetcher.fetch_profile_data("https://staff.tumblr.com")
        self.assertIsNotNone(data)
        self.assertEqual(data.platform, "Tumblr")
        self.assertEqual(data.username, "staff")
        self.assertEqual(data.display_name, "Tumblr Staff")
        self.assertEqual(data.followers_count, 5000)
        self.assertEqual(len(data.posts), 1)
        self.assertEqual(data.posts[0]["title"], "Hello")

    @patch("requests.Session.get")
    def test_fallback_fetch(self, mock_get):
        """Falls back to Open Graph scraping when no API key is set."""
        self.fetcher.api_key = None
        html = (
            '<html><head>'
            '<meta property="og:title" content="Tumblr Staff"/>'
            '<meta property="og:description" content="The official Tumblr blog"/>'
            '</head></html>'
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        mock_get.return_value = mock_resp

        data = self.fetcher.fetch_profile_data("https://staff.tumblr.com")
        self.assertIsNotNone(data)
        self.assertEqual(data.platform, "Tumblr")
        self.assertEqual(data.display_name, "Tumblr Staff")


class TestSocialMediaFetcherManager(unittest.TestCase):
    """Unit tests for SocialMediaFetcherManager with new fetchers registered."""

    def test_new_fetchers_registered(self):
        """GitHubFetcher, YouTubeFetcher, TikTokFetcher, and TumblrFetcher
        should be present in the manager's fetcher list."""
        from social_media_fetchers import (
            SocialMediaFetcherManager,
            GitHubFetcher,
            YouTubeFetcher,
            TikTokFetcher,
            TumblrFetcher,
        )
        manager = SocialMediaFetcherManager()
        fetcher_types = [type(f) for f in manager.fetchers]
        self.assertIn(GitHubFetcher, fetcher_types)
        self.assertIn(YouTubeFetcher, fetcher_types)
        self.assertIn(TikTokFetcher, fetcher_types)
        self.assertIn(TumblrFetcher, fetcher_types)

    def test_new_fetchers_precede_generic(self):
        """New specific fetchers must appear before GenericFetcher so they take priority."""
        from social_media_fetchers import (
            SocialMediaFetcherManager,
            GitHubFetcher,
            YouTubeFetcher,
            TikTokFetcher,
            TumblrFetcher,
            GenericFetcher,
        )
        manager = SocialMediaFetcherManager()
        fetcher_types = [type(f) for f in manager.fetchers]
        generic_idx = fetcher_types.index(GenericFetcher)
        for cls in (GitHubFetcher, YouTubeFetcher, TikTokFetcher, TumblrFetcher):
            self.assertLess(
                fetcher_types.index(cls),
                generic_idx,
                msg=f"{cls.__name__} must be registered before GenericFetcher",
            )

    def test_github_url_dispatched_to_github_fetcher(self):
        """The manager should route a GitHub URL to GitHubFetcher."""
        from social_media_fetchers import SocialMediaFetcherManager, GitHubFetcher
        manager = SocialMediaFetcherManager()
        matched = next(
            (f for f in manager.fetchers if f.can_handle_url("https://github.com/torvalds")),
            None,
        )
        self.assertIsInstance(matched, GitHubFetcher)

    def test_youtube_url_dispatched_to_youtube_fetcher(self):
        """The manager should route a YouTube URL to YouTubeFetcher."""
        from social_media_fetchers import SocialMediaFetcherManager, YouTubeFetcher
        manager = SocialMediaFetcherManager()
        matched = next(
            (f for f in manager.fetchers if f.can_handle_url("https://youtube.com/@PewDiePie")),
            None,
        )
        self.assertIsInstance(matched, YouTubeFetcher)

    def test_tiktok_url_dispatched_to_tiktok_fetcher(self):
        """The manager should route a TikTok URL to TikTokFetcher."""
        from social_media_fetchers import SocialMediaFetcherManager, TikTokFetcher
        manager = SocialMediaFetcherManager()
        matched = next(
            (f for f in manager.fetchers if f.can_handle_url("https://tiktok.com/@user")),
            None,
        )
        self.assertIsInstance(matched, TikTokFetcher)

    def test_tumblr_url_dispatched_to_tumblr_fetcher(self):
        """The manager should route a Tumblr URL to TumblrFetcher."""
        from social_media_fetchers import SocialMediaFetcherManager, TumblrFetcher
        manager = SocialMediaFetcherManager()
        matched = next(
            (f for f in manager.fetchers if f.can_handle_url("https://staff.tumblr.com")),
            None,
        )
        self.assertIsInstance(matched, TumblrFetcher)


if __name__ == "__main__":
    unittest.main()
