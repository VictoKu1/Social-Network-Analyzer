"""
Example configuration file for social media API credentials.
Copy this file to config.py and fill in your actual API keys.
"""

# OpenAI API Configuration
OPENAI_API_KEY = "your_openai_api_key_here"

# Twitter/X API Configuration
# Get these from https://developer.twitter.com/en/portal/dashboard
TWITTER_BEARER_TOKEN = "your_twitter_bearer_token_here"
TWITTER_API_KEY = "your_twitter_api_key_here"
TWITTER_API_SECRET = "your_twitter_api_secret_here"
TWITTER_ACCESS_TOKEN = "your_twitter_access_token_here"
TWITTER_ACCESS_TOKEN_SECRET = "your_twitter_access_token_secret_here"

# LinkedIn API Configuration
# Note: LinkedIn API requires authentication through their developer portal
LINKEDIN_EMAIL = "your_linkedin_email_here"
LINKEDIN_PASSWORD = "your_linkedin_password_here"

# Instagram API Configuration
# Note: Instagram has strict rate limits and may require business account
INSTAGRAM_USERNAME = "your_instagram_username_here"
INSTAGRAM_PASSWORD = "your_instagram_password_here"

# Facebook API Configuration
# Get these from https://developers.facebook.com/
FACEBOOK_ACCESS_TOKEN = "your_facebook_access_token_here"
FACEBOOK_APP_ID = "your_facebook_app_id_here"
FACEBOOK_APP_SECRET = "your_facebook_app_secret_here"

# Reddit API Configuration
# Get these from https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID = "your_reddit_client_id_here"
REDDIT_CLIENT_SECRET = "your_reddit_client_secret_here"
REDDIT_USER_AGENT = "SocialNetworkAnalyzer/1.0"

# Optional: Selenium Configuration for web scraping fallback
# If you want to use Selenium for JavaScript-rendered content
SELENIUM_HEADLESS = True
SELENIUM_TIMEOUT = 10

"""
INSTRUCTIONS FOR SETTING UP API CREDENTIALS:

1. TWITTER/X API:
   - Go to https://developer.twitter.com/en/portal/dashboard
   - Create a new app
   - Get your API keys and tokens
   - For v2 API, you need Bearer Token
   - For v1.1 API, you need API Key, API Secret, Access Token, and Access Token Secret

2. LINKEDIN API:
   - LinkedIn's official API is quite restrictive
   - The linkedin-api library uses web scraping with authentication
   - Use your LinkedIn email and password (not recommended for production)

3. INSTAGRAM API:
   - Instagram has very strict rate limits
   - The instaloader library can work with public profiles
   - For private profiles, you need to provide credentials
   - Consider using Instagram's Graph API for business accounts

4. FACEBOOK API:
   - Go to https://developers.facebook.com/
   - Create a new app
   - Get your App ID and App Secret
   - Generate an Access Token with appropriate permissions

5. REDDIT API:
   - Go to https://www.reddit.com/prefs/apps
   - Create a new app (script type)
   - Get your Client ID and Client Secret
   - Set a User Agent string

SECURITY NOTES:
- Never commit your actual API keys to version control
- Use environment variables or a secure configuration management system
- Consider using a secrets manager for production deployments
- Regularly rotate your API keys
- Monitor your API usage to avoid rate limits
""" 