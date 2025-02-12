# Social Network Analyzer

[![Pylint](https://github.com/VictoKu1/Social-Network-Analyzer/actions/workflows/pylint.yml/badge.svg)](https://github.com/VictoKu1/Social-Network-Analyzer/actions/workflows/pylint.yml)

This repository contains a **Flask-based web application** that lets users:

1. **Specify how many social network links** they want to analyze.
2. Enter and **validate** each link (Twitter, Instagram, Facebook, Threads, etc.).
3. Provide a **personal description** about the person whose profiles are being analyzed.
4. **Analyze** all collected data (links + description) via the OpenAI API to generate a **personality overview** or short psychological summary.

> **IMPORTANT DISCLAIMER**  
> - This is **not** a clinical or professional psychological tool.  
> - The output can contain errors or “hallucinations” typical of Large Language Models.  
> - Always comply with each social platform’s terms of service regarding data collection/scraping.  
> - Handle personal data with caution and respect user privacy.

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
  - A sample prompt demonstrates how to create a short “personality analysis.”  
  - Requires an **OpenAI API key** (set in `.env` or as an environment variable).

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

3. **Set Your OpenAI API Key**:

    You can either set it as an environment variable:
      - Linux:

          ```
          export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxx"
          ```
    
      - Windows:

        ```
        set OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
        ```

    Or create a .env file (not tracked in version control) and store your API key there:

        ```
        OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
        ```

4. **Run the Flask App**:

    ```
    python app.py
    ```

5. **Open Your Browser**:

Visit http://127.0.0.1:5000/ to access the web app.

---

## Usage
1. **Step A**: Select the number of social profiles (e.g., 2).
2. **Step B**: Enter each URL in the generated fields (e.g., https://x.com/example), then click **Validate Links**.
 * If a link is marked ✗, correct it.
 * If all links are ✓, the Continue button appears.
3. **Step C**: Provide a **personal description** for context (e.g., “She is very outgoing and enjoys discussing tech trends.”).
4. **Click** ```Analyze```: The server sends the data to OpenAI and displays a final summary.

---

## Project Structure

```
.
├── app.py              # Main Flask app with routes
├── analyze.py          # OpenAI-related analysis logic (link validation, prompt construction)
├── test_analyze.py     # Unit tests for the analyze.py logic
├── templates/
│   └── index.html      # Implements the multi-step form using JavaScript
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

- ```test_analyze.py```:
  - Contains **unit tests** for functions in ```analyze.py```.
  - Uses Python’s built-in ```unittest``` or can be adapted for ```pytest```.

- ```Templates/index.html```:
  - Implements the **multi-step form** using JavaScript.
  - Uses the Fetch API to call ```/validate_links``` and ```/analyze```.

- ```requirements.txt```:
  - Python package dependencies.

- ```.gitignore```:
  - Hides temporary or sensitive files (e.g., ```venv/```, ```.env```, ```__pycache__```, etc.) from version control.

---

## Testing

To run the **unit tests** for ```analyze.py```, use one of the following:

### Using Python’s built-in ```unittest```

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

Tests in ```test_analyze.py```:

- **Mock** the OpenAI API to avoid real API calls.
- Verify that functions like ```validate_social_link``` and ```analyze_personality``` behave as expected.

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

```
MIT License

Copyright (c) 2025 Victor Kushnir

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Please see the ```LICENSE``` file for more information.

---

## Disclaimer

- This software is provided “as is,” without any warranty or guarantee.
- The output from any language model can be inaccurate or biased.
- Please use responsibly and always comply with the relevant platform policies and laws.
- Do not use this software for any high-stakes decisions.
- Always respect user privacy and data protection laws.
- If you have any concerns, please contact the author.
- The author is not responsible for any misuse or damage caused by this software.

























