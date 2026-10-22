import pytest
from backend.app.database import init_db
from backend.app.services.soul import SoulEngine


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_soul_evolution_and_rollback():
    initial_state = SoulEngine.get_current_state()
    initial_ver = initial_state.version

    # Evolve interests
    evolved = SoulEngine.evolve_interests(["微观量子世界", "独立开源硬件"], "今天看完了量子计算与树莓派工程")
    assert evolved.version == initial_ver + 1
    assert "微观量子世界" in evolved.interests
    assert "独立开源硬件" in evolved.interests

    # Check history
    history = SoulEngine.get_version_history()
    assert len(history) >= 2
    assert history[0].version == evolved.version

    # Rollback to initial version
    rolled_back = SoulEngine.rollback_state(initial_ver)
    assert rolled_back.version == evolved.version + 1
    assert "【主人指令回滚】" in rolled_back.reason
    assert "微观量子世界" not in rolled_back.interests
