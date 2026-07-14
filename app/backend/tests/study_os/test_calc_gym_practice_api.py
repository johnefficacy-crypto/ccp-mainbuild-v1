from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import calc_gym_practice as api
from app.core.auth import get_current_user
from app.study_os import calc_gym
from tests.persona_questions._stub import SBStub

USER = "11111111-1111-1111-1111-111111111111"


def _client(sb):
    app = FastAPI()
    app.include_router(api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": USER}
    api.get_supabase_admin = lambda: sb
    return TestClient(app)


def test_get_and_submit_calc_gym_session():
    sb = SBStub({"calc_gym_sessions": [], "calc_gym_session_items": []})
    created = calc_gym.create_session(
        sb, user_id=USER, skill="tables", question_count=2, duration_sec=60, seed=8,
    )
    session_id = created["session_id"]
    client = _client(sb)
    current = client.get(f"/api/study/calculation-gym/sessions/{session_id}")
    assert current.status_code == 200
    assert "expected_answer" not in current.json()["items"][0]

    expected = calc_gym.generate_items("tables", 2, seed=8)
    response = client.post(
        f"/api/study/calculation-gym/sessions/{session_id}/submit",
        json={"answers": [
            {"item_index": item["item_index"], "user_answer": item["expected_answer"],
             "time_spent_sec": 2}
            for item in expected
        ]},
    )
    assert response.status_code == 200
    assert response.json()["score_correct"] == 2
    revealed = client.get(f"/api/study/calculation-gym/sessions/{session_id}").json()
    assert revealed["items"][0]["expected_answer"]


def test_duplicate_item_index_is_rejected():
    sb = SBStub({"calc_gym_sessions": [], "calc_gym_session_items": []})
    created = calc_gym.create_session(
        sb, user_id=USER, skill="tables", question_count=2, duration_sec=60, seed=8,
    )
    response = _client(sb).post(
        f"/api/study/calculation-gym/sessions/{created['session_id']}/submit",
        json={"answers": [
            {"item_index": 0, "user_answer": "1"},
            {"item_index": 0, "user_answer": "2"},
        ]},
    )
    assert response.status_code == 422
