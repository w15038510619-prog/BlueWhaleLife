import os
import pytest

# Ensure complete isolation of production database during tests
os.environ["WHALE_LIFE_TEST_MODE"] = "1"
os.environ["TESTING"] = "1"

from backend.app.database import init_db, get_db_path

@pytest.fixture(autouse=True, scope="session")
def setup_test_database():
    test_db = get_db_path()
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass
    init_db()
    yield
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass
