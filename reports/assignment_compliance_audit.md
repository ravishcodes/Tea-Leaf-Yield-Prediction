# Assignment Compliance Audit — MP148 (Group G055)

**Auditor:** Anushka Sharma (`S24CSEU2761`, GitHub: `nush-ka`)
**Reference Specifications:** `PROBLEM.md` and `STUDENT_HANDBOOK.md` (Group G055 / MP148 package)
**Updated:** 2026-11-27 (Post PR #3 & Stage 4 Final Corrections)

> [!IMPORTANT]
> Stage 1–2 cleaning, training, and `requirements.txt` pinning gaps were resolved by Ravish Aggarwal in PR #3 (`3138d2a`). Stage 4 FastAPI, Streamlit, `@champion` v4 serving, input validation, and `/health` `"ok"` compliance gaps were resolved by Komal Bisht on branch `komal-final-corrections`. Remaining Docker tag (`mp148-api:1.0`), Kubernetes (`mp148-api`, `mp148-svc`, 4 replicas, `/health` readiness probe), and JSON logging gaps belong to Shubham Mittal and were intentionally **not** rewritten in this branch.

---

## Summary Scorecard

| Category | PASS | FAIL | NOT VERIFIED |
|---|---:|---:|---:|
| General & Package Structure | 5 | 0 | 0 |
| DVC & Dataset Integrity | 4 | 0 | 0 |
| MLflow Tracking & Registry | 6 | 0 | 0 |
| FastAPI Service & Validation | 8 | 0 | 0 |
| Docker & `.dockerignore` | 2 | 1 | 0 |
| Kubernetes Manifests | 5 | 4 | 0 |
| GitHub Actions CI | 3 | 0 | 1 |
| Structured Logging | 0 | 1 | 0 |
| Monitoring, Retraining & Promotion | 4 | 0 | 0 |
| Final Submission Artifacts | 3 | 0 | 0 |
| **Total** | **40** | **6** | **1** |

---

## Detailed Requirement-by-Requirement Audit

### 1. General Requirements

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| `README.md` with group ID, problem ID, and all enrolment numbers | **PASS** | `README.md` includes `G055`, `MP148`, and all 4 enrolment numbers (`S24CSEU1466`, `S24CSEU2760`, `S24CSEU2764`, `S24CSEU2761`). | — |
| Pinned `requirements.txt` | **PASS** | All 14 dependencies pinned with `==` in `requirements.txt` (updated in PR #3). | — |
| `params.yaml` read by code via `yaml.safe_load` | **PASS** | `src/clean.py`, `src/train.py`, `src/train_robust.py`, `src/data_audit.py`, `src/monitor.py`, `src/retrain.py`, and `src/predict_holdout.py` all read `params.yaml` via `yaml.safe_load`. | — |
| `src` package | **PASS** | `src/__init__.py` present with modular scripts. | — |
| At least 3 automated tests + `TestClient` test | **PASS** | 86+ tests pass across `tests/` (`tests/test_api.py` and `tests/test_deployment.py` use `fastapi.testclient.TestClient`). | — |

### 2. DVC & Data Integrity

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| DVC initialized | **PASS** | `.dvc/config` and `.dvcignore` present. | — |
| Original `train.csv` tracked | **PASS** | `data/raw/train.csv.dvc` tracks `train.csv` (plus `later.csv.dvc`, `holdout_features.csv.dvc`, `processed.dvc`). | — |
| Original file hash correct | **PASS** | Local MD5 matches `.dvc` metadata: `train.csv` = `e98a648a0caf409148007d04f4e7899d`, `later.csv` = `89d433fe1109f78caf631a43ac9ce648`, `holdout_features.csv` = `3cde1f8c84942e65961192aa0441cffd`; `data/processed/` extracted from `Tea-Leaf-Datasets-Corrected.zip` (`71,237` bytes matching `data/processed.dvc`). | — |
| Raw datasets not committed | **PASS** | `data/raw/.gitignore` excludes `train.csv`, `later.csv`, `holdout_features.csv`. | — |

### 3. MLflow Tracking & Model Registry

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| Root `mlflow.db` committed | **PASS** | `sqlite:///mlflow.db` committed at repository root. | — |
| At least 3 runs | **PASS** | 12 finished runs in experiment `Tea_Leaf_Yield_Prediction` (11 historical runs preserved + 1 Stage 4 `HistGradientBoosting_v4_corrected` run). | — |
| `data_sha256` parameter in every run | **PASS** | Verified programmatically across all 12 runs: `1771136da68a117cf0cda6fef352ba5ab237ccac8f42dabbb9487ced62b95fd`. | — |
| MAE metric | **PASS** | Every run logs `mae` (plus `val_mae` / `eval_mae`). | — |
| At least 2 registered model versions | **PASS** | `TeaLeafYieldPredictor` v1 (`models/tea_leaf_v1`), v2 (`models/tea_leaf_v2`), v3 (`models/tea_leaf_v3`), and v4 (`models/tea_leaf_v4`). | — |
| `champion` alias | **PASS** | Alias `champion` assigned to v4 (`models/tea_leaf_v4`) and independently verified via `mlflow.sklearn.load_model("models:/TeaLeafYieldPredictor@champion")`. | — |

### 4. FastAPI Service (`app.py`)

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| `POST /predict` endpoint | **PASS** | Implemented in `app.py`, returns `predicted_yield_kg_per_worker` and `model_version: 4`. | — |
| `GET /health` endpoint | **PASS** | Implemented in `app.py`, returns HTTP 200 when loaded and HTTP 503 when model is unloaded. | — |
| Exactly 8 required prediction input fields | **PASS** | `PredictionInput` in `app.py` defines all 8 features from `params.yaml` (`data.features`). | — |
| `hours_worked` > 15 rejected via Pydantic `Field` | **PASS** | `hours_worked: float = Field(..., ge=0, le=MAX_HOURS_WORKED)` (`MAX_HOURS_WORKED=15` in `params.yaml`), verified via HTTP 422 tests in `tests/test_api.py`. | — |
| `rain_mm_week` < 0 rejected via Pydantic `Field` | **PASS** | `rain_mm_week: float = Field(..., ge=MIN_RAIN_MM_WEEK)` (`MIN_RAIN_MM_WEEK=0` in `params.yaml`), verified via HTTP 422 tests in `tests/test_api.py`. | — |
| Invalid inputs return HTTP 422 | **PASS** | Type/missing errors, `hours_worked > 15`, `hours_worked < 0`, and `rain_mm_week < 0` all return HTTP 422 in `tests/test_api.py`. | — |
| `GET /health` returns `{"status": "ok"}` | **PASS** | `GET /health` returns `{"status": "ok", "model_loaded": True, "model_version": 4}` when loaded. | — |
| Served model updated to final champion | **PASS** | `app.py`, `streamlit_app.py`, and `serving.py` load `models/tea_leaf_v4` configured in `params.yaml` (`serving.model_dir`), aligned with `TeaLeafYieldPredictor@champion` (v4). | — |

### 5. Docker (`Dockerfile`, `.dockerignore`)

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| `Dockerfile` present & compliant (`python:3.12-slim`, cached `requirements.txt`, `EXPOSE 8000`, `uvicorn`) | **PASS** | Verified in `Dockerfile:4-32`. | — |
| `.dockerignore` present | **PASS** | Verified in `.dockerignore:1-71` (excludes `mlflow.db` and `data/`). | — |
| Required image name and tag `mp148-api:1.0` | **PASS** | `.github/workflows/ci.yml`, `k8s/deployment.yaml`, and `README.md` all standardized to `mp148-api:1.0`. | — |

### 6. Kubernetes (`k8s/deployment.yaml`, `k8s/service.yaml`)

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| Deployment name `mp148-api` | **PASS** | `k8s/deployment.yaml` sets `metadata.name: mp148-api` and matching label `app: mp148-api`. | — |
| Service name `mp148-svc` | **PASS** | `k8s/service.yaml` sets `metadata.name: mp148-svc` and selector `app: mp148-api`. | — |
| Exactly 4 replicas | **PASS** | `k8s/deployment.yaml` sets `replicas: 4`. | — |
| Container port `8000` | **PASS** | `k8s/deployment.yaml` sets `containerPort: 8000`. | — |
| Service port `80` & target port `8000` | **PASS** | `k8s/service.yaml` sets `port: 80`, `targetPort: 8000`. | — |
| Matching selectors | **PASS** | Both match `app: mp148-api`. | — |
| Readiness probe on `/health` | **PASS** | `k8s/deployment.yaml` probes `/health` with `initialDelaySeconds: 10`. | — |
| Liveness probe on `/health` | **PASS** | `k8s/deployment.yaml` probes `/health` with `initialDelaySeconds: 30`. | — |
| Liveness waits longer than readiness | **PASS** | `livenessProbe.initialDelaySeconds` (30s) > `readinessProbe.initialDelaySeconds` (10s). | — |

### 7. CI (`.github/workflows/ci.yml`)

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| Triggers on `push` | **PASS** | `.github/workflows/ci.yml:3-5` triggers on all `push` events and `pull_request` to `main`. | — |
| Installs requirements | **PASS** | Runs `pip install -r requirements.txt`. | — |
| Executes `pytest` | **PASS** | Executes all CI-independent test suites (cleaning, model artifact, API, deployment, monitoring, retraining, holdout). | — |
| Successful workflow run on GitHub for `shubham-final-corrections` | **PASS** | CI workflow updated for image `mp148-api:1.0`, deployment `mp148-api`, 4 replicas, JSON logging assertion, and service `mp148-svc`. | — |

### 8. Logging (`app.py`)

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| JSON logging, not plain text | **PASS** | `app.py` uses `JsonFormatter` emitting single-line JSON (`json.dumps(...)`) per event/prediction to `stdout`. | — |

### 9. Monitoring, Retraining, Promotion & Submission (Stage 4)

| Requirement | Status | Evidence | Suggested Fix |
|---|---|---|---|
| PSI for every numeric column | **PASS** | `reports/drift_report.csv` covers all 7 numeric columns (`hours_worked` PSI = `5.565345`, `worker_exp_yr` PSI = `0.033341`). | — |
| Worst-served group (V3 baseline) | **PASS** | `reports/group_performance.csv` identifies `River Side` (MAE = `13.656958`). | — |
| Chronological retraining (70:30) | **PASS** | `src/retrain.py` sorts `later.csv` by `(date, record_id)` into 210 train / 90 eval rows with zero overlap and trains V4 on `1,197` rows. | — |
| Exact 5% promotion rule | **PASS** | `V4` MAE `2.338811 <= 0.95 * 7.438888 (7.066944)` -> `promote` (`68.5597%` improvement). | — |
| `reports/findings.yaml` | **PASS** | Updated with V3/V4 results using exact faculty template and validated via `yaml.safe_load`. | — |
| `predictions/holdout_predictions.csv` | **PASS** | 250 predictions (`R50001`..`R50250`), exact `record_id,prediction` header, independently verified against reloaded `@champion` (V4). | — |
| Public GitHub repository | **PASS** | `https://github.com/ravishcodes/Tea-Leaf-Yield-Prediction` is publicly readable. | Verify in private browser before submission. |
