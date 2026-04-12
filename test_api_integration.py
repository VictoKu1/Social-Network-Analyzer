"""
Test script to demonstrate the new platform-specific social media API integration.
This script shows how to use the new fetchers and compare them with the old method.
"""

import os
import sys
from social_media_fetchers import fetch_social_media_data, format_social_media_data, SocialMediaFetcherManager
from analyze import fetch_social_media_content

def test_platform_specific_fetching():
    """Test the new platform-specific fetching system."""

    print("=== Social Media API Integration Test ===\n")

    # Test URLs for different platforms
    test_urls = [
        "https://twitter.com/elonmusk",
        "https://linkedin.com/in/williamhgates",
        "https://instagram.com/cristiano",
        "https://facebook.com/zuck",
        "https://reddit.com/user/spez",
        "https://github.com/torvalds",
        "https://youtube.com/@PewDiePie"
    ]

    manager = SocialMediaFetcherManager()

    for url in test_urls:
        print(f"Testing URL: {url}")
        print("-" * 50)

        # Test new platform-specific fetcher
        print("Using NEW platform-specific fetcher:")
        data = fetch_social_media_data(url)

        if data:
            print(f"✅ Success! Platform: {data.platform}")
            print(f"   Username: {data.username}")
            print(f"   Display Name: {data.display_name}")
            print(f"   Bio: {data.bio[:100]}..." if len(data.bio) > 100 else f"   Bio: {data.bio}")
            print(f"   Followers: {data.followers_count or 'Unknown'}")
            print(f"   Verified: {data.verified}")
        else:
            print("❌ Failed to fetch data")

        print()

        # Test old generic fetcher for comparison
        print("Using OLD generic fetcher:")
        try:
            old_content = fetch_social_media_content(url)
            if old_content and "Failed to fetch" not in old_content:
                print("✅ Success! (Generic method)")
                print(f"   Content length: {len(old_content)} characters")
            else:
                print("❌ Failed to fetch data (Generic method)")
        except Exception as e:
            print(f"❌ Error with generic method: {e}")

        print("\n" + "="*60 + "\n")

def test_rate_limiting():
    """Test rate limiting functionality."""

    print("=== Rate Limiting Test ===\n")

    from social_media_fetchers import RateLimiter

    # Test rate limiter
    limiter = RateLimiter(calls_per_minute=5)

    print("Testing rate limiter with 5 calls per minute...")
    for i in range(7):
        print(f"Call {i+1}: ", end="")
        limiter.wait_if_needed()
        print("✅ Proceeded")

    print("\nRate limiting test completed!")

def test_error_handling():
    """Test error handling and fallback mechanisms."""

    print("=== Error Handling Test ===\n")

    # Test with invalid URLs
    invalid_urls = [
        "https://invalid-domain-that-does-not-exist.com/user",
        "https://twitter.com/nonexistentuser123456789",
        "not-a-valid-url"
    ]

    for url in invalid_urls:
        print(f"Testing invalid URL: {url}")
        data = fetch_social_media_data(url)

        if data:
            print(f"✅ Unexpected success: {data.platform}")
        else:
            print("❌ Expected failure - handled gracefully")

        print()

def test_platform_detection():
    """Test platform detection functionality."""

    print("=== Platform Detection Test ===\n")

    manager = SocialMediaFetcherManager()

    test_urls = [
        "https://twitter.com/user",
        "https://x.com/user",
        "https://linkedin.com/in/user",
        "https://instagram.com/user",
        "https://facebook.com/user",
        "https://reddit.com/user/user",
        "https://youtube.com/user",
        "https://github.com/user",
        "https://medium.com/@user",
        "https://tiktok.com/@user"
    ]

    for url in test_urls:
        for fetcher in manager.fetchers:
            if fetcher.can_handle_url(url):
                print(f"URL: {url}")
                print(f"   Handled by: {fetcher.__class__.__name__}")
                print(f"   Extracted username: {fetcher.extract_username_from_url(url)}")
                break
        else:
            print(f"URL: {url} - No handler found")
        print()

def main():
    """Main test function."""

    print("Social Media API Integration Test Suite")
    print("=" * 50)

    # Check if required environment variables are set
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {missing_vars}")
        print("Some features may not work without proper API credentials.")
        print("See config_example.py for setup instructions.\n")

    try:
        # Run tests
        test_platform_detection()
        test_rate_limiting()
        test_error_handling()
        test_platform_specific_fetching()

        print("✅ All tests completed!")

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()