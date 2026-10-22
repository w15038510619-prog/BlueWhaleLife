import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["app"] == "BlueWhaleLife"


def test_api_pet_status():
    res = client.get("/api/pet/status")
    assert res.status_code == 200
    data = res.json()
    assert "state" in data
    assert "mood" in data
    assert "growth_score" in data


def test_api_pet_chat():
    res = client.post("/api/pet/chat", json={"message": "你好呀小肥鱼！"})
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 0


def test_api_discovery_explore():
    res = client.post("/api/discovery/explore")
    assert res.status_code == 200
    candidates = res.json()
    assert isinstance(candidates, list)
    assert len(candidates) > 0
    assert "reason" in candidates[0]


def test_api_watch_and_diary():
    # Discover candidates
    c_res = client.get("/api/discovery/candidates")
    assert c_res.status_code == 200
    candidates = c_res.json()
    bvid = candidates[0]["bvid"]

    # Watch video
    watch_res = client.post(f"/api/discovery/watch/{bvid}")
    assert watch_res.status_code == 200
    analysis = watch_res.json()
    assert analysis["bvid"] == bvid
    assert len(analysis["summary"]) > 0
    assert len(analysis["learned"]) > 0
    assert len(analysis["viewpoint"]) > 0

    # Retrieve from diary
    video_res = client.get(f"/api/videos/{bvid}")
    assert video_res.status_code == 200
    assert video_res.json()["title"] == analysis["title"]


def test_api_settings_update():
    # Test updating settings
    res = client.post("/api/settings", json={
        "demo_mode": True,
        "novelty_weight": 0.4
    })
    assert res.status_code == 200
    data = res.json()
    assert data["demo_mode"] is True
    assert data["novelty_weight"] == 0.4
