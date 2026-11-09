import os
from urllib.parse import quote_plus, urlsplit, urlunsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import main


def get_test_database_url():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    parsed = urlsplit(database_url)

    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is not configured")

    host = parsed.hostname
    port = parsed.port or 5432

    if not os.path.exists("/.dockerenv"):
        host = "localhost"

    netloc = f"datamask:{quote_plus(password)}@{host}:{port}"

    return urlunsplit((
        parsed.scheme,
        netloc,
        "/datamask_test",
        "",
        "",
    ))


TEST_DATABASE_URL = get_test_database_url()

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    join_transaction_mode="create_savepoint",
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(monkeypatch, db_session):
    def override_session_local():
        return db_session

    monkeypatch.setattr(
        main,
        "SessionLocal",
        override_session_local,
    )

    monkeypatch.setattr(
        main,
        "publish_task",
        lambda task_id, text: None,
    )

    with TestClient(main.app) as test_client:
        yield test_client