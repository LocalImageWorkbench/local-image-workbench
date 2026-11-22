import hashlib
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
import model_center


class _DownloadHandler(BaseHTTPRequestHandler):
    payload = b"fake safetensors payload"

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)


class ModelCenterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _DownloadHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def test_download_and_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "loras"
            root.mkdir()
            c = config.Config(data_dir=Path(td) / "data")
            c.set("lora_roots", [str(root)])
            payload = _DownloadHandler.payload
            rec = {
                "type": "LORA",
                "file_name": "test.safetensors",
                "download_url": f"http://127.0.0.1:{self.port}/file",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            result = model_center.download_model(rec, c)
            self.assertEqual(result.read_bytes(), payload)
            self.assertFalse(Path(str(result) + ".part").exists())

    def test_safe_filename(self):
        self.assertEqual(model_center.safe_filename("../../evil.safetensors"), "evil.safetensors")
        self.assertTrue(model_center.safe_filename("a/b.safetensors").endswith(".safetensors"))


if __name__ == "__main__":
    unittest.main()
