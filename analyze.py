"""
Module for analyzing social media links using OpenAI or local Ollama.
This version uses platform-specific API integration for better data fetching.
"""

from openai import OpenAI, OpenAIError, AuthenticationError
from dotenv import load_dotenv
from social_media_fetchers import fetch_social_media_data, format_social_media_data
from llm_providers import (
    LLMError, create_client, resolve_provider, resolve_model, generate_ollama_completion,
)
from safe_fetch import SOCIAL_DOMAINS, parse_profile_url
from security_limits import (
    MAX_COMPLETION_TOKENS, SecurityError, validate_links_list,
    validate_description, check_prompt_budget,
)

# Load environment variables from .env file if present
load_dotenv()


def _get_client(provider="openai") -> OpenAI:
    """Create a client for the explicitly selected inference destination."""
    return create_client(provider)

# List of social media domains and their names
domains = SOCIAL_DOMAINS

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
    try:
        return True, parse_profile_url(link)[3]
    except SecurityError:
        return False, None

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

# Keep validation, aggregation and provider cleanup in one visible analysis boundary.
def analyze_personality(links_info, personal_description, provider=None, model=None):  # pylint: disable=too-many-locals
    """
    Combines data fetched from user-provided links with the personal description,
    then sends it to the selected provider for personality analysis.
    Uses platform-specific API integration for better data extraction.
    """
    validate_description(personal_description)
    if not isinstance(links_info, list) or any(not isinstance(item, dict) for item in links_info):
        raise SecurityError("invalid_links", "Provide a list of profile links.")
    urls = validate_links_list([item.get("url") for item in links_info])
    profiles = [parse_profile_url(url) for url in urls]
    # Check credentials/model readiness before any external social-profile fetching.
    provider = resolve_provider(provider)
    model = resolve_model(provider, model)
    if not links_info and not personal_description:
        return "No data provided for analysis."

    # Fetch and combine content from each social media link using platform-specific fetchers
    combined_text = "Fetched Social Media Data:\n"
    for url, _host, _port, platform in profiles:
        combined_text += f"\n---\nPlatform: {platform}\nURL: {url}\n"

        # Use the new platform-specific fetcher
        data = fetch_social_media_data(url)
        if data:
            content = format_social_media_data(data)
        else:
            content = f"Failed to fetch content from {url}"

        combined_text += f"Extracted Content:\n{content}\n"
        check_prompt_budget(combined_text)

    combined_text += "\nUser Provided Personal Description:\n" + personal_description + "\n"

    # Build the prompt for the selected model.
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
    check_prompt_budget(prompt)

    disclaimer = """

**Disclaimer**: This analysis is based on limited publicly available information
and is a broad characterization rather than a definitive assessment of personality.
It should not be considered professional mental health advice.
    """
    messages = [
        {"role": "system", "content": "You are a helpful AI ..."},
        {"role": "user", "content": prompt},
    ]
    if provider == "ollama":
        return generate_ollama_completion(model, messages) + disclaimer

    client = _get_client(provider)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )
        content = response.choices[0].message.content if response.choices else None
        if not isinstance(content, str) or not content.strip():
            raise LLMError("analysis_failed", "The model returned no analysis. Please try again.", 502)
        return content + disclaimer
    except AuthenticationError as exc:
        message = (
            "OpenAI rejected the configured API key. Update OPENAI_API_KEY on the "
            "server, restart this app, or choose Ollama."
        )
        raise LLMError("openai_auth_error", message, 502) from exc
    except (OpenAIError, AttributeError, TypeError) as exc:
        raise LLMError(
            "analysis_failed",
            "OpenAI couldn't complete the analysis. Check the service and try again.",
            502,
        ) from exc
    finally:
        client.close()
