"""Tea Leaf Yield Prediction API — FastAPI application with production JSON logging."""

import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from serving import (
    build_feature_dataframe,
    load_serving_config,
    load_serving_model,
)

# ---------------------------------------------------------------------------
# Machine-readable JSON logging configuration
# ---------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    """Custom logging formatter that outputs structured JSON strings per line."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include structured extra fields if present
        for key in (
            "event",
            "request_id",
            "endpoint",
            "method",
            "status_code",
            "model_version",
            "prediction",
            "latency_ms",
            "client_ip",
            "error",
        ):
            if hasattr(record, key):
                log_payload[key] = getattr(record, key)

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())

logger = logging.getLogger("tea_leaf_api")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
SERVING_CONFIG = load_serving_config()
MODEL_PATH = SERVING_CONFIG["model_path"]
MODEL_VERSION = SERVING_CONFIG["model_version"]
FEATURES = SERVING_CONFIG["features"]
MAX_HOURS_WORKED = SERVING_CONFIG["max_hours_worked"]
MIN_RAIN_MM_WEEK = SERVING_CONFIG["min_rain_mm_week"]

# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
try:
    model = load_serving_model(SERVING_CONFIG)
    logger.info(
        "Model v%s loaded successfully",
        MODEL_VERSION,
        extra={
            "event": "model_load_success",
            "model_version": MODEL_VERSION,
            "model_path": MODEL_PATH,
        },
    )
except Exception as exc:
    logger.exception(
        "Failed to load model v%s",
        MODEL_VERSION,
        extra={
            "event": "model_load_failure",
            "model_version": MODEL_VERSION,
            "error": str(exc),
        },
    )
    model = None


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan manager for startup and shutdown logging."""
    logger.info(
        "Application starting up (model_version=v%s)",
        MODEL_VERSION,
        extra={
            "event": "app_startup",
            "model_version": MODEL_VERSION,
        },
    )
    yield
    logger.info(
        "Application shutting down",
        extra={
            "event": "app_shutdown",
            "model_version": MODEL_VERSION,
        },
    )


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Tea Leaf Yield Prediction API",
    description="Predict tea leaf yield in kg per worker with machine-readable JSON logging.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors in machine-readable JSON format and return HTTP 422."""
    request_id = str(uuid.uuid4())
    logger.warning(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
        extra={
            "event": "validation_error",
            "request_id": request_id,
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": 422,
            "model_version": MODEL_VERSION,
            "error": exc.errors(),
        },
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class PredictionInput(BaseModel):
    worker_exp_yr: float
    rain_mm_week: float = Field(
        ..., ge=MIN_RAIN_MM_WEEK, description="Weekly rainfall in mm (must be >= 0)"
    )
    slope_deg: float
    temp_c: float
    bush_age_yr: float
    hours_worked: float = Field(
        ..., ge=0, le=MAX_HOURS_WORKED, description="Hours worked (must be <= 15)"
    )
    flush: str
    section: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "Tea Leaf Yield Prediction API is running",
        "model_version": MODEL_VERSION,
    }


@app.get("/health")
def health():
    if model is None:
        logger.error(
            "Health check failed — model not loaded",
            extra={
                "event": "health_check",
                "status_code": 503,
                "endpoint": "/health",
                "method": "GET",
                "model_version": MODEL_VERSION,
            },
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "model_loaded": False,
                "model_version": MODEL_VERSION,
            },
        )
    return {
        "status": "ok",
        "model_loaded": True,
        "model_version": MODEL_VERSION,
    }


@app.get("/ready")
def readiness():
    """Kubernetes readiness probe endpoint."""
    if model is None:
        logger.warning(
            "Readiness check failed — model not loaded",
            extra={
                "event": "readiness_check",
                "status_code": 503,
                "endpoint": "/ready",
                "method": "GET",
                "model_version": MODEL_VERSION,
            },
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "model_loaded": False,
                "model_version": MODEL_VERSION,
            },
        )
    return {
        "status": "ready",
        "model_loaded": True,
        "model_version": MODEL_VERSION,
    }


@app.post("/predict")
def predict(data: PredictionInput):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    if model is None:
        logger.error(
            "Prediction attempted but model is not loaded",
            extra={
                "event": "prediction_error",
                "request_id": request_id,
                "endpoint": "/predict",
                "method": "POST",
                "status_code": 503,
                "model_version": MODEL_VERSION,
            },
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Model not loaded",
                "model_version": MODEL_VERSION,
            },
        )

    input_data = build_feature_dataframe(data.model_dump(), FEATURES)

    try:
        raw_pred = model.predict(input_data)[0]
        prediction_val = round(float(raw_pred), 2)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            "Prediction successful: yield=%.2f kg/worker in %.2f ms",
            prediction_val,
            latency_ms,
            extra={
                "event": "prediction_success",
                "request_id": request_id,
                "endpoint": "/predict",
                "method": "POST",
                "status_code": 200,
                "model_version": MODEL_VERSION,
                "prediction": prediction_val,
                "latency_ms": latency_ms,
            },
        )

        return {
            "predicted_yield_kg_per_worker": prediction_val,
            "model_version": MODEL_VERSION,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(
            "Prediction failed after %.2f ms: %s",
            latency_ms,
            str(exc),
            extra={
                "event": "prediction_failure",
                "request_id": request_id,
                "endpoint": "/predict",
                "method": "POST",
                "status_code": 500,
                "model_version": MODEL_VERSION,
                "latency_ms": latency_ms,
                "error": str(exc),
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Prediction failed",
                "model_version": MODEL_VERSION,
            },
        )
