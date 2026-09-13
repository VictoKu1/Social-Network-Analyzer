# Social Network Analyzer

[![Pylint](https://github.com/VictoKu1/Social-Network-Analyzer/actions/workflows/pylint.yml/badge.svg)](https://github.com/VictoKu1/Social-Network-Analyzer/actions/workflows/pylint.yml)

This repository contains a **Flask-based web application** that lets users:

1. **Specify how many social network links** they want to analyze.
2. Enter and **validate** each link (Twitter, Instagram, Facebook, Threads, etc.).
3. Provide a **personal description** about the person whose profiles are being analyzed.
4. **Analyze** all collected data (links + description) via OpenAI or a locally installed Ollama model to generate a **personality overview** or short psychological summary.

> **IMPORTANT DISCLAIMER**  
> - This is **not** a clinical or professional psychological tool.  
> - The output can contain errors or "hallucinations" typical of Large Language Models.  
> - Always comply with each social platform's terms of service regarding data collection/scraping.  
> - Handle personal data with caution and respect user privacy.

---

## 🚀 New Features: Platform-Specific API Integration

The application now includes **advanced platform-specific API integration** for reliable social media data fetching:

### ✅ Supported Platforms
- **Twitter/X**: Full API v2 and v1.1 support with rate limiting
- **LinkedIn**: Optional authenticated profile extraction for local use
- **Instagram**: Public profile access via instaloader; private profiles are rejected
- **Facebook**: Graph API integration for profile data
- **Reddit**: User data and post history via PRAW
- **Generic Platforms**: Web scraping fallback for supported public social domains

### 🔧 Key Improvements
- **Rate Limiting**: Per-fetcher pacing and bounded web analysis/model-discovery work
- **Authentication**: Optional platform credentials; shared access skips operator Twitter, Facebook, LinkedIn, Instagram and Reddit logins
- **Fallback Mechanisms**: Web scraping when APIs are unavailable
- **Structured Data**: Consistent data format across all platforms
- **Error Handling**: Comprehensive error handling and recovery

### 📊 Enhanced Data Extraction
- Profile information (name, bio, location, website)
- Follower/following counts
- Verification status
- Recent posts and activity
- Account creation dates
- Profile pictures

For detailed setup instructions, see [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md).

---

## Features

- **Multi-Step Flow**  
  - **Step A**: Select the number of social network links.  
  - **Step B**: Enter each link, then validate it against known social platforms.  
    - If all links are valid, you can continue. Otherwise, you must correct them.  
  - **Step C**: Provide a personal description for additional context.  
  - **Analysis**: The server combines the links + personal description into a prompt, sends it to the selected inference provider, and displays a final summary.

- **Dynamic Frontend**  
  - Uses JavaScript (Fetch API) to handle link validation and multi-step UI.  
  - Displays **✓** for valid links and **✗** for invalid links.

- **AI analysis**
  - Choose OpenAI or an installed local Ollama model.
  - OpenAI requires a server-side API key; Ollama mode does not.

- **Platform-Specific API Integration**  
  - Reliable data fetching using official APIs where available
  - HTML scraping for supported platforms without an available API adapter
  - Rate limiting and error handling for robust operation

---

## Quickstart

1. **Clone the Repository**:

   ```
   git clone https://github.com/VictoKu1/Social-Network-Analyzer.git
   cd Social-Network-Analyzer
    ```

2. **Install Dependencies**:

   - **Python 3.9+** required by the application code.
   - Install packages:

    ```
    pip install -r requirements.txt
    ```

3. **Set Your API Keys**:

    Create a `.env` file with your API credentials:

    ```env
   # Required only when using OpenAI mode
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   OPENAI_MODEL=gpt-4o
   LLM_PROVIDER=openai
    
    # Optional: Platform-specific APIs (see config_example.py for details)
    TWITTER_BEARER_TOKEN=your_twitter_bearer_token
    LINKEDIN_EMAIL=your_linkedin_email
    LINKEDIN_PASSWORD=your_linkedin_password
    INSTAGRAM_USERNAME=your_instagram_username
    INSTAGRAM_PASSWORD=your_instagram_password
    FACEBOOK_ACCESS_TOKEN=your_facebook_access_token
    REDDIT_CLIENT_ID=your_reddit_client_id
    REDDIT_CLIENT_SECRET=your_reddit_client_secret
    ```

   **Note**: OpenAI mode requires `OPENAI_API_KEY`. When it is missing or blank, the UI blocks continuation and the backend rejects analysis before scraping. Platform-specific APIs are optional and will fall back to web scraping if not provided.

4. **Run the Flask App**:

    ```
    python app.py
    ```

5. **Open Your Browser**:

Visit http://127.0.0.1:5000/ to access the web app.

`python app.py` binds to loopback with debug mode off. The default request policy allows local peers using `localhost`, `127.0.0.1` or `::1` as the host.

6. **Test the API Integration** (Optional):

    ```
    python test_api_integration.py
    ```

### Using local Ollama

Install [Ollama](https://ollama.com/download) on the **machine running Flask**, start it, and pull a model of your choice:

```sh
ollama serve
# In another terminal; replace MODEL_NAME with an Ollama model you want to run:
ollama pull MODEL_NAME
```

If the Ollama desktop app already runs the service, a separate `ollama serve` is unnecessary. Choose **Ollama (local)** in the website's Setup step, refresh models, and select an installed local model. Cloud-backed models and aliases are excluded. No OpenAI API key is required in Ollama mode. The app checks service/model availability before scraping and does not silently switch providers.

Optional `.env` settings:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
# Optional default; must name an installed model:
OLLAMA_MODEL=MODEL_NAME
```

The local endpoint can also end in `/v1`. Its address is configured only on the server. When Flask is hosted elsewhere, `localhost` refers to that server, not the visitor's browser. In Ollama mode, the analysis prompt goes to the configured Ollama service; social-profile retrieval still uses the network.

OpenAI mode uses the OpenAI service with the server's key and `OPENAI_MODEL` (default `gpt-4o`). It does not reuse `OPENAI_BASE_URL` as an implicit provider switch. Never put an OpenAI key in frontend JavaScript or commit it to Git. After changing `.env`, restart Flask and use **Check again** in Setup.

### Access and limits

For shared access, set `APP_ACCESS_TOKEN` to a random secret of at least 32 characters in the server environment or `.env`. Add external hostnames to `APP_ALLOWED_HOSTS` as a comma-separated list of names without schemes, ports or paths, for example `analyzer.example.com`. Restart the app after changing these settings. Sign in through the browser's HTTP Basic prompt with username `operator` and the token as the password. The app requires this credential for local requests too when a token is configured.

External access requires HTTPS as reported by the serving WSGI environment. The app does not trust `Forwarded` or `X-Forwarded-*` headers to establish the peer, host or HTTPS scheme; local-only mode rejects requests containing these headers. Configure the serving environment for HTTPS and the intended hostname. These settings do not change the loopback binding of `python app.py`.

Shared mode skips operator Twitter, Facebook, LinkedIn, Instagram and Reddit logins and uses public HTML scraping for those platforms, including when clients were initialized before shared mode was enabled. The Instagram adapter rejects private profiles before reading posts in local mode. Obtain explicit consent before analyzing sensitive personal information.

The server applies these budgets:

- At most **5 profiles**, **2,048 characters per URL**, **10,000 description characters** and **32 KiB per HTTP request body**.
- At most **50,000 characters in the analysis prompt**; requests to either inference provider specify **4,096 completion tokens**.
- A shared allowance of **30 work requests per rolling minute** and **2 concurrent requests** for `/analyze` and `/api/ollama/models`. Excess work returns HTTP 429. These counters cover one process; multiple workers require shared admission control.

HTML scraping and GitHub HTTP reads accept supported domains on standard HTTP(S) ports, require public DNS addresses, and connect to a validated IP while retaining HTTPS certificate checks. Each fetch permits at most **3 revalidated redirects**, a **15-second retrieval budget**, and **1 MiB for each of the encoded and decoded response bodies**. Oversized responses are rejected. These download limits apply to this HTTP transport; platform SDK calls and inference have their own behavior and timeouts, and a complete analysis may take longer.

---

## Usage
1. **Setup**: Choose OpenAI or Ollama, resolve any configuration message, select the number of profiles, and click **Continue**.
2. **Profiles**: Enter each profile URL and click **Continue**. Correct any inline validation errors to advance.
3. **Description**: Provide a **personal description** for context (e.g., "She is very outgoing and enjoys discussing tech trends.").
4. **Click** ```Analyze profiles```: The server sends the data to your selected inference provider and displays a final summary.

The application will now use platform-specific APIs when available, providing more reliable and comprehensive data extraction.

---

## Project Structure

```
.
├── static/             
│   └── css/
│       └── style.css    # CSS for the multi-step form
├── js/                 
│   └── app.js          # JavaScript for the multi-step form
├── templates/
│   └── index.html      # Implements the multi-step form using JavaScript
├── app.py              # Main Flask app with routes
├── analyze.py          # OpenAI-related analysis logic (link validation, prompt construction)
├── social_media_fetchers.py  # NEW: Platform-specific API integration
├── test_analyze.py     # Unit tests for the analyze.py logic
├── test_api_integration.py   # NEW: API integration tests
├── config_example.py   # NEW: Example configuration file
├── API_INTEGRATION_GUIDE.md  # NEW: Comprehensive API setup guide
├── requirements.txt    # Python package dependencies
├── README.md           # This README file
├── LICENSE             # License (MIT)
└── .gitignore          # Prevents committing unwanted files
```

- ```app.py```: 
  - Defines the Flask routes:
    - ```GET /``` serves the main page (```index.html```)
    - ```POST /validate_links``` checks if each link is a recognized social network
    - ```POST /analyze``` calls the analysis function in ```analyze.py``` and returns the result

- ```analyze.py```:
  - Contains the core **OpenAI analysis** logic:
    - ```validate_social_link(link)``` checks if a URL is recognized (Twitter, Instagram, etc.).
    - ```analyze_personality(links_info, personal_description)``` constructs a prompt and calls the OpenAI API.
    - **Updated** to use platform-specific fetchers for better data extraction.

- ```social_media_fetchers.py```: **NEW**
  - Platform-specific API integration for Twitter, LinkedIn, Instagram, Facebook, and Reddit
  - Rate limiting and error handling
  - Fallback mechanisms for unsupported platforms
  - Structured data extraction and formatting

- ```test_analyze.py```:
  - Contains **unit tests** for functions in ```analyze.py```.
  - Uses Python's built-in ```unittest``` or can be adapted for ```pytest```.

- ```test_api_integration.py```: **NEW**
  - Tests for the platform-specific API integration
  - Demonstrates the difference between old and new fetching methods
  - Validates rate limiting and error handling

- ```config_example.py```: **NEW**
  - Example configuration file showing all required API credentials
  - Detailed setup instructions for each platform
  - Security best practices

- ```API_INTEGRATION_GUIDE.md```: **NEW**
  - Comprehensive guide for setting up platform-specific APIs
  - Troubleshooting and performance optimization tips
  - Security considerations and best practices

- ```Templates/index.html```:
  - Implements the **multi-step form** using JavaScript.
  - Uses the Fetch API to call ```/validate_links``` and ```/analyze```.

- ```requirements.txt```:
  - Python package dependencies.
  - **Updated** to include platform-specific API libraries.

- ```.gitignore```:
  - Hides temporary or sensitive files (e.g., ```venv/```, ```.env```, ```__pycache__```, etc.) from version control.

---

## Testing

To run the **unit tests** for ```analyze.py```, use one of the following:

### Using Python's built-in ```unittest```

```
python -m unittest discover
```

or specifically:

```
python -m unittest test_analyze test_llm_providers test_safe_fetch test_security
```

### Using ```pytest``` (if installed)
```
pytest test_analyze.py test_llm_providers.py test_safe_fetch.py test_security.py
```

### Testing API Integration (NEW)

This optional demonstration contacts live social services and depends on their availability and credentials.

```
python test_api_integration.py
```

Browser security regressions run offline with `node --test tests/renderer_security.test.cjs`.
They require Playwright and Chrome; set `CHROME_EXECUTABLE_PATH` for installations outside the default Windows path.

Tests in ```test_analyze.py```:

- **Mock** the OpenAI API to avoid real API calls.
- Verify that functions like ```validate_social_link``` and ```analyze_personality``` behave as expected.

Tests in ```test_api_integration.py```:

- **Compare** old generic fetching with new platform-specific fetching
- **Validate** rate limiting and error handling
- **Test** platform detection and username extraction
- **Verify** fallback mechanisms work correctly

---

## API Setup

For detailed instructions on setting up platform-specific APIs, see [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md).

### Quick Setup Summary

1. **Twitter/X**: Get API keys from [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. **LinkedIn**: Optional email/password for local use; shared mode uses public scraping
3. **Instagram**: Public profiles only; shared mode skips operator login
4. **Facebook**: Get access token from [Facebook Developers](https://developers.facebook.com/)
5. **Reddit**: Create app at [Reddit App Preferences](https://www.reddit.com/prefs/apps)

### Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive data
- Regularly rotate your API keys
- Monitor API usage to avoid rate limits

---

## Contributing

1. **Fork** this repo and clone your fork.
2. **Create** a new branch for your feature/bugfix:
```
git checkout -b feature/new-stuff
```

3. **Commit** and push your changes:
```
git commit -m "Add new feature"
git push origin feature/new-stuff
```

4. **Open** a Pull Request on GitHub.

---

## License


Please see the [LICENSE](LICENSE) file for details.


## Disclaimer

- This software is provided "as is," without any warranty or guarantee.
- Always comply with social media platforms' terms of service and API usage policies.
- Respect user privacy and data protection regulations.




































