import pytest
from backend.app.database import init_db
from backend.app.services.discovery import DiscoveryEngine


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_autonomous_exploration():
    candidates = DiscoveryEngine.explore()
    assert len(candidates) > 0

    first = candidates[0]
    assert first.bvid.startswith("BV")
    assert len(first.reason) > 5  # Has a concrete explanation why chosen
    assert 0.0 <= first.score <= 1.0


def test_cached_candidates():
    cached = DiscoveryEngine.get_cached_candidates(limit=5)
    assert len(cached) > 0
    assert cached[0].status == "discovered"
