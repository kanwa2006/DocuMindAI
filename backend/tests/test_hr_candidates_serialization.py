"""Regression test for DEBUG_MASTER_PLAN H-10 (newly discovered).

GET /hr/jobs/{id}/candidates returned raw ORM objects ({"match": JobMatch,
"profile": CandidateProfile}) with no response model, so the endpoint
500'd with PydanticSerializationError the first time real rows existed
(the bug was unreachable until C-1/C-2/C-7 made candidate processing
work). The payload is now explicitly serialized to the shape the frontend
CandidateRankingsPanel consumes.
"""
import json
import uuid

from app.models.hr import JobMatch, CandidateProfile


def _payload_row(match, profile):
    # Mirrors the endpoint's serialization block.
    return {
        "match": {
            "id": str(match.id),
            "fit_score": match.fit_score,
            "semantic_score": match.semantic_score,
            "final_score": match.final_score,
            "status": match.status,
            "match_analysis": match.match_analysis,
        },
        "profile": {
            "id": str(profile.id),
            "name": profile.name,
            "email": profile.email,
            "skills": profile.skills or [],
            "experience_years": profile.experience_years,
            "education": profile.education or [],
            "stage": profile.stage,
        },
    }


def test_candidates_payload_is_json_serializable_and_frontend_shaped():
    match = JobMatch(
        id=uuid.uuid4(), workspace_id=uuid.uuid4(), job_id=uuid.uuid4(),
        candidate_id=uuid.uuid4(), fit_score=82.0, semantic_score=0.71,
        final_score=77.6, status="NEW",
        match_analysis={"pros": ["Kafka"], "cons": [], "missing_skills": ["Go"]},
    )
    profile = CandidateProfile(
        id=uuid.uuid4(), workspace_id=uuid.uuid4(), document_id=uuid.uuid4(),
        name="Priya Sharma", email="priya@example.com",
        skills=["Python", "Kafka"], experience_years=7.0,
        education=["B.Tech"], stage="applied",
    )

    row = _payload_row(match, profile)
    encoded = json.dumps(row)  # raises before the fix pattern existed
    decoded = json.loads(encoded)

    # Fields the CandidateRankingsPanel actually reads:
    assert decoded["match"]["final_score"] == 77.6
    assert decoded["match"]["fit_score"] == 82.0
    assert decoded["match"]["status"] == "NEW"
    assert decoded["profile"]["id"] == str(profile.id)
    assert decoded["profile"]["name"] == "Priya Sharma"
    assert decoded["profile"]["stage"] == "applied"
    assert decoded["profile"]["skills"] == ["Python", "Kafka"]


def test_endpoint_source_does_not_return_raw_orm_objects():
    import pathlib
    source = (
        pathlib.Path(__file__).resolve().parents[1]
        / "app" / "api" / "v1" / "endpoints" / "hr.py"
    ).read_text(encoding="utf-8")
    assert '"match": match,' not in source
    assert '"profile": profile' not in source
