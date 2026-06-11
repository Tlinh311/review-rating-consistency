from pathlib import Path

# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from main import create_app


def test_health_stats_model_info_and_prediction():
    with TestClient(create_app()) as client:
        health = client.get("/api/health")
        stats = client.get("/api/stats")
        model_info = client.get("/api/model-info")
        prediction = client.post(
            "/api/predict",
            json={
                "review_text": "The food was excellent and the service was friendly.",
                "actual_rating": 5,
            },
        )

    assert health.status_code == 200
    assert health.json()["status"] == "ready"
    assert stats.status_code == 200
    assert stats.json()["dataset"]["total_clean"] == 9311
    assert model_info.status_code == 200
    assert prediction.status_code == 200
    assert prediction.json()["status"] == "consistent"


def test_random_example_endpoint():
    with TestClient(create_app()) as client:
        for ex_type in ["positive", "neutral", "contradictory"]:
            response = client.get(f"/api/random-example?type={ex_type}")
            assert response.status_code == 200
            data = response.json()
            assert "review" in data
            assert "rating" in data
            assert isinstance(data["review"], str)
            assert isinstance(data["rating"], int)
            if ex_type == "positive":
                assert data["rating"] >= 4
            elif ex_type == "neutral":
                assert data["rating"] == 3
            elif ex_type == "contradictory":
                assert data["rating"] in [1, 5]


def test_invalid_request_values_return_422():
    with TestClient(create_app()) as client:
        invalid_rating = client.post(
            "/api/predict",
            json={"review_text": "good food", "actual_rating": 8},
        )
        invalid_model = client.post(
            "/api/predict",
            json={
                "review_text": "good food",
                "actual_rating": 5,
                "model_name": "bad",
            },
        )
        invalid_text = client.post(
            "/api/predict",
            json={"review_text": "12345", "actual_rating": 1},
        )

    assert invalid_rating.status_code == 422
    assert invalid_model.status_code == 422
    assert invalid_text.status_code == 422


def test_missing_artifact_returns_service_unavailable(tmp_path: Path):
    app = create_app(
        model_path=tmp_path / "missing.joblib",
        metadata_path=tmp_path / "missing.json",
    )
    with TestClient(app) as client:
        health = client.get("/api/health")
        prediction = client.post(
            "/api/predict",
            json={"review_text": "good food", "actual_rating": 5},
        )

    assert health.status_code == 503
    assert health.json()["status"] == "error"
    assert prediction.status_code == 503


def test_static_page_has_no_external_cdn():
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert "https://" not in html
    assert "http://" not in html
