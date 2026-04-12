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

    @patch("analyze.fetch_social_media_data")
    @patch("analyze._get_client")
    def test_analyze_personality(self, mock_get_client, mock_fetch):
        """
        Test analyze_personality with mocked OpenAI API call.
        """
        mock_message = MagicMock()
        mock_message.content = "Mocked analysis text"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        # Return None so the fetcher falls back to "Failed to fetch" message
        mock_fetch.return_value = None

        links_info = [
            {"url": "https://twitter.com/elonmusk", "platform": "Twitter"},
            {"url": "https://instagram.com/janedoe", "platform": "Instagram"},
        ]
        personal_description = "Jane loves travel and technology."

        result = analyze_personality(links_info, personal_description)

        # Check that we got back the mocked text
        self.assertIn("Mocked analysis text", result)

        # Verify the OpenAI API was called once
        mock_client.chat.completions.create.assert_called_once()

    def test_analyze_personality_empty(self):
        """
        Test analyze_personality with empty input.
        """
        result = analyze_personality([], "")
        self.assertEqual(result, "No data provided for analysis.")


class TestSocialMediaFetchers(unittest.TestCase):
    """Test cases for the social_media_fetchers module."""

    def setUp(self):
        from social_media_fetchers import (
            TwitterFetcher, LinkedInFetcher, InstagramFetcher,
            FacebookFetcher, RedditFetcher, GitHubFetcher, GenericFetcher,
            SocialMediaFetcherManager,
        )
        self.TwitterFetcher = TwitterFetcher
        self.LinkedInFetcher = LinkedInFetcher
        self.InstagramFetcher = InstagramFetcher
        self.FacebookFetcher = FacebookFetcher
        self.RedditFetcher = RedditFetcher
        self.GitHubFetcher = GitHubFetcher
        self.GenericFetcher = GenericFetcher
        self.SocialMediaFetcherManager = SocialMediaFetcherManager

    def test_fetcher_manager_contains_all_fetchers(self):
        """SocialMediaFetcherManager should include all platform fetchers."""
        manager = self.SocialMediaFetcherManager()
        class_names = [f.__class__.__name__ for f in manager.fetchers]
        for expected in [
            'TwitterFetcher', 'LinkedInFetcher', 'InstagramFetcher',
            'FacebookFetcher', 'RedditFetcher', 'GitHubFetcher', 'GenericFetcher',
        ]:
            self.assertIn(expected, class_names)

    def test_url_domain_matching_correct(self):
        """can_handle_url should match exact domains, not substrings."""
        tw = self.TwitterFetcher()
        self.assertTrue(tw.can_handle_url('https://twitter.com/user'))
        self.assertTrue(tw.can_handle_url('https://x.com/user'))
        self.assertFalse(tw.can_handle_url('https://notx.com/user'))

        gh = self.GitHubFetcher()
        self.assertTrue(gh.can_handle_url('https://github.com/torvalds'))
        self.assertTrue(gh.can_handle_url('https://gist.github.com/user'))
        self.assertFalse(gh.can_handle_url('https://notgithub.com/user'))

        rd = self.RedditFetcher()
        self.assertTrue(rd.can_handle_url('https://reddit.com/user/test'))
        self.assertFalse(rd.can_handle_url('https://notreddit.com/user'))

    def test_github_username_extraction(self):
        """GitHubFetcher should extract usernames correctly."""
        gh = self.GitHubFetcher()
        self.assertEqual(gh.extract_username_from_url('https://github.com/torvalds'), 'torvalds')
        self.assertEqual(gh.extract_username_from_url('https://github.com/VictoKu1'), 'VictoKu1')

    @patch('social_media_fetchers.requests.Session.get')
    def test_github_fetcher_success(self, mock_get):
        """GitHubFetcher should parse a successful API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'login': 'torvalds',
            'name': 'Linus Torvalds',
            'bio': 'Linux kernel creator',
            'followers': 100000,
            'following': 0,
            'avatar_url': 'https://avatars.githubusercontent.com/u/1',
            'created_at': '2011-09-03T15:26:22Z',
            'location': 'Portland, OR',
            'blog': 'https://www.linuxfoundation.org',
        }
        mock_get.return_value = mock_response

        gh = self.GitHubFetcher()
        data = gh.fetch_profile_data('https://github.com/torvalds')

        self.assertIsNotNone(data)
        self.assertEqual(data.platform, 'GitHub')
        self.assertEqual(data.username, 'torvalds')
        self.assertEqual(data.display_name, 'Linus Torvalds')
        self.assertEqual(data.followers_count, 100000)


if __name__ == "__main__":
    unittest.main()
