"""
Example environment settings for inference and social media API credentials.
The app reads environment variables or .env, not this Python file.
"""

# OpenAI API Configuration
OPENAI_API_KEY = "your_openai_api_key_here"
OPENAI_MODEL = "gpt-4o"

# Inference defaults. The website also allows selecting OpenAI or Ollama per analysis.
LLM_PROVIDER = "openai"  # "openai" or "ollama"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = ""  # Optional installed model name; otherwise choose in the website.

# Access: leave blank for local-only use. For shared access, set a random secret
# of at least 32 characters in the environment/.env, then restart the app.
# HTTP Basic username is "operator"; the password is APP_ACCESS_TOKEN.
APP_ACCESS_TOKEN = ""
# Comma-separated external hostnames without schemes, ports or paths.
APP_ALLOWED_HOSTS = ""  # Example: "analyzer.example.com"
# External access requires HTTPS in the serving WSGI environment. The app does
# not trust forwarded headers; these settings do not alter its loopback listener.
# /analyze and /api/ollama/models share 30 requests/minute and 2 concurrent work
# slots per process. Multiple workers need shared admission control.
# Fixed budgets: 5 links, 2048 characters/URL, 10000 description characters,
# 32 KiB request bodies, 50000 prompt characters and 4096 completion tokens.
# HTML scraping/GitHub HTTP reads: public DNS/IP pinning, 1 MiB encoded/decoded
# bodies, a 15-second fetch budget and at most 3 revalidated redirects.
# These download budgets do not cover SDK calls or a whole analysis.

# Twitter/X API Configuration
# Get these from https://developer.twitter.com/en/portal/dashboard
# Shared mode skips these credentials and uses public scraping.
TWITTER_BEARER_TOKEN = "your_twitter_bearer_token_here"
TWITTER_API_KEY = "your_twitter_api_key_here"
TWITTER_API_SECRET = "your_twitter_api_secret_here"
TWITTER_ACCESS_TOKEN = "your_twitter_access_token_here"
TWITTER_ACCESS_TOKEN_SECRET = "your_twitter_access_token_secret_here"

# LinkedIn API Configuration
# Optional local login through linkedin-api; shared mode uses public scraping.
LINKEDIN_EMAIL = "your_linkedin_email_here"
LINKEDIN_PASSWORD = "your_linkedin_password_here"

# Instagram API Configuration
# Optional local login for public profiles; private profiles are rejected.
# Shared mode bypasses this login and uses public HTML scraping.
INSTAGRAM_USERNAME = "your_instagram_username_here"
INSTAGRAM_PASSWORD = "your_instagram_password_here"

# Facebook API Configuration
# Get these from https://developers.facebook.com/
# Shared mode skips these credentials and uses public scraping.
FACEBOOK_ACCESS_TOKEN = "your_facebook_access_token_here"
FACEBOOK_APP_ID = "your_facebook_app_id_here"
FACEBOOK_APP_SECRET = "your_facebook_app_secret_here"

# Reddit API Configuration (local use only; shared mode uses anonymous HTML)
# Get these from https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID = "your_reddit_client_id_here"
REDDIT_CLIENT_SECRET = "your_reddit_client_secret_here"
REDDIT_USER_AGENT = "SocialNetworkAnalyzer/1.0"

# GitHub API Configuration
# Optional: get a Personal Access Token from https://github.com/settings/tokens
# Local pacing is 1 fetch/minute without a token or 83/minute with a token.
# GitHub also applies its own account quota.
GITHUB_TOKEN = "your_github_token_here"

# Reserved examples: the current YouTube/Tumblr adapters use public HTML
# scraping and do not consume these API keys.
YOUTUBE_API_KEY = "your_youtube_api_key_here"

TUMBLR_API_KEY = "your_tumblr_api_key_here"

# Reserved examples: the current scraping transport does not use Selenium.
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
   - Optional local login uses your LinkedIn email and password
   - Shared mode skips the login and uses public scraping

3. INSTAGRAM API:
   - Instagram has very strict rate limits
   - The instaloader library can work with public profiles
   - Private profiles are rejected, even with local credentials
   - Shared mode bypasses operator login and uses public HTML scraping
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

6. GITHUB API:
   - A Personal Access Token is optional but recommended for higher rate limits.
   - Generate one at https://github.com/settings/tokens
   - Local pacing is 1 fetch/minute without a token or 83/minute with a token.
   - Check the account's current GitHub API quota separately.

7. YOUTUBE DATA API v3:
   - The current adapter uses public HTML scraping and does not read an API key.

8. TUMBLR API:
   - The current adapter uses public HTML scraping and does not read an API key.

SECURITY NOTES:
- Never commit your actual API keys to version control
- Use environment variables or a secure configuration management system
- Consider using a secrets manager for production deployments
- Regularly rotate your API keys
- Monitor your API usage to avoid rate limits
"""
