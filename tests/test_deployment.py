"""Tests for Docker, Kubernetes manifests, JSON logging, and deployment endpoints."""

import io
import json
import logging
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app import JsonFormatter, PredictionInput, app, health, predict, readiness

ROOT = Path(__file__).resolve().parent.parent


# ================================================================
# Dockerfile tests
# ================================================================
class TestDockerfiles:
    """Validate that required Docker files exist and are well-formed."""

    def test_dockerfile_exists(self):
        assert (ROOT / "Dockerfile").exists()

    def test_dockerignore_exists(self):
        assert (ROOT / ".dockerignore").exists()

    def test_dockerfile_exposes_port_8000(self):
        content = (ROOT / "Dockerfile").read_text()
        assert "EXPOSE 8000" in content

    def test_dockerfile_uses_non_root_user(self):
        content = (ROOT / "Dockerfile").read_text()
        assert "USER" in content

    def test_dockerfile_has_healthcheck(self):
        content = (ROOT / "Dockerfile").read_text()
        assert "HEALTHCHECK" in content

    def test_dockerignore_excludes_venv(self):
        content = (ROOT / ".dockerignore").read_text()
        assert ".venv" in content

    def test_dockerignore_excludes_git(self):
        content = (ROOT / ".dockerignore").read_text()
        assert ".git" in content

    def test_dockerignore_excludes_data(self):
        content = (ROOT / ".dockerignore").read_text()
        assert "data/" in content


# ================================================================
# Kubernetes manifest fixtures & tests
# ================================================================
@pytest.fixture(scope="module")
def deployment_manifest():
    path = ROOT / "k8s" / "deployment.yaml"
    assert path.exists(), "k8s/deployment.yaml not found"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def service_manifest():
    path = ROOT / "k8s" / "service.yaml"
    assert path.exists(), "k8s/service.yaml not found"
    with open(path) as f:
        return yaml.safe_load(f)


class TestKubernetesManifests:
    """Validate Kubernetes YAML structure against assignment requirements."""

    def test_deployment_api_version(self, deployment_manifest):
        assert deployment_manifest["apiVersion"] == "apps/v1"

    def test_deployment_kind(self, deployment_manifest):
        assert deployment_manifest["kind"] == "Deployment"

    def test_deployment_name(self, deployment_manifest):
        assert deployment_manifest["metadata"]["name"] == "mp148-api"

    def test_deployment_replicas(self, deployment_manifest):
        assert deployment_manifest["spec"]["replicas"] == 4

    def test_deployment_image_tag(self, deployment_manifest):
        container = deployment_manifest["spec"]["template"]["spec"]["containers"][0]
        assert container["name"] == "mp148-api"
        assert container["image"] == "mp148-api:1.0"

    def test_deployment_container_port(self, deployment_manifest):
        containers = deployment_manifest["spec"]["template"]["spec"]["containers"]
        ports = containers[0]["ports"]
        assert any(p["containerPort"] == 8000 for p in ports)

    def test_deployment_has_readiness_probe(self, deployment_manifest):
        container = deployment_manifest["spec"]["template"]["spec"]["containers"][0]
        assert "readinessProbe" in container
        assert container["readinessProbe"]["httpGet"]["path"] == "/health"
        assert container["readinessProbe"]["httpGet"]["port"] == 8000
        assert container["readinessProbe"]["initialDelaySeconds"] == 10

    def test_deployment_has_liveness_probe(self, deployment_manifest):
        container = deployment_manifest["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container
        assert container["livenessProbe"]["httpGet"]["path"] == "/health"
        assert container["livenessProbe"]["httpGet"]["port"] == 8000
        assert container["livenessProbe"]["initialDelaySeconds"] == 30
        assert (
            container["livenessProbe"]["initialDelaySeconds"]
            > container["readinessProbe"]["initialDelaySeconds"]
        )

    def test_deployment_has_startup_probe(self, deployment_manifest):
        container = deployment_manifest["spec"]["template"]["spec"]["containers"][0]
        assert "startupProbe" in container
        assert container["startupProbe"]["httpGet"]["path"] == "/health"
        assert container["startupProbe"]["httpGet"]["port"] == 8000

    def test_deployment_has_resource_limits(self, deployment_manifest):
        container = deployment_manifest["spec"]["template"]["spec"]["containers"][0]
        assert "resources" in container
        assert "limits" in container["resources"]
        assert "requests" in container["resources"]

    def test_deployment_rolling_update_strategy(self, deployment_manifest):
        strategy = deployment_manifest["spec"]["strategy"]
        assert strategy["type"] == "RollingUpdate"

    def test_deployment_selector_matches_labels(self, deployment_manifest):
        selector = deployment_manifest["spec"]["selector"]["matchLabels"]
        template_labels = deployment_manifest["spec"]["template"]["metadata"]["labels"]
        for key, value in selector.items():
            assert template_labels.get(key) == value

    def test_service_api_version(self, service_manifest):
        assert service_manifest["apiVersion"] == "v1"

    def test_service_kind(self, service_manifest):
        assert service_manifest["kind"] == "Service"

    def test_service_name(self, service_manifest):
        assert service_manifest["metadata"]["name"] == "mp148-svc"

    def test_service_type(self, service_manifest):
        assert service_manifest["spec"]["type"] == "ClusterIP"

    def test_service_port(self, service_manifest):
        ports = service_manifest["spec"]["ports"]
        assert any(p["port"] == 80 for p in ports)

    def test_service_target_port(self, service_manifest):
        ports = service_manifest["spec"]["ports"]
        assert any(p["targetPort"] == 8000 for p in ports)

    def test_service_selector_matches_deployment(self, deployment_manifest, service_manifest):
        deploy_labels = deployment_manifest["spec"]["template"]["metadata"]["labels"]
        svc_selector = service_manifest["spec"]["selector"]
        for key, value in svc_selector.items():
            assert deploy_labels.get(key) == value


# ================================================================
# Readiness and health endpoint tests
# ================================================================
class TestHealthAndReadinessEndpoints:
    """Verify health and readiness probe endpoints."""

    def test_health_direct(self):
        response = health()
        assert response["status"] == "ok"
        assert response["model_loaded"] is True
        assert response["model_version"] == 4

    def test_readiness_direct(self):
        response = readiness()
        assert response["status"] == "ready"
        assert response["model_loaded"] is True
        assert response["model_version"] == 4

    def test_readiness_http(self):
        client = TestClient(app)
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["model_loaded"] is True
        assert data["model_version"] == 4

    def test_health_http(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert data["model_version"] == 4


# ================================================================
# Logging tests (Machine-readable JSON)
# ================================================================
class TestApplicationLogging:
    """Verify that the app configures and executes machine-readable JSON logging."""

    def test_app_uses_logging(self):
        content = (ROOT / "app.py").read_text()
        assert "import logging" in content
        assert "import json" in content

    def test_app_configures_json_formatter(self):
        content = (ROOT / "app.py").read_text()
        assert "class JsonFormatter" in content
        assert "json.dumps" in content

    def test_app_logs_to_stdout(self):
        content = (ROOT / "app.py").read_text()
        assert "StreamHandler(sys.stdout)" in content

    def test_app_has_lifespan_logging(self):
        content = (ROOT / "app.py").read_text()
        assert "starting up" in content.lower() or "startup" in content.lower()

    def test_app_has_prediction_logging(self):
        content = (ROOT / "app.py").read_text()
        assert "prediction" in content.lower()

    def test_prediction_emits_valid_json_log(self):
        """Execute a prediction and verify that captured log lines parse as valid JSON."""
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setFormatter(JsonFormatter())

        target_logger = logging.getLogger("tea_leaf_api")
        target_logger.addHandler(ch)

        try:
            data = PredictionInput(
                worker_exp_yr=48,
                rain_mm_week=285,
                slope_deg=21,
                temp_c=15.9,
                bush_age_yr=10,
                hours_worked=5.4,
                flush="monsoon",
                section="River Side",
            )
            result = predict(data)
            assert "predicted_yield_kg_per_worker" in result

            log_output = log_capture_string.getvalue().strip()
            assert log_output, "No log records captured"

            # Parse each captured line as JSON
            lines = [line for line in log_output.split("\n") if line.strip()]
            records = [json.loads(line) for line in lines]

            # Look for the prediction_success record
            success_records = [r for r in records if r.get("event") == "prediction_success"]
            assert len(success_records) >= 1, f"Expected prediction_success event, found {records}"

            rec = success_records[0]
            assert "timestamp" in rec
            assert rec["level"] == "INFO"
            assert rec["model_version"] == 4
            assert "prediction" in rec
            assert "latency_ms" in rec
            assert rec["status_code"] == 200
            assert rec["endpoint"] == "/predict"
        finally:
            target_logger.removeHandler(ch)
