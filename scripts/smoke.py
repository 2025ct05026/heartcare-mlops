"""Exercise a real running HTTP service, including validation and monitoring."""

import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from heartcare.data import ROOT

base = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/")
patient = (ROOT / "examples/patient.json").read_bytes()
with urlopen(base + "/health", timeout=10) as response:
    assert json.load(response)["status"] == "ok"
request = Request(base + "/predict", data=patient, headers={"Content-Type": "application/json"})
with urlopen(request, timeout=10) as response:
    body = json.load(response)
assert body["prediction"] in [0, 1] and 0 <= body["probability"] <= 1
print(json.dumps(body, indent=2))
invalid = Request(base + "/predict", data=b'{}', headers={"Content-Type": "application/json"})
try:
    urlopen(invalid, timeout=10)
    raise AssertionError("Invalid input was accepted")
except HTTPError as error:
    assert error.code == 422
with urlopen(base + "/metrics", timeout=10) as response:
    assert "heartcare_predictions_total" in response.read().decode()
print("PASS: health, prediction, invalid input and metrics")
