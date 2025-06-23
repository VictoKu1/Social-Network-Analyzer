# Social Network Analyzer

[![Pylint](https://github.com/VictoKu1/Social-Network-Analyzer/actions/workflows/pylint.yml/badge.svg)](https://github.com/VictoKu1/Social-Network-Analyzer/actions/workflows/pylint.yml)

This repository contains a **Flask-based web application** that lets users:

1. **Specify how many social network links** they want to analyze.
2. Enter and **validate** each link (Twitter, Instagram, Facebook, Threads, etc.).
3. Provide a **personal description** about the person whose profiles are being analyzed.
4. **Analyze** all collected data (links + description) via the OpenAI API to generate a **personality overview** or short psychological summary.

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
- **LinkedIn**: Profile data extraction with authentication
- **Instagram**: Public and private profile access via instaloader
- **Facebook**: Graph API integration for profile data
- **Reddit**: User data and post history via PRAW
- **Generic Platforms**: Web scraping fallback for other platforms

### 🔧 Key Improvements
- **Rate Limiting**: Automatic API rate limit management
- **Authentication**: OAuth and API key support for each platform
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
  - **Analysis**: The server combines the links + personal description into a prompt, sends it to OpenAI, and displays a final summary.

- **Dynamic Frontend**  
  - Uses JavaScript (Fetch API) to handle link validation and multi-step UI.  
  - Displays **✓** for valid links and **✗** for invalid links.

- **OpenAI Integration**  
  - A sample prompt demonstrates how to create a short "personality analysis."  
  - Requires an **OpenAI API key** (set in `.env` or as an environment variable).

- **Platform-Specific API Integration**  
  - Reliable data fetching using official APIs where available
  - Automatic fallback to web scraping for unsupported platforms
  - Rate limiting and error handling for robust operation

---

## Quickstart

1. **Clone the Repository**:

   ```
   git clone https://github.com/VictoKu1/Social-Network-Analyzer.git
   cd Social-Network-Analyzer
    ```

2. **Install Dependencies**:

   - **Python 3.8+** recommended.
   - Install packages:

    ```
    pip install -r requirements.txt
    ```

3. **Set Your API Keys**:

    Create a `.env` file with your API credentials:

    ```env
    # Required: OpenAI API
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
    
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

    **Note**: Only the OpenAI API key is required. Platform-specific APIs are optional and will fall back to web scraping if not provided.

4. **Run the Flask App**:

    ```
    python app.py
    ```

5. **Open Your Browser**:

Visit http://127.0.0.1:5000/ to access the web app.

6. **Test the API Integration** (Optional):

    ```
    python test_api_integration.py
    ```

---

## Usage
1. **Step A**: Select the number of social profiles (e.g., 2).
2. **Step B**: Enter each URL in the generated fields (e.g., https://x.com/example), then click **Validate Links**.
 * If a link is marked ✗, correct it.
 * If all links are ✓, the Continue button appears.
3. **Step C**: Provide a **personal description** for context (e.g., "She is very outgoing and enjoys discussing tech trends.").
4. **Click** ```Analyze```: The server sends the data to OpenAI and displays a final summary.

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
python -m unittest test_analyze.py
````

### Using ```pytest``` (if installed)
```
pytest
```

### Testing API Integration (NEW)

```
python test_api_integration.py
```

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
2. **LinkedIn**: Use email/password (not recommended for production)
3. **Instagram**: Use username/password for private profiles
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






































