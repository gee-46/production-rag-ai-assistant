"""
Test fixtures.

Uses the same live Postgres instance (with pgvector) as the rest of this
project — a dedicated `ragdb_test` database, migrated fresh via Alembic for
every test session and dropped after. Embedding/LLM/reranker providers are
overridden to their `fake` implementations so tests never need model
weights, GPU, or a paid API key, while still exercising the real SQL,
pgvector, and full-text search code paths.
"""
import os
import uuid

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text as sql_text
from sqlalchemy.orm import sessionmaker

from alembic import command

_DB_HOST = os.getenv("TEST_DB_HOST", "localhost")
TEST_DB_URL = f"postgresql+psycopg2://postgres:postgres@{_DB_HOST}:5432/ragdb_test"
ADMIN_DB_URL = f"postgresql+psycopg2://postgres:postgres@{_DB_HOST}:5432/postgres"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["EMBEDDING_PROVIDER"] = "fake"
os.environ["LLM_PROVIDER"] = "fake"
os.environ["RERANKER_PROVIDER"] = "fake"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"


@pytest.fixture(scope="session")
def engine():
    from frontend.standalone_engine import StandaloneEngine
    return StandaloneEngine()


@pytest.fixture(scope="session")
def _test_database():
    try:
        admin_engine = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 2})
        with admin_engine.connect() as conn:
            conn.execute(sql_text("DROP DATABASE IF EXISTS ragdb_test"))
            conn.execute(sql_text("CREATE DATABASE ragdb_test"))
    except Exception as e:
        pytest.skip(f"Live PostgreSQL database is not reachable at {_DB_HOST}:5432 ({e}).", allow_module_level=True)

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DB_URL)
    command.upgrade(cfg, "head")

    yield

    try:
        with admin_engine.connect() as conn:
            conn.execute(
                sql_text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = 'ragdb_test' AND pid <> pg_backend_pid()"
                )
            )
            conn.execute(sql_text("DROP DATABASE IF EXISTS ragdb_test"))
    except Exception:
        pass


@pytest.fixture()
def db_session(_test_database):
    from app.db.session import engine as _unused  # noqa: F401 - ensure app engine module loads with test URL

    engine = create_engine(TEST_DB_URL, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(_test_database, monkeypatch):
    from app.core.config import get_settings
    from app.db import session as db_session_module
    from app.main import create_app

    get_settings.cache_clear()
    engine = create_engine(TEST_DB_URL, future=True)
    TestSessionLocal = sessionmaker(bind=engine, future=True)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[db_session_module.get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    engine.dispose()


@pytest.fixture()
def registered_user(client):
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    password = "password123"
    client.post("/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"email": email, "password": password, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture()
def workspace(client, registered_user):
    resp = client.post("/workspaces", json={"name": "Test Workspace"}, headers=registered_user["headers"])
    return resp.json()
