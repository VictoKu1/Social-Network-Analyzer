# Recruiter Brief: Social Network Analyzer

## One-minute summary

Social Network Analyzer is a Flask application that validates user-provided social profile URLs, gathers publicly available profile context through platform-specific fetchers where possible, and asks an OpenAI-compatible model to generate a short, clearly-disclaimed personality-style summary. It demonstrates Python backend work, API integration, resilient data-fetching patterns, privacy-aware product design, and responsible AI disclaimers.

## What it demonstrates

- Backend development with Flask routes for link validation, multi-step analysis, and JSON responses.
- API integration across Twitter/X, LinkedIn, Instagram, Facebook, Reddit, GitHub, and generic web pages, with fallback scraping where official APIs are unavailable.
- Reliability patterns including rate limiting, retry-enabled sessions, platform detection, structured data formatting, and explicit error handling.
- Responsible AI/product judgment through privacy notes, data-handling warnings, and non-clinical disclaimers.
- Testability with unit and integration tests for analysis and platform fetcher behavior.

## Architecture at a glance

```text
Browser form
  -> Flask validation endpoint
  -> platform-specific URL detection
  -> API fetcher or fallback scraper
  -> structured profile summary
  -> OpenAI-compatible analysis call
  -> web result
```

Important files:

- `app.py` - Flask routes and request handling.
- `analyze.py` - link validation, prompt construction, and OpenAI analysis flow.
- `social_media_fetchers.py` - platform-specific fetchers, rate limiter, retries, and formatting.
- `API_INTEGRATION_GUIDE.md` - credential and integration setup notes.
- `test_analyze.py` and `test_api_integration.py` - verification examples.
- `templates/` and `static/` - frontend form and styling.

## How to verify locally

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set OPENAI_API_KEY=your_key_here
python app.py
```

Open `http://127.0.0.1:5000/` and run the multi-step flow with public profile URLs. Optional platform credentials can be configured from `API_INTEGRATION_GUIDE.md`.

## Role positioning

Best aligned roles:

- Backend Developer
- Python Developer
- Software Engineer
- AI Application Developer
- Data/API Integration Engineer
- Privacy-aware product/security role

Suggested portfolio phrasing:

> Built a privacy-aware social profile analysis prototype with Flask, platform-specific API fetchers, fallback scraping, OpenAI integration, rate limiting, retries, structured data extraction, and explicit responsible-use disclaimers.

## Responsible claims

Do not present the output as clinical, psychological, hiring, credit, or legal evaluation. It is an experimental AI summarization app and should only process data the user is allowed to provide and analyze.
