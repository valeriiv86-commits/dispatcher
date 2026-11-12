from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    assert client.get("/").json()["ok"] is True


def test_order_lifecycle():
    r = client.post("/orders/", json={
        "client_name": "Иван", "client_phone": "+70000000000",
        "from_address": "A", "to_address": "B", "price": 100,
    })
    assert r.status_code == 200
    oid = r.json()["id"]
    assert client.get(f"/orders/{oid}").json()["status"] == "new"
    assert client.patch(f"/orders/{oid}", json={"status": "done"}).json()["status"] == "done"
    assert client.get("/orders/nope").status_code == 404


def test_stub_routers():
    for path in ("/performers/", "/users/", "/auth/", "/audit/"):
        assert client.get(path).status_code == 200
