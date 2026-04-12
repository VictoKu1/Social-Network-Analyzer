"""
Platform-specific social media data fetching module.
Handles API integration, OAuth, rate limiting, and data extraction for various platforms.
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SocialMediaData:
    """Data structure for social media profile information."""
    platform: str
    username: str
    display_name: str
    bio: str
    posts: List[Dict[str, Any]]
    followers_count: Optional[int]
    following_count: Optional[int]
    profile_picture: Optional[str]
    verified: bool
    join_date: Optional[str]
    location: Optional[str]
    website: Optional[str]
    raw_data: Dict[str, Any]

class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []

    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]

        if len(self.calls) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.calls[0])
            if sleep_time > 0:
                logger.info("Rate limit reached, waiting %.2f seconds", sleep_time)
                time.sleep(sleep_time)

        self.calls.append(now)

class BaseSocialMediaFetcher(ABC):
    """Abstract base class for social media fetchers."""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @abstractmethod
    def can_handle_url(self, url: str) -> bool:
        """Check if this fetcher can handle the given URL."""

    @abstractmethod
    def extract_username_from_url(self, url: str) -> str:
        """Extract username from URL."""

    @abstractmethod
    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch profile data from the given URL."""

    def _handle_rate_limit(self):
        """Handle rate limiting."""
        self.rate_limiter.wait_if_needed()

class TwitterFetcher(BaseSocialMediaFetcher):
    """Twitter/X API fetcher."""

    def __init__(self):
        super().__init__()
        self.api = None
        self._initialize_api()

    def _initialize_api(self):
        """Initialize Twitter API client."""
        try:
            # Twitter API v2 credentials
            bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            api_key = os.getenv('TWITTER_API_KEY')
            api_secret = os.getenv('TWITTER_API_SECRET')
            access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

            if bearer_token:
                # Import tweepy only if credentials are available
                try:
                    import tweepy
                    self.api = tweepy.Client(bearer_token=bearer_token)
                except ImportError:
                    logger.warning("tweepy not installed, Twitter API unavailable")
            elif all([api_key, api_secret, access_token, access_token_secret]):
                try:
                    import tweepy
                    auth = tweepy.OAuthHandler(api_key, api_secret)
                    auth.set_access_token(access_token, access_token_secret)
                    self.api = tweepy.API(auth)
                except ImportError:
                    logger.warning("tweepy not installed, Twitter API unavailable")
            else:
                logger.warning("Twitter API credentials not found")
        except Exception as e:
            logger.error("Failed to initialize Twitter API: %s", e)

    def can_handle_url(self, url: str) -> bool:
        return 'twitter.com' in url or 'x.com' in url

    def extract_username_from_url(self, url: str) -> str:
        """Extract username from Twitter URL."""
        path = urlparse(url).path
        username = path.strip('/').split('/')[0]
        return username

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch Twitter profile data."""
        if not self.api:
            return self._fallback_fetch(url)

        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)

            # Try API v2 first
            if hasattr(self.api, 'get_user'):
                user = self.api.get_user(username=username)
                if user.data:
                    return self._parse_twitter_user(user.data, username)

            # Fallback to v1.1 API
            if hasattr(self.api, 'get_user'):
                user = self.api.get_user(screen_name=username)
                return self._parse_twitter_user_v1(user, username)

            return self._fallback_fetch(url)

        except Exception as e:
            logger.error("Twitter API error: %s", e)
            return self._fallback_fetch(url)

    def _parse_twitter_user(self, user, username: str) -> SocialMediaData:
        """Parse Twitter API v2 user data."""
        return SocialMediaData(
            platform="Twitter",
            username=username,
            display_name=user.name,
            bio=user.description or "",
            posts=[],  # Would need separate API call for tweets
            followers_count=user.public_metrics.followers_count if hasattr(user, 'public_metrics') else None,
            following_count=user.public_metrics.following_count if hasattr(user, 'public_metrics') else None,
            profile_picture=user.profile_image_url,
            verified=user.verified,
            join_date=user.created_at.isoformat() if user.created_at else None,
            location=user.location,
            website=user.url,
            raw_data=user._json
        )

    def _parse_twitter_user_v1(self, user, username: str) -> SocialMediaData:
        """Parse Twitter API v1.1 user data."""
        return SocialMediaData(
            platform="Twitter",
            username=username,
            display_name=user.name,
            bio=user.description or "",
            posts=[],
            followers_count=user.followers_count,
            following_count=user.friends_count,
            profile_picture=user.profile_image_url,
            verified=user.verified,
            join_date=user.created_at.isoformat() if user.created_at else None,
            location=user.location,
            website=user.url,
            raw_data=user._json
        )

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Fallback to web scraping when API is not available."""
        try:
            # Simple web scraping without Selenium for now
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Try to extract basic info
                display_name = ""
                bio = ""

                # Look for common selectors
                name_selectors = ['h1', 'h2', '[data-testid="UserName"]', '.profile-name']
                bio_selectors = ['[data-testid="UserDescription"]', '.bio', '.description']

                for selector in name_selectors:
                    element = soup.select_one(selector)
                    if element:
                        display_name = element.get_text().strip()
                        break

                for selector in bio_selectors:
                    element = soup.select_one(selector)
                    if element:
                        bio = element.get_text().strip()
                        break

                return SocialMediaData(
                    platform="Twitter",
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={}
                )

        except Exception as e:
            logger.error("Twitter fallback fetch error: %s", e)

        return None

class LinkedInFetcher(BaseSocialMediaFetcher):
    """LinkedIn API fetcher."""

    def __init__(self):
        super().__init__()
        self.api = None
        self._initialize_api()

    def _initialize_api(self):
        """Initialize LinkedIn API client."""
        try:
            email = os.getenv('LINKEDIN_EMAIL')
            password = os.getenv('LINKEDIN_PASSWORD')

            if email and password:
                try:
                    from linkedin_api import Linkedin
                    self.api = Linkedin(email, password)
                except ImportError:
                    logger.warning("linkedin-api not installed, LinkedIn API unavailable")
            else:
                logger.warning("LinkedIn credentials not found")
        except Exception as e:
            logger.error("Failed to initialize LinkedIn API: %s", e)

    def can_handle_url(self, url: str) -> bool:
        return 'linkedin.com' in url

    def extract_username_from_url(self, url: str) -> str:
        """Extract username from LinkedIn URL."""
        path = urlparse(url).path
        parts = path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'in':
            return parts[1]
        return parts[0] if parts else ""

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch LinkedIn profile data."""
        if not self.api:
            return self._fallback_fetch(url)

        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)

            profile = self.api.get_profile(username)

            return SocialMediaData(
                platform="LinkedIn",
                username=username,
                display_name=profile.get('name', ''),
                bio=profile.get('summary', ''),
                posts=[],
                followers_count=profile.get('followers_count'),
                following_count=None,
                profile_picture=profile.get('profile_picture'),
                verified=False,
                join_date=None,
                location=profile.get('location'),
                website=profile.get('website'),
                raw_data=profile
            )

        except Exception as e:
            logger.error("LinkedIn API error: %s", e)
            return self._fallback_fetch(url)

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Fallback to web scraping."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                display_name = ""
                bio = ""

                # LinkedIn specific selectors
                name_element = soup.select_one('h1.text-heading-xlarge')
                if name_element:
                    display_name = name_element.get_text().strip()

                bio_element = soup.select_one('.pv-shared-text-with-see-more')
                if bio_element:
                    bio = bio_element.get_text().strip()

                return SocialMediaData(
                    platform="LinkedIn",
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={}
                )

        except Exception as e:
            logger.error("LinkedIn fallback fetch error: %s", e)

        return None

class InstagramFetcher(BaseSocialMediaFetcher):
    """Instagram API fetcher using instaloader."""

    def __init__(self):
        super().__init__()
        self.loader = None
        self._initialize_loader()

    def _initialize_loader(self):
        """Initialize instaloader."""
        try:
            username = os.getenv('INSTAGRAM_USERNAME')
            password = os.getenv('INSTAGRAM_PASSWORD')

            try:
                import instaloader
                self.loader = instaloader.Instaloader()

                if username and password:
                    self.loader.login(username, password)
                else:
                    logger.warning("Instagram credentials not found, using public access")
            except ImportError:
                logger.warning("instaloader not installed, Instagram API unavailable")
        except Exception as e:
            logger.error("Failed to initialize Instagram loader: %s", e)

    def can_handle_url(self, url: str) -> bool:
        return 'instagram.com' in url

    def extract_username_from_url(self, url: str) -> str:
        """Extract username from Instagram URL."""
        path = urlparse(url).path
        username = path.strip('/').split('/')[0]
        return username

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch Instagram profile data."""
        if not self.loader:
            return self._fallback_fetch(url)

        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)

            import instaloader
            profile = instaloader.Profile.from_username(self.loader.context, username)

            # Get recent posts
            posts = []
            for post in profile.get_posts():
                if len(posts) >= 10:  # Limit to 10 recent posts
                    break
                posts.append({
                    'caption': post.caption or '',
                    'likes': post.likes,
                    'comments': post.comments,
                    'date': post.date.isoformat() if post.date else None
                })

            return SocialMediaData(
                platform="Instagram",
                username=username,
                display_name=profile.full_name,
                bio=profile.biography,
                posts=posts,
                followers_count=profile.followers,
                following_count=profile.followees,
                profile_picture=profile.profile_pic_url,
                verified=profile.is_verified,
                join_date=None,
                location=None,
                website=profile.external_url,
                raw_data={
                    'is_private': profile.is_private,
                    'is_business_account': profile.is_business_account,
                    'posts_count': profile.mediacount
                }
            )

        except Exception as e:
            logger.error("Instagram API error: %s", e)
            return self._fallback_fetch(url)

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Fallback to web scraping."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                display_name = ""
                bio = ""

                # Instagram specific selectors
                name_element = soup.select_one('h2')
                if name_element:
                    display_name = name_element.get_text().strip()

                bio_element = soup.select_one('h1 + div')
                if bio_element:
                    bio = bio_element.get_text().strip()

                return SocialMediaData(
                    platform="Instagram",
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={}
                )

        except Exception as e:
            logger.error("Instagram fallback fetch error: %s", e)

        return None

class FacebookFetcher(BaseSocialMediaFetcher):
    """Facebook API fetcher."""

    def __init__(self):
        super().__init__()
        self.graph = None
        self._initialize_api()

    def _initialize_api(self):
        """Initialize Facebook Graph API."""
        try:
            access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
            app_id = os.getenv('FACEBOOK_APP_ID')
            app_secret = os.getenv('FACEBOOK_APP_SECRET')

            if access_token:
                try:
                    import facebook
                    self.graph = facebook.GraphAPI(access_token=access_token)
                except ImportError:
                    logger.warning("facebook-sdk not installed, Facebook API unavailable")
            elif app_id and app_secret:
                try:
                    import facebook
                    self.graph = facebook.GraphAPI()
                    # Note: This requires user authentication flow
                except ImportError:
                    logger.warning("facebook-sdk not installed, Facebook API unavailable")
            else:
                logger.warning("Facebook API credentials not found")
        except Exception as e:
            logger.error("Failed to initialize Facebook API: %s", e)

    def can_handle_url(self, url: str) -> bool:
        return 'facebook.com' in url

    def extract_username_from_url(self, url: str) -> str:
        """Extract username from Facebook URL."""
        path = urlparse(url).path
        username = path.strip('/').split('/')[0]
        return username

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch Facebook profile data."""
        if not self.graph:
            return self._fallback_fetch(url)

        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)

            # Facebook Graph API requires specific permissions
            profile = self.graph.get_object(
                username,
                fields='name,about,bio,website,location,verified'
            )

            return SocialMediaData(
                platform="Facebook",
                username=username,
                display_name=profile.get('name', ''),
                bio=profile.get('about', '') or profile.get('bio', ''),
                posts=[],
                followers_count=None,
                following_count=None,
                profile_picture=None,
                verified=profile.get('verified', False),
                join_date=None,
                location=profile.get('location', {}).get('name') if profile.get('location') else None,
                website=profile.get('website'),
                raw_data=profile
            )

        except Exception as e:
            logger.error("Facebook API error: %s", e)
            return self._fallback_fetch(url)

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Fallback to web scraping."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                display_name = ""
                bio = ""

                # Facebook specific selectors
                name_element = soup.select_one('h1')
                if name_element:
                    display_name = name_element.get_text().strip()

                bio_element = soup.select_one('[data-testid="profile_bio"]')
                if bio_element:
                    bio = bio_element.get_text().strip()

                return SocialMediaData(
                    platform="Facebook",
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={}
                )

        except Exception as e:
            logger.error("Facebook fallback fetch error: %s", e)

        return None

class RedditFetcher(BaseSocialMediaFetcher):
    """Reddit API fetcher using PRAW."""

    def __init__(self):
        super().__init__()
        self.reddit = None
        self._initialize_api()

    def _initialize_api(self):
        """Initialize Reddit API client."""
        try:
            client_id = os.getenv('REDDIT_CLIENT_ID')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET')
            user_agent = os.getenv('REDDIT_USER_AGENT', 'SocialNetworkAnalyzer/1.0')

            if client_id and client_secret:
                try:
                    import praw
                    self.reddit = praw.Reddit(
                        client_id=client_id,
                        client_secret=client_secret,
                        user_agent=user_agent
                    )
                except ImportError:
                    logger.warning("praw not installed, Reddit API unavailable")
            else:
                logger.warning("Reddit API credentials not found")
        except Exception as e:
            logger.error("Failed to initialize Reddit API: %s", e)

    def can_handle_url(self, url: str) -> bool:
        return 'reddit.com' in url

    def extract_username_from_url(self, url: str) -> str:
        """Extract username from Reddit URL."""
        path = urlparse(url).path
        if '/user/' in path:
            return path.split('/user/')[1].split('/')[0]
        if '/u/' in path:
            return path.split('/u/')[1].split('/')[0]
        return ""

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch Reddit profile data."""
        if not self.reddit:
            return self._fallback_fetch(url)

        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)

            redditor = self.reddit.redditor(username)

            # Get recent posts and comments
            posts = []
            for submission in redditor.submissions.new(limit=10):
                posts.append({
                    'title': submission.title,
                    'content': submission.selftext,
                    'subreddit': submission.subreddit.display_name,
                    'score': submission.score,
                    'date': submission.created_utc
                })

            return SocialMediaData(
                platform="Reddit",
                username=username,
                display_name=redditor.name,
                bio="",  # Reddit doesn't have bios
                posts=posts,
                followers_count=None,
                following_count=None,
                profile_picture=None,
                verified=False,
                join_date=redditor.created_utc,
                location=None,
                website=None,
                raw_data={
                    'comment_karma': redditor.comment_karma,
                    'link_karma': redditor.link_karma,
                    'is_gold': redditor.is_gold,
                    'is_mod': redditor.is_mod
                }
            )

        except Exception as e:
            logger.error("Reddit API error: %s", e)
            return self._fallback_fetch(url)

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Fallback to web scraping."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                display_name = ""

                # Reddit specific selectors
                name_element = soup.select_one('h1')
                if name_element:
                    display_name = name_element.get_text().strip()

                return SocialMediaData(
                    platform="Reddit",
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio="",
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={}
                )

        except Exception as e:
            logger.error("Reddit fallback fetch error: %s", e)

        return None

class GitHubFetcher(BaseSocialMediaFetcher):
    """GitHub REST API fetcher. Works without authentication for public profiles;
    set GITHUB_TOKEN for a higher rate limit (5,000 requests/hour vs 60/hour)."""

    def __init__(self):
        super().__init__()
        token = os.getenv('GITHUB_TOKEN')
        if token:
            self.session.headers.update({'Authorization': f'token {token}'})
        self.session.headers.update({'Accept': 'application/vnd.github+json'})

    def can_handle_url(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return netloc == 'github.com' or netloc.endswith('.github.com')

    def extract_username_from_url(self, url: str) -> str:
        """Extract GitHub username from URL."""
        path = urlparse(url).path
        parts = path.strip('/').split('/')
        return parts[0] if parts else ''

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch GitHub profile via the public REST API."""
        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)

            response = self.session.get(
                f'https://api.github.com/users/{username}',
                timeout=10
            )

            if response.status_code != 200:
                logger.warning("GitHub API returned %s for %s", response.status_code, username)
                return None

            profile = response.json()

            # Fetch the 5 most-recently-updated public repos as "posts"
            repos_response = self.session.get(
                f'https://api.github.com/users/{username}/repos',
                params={'sort': 'updated', 'per_page': 5},
                timeout=10
            )
            posts = []
            if repos_response.status_code == 200:
                for repo in repos_response.json():
                    posts.append({
                        'title': repo['name'],
                        'caption': repo.get('description') or '',
                        'stars': repo.get('stargazers_count', 0),
                        'language': repo.get('language') or '',
                        'url': repo.get('html_url', ''),
                    })

            return SocialMediaData(
                platform="GitHub",
                username=username,
                display_name=profile.get('name') or username,
                bio=profile.get('bio') or '',
                posts=posts,
                followers_count=profile.get('followers'),
                following_count=profile.get('following'),
                profile_picture=profile.get('avatar_url'),
                verified=False,
                join_date=profile.get('created_at'),
                location=profile.get('location'),
                website=profile.get('blog') or profile.get('html_url'),
                raw_data=profile,
            )

        except Exception as e:
            logger.error("GitHub API error: %s", e)
            return None


class YouTubeFetcher(BaseSocialMediaFetcher):
    """YouTube Data API v3 fetcher.
    Requires YOUTUBE_API_KEY environment variable; falls back to meta-tag scraping."""

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('YOUTUBE_API_KEY')

    def can_handle_url(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return netloc in ('youtube.com', 'youtu.be') or netloc.endswith('.youtube.com')

    def extract_username_from_url(self, url: str) -> str:
        """Extract channel handle or name from a YouTube URL."""
        path = urlparse(url).path
        parts = path.strip('/').split('/')
        if parts and parts[0].startswith('@'):
            return parts[0][1:]   # strip leading @
        if len(parts) >= 2 and parts[0] in ('c', 'user', 'channel'):
            return parts[1]
        return parts[0] if parts else ''

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch YouTube channel data using the Data API v3."""
        if not self.api_key:
            logger.warning("YOUTUBE_API_KEY not set; using fallback scraping")
            return self._fallback_fetch(url)

        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)
            channel = self._lookup_channel(username)
            if channel is None:
                return self._fallback_fetch(url)

            snippet = channel.get('snippet', {})
            statistics = channel.get('statistics', {})

            subscriber_count = None
            raw_sub = statistics.get('subscriberCount')
            if raw_sub is not None:
                try:
                    subscriber_count = int(raw_sub)
                except (ValueError, TypeError):
                    pass

            return SocialMediaData(
                platform="YouTube",
                username=username,
                display_name=snippet.get('title', ''),
                bio=snippet.get('description', ''),
                posts=[],
                followers_count=subscriber_count,
                following_count=None,
                profile_picture=(
                    snippet.get('thumbnails', {}).get('high', {}).get('url')
                ),
                verified=False,
                join_date=snippet.get('publishedAt'),
                location=snippet.get('country'),
                website=snippet.get('customUrl'),
                raw_data=channel,
            )

        except Exception as e:
            logger.error("YouTube API error: %s", e)
            return self._fallback_fetch(url)

    def _lookup_channel(self, username: str) -> Optional[dict]:
        """Resolve a YouTube channel by handle/name and return its API object."""
        search_resp = self.session.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={
                'key': self.api_key,
                'q': username,
                'type': 'channel',
                'part': 'snippet',
                'maxResults': 1,
            },
            timeout=10,
        )
        if search_resp.status_code != 200:
            return None
        items = search_resp.json().get('items', [])
        if not items:
            return None
        channel_id = items[0]['snippet']['channelId']

        channel_resp = self.session.get(
            'https://www.googleapis.com/youtube/v3/channels',
            params={
                'key': self.api_key,
                'id': channel_id,
                'part': 'snippet,statistics',
            },
            timeout=10,
        )
        if channel_resp.status_code != 200:
            return None
        channels = channel_resp.json().get('items', [])
        return channels[0] if channels else None

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Fallback to Open Graph meta-tag scraping."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                display_name = ''
                bio = ''

                og_title = soup.find('meta', {'property': 'og:title'})
                if og_title:
                    display_name = og_title.get('content', '')

                og_desc = soup.find('meta', {'property': 'og:description'})
                if og_desc:
                    bio = og_desc.get('content', '')

                return SocialMediaData(
                    platform="YouTube",
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={},
                )

        except Exception as e:
            logger.error("YouTube fallback fetch error: %s", e)

        return None


class TikTokFetcher(BaseSocialMediaFetcher):
    """TikTok data fetcher.
    TikTok has no publicly accessible API, so this fetcher relies on Open
    Graph meta-tag scraping from the profile page."""

    def can_handle_url(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return netloc == 'tiktok.com' or netloc.endswith('.tiktok.com')

    def extract_username_from_url(self, url: str) -> str:
        """Extract TikTok username from URL (handles /@username paths)."""
        path = urlparse(url).path
        parts = path.strip('/').split('/')
        if parts and parts[0].startswith('@'):
            return parts[0][1:]   # strip leading @
        return parts[0] if parts else ''

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch TikTok profile data via web scraping."""
        return self._fallback_fetch(url)

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Web-scraping implementation for TikTok profile pages."""
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            }
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                display_name = ''
                bio = ''

                og_title = soup.find('meta', {'property': 'og:title'})
                if og_title:
                    display_name = og_title.get('content', '')

                og_desc = soup.find('meta', {'property': 'og:description'})
                if og_desc:
                    bio = og_desc.get('content', '')

                og_image = soup.find('meta', {'property': 'og:image'})
                profile_picture = og_image.get('content') if og_image else None

                username = self.extract_username_from_url(url)

                return SocialMediaData(
                    platform="TikTok",
                    username=username,
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=profile_picture,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={},
                )

        except Exception as e:
            logger.error("TikTok fetch error: %s", e)

        return None


class TumblrFetcher(BaseSocialMediaFetcher):
    """Tumblr API fetcher.
    Uses the public Tumblr API v2; set TUMBLR_API_KEY for authenticated requests.
    Falls back to Open Graph meta-tag scraping when no key is available."""

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('TUMBLR_API_KEY')

    def can_handle_url(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return netloc == 'tumblr.com' or netloc.endswith('.tumblr.com')

    def extract_username_from_url(self, url: str) -> str:
        """Extract blog name from a Tumblr URL.

        Handles both https://username.tumblr.com and
        https://www.tumblr.com/username formats.
        """
        parsed = urlparse(url)
        hostname = parsed.netloc
        # username.tumblr.com
        if hostname.endswith('.tumblr.com') and not hostname.startswith('www.'):
            return hostname.replace('.tumblr.com', '')
        # www.tumblr.com/username
        path = parsed.path
        parts = path.strip('/').split('/')
        return parts[0] if parts else ''

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch Tumblr blog data using the Tumblr API v2."""
        if not self.api_key:
            logger.warning("TUMBLR_API_KEY not set; using fallback scraping")
            return self._fallback_fetch(url)

        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)
            blog_name = f"{username}.tumblr.com"

            # Fetch blog info
            info_resp = self.session.get(
                f'https://api.tumblr.com/v2/blog/{blog_name}/info',
                params={'api_key': self.api_key},
                timeout=10,
            )

            if info_resp.status_code != 200:
                return self._fallback_fetch(url)

            blog_data = info_resp.json().get('response', {}).get('blog', {})

            # Fetch 5 most recent posts
            posts_resp = self.session.get(
                f'https://api.tumblr.com/v2/blog/{blog_name}/posts',
                params={'api_key': self.api_key, 'limit': 5},
                timeout=10,
            )
            posts = []
            if posts_resp.status_code == 200:
                for post in posts_resp.json().get('response', {}).get('posts', []):
                    posts.append({
                        'title': post.get('title') or post.get('type', ''),
                        'caption': (
                            post.get('body')
                            or post.get('caption')
                            or post.get('text')
                            or ''
                        ),
                        'tags': post.get('tags', []),
                        'date': post.get('date'),
                    })

            avatar = blog_data.get('avatar', [])
            profile_picture = avatar[0].get('url') if avatar else None

            return SocialMediaData(
                platform="Tumblr",
                username=username,
                display_name=blog_data.get('title', ''),
                bio=blog_data.get('description', ''),
                posts=posts,
                followers_count=blog_data.get('followers'),
                following_count=None,
                profile_picture=profile_picture,
                verified=False,
                join_date=None,
                location=None,
                website=blog_data.get('url'),
                raw_data=blog_data,
            )

        except Exception as e:
            logger.error("Tumblr API error: %s", e)
            return self._fallback_fetch(url)

    def _fallback_fetch(self, url: str) -> Optional[SocialMediaData]:
        """Fallback to Open Graph meta-tag scraping."""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                display_name = ''
                bio = ''

                og_title = soup.find('meta', {'property': 'og:title'})
                if og_title:
                    display_name = og_title.get('content', '')

                og_desc = soup.find('meta', {'property': 'og:description'})
                if og_desc:
                    bio = og_desc.get('content', '')

                return SocialMediaData(
                    platform="Tumblr",
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={},
                )

        except Exception as e:
            logger.error("Tumblr fallback fetch error: %s", e)

        return None


class GenericFetcher(BaseSocialMediaFetcher):
    """Generic fetcher for platforms without specific API support."""

    def can_handle_url(self, url: str) -> bool:
        return True  # Handles any URL

    def extract_username_from_url(self, url: str) -> str:
        """Extract username from generic URL."""
        path = urlparse(url).path
        return path.strip('/').split('/')[0] if path.strip('/') else ""

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Generic web scraping fallback."""
        try:
            self._handle_rate_limit()

            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Try to extract basic information
                display_name = ""
                bio = ""

                # Common selectors for profile information
                name_selectors = ['h1', 'h2', '.profile-name', '.username', '.display-name']
                bio_selectors = ['.bio', '.description', '.about', '.profile-bio']

                for selector in name_selectors:
                    element = soup.select_one(selector)
                    if element:
                        display_name = element.get_text().strip()
                        break

                for selector in bio_selectors:
                    element = soup.select_one(selector)
                    if element:
                        bio = element.get_text().strip()
                        break

                platform = self._detect_platform(url)

                return SocialMediaData(
                    platform=platform,
                    username=self.extract_username_from_url(url),
                    display_name=display_name,
                    bio=bio,
                    posts=[],
                    followers_count=None,
                    following_count=None,
                    profile_picture=None,
                    verified=False,
                    join_date=None,
                    location=None,
                    website=None,
                    raw_data={}
                )

        except Exception as e:
            logger.error("Generic fetch error: %s", e)

        return None

    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL."""
        domain = urlparse(url).netloc.lower()

        platform_map = {
            'youtube.com': 'YouTube',
            'github.com': 'GitHub',
            'medium.com': 'Medium',
            'tumblr.com': 'Tumblr',
            'pinterest.com': 'Pinterest',
            'tiktok.com': 'TikTok',
            'snapchat.com': 'Snapchat',
            'twitch.tv': 'Twitch',
            'soundcloud.com': 'SoundCloud',
            'spotify.com': 'Spotify',
        }

        for domain_part, platform in platform_map.items():
            if domain_part in domain:
                return platform

        return 'Unknown'

class SocialMediaFetcherManager:
    """Manager class to handle multiple social media fetchers."""

    def __init__(self):
        self.fetchers = [
            TwitterFetcher(),
            LinkedInFetcher(),
            InstagramFetcher(),
            FacebookFetcher(),
            RedditFetcher(),
            GitHubFetcher(),
            YouTubeFetcher(),
            TikTokFetcher(),
            TumblrFetcher(),
            GenericFetcher(),
        ]

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch profile data using the appropriate fetcher."""
        for fetcher in self.fetchers:
            if fetcher.can_handle_url(url):
                logger.info("Using %s for %s", fetcher.__class__.__name__, url)
                return fetcher.fetch_profile_data(url)

        logger.warning("No fetcher found for URL: %s", url)
        return None

    def get_supported_platforms(self) -> List[str]:
        """Get list of supported platforms."""
        platforms = []
        for fetcher in self.fetchers:
            if hasattr(fetcher, 'platform_name'):
                platforms.append(fetcher.platform_name)
        return platforms

# Global instance
fetcher_manager = SocialMediaFetcherManager()

def fetch_social_media_data(url: str) -> Optional[SocialMediaData]:
    """Convenience function to fetch social media data."""
    return fetcher_manager.fetch_profile_data(url)

def format_social_media_data(data: SocialMediaData) -> str:
    """Format social media data for analysis."""
    if not data:
        return "No data available"

    formatted = f"""
Platform: {data.platform}
Username: {data.username}
Display Name: {data.display_name}
Bio: {data.bio}
Followers: {data.followers_count or 'Unknown'}
Following: {data.following_count or 'Unknown'}
Verified: {data.verified}
Location: {data.location or 'Unknown'}
Website: {data.website or 'Unknown'}
Join Date: {data.join_date or 'Unknown'}
"""

    if data.posts:
        formatted += "\nRecent Posts:\n"
        for i, post in enumerate(data.posts[:5], 1):  # Limit to 5 posts
            formatted += f"{i}. {post.get('caption', post.get('title', ''))[:200]}...\n"

    return formatted
