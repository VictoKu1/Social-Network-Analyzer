# Social Media API Integration Guide

This guide explains how to set up and use the platform-specific social media data fetching system that replaces the generic web scraping approach.

## Overview

The new system provides:
- **Platform-specific API integration** for Twitter, LinkedIn, Instagram, Facebook, and Reddit
- **Rate limiting** to respect API limits
- **Fallback mechanisms** when APIs are unavailable
- **Structured data extraction** for better analysis
- **OAuth and authentication handling**

## Supported Platforms

### 1. Twitter/X
- **API**: Twitter API v2 and v1.1
- **Library**: `tweepy`
- **Features**: Profile data, follower counts, verification status
- **Rate Limits**: 300 requests per 15-minute window (v2), 900 requests per 15-minute window (v1.1)

### 2. LinkedIn
- **API**: LinkedIn API (unofficial via `linkedin-api`)
- **Library**: `linkedin-api`
- **Features**: Profile data, work experience, education
- **Rate Limits**: Varies, requires authentication

### 3. Instagram
- **API**: Instagram Graph API (via `instaloader`)
- **Library**: `instaloader`
- **Features**: Profile data, recent posts, follower counts
- **Rate Limits**: Very strict, 200 requests per hour

### 4. Facebook
- **API**: Facebook Graph API
- **Library**: `facebook-sdk`
- **Features**: Profile data, public posts
- **Rate Limits**: 200 requests per hour per user

### 5. Reddit
- **API**: Reddit API
- **Library**: `praw`
- **Features**: User data, recent posts, karma
- **Rate Limits**: 60 requests per minute

### 6. GitHub
- **API**: GitHub REST API v3 (public)
- **Authentication**: Optional `GITHUB_TOKEN` for higher rate limits (5,000 req/hour vs 60 req/hour)
- **Features**: Profile data, public repositories, follower/following counts, location, website
- **Rate Limits**: 60 unauthenticated requests/hour; 5,000 with token

### 7. YouTube
- **API**: YouTube Data API v3
- **Authentication**: `YOUTUBE_API_KEY` required; falls back to Open Graph scraping
- **Features**: Channel info, subscriber count, description, country, join date
- **Rate Limits**: 10,000 units/day (search = 100 units, channels = 1 unit)

### 8. TikTok
- **API**: None (no official public API)
- **Method**: Open Graph meta-tag scraping
- **Features**: Display name, bio, profile picture (best-effort — anti-scraping measures may limit results)

### 9. Tumblr
- **API**: Tumblr API v2 (public read-only endpoints)
- **Authentication**: `TUMBLR_API_KEY` required; falls back to Open Graph scraping
- **Features**: Blog title, description, recent posts, follower count, avatar
- **Rate Limits**: 1,000 requests/hour (unauthenticated), 5,000/hour (with key)

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

3. For Selenium-based fallback (optional):
```bash
pip install webdriver-manager
```

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

# YouTube Data API v3
YOUTUBE_API_KEY=your_youtube_api_key_here

# Tumblr API
TUMBLR_API_KEY=your_tumblr_consumer_key_here
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

1. Use your LinkedIn email and password
2. **Security Warning**: This method is not recommended for production use
3. Consider using LinkedIn's official API for business applications

#### Instagram API Setup

1. The `instaloader` library can work with public profiles without authentication
2. For private profiles, provide your Instagram credentials
3. Consider using Instagram's Graph API for business accounts

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
3. Without a token the public API allows 60 requests/hour (unauthenticated); with a token you get up to 5,000 requests/hour.
4. No special permissions are required to read public profiles.

#### YouTube Data API v3 Setup

1. Go to [Google Developers Console](https://console.developers.google.com/).
2. Create (or select) a project and enable the **YouTube Data API v3**.
3. Create an **API key** credential.
4. Without the key, the fetcher falls back to Open Graph meta-tag scraping.

#### TikTok Setup

TikTok provides no publicly accessible API for third-party profile data.  
The fetcher uses Open Graph meta-tag scraping, which is best-effort and may be
affected by TikTok's anti-scraping measures.

#### Tumblr API Setup

1. Register an application at [Tumblr OAuth Apps](https://www.tumblr.com/oauth/apps).
2. The **Consumer Key** shown on that page is your `TUMBLR_API_KEY`.
3. Without the key, the fetcher falls back to Open Graph meta-tag scraping.

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

The new system is backward compatible. Your existing code will automatically use the new platform-specific fetchers:

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

## Rate Limiting

The system includes built-in rate limiting:

- **Twitter**: 60 requests per minute
- **LinkedIn**: 60 requests per minute
- **Instagram**: 60 requests per minute
- **Facebook**: 60 requests per minute
- **Reddit**: 60 requests per minute

Rate limits are automatically enforced, and the system will wait when limits are reached.

## Error Handling

The system includes comprehensive error handling:

1. **API Errors**: If an API call fails, the system falls back to web scraping
2. **Authentication Errors**: If credentials are invalid, the system uses fallback methods
3. **Rate Limit Errors**: The system automatically waits and retries
4. **Network Errors**: Retry logic with exponential backoff

## Fallback Mechanisms

When APIs are unavailable, the system falls back to:

1. **Web Scraping**: Using BeautifulSoup to extract basic information
2. **Generic Fetcher**: For platforms without specific API support
3. **Error Reporting**: Clear error messages for debugging

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Environment Variables**: Use environment variables for sensitive data
3. **Rate Limiting**: Respect platform rate limits
4. **Data Privacy**: Only fetch publicly available data
5. **Authentication**: Use secure authentication methods

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed
2. **Authentication Errors**: Check your API credentials
3. **Rate Limit Errors**: The system will automatically handle these
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
3. **Connection Pooling**: The system uses connection pooling for HTTP requests
4. **Memory Management**: Large responses are automatically truncated

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