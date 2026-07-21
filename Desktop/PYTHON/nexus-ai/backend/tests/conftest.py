import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock

# Register all models with Base before importing app so create_all sees them.
# These imports MUST come before `from app.main import app` to avoid the
# `import app.*` statement shadowing the FastAPI instance with the package.
import app.models.user          # noqa: F401
import app.models.upload_job    # noqa: F401
import app.models.sales_data    # noqa: F401
import app.models.dim_date      # noqa: F401
import app.models.dim_product   # noqa: F401
import app.models.dim_region    # noqa: F401
import app.models.dim_customer  # noqa: F401
import app.models.fact_sales    # noqa: F401

from app.db.postgres import Base, get_db
from app.core.limiter import limiter
from app.main import app

TEST_DB_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    limiter.enabled = False
    yield
    limiter.enabled = True
    limiter.reset()


@pytest.fixture(autouse=True)
def mock_mongo(monkeypatch):
    """Replace Motor collections with AsyncMocks so tests don't need MongoDB."""
    # Shared in-memory store so replace_one / find_one are coherent.
    _store: dict[str, dict] = {}

    async def _replace_one(filter_doc, document, upsert=False):
        key = filter_doc.get("job_id", "")
        _store[key] = document
        return MagicMock(upserted_id=None)

    async def _find_one(filter_doc):
        return _store.get(filter_doc.get("job_id", ""))

    async def _insert_one(document):
        return MagicMock(inserted_id="fake_id")

    mock_coll = MagicMock()
    mock_coll.insert_one = _insert_one
    mock_coll.replace_one = _replace_one
    mock_coll.find_one = _find_one

    # Patch every module that holds a reference to a Motor collection.
    monkeypatch.setattr("app.api.v1.uploads.raw_uploads", mock_coll)
    monkeypatch.setattr("app.api.v1.uploads.pipeline_results", mock_coll)
    monkeypatch.setattr("app.services.etl.pipeline_results", mock_coll)

    return _store


@pytest.fixture(autouse=True)
def patch_etl_session(monkeypatch):
    """Make run_etl use the SQLite TestingSession instead of real Postgres."""
    monkeypatch.setattr("app.services.etl.SessionLocal", TestingSession)


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
