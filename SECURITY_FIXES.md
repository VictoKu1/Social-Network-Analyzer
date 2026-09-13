# Security fixes — 2026-09-13

Outcome: **fixed in the working tree and activated locally** at `http://127.0.0.1:5000`.

Activation check on 2026-09-13: the running app returned the patched page and security headers, rejected forged hosts/origins and unsafe profile URLs, enforced input/body limits, and blocked OpenAI analysis when no key was configured. No model inference or social requests were made. Startup used the working bundled Python runtime and temporary dependency directory because the existing `.venv` references a removed Python 3.9 installation.

The three reported paths were addressed at their shared boundaries:

- **Profile URL SSRF:** `safe_fetch.py` validates supported hostnames and standard ports, rejects credentials and non-public DNS answers, connects to checked IPs with the original TLS identity, and repeats these checks on redirects. All direct HTML/GitHub downloads in `social_media_fetchers.py` use it. Alternate checked addresses retain connectivity when the first address is unreachable.
- **Generated Markdown XSS:** `static/js/analysis-renderer.js` creates a restricted set of DOM elements and text nodes. Raw HTML, executable URLs and embedded media stay inert. `static/js/app.js` and `templates/index.html` use that renderer with a local, licensed Marked parser. `app.py` supplies restrictive security headers.
- **Unbounded inputs/downloads:** `security_limits.py`, `safe_fetch.py`, `analyze.py` and `llm_providers.py` enforce input, prompt, completion, download and retrieval limits. `request_security.py` adds atomic workload admission and authenticated shared access. Shared requests bypass operator social sessions, including Reddit. Private Instagram posts are rejected before retrieval.

`README.md`, `API_INTEGRATION_GUIDE.md` and `config_example.py` document setup and limits. Existing UI and Ollama changes were preserved.

Verification, in order:

1. Python compilation, `node --check` for both application scripts and `git diff --check`: passed.
2. `python -B -m unittest test_safe_fetch test_security -q`: **24 passed**. Private destinations, redirect attacks, mixed DNS answers, compressed/chunked oversized bodies, slow responses, malformed input, excess work and shared-session reuse are rejected. Normal HTML/gzip downloads, DNS failover and authenticated access succeed.
3. `node --test tests/renderer_security.test.cjs`: **5 passed** in headless Chrome. XSS fixtures that executed before the fix remain inert; headings, emphasis, lists, code, tables and safe HTTPS links still render.
4. `python -B -m unittest test_analyze test_llm_providers -q`: **35 passed**. OpenAI and Ollama routing, missing-key blocking and local credential isolation remain intact using isolated HTTP peers. The integration demo's rate-limit check also passed.
5. Pylint across tracked Python files and new modules/tests: **10.00/10, exit 0**.

Python checks used the bundled Python 3.12 runtime and temporary test dependencies. Tests were added in `test_safe_fetch.py`, `test_security.py` and `tests/renderer_security.test.cjs`; existing analysis/provider tests and the integration demo were adjusted for the new boundaries. Independent review identified DNS failover and inherited Reddit authentication issues; both were reproduced and corrected.

Live social APIs, real model inference and external HTTPS deployment were not exercised. Scraper byte/deadline limits do not cover third-party SDK internals or the whole analysis. Admission counters apply to one process; multiple workers require shared counters. Deployment instructions are in `README.md`.
