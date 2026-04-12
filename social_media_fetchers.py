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
from dotenv import load_dotenv

# Optional dependency – imported at module level to avoid repeated per-call overhead.
try:
    import tweepy
except ImportError:  # pragma: no cover
    tweepy = None  # type: ignore[assignment]

# Load environment variables from .env file if present
load_dotenv()

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
                logger.info(f"Rate limit reached, waiting {sleep_time:.2f} seconds")
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
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SocialNetworkAnalyzer/1.0)'
        })
        return session

    def _url_matches_domain(self, url: str, *domains: str) -> bool:
        """Return True if the URL's netloc matches any of the given domains (or a subdomain)."""
        netloc = urlparse(url).netloc.lower()
        # Strip port if present
        netloc = netloc.split(':')[0]
        return any(netloc == d or netloc.endswith('.' + d) for d in domains)

    @abstractmethod
    def can_handle_url(self, url: str) -> bool:
        """Check if this fetcher can handle the given URL."""
        pass

    @abstractmethod
    def extract_username_from_url(self, url: str) -> str:
        """Extract username from URL."""
        pass

    @abstractmethod
    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch profile data from the given URL."""
        pass

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
        if tweepy is None:
            logger.warning("tweepy not installed, Twitter API unavailable")
            return
        try:
            # Twitter API v2 credentials
            bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
            api_key = os.getenv('TWITTER_API_KEY')
            api_secret = os.getenv('TWITTER_API_SECRET')
            access_token = os.getenv('TWITTER_ACCESS_TOKEN')
            access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

            if bearer_token:
                self.api = tweepy.Client(bearer_token=bearer_token)
            elif all([api_key, api_secret, access_token, access_token_secret]):
                auth = tweepy.OAuthHandler(api_key, api_secret)
                auth.set_access_token(access_token, access_token_secret)
                self.api = tweepy.API(auth)
            else:
                logger.warning("Twitter API credentials not found")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to initialize Twitter API: %s", e)

    def can_handle_url(self, url: str) -> bool:
        return self._url_matches_domain(url, 'twitter.com', 'x.com')

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

            # Distinguish between API v2 (tweepy.Client) and v1.1 (tweepy.API)
            if tweepy and isinstance(self.api, tweepy.Client):
                user = self.api.get_user(
                    username=username,
                    user_fields=[
                        'description', 'public_metrics', 'profile_image_url',
                        'verified', 'location', 'url', 'created_at'
                    ]
                )
                if user.data:
                    return self._parse_twitter_user(user.data, username)
            elif tweepy and isinstance(self.api, tweepy.API):
                user = self.api.get_user(screen_name=username)
                return self._parse_twitter_user_v1(user, username)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Twitter API error: %s", e)
            return self._fallback_fetch(url)

        return self._fallback_fetch(url)

    def _parse_twitter_user(self, user, username: str) -> SocialMediaData:
        """Parse Twitter API v2 user data."""
        public_metrics = user.public_metrics or {}
        return SocialMediaData(
            platform="Twitter",
            username=username,
            display_name=user.name,
            bio=user.description or "",
            posts=[],  # Would need separate API call for tweets
            followers_count=public_metrics.get('followers_count'),
            following_count=public_metrics.get('following_count'),
            profile_picture=user.profile_image_url,
            verified=user.verified or False,
            join_date=user.created_at.isoformat() if user.created_at else None,
            location=user.location,
            website=user.url,
            raw_data={
                'name': user.name,
                'description': user.description,
                'location': user.location,
                'url': user.url,
                'public_metrics': dict(public_metrics),
            }
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
            raw_data=user._json if hasattr(user, '_json') else {}
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
            logger.error(f"Twitter fallback fetch error: {e}")

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
            logger.error(f"Failed to initialize LinkedIn API: {e}")

    def can_handle_url(self, url: str) -> bool:
        return self._url_matches_domain(url, 'linkedin.com')

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
            logger.error(f"LinkedIn API error: {e}")
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
            logger.error(f"LinkedIn fallback fetch error: {e}")

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
            logger.error(f"Failed to initialize Instagram loader: {e}")

    def can_handle_url(self, url: str) -> bool:
        return self._url_matches_domain(url, 'instagram.com')

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
            logger.error(f"Instagram API error: {e}")
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
            logger.error(f"Instagram fallback fetch error: {e}")

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
            logger.error(f"Failed to initialize Facebook API: {e}")

    def can_handle_url(self, url: str) -> bool:
        return self._url_matches_domain(url, 'facebook.com')

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
                location=(
                    profile['location'].get('name') if profile.get('location') else None
                ),
                website=profile.get('website'),
                raw_data=profile
            )

        except Exception as e:
            logger.error(f"Facebook API error: {e}")
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
            logger.error(f"Facebook fallback fetch error: {e}")

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
            logger.error(f"Failed to initialize Reddit API: {e}")

    def can_handle_url(self, url: str) -> bool:
        return self._url_matches_domain(url, 'reddit.com')

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
            logger.error(f"Reddit API error: {e}")
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
            logger.error(f"Reddit fallback fetch error: {e}")

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
            logger.error(f"Generic fetch error: {e}")

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

class GitHubFetcher(BaseSocialMediaFetcher):
    """GitHub API fetcher using the public REST API."""

    def __init__(self):
        super().__init__()
        # Optional: provide a GITHUB_TOKEN to raise the rate limit from
        # 60 requests/hour (unauthenticated) to 5,000 requests/hour (per
        # authenticated user).
        token = os.getenv('GITHUB_TOKEN')
        if token:
            self.session.headers.update({'Authorization': f'Bearer {token}'})
        self.session.headers.update({'Accept': 'application/vnd.github.v3+json'})

    def can_handle_url(self, url: str) -> bool:
        return self._url_matches_domain(url, 'github.com')

    def extract_username_from_url(self, url: str) -> str:
        """Extract username from GitHub URL."""
        path = urlparse(url).path
        parts = path.strip('/').split('/')
        return parts[0] if parts else ""

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch GitHub profile data via the public REST API."""
        try:
            self._handle_rate_limit()
            username = self.extract_username_from_url(url)
            if not username:
                return None

            api_url = f"https://api.github.com/users/{username}"
            response = self.session.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return SocialMediaData(
                    platform="GitHub",
                    username=username,
                    display_name=data.get('name') or username,
                    bio=data.get('bio') or "",
                    posts=[],
                    followers_count=data.get('followers'),
                    following_count=data.get('following'),
                    profile_picture=data.get('avatar_url'),
                    verified=False,
                    join_date=data.get('created_at'),
                    location=data.get('location'),
                    website=data.get('blog') or None,
                    raw_data=data
                )
            logger.warning("GitHub API returned %s for %s", response.status_code, url)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("GitHub API error: %s", e)

        return None


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
            GenericFetcher()
        ]

    def fetch_profile_data(self, url: str) -> Optional[SocialMediaData]:
        """Fetch profile data using the appropriate fetcher."""
        for fetcher in self.fetchers:
            if fetcher.can_handle_url(url):
                logger.info(f"Using {fetcher.__class__.__name__} for {url}")
                return fetcher.fetch_profile_data(url)

        logger.warning(f"No fetcher found for URL: {url}")
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
