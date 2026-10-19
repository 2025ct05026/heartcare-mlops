"""Validated prediction service with request counters and latency metrics."""

import hashlib
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

from heartcare.data import FEATURES, ROOT

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("heartcare")
REQUESTS = Counter("heartcare_requests_total", "HTTP responses", ["route", "method", "status"])
LATENCY = Histogram("heartcare_request_seconds", "HTTP response latency", ["route"])
PREDICTIONS = Counter("heartcare_predictions_total", "Predictions by class", ["prediction"])


class Patient(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    age: float | None = Field(..., ge=1, le=120)
    sex: Literal[0, 1] | None
    cp: Literal[1, 2, 3, 4] | None
    trestbps: float | None = Field(..., ge=50, le=300)
    chol: float | None = Field(..., ge=50, le=700)
    fbs: Literal[0, 1] | None
    restecg: Literal[0, 1, 2] | None
    thalach: float | None = Field(..., ge=40, le=250)
    exang: Literal[0, 1] | None
    oldpeak: float | None = Field(..., ge=0, le=10)
    slope: Literal[1, 2, 3] | None
    ca: Literal[0, 1, 2, 3] | None
    thal: Literal[3, 6, 7] | None


class Prediction(BaseModel):
    prediction: int
    probability: float
    confidence: float
    model_version: str


def create_app(model_path=None):
    path = Path(model_path or os.environ.get("MODEL_PATH", ROOT / "models/model.joblib"))

    @asynccontextmanager
    async def lifespan(app):
        # Load only trusted local artifacts. Joblib is executable serialization.
        app.state.model = joblib.load(path)
        app.state.version = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        yield

    app = FastAPI(title="HeartCare educational classifier", version="1.0", lifespan=lifespan)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - started
            route = request.scope.get("route")
            route_name = route.path if route else "unmatched"
            REQUESTS.labels(route_name, request.method, str(status)).inc()
            LATENCY.labels(route_name).observe(elapsed)
            logger.info(json.dumps({"route": route_name, "method": request.method,
                                    "status": status, "duration_ms": round(elapsed * 1000, 2)}))

    @app.get("/health")
    def health():
        return {"status": "ok", "model_version": app.state.version}

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.post("/predict", response_model=Prediction)
    def predict(patient: Patient):
        row = {k: np.nan if v is None else v for k, v in patient.model_dump().items()}
        probability = float(app.state.model.predict_proba(pd.DataFrame([row], columns=FEATURES))[0, 1])
        predicted = int(probability >= 0.5)
        PREDICTIONS.labels(str(predicted)).inc()
        return Prediction(prediction=predicted, probability=probability,
                          confidence=probability if predicted else 1 - probability,
                          model_version=app.state.version)

    return app


app = create_app()
