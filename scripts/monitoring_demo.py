"""Verify the real Compose stack and save reproducible monitoring evidence."""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from heartcare.data import ROOT


def get_json(url):
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def wait_until(check):
    for _ in range(90):
        try:
            if check():
                return
        except (HTTPError, URLError, TimeoutError, KeyError):
            pass
        time.sleep(2)
    raise AssertionError("Service did not become ready")


def main():
    wait_until(lambda: get_json("http://127.0.0.1:8000/health")["status"] == "ok")
    wait_until(lambda: get_json("http://127.0.0.1:3000/api/health")["database"] == "ok")
    targets_url = "http://127.0.0.1:9090/api/v1/targets"
    wait_until(lambda: any(t["health"] == "up" for t in get_json(targets_url)["data"]["activeTargets"]))
    patient = json.loads((ROOT / "examples/patient.json").read_text())
    statuses = {"200": 0, "422": 0}
    for index in range(100):
        payload = dict(patient)
        if index % 2:
            payload.update(cp=4, exang=1, ca=2, thal=7, oldpeak=4)
        if index % 5 == 0:
            payload = {}
        request = Request("http://127.0.0.1:8000/predict", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                assert json.load(response)["prediction"] in (0, 1)
                statuses[str(response.status)] += 1
        except HTTPError as error:
            assert error.code == 422
            statuses["422"] += 1
        time.sleep(0.35)
    time.sleep(12)
    query = "http://127.0.0.1:9090/api/v1/query?query=heartcare_predictions_total"
    measured = get_json(query)
    assert measured["status"] == "success" and measured["data"]["result"]
    evidence = {"http_status_counts": statuses, "targets": get_json(targets_url), "predictions": measured}
    (ROOT / "evidence/monitoring-verification.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(statuses), "PASS: Prometheus target UP and prediction metrics present")


if __name__ == "__main__":
    main()
