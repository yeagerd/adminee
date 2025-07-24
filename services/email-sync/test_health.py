import importlib.util
import sys
import os

spec = importlib.util.spec_from_file_location(
    "app", os.path.join(os.path.dirname(__file__), "app.py")
)
app_module = importlib.util.module_from_spec(spec)
sys.modules["app"] = app_module
spec.loader.exec_module(app_module)
app = app_module.app

def test_healthz():
    with app.test_client() as client:
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json["status"] == "ok" 