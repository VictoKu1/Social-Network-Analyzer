"""
Module for analyzing social media links using OpenAI API.
This version uses platform-specific API integration for better data fetching.
"""

import os
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
from social_media_fetchers import fetch_social_media_data, format_social_media_data

# Load environment variables from .env file if present
load_dotenv()


def _get_client() -> OpenAI:
    """Create and return an OpenAI client using the current environment."""
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

# List of parameters for numerical evaluation
parameters = [
    "Reliability",
    "Integrity",
    "Sense of Humor",
    "Adaptability",
    "Empathy",
    "Creativity",
    "Emotional Intelligence",
    "Resilience",
    "Patience",
    "Charisma",
    "Communication Skills",
    "Conflict Resolution",
    "Teamwork",
    "Trustworthiness",
    "Learning Ability",
    "Critical Thinking",
    "Problem-Solving Skills",
    "Attention to Detail",
    "Memory Retention",
    "Practical Intelligence",
    "Intellectual Curiosity",
    "Emotional Stability",
    "Optimism",
    "Sensitivity",
    "Self-Awareness",
    "Self-Esteem",
    "Emotional Dysregulation",
    "Social Awareness",
    "Openness to Feedback",
    "Cultural Awareness",
    "Friendship Potential",
    "Boundary Respect",
    "Leadership Ability",
    "Innovation",
    "Strategic Thinking",
    "Work-Life Balance",
    "Resourcefulness",
    "Time Management",
    "Professional Ethics",
    "Risk-Taking Behavior",
    "Impulsivity",
    "Self-Motivation",
    "Decision-Making Speed",
    "Reward Sensitivity",
    "Fantasy-Prone Thinking",
    "Paranoia",
    "Reality Distortion",
    "Mood Variability",
    "Resilience to Failure",
    "Self-Criticism",
    "Stress Coping Mechanisms",
    "Social Influence",
    "Genetic Predisposition",
    "Parental Involvement",
    "Parenting Style",
    "Emotional Support",
    "Discipline Style",
    "Attachment Style",
    "Self-Identification",
    "Self-Expression",
    "Behavioral Expression",
    "Fluidity",
    "Humility",
    "Independence",
    "Curiosity",
    "Forgiveness",
    "Egoism",
    "Procrastination",
    "Dishonesty",
    "Overreaction",
]

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

def fetch_social_media_content(url: str) -> str:
    """
    DEPRECATED: Use fetch_social_media_data from social_media_fetchers instead.
    This function is kept for backward compatibility but will be removed in future versions.
    """
    # Use the new platform-specific fetcher
    data = fetch_social_media_data(url)
    if data:
        return format_social_media_data(data)
    return f"Failed to fetch content from {url}"

def analyze_personality(links_info, personal_description):
    """
    Combines data fetched from user-provided links with the personal description,
    then sends it to the OpenAI API for personality analysis.
    Uses platform-specific API integration for better data extraction.
    """
    if not links_info and not personal_description:
        return "No data provided for analysis."

    # Fetch and combine content from each social media link using platform-specific fetchers
    combined_text = "Fetched Social Media Data:\n"
    for link_data in links_info:
        url = link_data.get('url')
        platform = link_data.get('platform')
        combined_text += f"\n---\nPlatform: {platform}\nURL: {url}\n"

        # Use the new platform-specific fetcher
        data = fetch_social_media_data(url)
        if data:
            content = format_social_media_data(data)
        else:
            content = f"Failed to fetch content from {url}"

        combined_text += f"Extracted Content:\n{content}\n"

    combined_text += "\nUser Provided Personal Description:\n" + personal_description + "\n"

    # Build the prompt for OpenAI
    prompt = f"""
You are an AI that analyzes a person's social media presence and personal description
to provide a concise "personality" summary. Here is the provided data:

{combined_text}

Please provide:
1. Overall tone or impression.
2. Possible personality traits (Big Five or a similar framework).
3. Possible likes, dislikes, or interests.
4. Warning signs or red flags.
5. Any other relevant insights.

After generating the above text, please provide a (0-100)
evaluation for each of the following parameters with 1 line explanation
and return it as a table:
{', '.join(parameters)}
    """

    disclaimer = """

**Disclaimer**: This analysis is based on limited publicly available information
and is a broad characterization rather than a definitive assessment of personality.
It should not be considered professional mental health advice.
    """
    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o",  # Replace with your actual model if needed.
            messages=[
                {"role": "system", "content": "You are a helpful AI ..."},
                {"role": "user", "content": prompt},
            ],
            # You can adjust max_tokens, temperature, etc. as needed.
        )
        result = response.choices[0].message.content + disclaimer
        return result
    except OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return f"OpenAI API Error: {e}"
