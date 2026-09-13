# Social Media API Integration Guide

This guide covers the platform API adapters and public HTML scraping fallback.

## Overview

The new system provides:
- **Platform-specific API integration** for Twitter, LinkedIn, Instagram, Facebook, and Reddit
- **Work admission limits** and per-fetcher pacing
- **Fallback mechanisms** when APIs are unavailable
- **Structured data extraction** for better analysis
- **OAuth and authentication handling**

## Access and data rules

The app defaults to local-only access. `python app.py` binds to `127.0.0.1` with debug mode off; local requests must use a loopback hostname. For shared access, set a random `APP_ACCESS_TOKEN` of at least 32 characters and list external hostnames in `APP_ALLOWED_HOSTS`, separated by commas without schemes, ports or paths. Restart the app, then use HTTP Basic username `operator` and the token as the password. A configured token also applies to local requests.

External requests require HTTPS in the serving WSGI environment. The app does not trust forwarded headers to establish the peer, hostname or HTTPS scheme; local-only mode rejects `Forwarded` and `X-Forwarded-*` headers. Configure the serving environment for HTTPS. See [Access and limits](README.md#access-and-limits) for the full setup and limits.

Setting `APP_ACCESS_TOKEN` enables shared mode and uses public HTML scraping for Twitter, Facebook, LinkedIn, Instagram and Reddit, bypassing operator logins and previously initialized authenticated clients. The Instagram adapter rejects private profiles before reading posts in local mode. Obtain explicit consent before analyzing sensitive personal information.

## Supported Platforms

### 1. Twitter/X
- **API**: Twitter API v2 and v1.1
- **Library**: `tweepy`
- **Features**: Profile data, follower counts, verification status
- **Access**: Configured SDK credentials in local mode; public scraping in shared mode

### 2. LinkedIn
- **API**: LinkedIn API (unofficial via `linkedin-api`)
- **Library**: `linkedin-api`
- **Features**: Profile data, work experience, education
- **Rate Limits**: Varies, requires authentication

### 3. Instagram
- **Adapter**: Public profile retrieval via `instaloader`
- **Library**: `instaloader`
- **Features**: Profile data, recent posts, follower counts
- **Access**: Private profiles are rejected by the local adapter; shared mode uses public HTML scraping

### 4. Facebook
- **API**: Facebook Graph API
- **Library**: `facebook-sdk`
- **Features**: Profile data, public posts
- **Access**: Configured SDK credentials in local mode; public scraping in shared mode

### 5. Reddit
- **API**: Reddit API
- **Library**: `praw`
- **Features**: User data, recent posts, karma
- **Pacing**: The adapter uses an in-process rate gate; the platform applies its own account quota

### 6. GitHub
- **API**: GitHub REST API v3 (public)
- **Authentication**: Optional `GITHUB_TOKEN` for the public user-profile endpoint
- **Features**: Profile data, public repositories, follower/following counts, location, website
- **Pacing**: 1 fetch/minute without a token or 83/minute with a token; platform quotas also apply

### 7. YouTube
- **Method**: Generic public HTML scraping with profile text selectors
- **Authentication**: The current adapter does not consume `YOUTUBE_API_KEY`
- **Features**: Basic name and description when available in the HTML

### 8. TikTok
- **Adapter**: No dedicated API integration in this repository
- **Method**: Generic public HTML scraping with profile text selectors
- **Features**: Basic name and description when available in the HTML; anti-scraping measures may prevent retrieval

### 9. Tumblr
- **Method**: Generic public HTML scraping with profile text selectors
- **Authentication**: The current adapter does not consume `TUMBLR_API_KEY`
- **Features**: Basic name and description when available in the HTML

### 10. Generic Platforms
- **Method**: Web scraping with BeautifulSoup
- **Features**: Basic profile information
- **Fallback**: Used when no specific API is available

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your API credentials (see Configuration section below)

The current HTML fallback does not use Selenium or run page JavaScript.

## Configuration

### Environment Variables

Create a `.env` file in your project root with the following variables:

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Twitter/X API
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret_here

# LinkedIn API
LINKEDIN_EMAIL=your_linkedin_email_here
LINKEDIN_PASSWORD=your_linkedin_password_here

# Instagram API
INSTAGRAM_USERNAME=your_instagram_username_here
INSTAGRAM_PASSWORD=your_instagram_password_here

# Facebook API
FACEBOOK_ACCESS_TOKEN=your_facebook_access_token_here
FACEBOOK_APP_ID=your_facebook_app_id_here
FACEBOOK_APP_SECRET=your_facebook_app_secret_here

# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=SocialNetworkAnalyzer/1.0

# GitHub API (optional – raises rate limit from 60 to 5,000 requests/hour)
GITHUB_TOKEN=your_github_personal_access_token_here

# Access defaults: leave blank for local-only use
APP_ACCESS_TOKEN=
APP_ALLOWED_HOSTS=
```

### Platform-Specific Setup

#### Twitter/X API Setup

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Create a new app
3. Apply for API access (Basic or Elevated)
4. Generate your API keys and tokens
5. For v2 API, use the Bearer Token
6. For v1.1 API, use API Key, API Secret, Access Token, and Access Token Secret

#### LinkedIn API Setup

**Note**: LinkedIn's official API is very restrictive. The `linkedin-api` library uses web scraping with authentication.

1. Optional local login uses your LinkedIn email and password.
2. Shared mode skips this login and uses public HTML scraping.
3. This adapter uses the unofficial `linkedin-api` library.

#### Instagram API Setup

1. Use public Instagram profiles; `instaloader` can fetch them without authentication.
2. The adapter rejects private profiles before reading posts, even with local credentials.
3. Shared mode bypasses operator login and uses public HTML scraping.

#### Facebook API Setup

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Get your App ID and App Secret
4. Generate an Access Token with appropriate permissions
5. Add the required permissions to your app

#### Reddit API Setup

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Create a new app (script type)
3. Get your Client ID and Client Secret
4. Set a User Agent string

#### GitHub API Setup

1. A Personal Access Token is **optional** but strongly recommended.
2. Generate one at [GitHub Settings → Tokens](https://github.com/settings/tokens).
3. The adapter paces requests at 1/minute without a token or 83/minute with one. Check your GitHub account's current API quota separately.
4. No special permissions are required to read public profiles.

#### YouTube Setup

Use a supported public YouTube URL. The current implementation uses generic HTML scraping and does not read `YOUTUBE_API_KEY`.

#### TikTok Setup

The fetcher uses generic HTML scraping. TikTok's page rendering and anti-scraping measures may prevent retrieval.

#### Tumblr Setup

Use a supported public Tumblr URL. The current implementation uses generic HTML scraping and does not read `TUMBLR_API_KEY`.

## Usage

### Basic Usage

```python
from social_media_fetchers import fetch_social_media_data, format_social_media_data

# Fetch data from a social media profile
url = "https://twitter.com/username"
data = fetch_social_media_data(url)

if data:
    # Format the data for analysis
    formatted_data = format_social_media_data(data)
    print(formatted_data)
else:
    print("Failed to fetch data")
```

### Advanced Usage

```python
from social_media_fetchers import SocialMediaFetcherManager

# Create a custom fetcher manager
manager = SocialMediaFetcherManager()

# Fetch data with custom configuration
data = manager.fetch_profile_data("https://linkedin.com/in/username")

# Get supported platforms
platforms = manager.get_supported_platforms()
print(f"Supported platforms: {platforms}")
```

### Integration with Existing Code

Existing callers can use the same entry points. They must supply supported profile URLs and stay within the input budgets; rejected destinations and private Instagram profiles raise a `SecurityError`:

```python
from analyze import analyze_personality

# This will now use platform-specific APIs
result = analyze_personality(links_info, personal_description)
```

## Data Structure

The system returns structured data in the `SocialMediaData` format:

```python
@dataclass
class SocialMediaData:
    platform: str              # Platform name (e.g., "Twitter", "LinkedIn")
    username: str              # Username/handle
    display_name: str          # Display name
    bio: str                   # Bio/description
    posts: List[Dict]          # Recent posts
    followers_count: int       # Number of followers
    following_count: int       # Number of following
    profile_picture: str       # Profile picture URL
    verified: bool             # Verification status
    join_date: str             # Account creation date
    location: str              # Location
    website: str               # Website URL
    raw_data: Dict             # Raw API response
```

## Request and download limits

`/analyze` and `/api/ollama/models` share a rolling allowance of **30 work requests per minute** and **2 concurrent requests**. Excess work returns HTTP 429 with `Retry-After: 60`. These counters cover one process; multiple workers require shared admission control. Per-fetcher pacing is separate and does not guarantee compliance with a platform's account quota or count every SDK request.

The web API accepts at most **5 profile URLs**, **2,048 characters per URL**, **10,000 description characters** and **32 KiB per request body**. Analysis rejects prompts over **50,000 characters** and requests at most **4,096 completion tokens** from either inference provider.

The shared HTTP transport for HTML scraping and GitHub reads:

- Accepts supported social domains on standard HTTP(S) ports and requires all DNS answers to be public Internet addresses.
- Connects to a validated IP, retains the original HTTPS hostname for certificate verification, and validates each redirect destination.
- Permits at most **3 redirects** within a **15-second retrieval budget** per fetch.
- Rejects encoded or decoded bodies over **1 MiB**, including oversized gzip content.

These HTTP download limits do not extend to platform SDK internals, inference response bodies or the duration of a complete analysis. Operator-configured Ollama endpoints use a separate transport so local inference remains available.

## Error Handling

Platform adapters may fall back to public HTML scraping after an API failure. Security rejections, including unsafe destinations, oversized downloads and private Instagram profiles, stop the request. The web API returns structured error codes; callers should correct rejected inputs or wait after HTTP 429 before retrying. SDK retry behavior depends on the adapter.

## Fallback Mechanisms

When APIs are unavailable, the system falls back to:

1. **Web Scraping**: Using BeautifulSoup to extract basic information
2. **Generic Fetcher**: For platforms without specific API support
3. **Error Reporting**: Clear error messages for debugging

## Security Considerations

Keep API credentials and `APP_ACCESS_TOKEN` in the server environment or `.env`, out of Git and browser code. Fetch public profiles with the required consent and respect each platform's terms and quotas. Shared mode uses one operator credential; it does not provide separate user accounts or tenant isolation. See [SECURITY.md](SECURITY.md) for private vulnerability reporting.

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed
2. **Authentication Errors**: Check your API credentials
3. **Rate Limit Errors**: Wait for the indicated retry interval; check platform quotas separately
4. **Network Errors**: Check your internet connection

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing

Run the test suite:

```bash
python -m pytest test_analyze.py
```

## Performance Optimization

1. **Caching**: Consider implementing caching for frequently accessed profiles
2. **Async Processing**: For multiple profiles, consider async processing
3. **Concurrency**: Keep deployment worker counts consistent with the shared work budget
4. **Memory Management**: HTML/GitHub HTTP reads reject oversized bodies; formatted post excerpts have separate length limits

## Future Enhancements

1. **Additional Platforms**: Support for more social media platforms
2. **Advanced Analytics**: More sophisticated data analysis
3. **Real-time Updates**: WebSocket support for real-time data
4. **Machine Learning**: ML-based content analysis
5. **Graph Analysis**: Social network graph analysis

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the platform-specific documentation
3. Check the GitHub issues page
4. Contact the development team

## License

This project is licensed under the MIT License. See the LICENSE file for details.
