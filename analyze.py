"""
Module for analyzing social media links using OpenAI API.
"""

import os
from openai import OpenAI, OpenAIError
import snscrape.modules.twitter as sntwitter
import snscrape.modules.instagram as sninstagram
import snscrape.modules.facebook as snfacebook
import snscrape.modules.threads as snthreads
from bs4 import BeautifulSoup
import requests

# OpenAI API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY"))

# List of social media domains and their names
domains = {
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "twitter.com": "Twitter",
    "x.com": "X",
    "threads.net": "Threads",
    "linkedin.com": "LinkedIn",
    "pinterest.com": "Pinterest",
    "snapchat.com": "Snapchat",
    "tiktok.com": "TikTok",
    "youtube.com": "YouTube",
    "reddit.com": "Reddit",
    "tumblr.com": "Tumblr",
    "github.com": "GitHub",
    "stackoverflow.com": "Stack Overflow",
    "medium.com": "Medium",
    "wordpress.com": "WordPress",
    "blogger.com": "Blogger",
    "twitch.tv": "Twitch",
    "soundcloud.com": "SoundCloud",
    "spotify.com": "Spotify",
    "apple.com": "Apple",
    "amazon.com": "Amazon",
    "ebay.com": "eBay",
    "etsy.com": "Etsy",
    "patreon.com": "Patreon",
}


def validate_social_link(link: str):
    """
    Check if a link is a recognized social network.
    Returns (is_valid, platform_name).
    """
    if not (link.startswith("http://") or link.startswith("https://")):
        return (False, None)

    for domain, name in domains.items():
        if domain in link:
            return (True, name)
    return (False, None)


def gather_twitter_data(username):
    tweets = []
    for tweet in sntwitter.TwitterUserScraper(username).get_items():
        tweets.append(tweet.content)
        if len(tweets) == 10:  # Limit to 10 tweets
            break
    return tweets


def gather_instagram_data(username):
    posts = []
    for post in sninstagram.InstagramUserScraper(username).get_items():
        posts.append(post.content)
        if len(posts) == 10:  # Limit to 10 posts
            break
    return posts


def gather_facebook_data(username):
    posts = []
    for post in snfacebook.FacebookUserScraper(username).get_items():
        posts.append(post.content)
        if len(posts) == 10:  # Limit to 10 posts
            break
    return posts


def gather_threads_data(username):
    posts = []
    for post in snthreads.ThreadsUserScraper(username).get_items():
        posts.append(post.content)
        if len(posts) == 10:  # Limit to 10 posts
            break
    return posts


def gather_data_from_user_pages(links_info):
    gathered_data = {}
    for link_data in links_info:
        platform = link_data["platform"]
        url = link_data["url"]
        username = url.split("/")[-1]

        if platform == "Twitter":
            gathered_data[platform] = gather_twitter_data(username)
        elif platform == "Instagram":
            gathered_data[platform] = gather_instagram_data(username)
        elif platform == "Facebook":
            gathered_data[platform] = gather_facebook_data(username)
        elif platform == "Threads":
            gathered_data[platform] = gather_threads_data(username)
        # Add more platforms as needed

    return gathered_data


def analyze_personality(links_info, personal_description):
    """
    Combine link data + personal description into a prompt,
    then call OpenAI for a personality-like analysis.

    links_info: list of dict, each with {"url": <str>, "platform": <str>}
    personal_description: str
    """
    if not links_info and not personal_description:
        return "No data provided for analysis."

    # Gather data from user pages
    gathered_data = gather_data_from_user_pages(links_info)

    # Construct a simple text prompt (placeholder)
    combined_text = "User Provided Links:\n"
    for link_data in links_info:
        combined_text += f" - {link_data['url']} ({link_data['platform']})\n"

    combined_text += f"\nPersonal Description:\n{personal_description}\n"

    # Include gathered data in the prompt
    combined_text += "\nGathered Data:\n"
    for platform, data in gathered_data.items():
        combined_text += f"\n{platform}:\n"
        for item in data:
            combined_text += f" - {item}\n"

    prompt = f"""
    You are an AI that analyzes a person's social network platforms and personal description 
    to provide a concise "personality" summary. 
    Here is the provided data:

    {combined_text}

    Please give:
    1. Overall tone or impression.
    2. Possible personality traits (Big Five or a similar framework).
    3. Possible likes, dislikes, or interests.
    4. Warning signs or red flags.
    5. Any other relevant insights.
    """
    disclamer = """
    \n\n **Disclamer**: This analysis is based on limited publicly available 
    information and is a broad characterization rather than a definitive 
    assessment of personality. It is important to note that this 
    summary should not be considered professional mental health advice 
    or a diagnostic tool. Personality is complex and multifaceted, 
    often requiring in-depth and personal assessment for accuracy.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful AI ..."},
                {"role": "user", "content": prompt},
            ],
            # max_tokens=300,
            # temperature=0.7,
        )
        result = response.choices[0].message.content + disclamer
        return result
    # Should use specific exceptions not just Exception
    except OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return f"OpenAI API Error: {e}"
