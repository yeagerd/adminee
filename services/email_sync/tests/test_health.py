import importlib.util
import os
import sys

# Set environment variables before importing app
os.environ["PYTHON_ENV"] = "test"
os.environ["GMAIL_WEBHOOK_SECRET"] = "test-gmail-webhook-secret"
os.environ["MICROSOFT_WEBHOOK_SECRET"] = "test-microsoft-webhook-secret"

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest

spec = importlib.util.spec_from_file_location(
    "app", os.path.join(os.path.dirname(__file__), "../app.py")
)
app_module = importlib.util.module_from_spec(spec)
sys.modules["app"] = app_module
spec.loader.exec_module(app_module)
app = app_module.app


class TestHealth(BaseSelectiveHTTPIntegrationTest):
    def test_healthz(self):
        client = self.create_test_client(app)
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
