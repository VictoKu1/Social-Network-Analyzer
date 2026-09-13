"""Provider routing and configuration regression tests through the Flask API."""
# Test method names describe assertions; HTTP handler names are framework callbacks.
# pylint: disable=missing-function-docstring,missing-class-docstring,invalid-name,too-many-public-methods

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from openai import OpenAI

from app import app
from request_security import WorkAdmission


class FakeLLMHandler(BaseHTTPRequestHandler):
    """Exercise real HTTP clients without contacting a provider or credentials."""

    def log_message(self, *_args):
        pass

    def respond(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.server.requests.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path != "/api/tags":
            self.respond({"error": "Unknown path"}, 404)
            return
        self.respond(self.server.tags, self.server.tags_status)

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.last_headers = {name.lower(): value for name, value in self.headers.items()}
        self.server.requests.append(("POST", self.path, self.headers.get("Authorization"), data))
        if self.path != "/v1/chat/completions":
            self.respond({"error": "Unknown path"}, 404)
            return
        if self.server.completion_payload is not None:
            self.respond(self.server.completion_payload, self.server.completion_status)
            return
        self.respond({
            "id": "chatcmpl-local-test", "object": "chat.completion", "created": 0,
            "model": data["model"],
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Local test analysis."},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })


class TestLLMProviders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeLLMHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        admission = patch("app.work_admission", WorkAdmission())
        admission.start()
        self.addCleanup(admission.stop)
        self.env = patch.dict(os.environ, {
            **{key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ},
            "OPENAI_BASE_URL": self.base_url + "/v1",
            "OLLAMA_BASE_URL": self.base_url,
            "NO_PROXY": "*",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fetched_urls = []
        fetch = patch("analyze.fetch_social_media_data", side_effect=self.record_fetch)
        fetch.start()
        self.addCleanup(fetch.stop)
        self.server.requests = []
        self.server.last_headers = {}
        self.server.tags_status = 200
        self.server.completion_payload = None
        self.server.completion_status = 200
        self.server.tags = {"models": [{"name": "llama3.2:latest"}, {"name": "qwen3:8b"}]}
        self.client = app.test_client()

    def record_fetch(self, url):
        self.fetched_urls.append(url)

    def analyze(self, **extra):
        return self.client.post("/analyze", json={
            "links_info": [{"url": "https://github.com/example", "platform": "GitHub"}],
            "personal_description": "I enjoy building things.",
            **extra,
        })

    def local_cloud_client(self, **kwargs):
        # Intercept only the external destination; retain the real SDK/auth/body.
        self.assertEqual(kwargs.pop("base_url"), "https://api.openai.com/v1")
        client = OpenAI(base_url=self.base_url + "/v1", **kwargs)
        self.addCleanup(client.close)
        return client

    def assert_blocked(self, response, code, status):
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        self.assertEqual(response.get_json()["error"]["code"], code)
        self.assertEqual(self.fetched_urls, [])
        self.assertFalse(any(entry[0] == "POST" for entry in self.server.requests))

    def test_missing_openai_key_blocks_before_scraping(self):
        self.assert_blocked(self.analyze(provider="openai"), "openai_key_missing", 503)

    def test_whitespace_openai_key_is_missing(self):
        os.environ["OPENAI_API_KEY"] = "   "
        self.assert_blocked(self.analyze(provider="openai"), "openai_key_missing", 503)

    def test_default_mode_also_blocks_without_openai_key(self):
        self.assert_blocked(self.analyze(), "openai_key_missing", 503)

    def test_unknown_provider_does_not_fall_back(self):
        self.assert_blocked(self.analyze(provider="typo"), "unsupported_provider", 400)

    def test_config_reports_missing_key_without_network_requests(self):
        response = self.client.get("/api/llm-config")
        self.assertEqual(response.status_code, 200)
        config = response.get_json()
        self.assertEqual(config["default_provider"], "openai")
        self.assertFalse(config["openai"]["configured"])
        self.assertEqual(config["openai"]["model"], "gpt-4o")
        self.assertEqual(self.server.requests, [])

    def test_config_reports_selected_defaults_without_exposing_key(self):
        os.environ.update(OPENAI_API_KEY="secret-test-key", OPENAI_MODEL="configured-openai-model",
                          LLM_PROVIDER="ollama", OLLAMA_MODEL="qwen3:8b")
        response = self.client.get("/api/llm-config")
        self.assertEqual(response.status_code, 200)
        config = response.get_json()
        self.assertEqual(config["default_provider"], "ollama")
        self.assertTrue(config["openai"]["configured"])
        self.assertEqual(config["openai"]["model"], "configured-openai-model")
        self.assertEqual(config["ollama"]["configured_model"], "qwen3:8b")
        self.assertNotIn("secret-test-key", response.get_data(as_text=True))

    def test_model_discovery_uses_tags_and_normalizes_v1_suffix(self):
        os.environ.update(OLLAMA_BASE_URL=self.base_url + "/v1/", OLLAMA_MODEL="qwen3:8b")
        response = self.client.get("/api/ollama/models")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["models"], ["llama3.2:latest", "qwen3:8b"])
        self.assertEqual(response.get_json()["default_model"], "qwen3:8b")
        self.assertEqual(self.server.requests[0][:3], ("GET", "/api/tags", None))

    def test_ollama_analyzes_without_openai_key_using_selected_model(self):
        response = self.analyze(provider="ollama", model="qwen3:8b")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Local test analysis.", response.get_json()["analysis"])
        self.assertEqual(self.fetched_urls, ["https://github.com/example"])
        self.assertEqual(len(self.server.requests), 2)
        method, path, authorization, payload = self.server.requests[-1]
        self.assertEqual((method, path, authorization), ("POST", "/v1/chat/completions", "Bearer ollama"))
        self.assertEqual(payload["model"], "qwen3:8b")
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertIn("I enjoy building things.", payload["messages"][-1]["content"])

    def test_local_ollama_requests_do_not_use_environment_proxy(self):
        os.environ.update(HTTP_PROXY="http://127.0.0.1:1", HTTPS_PROXY="http://127.0.0.1:1",
                          ALL_PROXY="http://127.0.0.1:1", NO_PROXY="")
        response = self.analyze(provider="ollama", model="qwen3:8b")
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(self.server.requests[-1][1], "/v1/chat/completions")

    def test_ollama_does_not_inherit_openai_custom_credentials(self):
        os.environ["OPENAI_CUSTOM_HEADERS"] = (
            "Authorization: Bearer synthetic-cloud-secret\nx-api-key: synthetic-private-key"
        )
        response = self.analyze(provider="ollama", model="qwen3:8b")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.server.last_headers.get("authorization"), "Bearer ollama")
        self.assertNotIn("x-api-key", self.server.last_headers)

    def test_cloud_backed_alias_is_excluded_from_local_models(self):
        self.server.tags["models"].append({
            "name": "my-renamed-model:latest", "remote_host": "https://ollama.com",
            "remote_model": "remote-model",
        })
        response = self.client.get("/api/ollama/models")
        self.assertEqual(response.get_json()["models"], ["llama3.2:latest", "qwen3:8b"])
        self.assert_blocked(self.analyze(provider="ollama", model="my-renamed-model:latest"),
                            "ollama_model_missing", 400)

    def test_cloud_only_installation_is_not_ready_for_local_inference(self):
        self.server.tags = {"models": [{"name": "cloud-alias", "remote_model": "remote-model"}]}
        self.assert_blocked(self.analyze(provider="ollama", model="cloud-alias"),
                            "ollama_no_models", 503)

    def test_malformed_local_completion_returns_actionable_error(self):
        for payload in ([], {"choices": []}, {"choices": [{"message": None}]},
                        {"choices": [{"message": {"content": ""}}]}):
            with self.subTest(payload=payload):
                self.server.completion_payload = payload
                response = self.analyze(provider="ollama", model="qwen3:8b")
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.get_json()["error"]["code"], "analysis_failed")

    def test_local_service_errors_do_not_echo_upstream_details(self):
        self.server.completion_payload = {"error": "synthetic-private-upstream-details"}
        self.server.completion_status = 500
        response = self.analyze(provider="ollama", model="qwen3:8b")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"]["code"], "analysis_failed")
        self.assertNotIn("synthetic-private-upstream-details", response.get_data(as_text=True))

    def test_ollama_never_receives_configured_openai_key(self):
        os.environ["OPENAI_API_KEY"] = "secret-test-key"
        response = self.analyze(provider="ollama", model="qwen3:8b")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.server.requests[-1][2], "Bearer ollama")
        self.assertNotIn("secret-test-key", json.dumps(self.server.requests))
        self.assertNotIn("secret-test-key", response.get_data(as_text=True))

    def test_ollama_default_mode_and_model_work_without_key(self):
        os.environ.update(LLM_PROVIDER="ollama", OLLAMA_MODEL="llama3.2:latest")
        response = self.analyze()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Local test analysis.", response.get_json()["analysis"])
        self.assertEqual(self.server.requests[-1][3]["model"], "llama3.2:latest")

    def test_ollama_without_model_uses_first_installed_model(self):
        response = self.analyze(provider="ollama")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.server.requests[-1][3]["model"], "llama3.2:latest")

    def test_ollama_uninstalled_or_empty_model_blocks_before_scraping(self):
        for model in ("not-installed:latest", "", "   "):
            with self.subTest(model=model):
                self.assert_blocked(self.analyze(provider="ollama", model=model), "ollama_model_missing", 400)

    def test_ollama_stale_configured_model_blocks_before_scraping(self):
        os.environ["OLLAMA_MODEL"] = "not-installed:latest"
        self.assert_blocked(self.analyze(provider="ollama"), "ollama_model_missing", 400)

    def test_ollama_with_no_installed_models_blocks_before_scraping(self):
        self.server.tags = {"models": []}
        self.assert_blocked(self.analyze(provider="ollama", model="qwen3:8b"), "ollama_no_models", 503)

    def test_ollama_unavailable_blocks_before_scraping(self):
        self.server.tags_status = 503
        self.assert_blocked(self.analyze(provider="ollama", model="qwen3:8b"), "ollama_unavailable", 503)

    def test_malformed_ollama_tags_blocks_before_scraping(self):
        for payload in ({"unexpected": []}, {"models": "invalid"}, {"models": [{}]}):
            with self.subTest(payload=payload):
                self.server.tags = payload
                self.assert_blocked(self.analyze(provider="ollama", model="qwen3:8b"),
                                    "ollama_unavailable", 503)

    def test_openai_default_model_uses_configured_key(self):
        os.environ["OPENAI_API_KEY"] = "secret-test-key"
        with patch("llm_providers.OpenAI", side_effect=self.local_cloud_client):
            response = self.analyze(provider="openai")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Local test analysis.", response.get_json()["analysis"])
        self.assertEqual(self.server.requests[-1][2], "Bearer secret-test-key")
        self.assertEqual(self.server.requests[-1][3]["model"], "gpt-4o")
        self.assertEqual(self.server.requests[-1][3]["max_completion_tokens"], 4096)

    def test_openai_uses_server_configured_model(self):
        os.environ.update(OPENAI_API_KEY="secret-test-key", OPENAI_MODEL="configured-openai-model")
        with patch("llm_providers.OpenAI", side_effect=self.local_cloud_client):
            response = self.analyze(provider="openai", model="qwen3:8b")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.server.requests[-1][3]["model"], "configured-openai-model")


if __name__ == "__main__":
    unittest.main()
