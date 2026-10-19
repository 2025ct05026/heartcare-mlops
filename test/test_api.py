import json

import pytest
from fastapi.testclient import TestClient

from heartcare.api import create_app
from heartcare.data import ROOT


@pytest.fixture
def client():
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def example():
    return json.loads((ROOT / "examples/patient.json").read_text())


def test_prediction_and_health(client, example):
    assert client.get("/health").status_code == 200
    result = client.post("/predict", json=example)
    assert result.status_code == 200
    body = result.json()
    assert body["prediction"] in [0, 1]
    assert 0 <= body["probability"] <= 1
    assert 0.5 <= body["confidence"] <= 1
    assert len(body["model_version"]) == 12


@pytest.mark.parametrize("change", [{"cp": 99}, {"age": -2}, {"extra": 1}, {"thal": 2}])
def test_invalid_inputs_rejected(client, example, change):
    assert client.post("/predict", json={**example, **change}).status_code == 422


def test_missing_field_rejected(client, example):
    del example["age"]
    assert client.post("/predict", json=example).status_code == 422


def test_explicit_nulls_supported(client, example):
    example["ca"] = None
    assert client.post("/predict", json=example).status_code == 200


def test_metrics_record_requests(client, example):
    client.post("/predict", json=example)
    text = client.get("/metrics").text
    assert "heartcare_predictions_total" in text
    assert "heartcare_request_seconds_count" in text


def test_missing_model_fails_at_startup(tmp_path):
    with pytest.raises(FileNotFoundError):
        with TestClient(create_app(tmp_path / "missing.joblib")):
            pass
