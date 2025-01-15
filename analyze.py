import os
import re
import openai

# Set the OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

def validate_social_link(link: str):
    """
    Check if a link is a recognized social network.
    Returns (is_valid, platform_name).
    """
    if not (link.startswith("http://") or link.startswith("https://")):
        return (False, None)

    domains = {
        "twitter.com": "Twitter",
        "facebook.com": "Facebook",
        "instagram.com": "Instagram",
        "threads.net": "Threads"
    }
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
    3. Disclaimers that this is NOT professional mental health advice.
    """

    try:
        # Example with text-davinci-003 (Completion API).
        # If you prefer ChatCompletion, you'd use openai.ChatCompletion.create() instead.
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "Error analyzing with OpenAI. Check logs or API key."
