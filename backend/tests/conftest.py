import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="dispatcher-test-")
os.environ["DB_PATH"] = os.path.join(_TMP, "init.db")
os.environ["ADMIN_PASSWORD"] = "adminpass123"
os.environ.pop("ADMIN_USERNAME", None)

import pytest
from fastapi.testclient import TestClient

from app import security
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass123")
    security.reset_limiter()
    with TestClient(app) as c:
        yield c


def login(client, username="admin", password="adminpass123"):
    return client.post("/auth/login", data={"username": username, "password": password})


@pytest.fixture
def auth(client):
    t = login(client).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}
