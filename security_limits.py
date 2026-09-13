"""Shared input budgets and safe errors for the analysis boundary."""

MAX_LINKS = 5
MAX_URL_LENGTH = 2048
MAX_DESCRIPTION_LENGTH = 10000
MAX_PROMPT_LENGTH = 50000
MAX_COMPLETION_TOKENS = 4096
MAX_REQUEST_BYTES = 32768


class SecurityError(ValueError):
    """A fixed, user-safe error; never include credentials or upstream bodies."""

    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def validate_links_list(links):
    """Bound URL count and representation before any provider or scraper work."""
    if not isinstance(links, list) or len(links) > MAX_LINKS:
        raise SecurityError("invalid_links", "Provide at most five profile links.")
    if any(not isinstance(link, str) or not link or len(link) > MAX_URL_LENGTH for link in links):
        raise SecurityError("invalid_links", "Each profile link must be a URL of at most 2048 characters.")
    return links


def validate_description(description):
    """Reject non-text descriptions and excess input before aggregation."""
    if not isinstance(description, str) or len(description) > MAX_DESCRIPTION_LENGTH:
        raise SecurityError("invalid_description", "The description must be text of at most 10000 characters.")


def check_prompt_budget(text):
    """Reject oversized collected content without silently changing the input."""
    if len(text) > MAX_PROMPT_LENGTH:
        raise SecurityError("analysis_too_large",
                            "The collected profile content is too large. Use fewer profiles.", 413)
