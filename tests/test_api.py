"""
Basic integration tests for OffshoreIQ.
Run with: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "OffshoreIQ" in response.text


def test_rfp_analyze_empty_body():
    response = client.post("/api/v1/rfp/analyze", json={"rfp_text": ""})
    assert response.status_code == 422  # Validation error (min_length)


def test_rfp_analyze_short_text():
    response = client.post("/api/v1/rfp/analyze", json={"rfp_text": "too short"})
    assert response.status_code == 422


@patch("app.api.routes.run_pipeline")
def test_rfp_analyze_success(mock_pipeline):
    """Test RFP analysis with mocked pipeline (no LLM/Neo4j needed)."""
    mock_pipeline.return_value = {
        "requirements": {
            "skills": ["Python", "FastAPI"],
            "compliance_frameworks": ["GDPR"],
            "certifications": [],
            "sector": "Banking & Finance",
            "languages": ["French"],
            "summary": "Test summary.",
            "seniority": "senior",
        },
        "team_engineers": [
            {
                "id": "eng001", "name": "Youssef El Amrani",
                "city": "Casablanca", "years_exp": 6,
                "languages": ["French", "English"],
                "matching_skills": ["Python", "FastAPI"],
                "match_score": 0.85,
                "clients": [], "compliance_experience": [],
            }
        ],
        "gaps": [],
        "proposal": "We are pleased to propose our team...",
        "graph_data": {"nodes": [], "edges": []},
        "agent_trace": [
            {"agent": "RFPParserAgent", "status": "success", "output": "Parsed."},
        ],
    }

    response = client.post(
        "/api/v1/rfp/analyze",
        json={"rfp_text": "We need a Python FastAPI team with GDPR expertise for a French banking client."},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["matched_engineers"]) == 1
    assert data["matched_engineers"][0]["name"] == "Youssef El Amrani"
    assert data["matched_engineers"][0]["match_score"] == 0.85
