import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app import main


TEST_DATABASE_URL = (
    "postgresql+psycopg://datamask:datamask@postgres:5432/datamask_test"
)

# Для запуска тестов внутри Docker используем имя postgres.
# Для локального запуска на Mac — localhost.
if not os.path.exists("/.dockerenv"):
    TEST_DATABASE_URL = (
        "postgresql+psycopg://datamask:datamask@localhost:5432/datamask_test"
    )


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