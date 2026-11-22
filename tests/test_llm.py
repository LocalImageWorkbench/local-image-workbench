import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config
import llm_client


class _Handler(BaseHTTPRequestHandler):
    seen_auth = ""

    def log_message(self, *args):
        pass

    def _json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.endswith("/v1/models"):
            type(self).seen_auth = self.headers.get("Authorization", "")
            self._json({"data": [{"id": "cloud-model"}]})
        elif self.path.endswith("/api/tags"):
            self._json({"models": [{"name": "local-model", "size": 123}]})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path.endswith("/v1/chat/completions"):
            self._json({"choices": [{"message": {"content": "cloud answer"}}]})
        elif self.path.endswith("/api/show"):
            self._json({"capabilities": ["completion"]})
        elif self.path.endswith("/api/chat"):
            self._json({"message": {"content": "local answer"}})
        else:
            self._json({"error": "not found"}, 404)


class LLMTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def cfg(self):
        with tempfile.TemporaryDirectory() as td:
            c = config.Config(data_dir=Path(td))
            c.set("llm_type", "openai")
            c.set("llm_base_url", f"http://127.0.0.1:{self.port}/v1")
            c.set("llm_api_key", "secret")
            c.set("llm_model", "cloud-model")
            return c

    def test_openai_models_and_chat(self):
        c = self.cfg()
        models = llm_client.list_models(c)
        self.assertEqual(models[0]["name"], "cloud-model")
        self.assertEqual(_Handler.seen_auth, "Bearer secret")
        text = llm_client.chat(c, [{"role": "user", "content": "hello"}])
        self.assertEqual(text, "cloud answer")

    def test_ollama_models_and_chat(self):
        with tempfile.TemporaryDirectory() as td:
            c = config.Config(data_dir=Path(td))
            c.set("llm_type", "ollama")
            c.set("llm_base_url", f"http://127.0.0.1:{self.port}")
            c.set("llm_model", "local-model")
            models = llm_client.list_models(c)
            self.assertEqual(models[0]["name"], "local-model")
            text = llm_client.chat(c, [{"role": "user", "content": "hello"}])
            self.assertEqual(text, "local answer")


if __name__ == "__main__":
    unittest.main()
