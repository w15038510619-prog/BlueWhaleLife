import pytest
from fastapi.testclient import TestClient
from backend.app.main import app, _validate_base_url
from backend.app.config import AppSettings, protect_secret, unprotect_secret
from backend.app.services.llm_client import LLMClient, LLMAPIError
from backend.app.database import log_api_usage, get_daily_api_cost, get_api_usage_summary


@pytest.fixture
def client():
    return TestClient(app)


def test_dpapi_secret_encryption():
    test_key = "sk-aixoras-secret-test-token-abcdef123456"
    protected = protect_secret(test_key)
    assert protected.startswith("dpapi:") or protected.startswith("enc:")
    assert protected != test_key
    assert test_key not in protected

    recovered = unprotect_secret(protected)
    assert recovered == test_key


def test_ssrf_protection_guard():
    # Valid URLs
    _validate_base_url("https://api.aixoras.com/v1")
    _validate_base_url("http://127.0.0.1:8000/v1")
    _validate_base_url("https://api.deepseek.com/v1")

    # Invalid protocols
    with pytest.raises(Exception):
        _validate_base_url("file:///etc/passwd")
    with pytest.raises(Exception):
        _validate_base_url("gopher://evil.com")

    # Cloud metadata IP attack blocked
    with pytest.raises(Exception):
        _validate_base_url("http://169.254.169.254/latest/meta-data")


def test_api_usage_and_daily_budget():
    initial_cost = get_daily_api_cost()
    # Log simulated call
    cost_added = log_api_usage(
        model="deepseek-chat",
        endpoint="https://api.aixoras.com/v1/responses",
        protocol="responses",
        input_tokens=1000,
        output_tokens=500,
        caller="test_suite"
    )
    # 1000 * 1.0 + 500 * 2.0 = 2000 / 1_000_000 = 0.002
    assert cost_added == 0.002
    new_cost = get_daily_api_cost()
    assert new_cost >= initial_cost + 0.002

    summary = get_api_usage_summary()
    assert summary["total_calls"] >= 1
    assert summary["today_cost_cny"] >= 0.002


import asyncio

def test_llm_client_budget_guard():
    async def _run():
        settings = AppSettings(
            llm_base_url="https://api.aixoras.com/v1",
            llm_model="deepseek-chat",
            llm_protocol="responses",
            demo_mode=False,
            daily_cost_budget=0.0001
        )
        settings.llm_api_key = "sk-fake-valid-key"
        client = LLMClient(settings)

        with pytest.raises(LLMAPIError) as exc_info:
            await client.chat_completion([{"role": "user", "content": "hi"}])
        assert "已达到今日 API 费用预算限制" in str(exc_info.value)
    asyncio.run(_run())


def test_llm_client_emergency_stop_guard():
    async def _run():
        settings = AppSettings(
            llm_base_url="https://api.aixoras.com/v1",
            llm_model="deepseek-chat",
            demo_mode=False,
            emergency_stop=True
        )
        settings.llm_api_key = "sk-fake-valid-key"
        client = LLMClient(settings)

        with pytest.raises(LLMAPIError) as exc_info:
            await client.chat_completion([{"role": "user", "content": "hi"}])
        assert "紧急制动已触发" in str(exc_info.value)
    asyncio.run(_run())


def test_api_settings_and_test_connection_endpoint(client):
    # Test getting settings
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "llm_protocol" in data
    assert "daily_cost_budget" in data

    # Test test-connection endpoint without key -> returns clear error rather than fake reply
    res = client.post("/api/settings/test-connection", json={
        "base_url": "https://api.aixoras.com/v1",
        "api_key": "",
        "model": "deepseek-chat",
        "protocol": "responses"
    })
    assert res.status_code == 200
    test_result = res.json()
    assert test_result["success"] is False
    assert "未提供 API Key" in test_result.get("error_message", "")
