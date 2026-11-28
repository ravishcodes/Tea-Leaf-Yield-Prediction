# 🍃 Tea Leaf Yield Prediction

Predict tea leaf yield (kg per worker) based on plantation conditions, worker experience, and environmental features.

**Course:** SCSE3040 — MLOps | **Group:** G055 | **Problem ID:** MP148

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker Desktop (for containerized deployment)
- kubectl + Kubernetes cluster (for orchestrated deployment)

### Local Development

```bash
python -m pip install -r requirements.txt

# Run FastAPI server
uvicorn app:app --host 0.0.0.0 --port 8000

# Run Streamlit frontend
streamlit run streamlit_app.py

# Run tests
python -m pytest tests/test_model_artifact.py tests/test_api.py tests/test_deployment.py tests/test_monitoring.py tests/test_retraining.py tests/test_holdout_predictions.py -v
```

### Stage 4 Monitoring, Retraining & Holdout Predictions

```bash
python -m src.data_audit        # Audit the 7 faculty data quality issues
python -m src.monitor           # PSI drift report + v1 section-wise MAE on later.csv
python -m src.retrain           # Chronological 70:30 retraining, 5% rule & MLflow @champion
python -m src.predict_holdout   # Generate predictions/holdout_predictions.csv via @champion
```

### Docker Deployment

```bash
docker build -t mp148-api:1.0 .
docker run -d --name mp148-api -p 8000:8000 mp148-api:1.0
```

### Kubernetes Deployment

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/mp148-api --timeout=180s
kubectl port-forward service/mp148-svc 8080:80
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home — service status and served model version |
| GET | `/health` | Health check (`{"status": "ok", "model_loaded": true, "model_version": 4}`) |
| GET | `/ready` | Readiness probe |
| POST | `/predict` | Predict tea leaf yield (rejects `hours_worked > 15` and `rain_mm_week < 0` with HTTP 422) |
| GET | `/docs` | Swagger documentation |

### Sample Prediction Request

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "worker_exp_yr": 12,
    "rain_mm_week": 150,
    "slope_deg": 17,
    "temp_c": 25,
    "bush_age_yr": 10,
    "hours_worked": 6,
    "flush": "monsoon",
    "section": "River Side"
  }'
```

**Response:**

```json
{"predicted_yield_kg_per_worker": 24.39, "model_version": 4}
```

---

## Project Structure

```
├── app.py                      # FastAPI application with logging (serves v4 @champion)
├── serving.py                  # Shared serving config & champion model loader
├── streamlit_app.py            # Streamlit frontend (serves v4 @champion)
├── Dockerfile                  # Production Docker image
├── .dockerignore               # Docker build exclusions
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render deployment config
├── models/tea_leaf_v1/         # Initial MLflow v1 model artifacts
├── models/tea_leaf_v2/         # Initial retrained MLflow v2 model artifacts
├── models/tea_leaf_v3/         # Corrected baseline MLflow v3 model artifacts
├── models/tea_leaf_v4/         # Final retrained MLflow v4 model artifacts (@champion)
├── mlflow.db                   # SQLite MLflow tracking & model registry
├── params.yaml                 # Centralized pipeline configuration
├── predictions/
│   └── holdout_predictions.csv # Final holdout predictions (250 rows)
├── k8s/
│   ├── deployment.yaml         # Kubernetes Deployment (3 replicas)
│   └── service.yaml            # Kubernetes Service (ClusterIP)
├── tests/
│   ├── test_api.py             # API endpoint tests
│   ├── test_model_artifact.py  # Model artifact tests
│   ├── test_deployment.py      # Docker & Kubernetes manifest tests
│   ├── test_monitoring.py      # PSI drift & section-wise evaluation tests
│   ├── test_retraining.py      # Chronological split & 5% promotion rule tests
│   ├── test_holdout_predictions.py # Holdout prediction schema & validation tests
│   ├── test_cleaning_pipeline.py # Synthetic cleaning pipeline tests
│   ├── test_data_quality.py    # Data quality tests (requires datasets)
│   └── test_model.py           # Model tests (requires MLflow DB)
├── docs/
│   ├── komal_contribution.md   # API, serving, Streamlit, CI & attribution documentation
│   ├── shubham_deployment.md   # Deployment documentation
│   └── anushka_monitoring.md   # Monitoring, retraining & holdout documentation
├── src/                        # Data cleaning, training, monitoring & retraining scripts
├── data/                       # DVC-tracked datasets
├── notebooks/                  # Exploratory analysis
└── reports/                    # Model comparison, drift, compliance & findings reports
```

---

## Team Contributions

| Member | Enrolment | Responsibilities |
|--------|-----------|-----------------|
| Ravish Aggarwal | S24CSEU1466 | Repository, DVC, data cleaning, model training, MLflow tracking |
| Komal Bisht | S24CSEU2760 | Model artifact testing, CI, FastAPI serving, Render, Streamlit |
| Shubham Mittal | S24CSEU2764 | Docker, Kubernetes, logging, CI deployment tests, documentation |
| Anushka Sharma | S24CSEU2761 | Data audit, PSI drift monitoring, chronological retraining, `@champion` selection, holdout predictions, `findings.yaml`, compliance audit |
