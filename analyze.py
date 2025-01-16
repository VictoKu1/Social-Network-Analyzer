"""
Module for analyzing social media links using OpenAI API.
"""

import os
from openai import OpenAI

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


def analyze_personality(links_info, personal_description):
    """
    Combine link data + personal description into a prompt,
    then call OpenAI for a personality-like analysis.

    links_info: list of dict, each with {"url": <str>, "platform": <str>}
    personal_description: str
    """
    if not links_info and not personal_description:
        return "No data provided for analysis."

    # Construct a simple text prompt (placeholder)
    # In a real app, you might fetch user posts from each link here.
    combined_text = "User Provided Links:\n"
    for link_data in links_info:
        combined_text += f" - {link_data['url']} ({link_data['platform']})\n"

    combined_text += f"\nPersonal Description:\n{personal_description}\n"

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
    #Should use specific exceptions not just Exception
    except OpenAI.error.AuthenticationError as e:
        print(f"OpenAI authentication error: {e}")
    except Exception as e:
        print(f"Error analyzing with OpenAI: {e}")
        return "Error analyzing with OpenAI. Check logs or API key."
