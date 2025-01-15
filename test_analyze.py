import unittest
from unittest.mock import patch, MagicMock
from analyze import validate_social_link, analyze_personality

class TestAnalyze(unittest.TestCase):

    def test_validate_social_link_valid(self):
        link = "https://twitter.com/elonmusk"
        is_valid, platform = validate_social_link(link)
        self.assertTrue(is_valid)
        self.assertEqual(platform, "Twitter")

    def test_validate_social_link_invalid_prefix(self):
        link = "ftp://facebook.com/page"
        is_valid, platform = validate_social_link(link)
        self.assertFalse(is_valid)
        self.assertIsNone(platform)

    def test_validate_social_link_unknown_domain(self):
        link = "https://example.com/user"
        is_valid, platform = validate_social_link(link)
        self.assertFalse(is_valid)
        self.assertIsNone(platform)

    @patch('openai.Completion.create')
    def test_analyze_personality(self, mock_openai_create):
        # Mock the OpenAI API call to avoid real calls during tests
        mock_openai_create.return_value = MagicMock(choices=[MagicMock(text="Mocked analysis text")])
        
        links_info = [
            {"url": "https://twitter.com/elonmusk", "platform": "Twitter"},
            {"url": "https://instagram.com/janedoe", "platform": "Instagram"}
        ]
        personal_description = "Jane loves travel and technology."

        result = analyze_personality(links_info, personal_description)

        # Check that we got back the mocked text
        self.assertIn("Mocked analysis text", result)

        # Verify the OpenAI API was called once
        mock_openai_create.assert_called_once()

    def test_analyze_personality_empty(self):
        result = analyze_personality([], "")
        self.assertEqual(result, "No data provided for analysis.")

if __name__ == '__main__':
    unittest.main()
