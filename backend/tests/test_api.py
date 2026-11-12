import os
import sqlite3

from conftest import login

ORDER = {"client_name": "Иван", "client_phone": "+7000", "from_address": "A",
         "to_address": "B", "price": 100}


def test_health_no_auth(client):
    assert client.get("/").json() == {"ok": True, "service": "dispatcher"}


def test_401_everywhere(client):
    for path in ("/orders/", "/performers/", "/users/", "/audit/", "/auth/me", "/orders/x"):
        assert client.get(path).status_code == 401, path
    assert client.post("/orders/", json=ORDER).status_code == 401
    assert client.post("/auth/logout").status_code == 401
    assert client.post("/performers/", json={"name": "a", "phone": "1"}).status_code == 401


def test_login(client):
    r = login(client)
    assert r.status_code == 200
    j = r.json()
    assert j["token_type"] == "bearer" and j["user"]["role"] == "admin"
    assert login(client, password="wrong").status_code == 401
    assert login(client, "nobody", "x").status_code == 401


def test_lockout(client):
    for _ in range(5):
        assert login(client, password="bad").status_code == 401
    assert login(client, password="bad").status_code == 429
    assert login(client).status_code == 429


def test_logout_and_me(client, auth):
    assert client.get("/auth/me", headers=auth).json()["username"] == "admin"
    assert client.post("/auth/logout", headers=auth).json() == {"ok": True}
    assert client.get("/auth/me", headers=auth).status_code == 401


def test_password_change(client, auth):
    r = client.post("/auth/password", headers=auth, json={"old_password": "no", "new_password": "newpass1234"})
    assert r.status_code == 400
    r = client.post("/auth/password", headers=auth, json={"old_password": "adminpass123", "new_password": "short"})
    assert r.status_code == 422
    r = client.post("/auth/password", headers=auth, json={"old_password": "adminpass123", "new_password": "newpass1234"})
    assert r.json() == {"ok": True}
    assert login(client).status_code == 401
    assert login(client, password="newpass1234").status_code == 200


def _mk_dispatcher(client, auth, name="disp"):
    r = client.post("/users/", headers=auth, json={"username": name, "password": "disppass123", "role": "dispatcher"})
    assert r.status_code == 200, r.text
    tok = login(client, name, "disppass123").json()["access_token"]
    return r.json(), {"Authorization": f"Bearer {tok}"}


def test_admin_only(client, auth):
    _, d = _mk_dispatcher(client, auth)
    assert client.get("/users/", headers=d).status_code == 403
    assert client.post("/users/", headers=d, json={"username": "x", "password": "xxxxxxxx", "role": "admin"}).status_code == 403
    assert client.patch("/users/1", headers=d, json={"active": False}).status_code == 403
    assert client.get("/audit/", headers=d).status_code == 403
    assert client.get("/orders/", headers=d).status_code == 200


def test_users(client, auth):
    u, d = _mk_dispatcher(client, auth)
    assert u["active"] is True and "password_hash" not in u
    dup = client.post("/users/", headers=auth, json={"username": "disp", "password": "disppass123", "role": "dispatcher"})
    assert dup.status_code == 409
    assert len(client.get("/users/", headers=auth).json()) == 2
    assert client.patch(f"/users/{u['id']}", headers=auth, json={"active": False}).json()["active"] is False
    assert client.get("/orders/", headers=d).status_code == 401
    assert login(client, "disp", "disppass123").status_code == 401
    # self-protection
    assert client.patch("/users/1", headers=auth, json={"active": False}).status_code == 400
    assert client.patch("/users/1", headers=auth, json={"role": "dispatcher"}).status_code == 400
    assert client.patch("/users/999", headers=auth, json={"active": True}).status_code == 404


def test_performers(client, auth):
    r = client.post("/performers/", headers=auth, json={"name": "Пётр", "phone": "123"})
    p = r.json()
    assert p["active"] is True and p["comment"] == ""
    client.post("/performers/", headers=auth, json={"name": "Ян", "phone": "5", "comment": "c"})
    r = client.patch(f"/performers/{p['id']}", headers=auth, json={"active": False, "name": "Пётр2"})
    assert r.json()["active"] is False and r.json()["name"] == "Пётр2"
    assert len(client.get("/performers/", headers=auth).json()) == 2
    act = client.get("/performers/?active=true", headers=auth).json()
    assert len(act) == 1 and act[0]["name"] == "Ян"
    assert client.patch("/performers/999", headers=auth, json={"name": "x"}).status_code == 404


def test_order_lifecycle(client, auth):
    r = client.post("/orders/", headers=auth, json=ORDER)
    assert r.status_code == 200
    o = r.json()
    assert o["status"] == "new" and o["performer_name"] is None and o["created_by"] == "admin"
    oid = o["id"]
    pid = client.post("/performers/", headers=auth, json={"name": "Пётр", "phone": "1"}).json()["id"]
    r = client.patch(f"/orders/{oid}", headers=auth, json={"performer_id": pid}).json()
    assert r["status"] == "assigned" and r["performer_name"] == "Пётр"
    r = client.patch(f"/orders/{oid}", headers=auth, json={"status": "in_progress", "price": 150, "comment": "hi"}).json()
    assert r["status"] == "in_progress" and r["price"] == 150 and r["comment"] == "hi"
    assert client.get(f"/orders/{oid}", headers=auth).json()["status"] == "in_progress"
    assert client.get("/orders/?status=done", headers=auth).json() == []
    assert len(client.get("/orders/?status=in_progress", headers=auth).json()) == 1
    # validation
    assert client.patch(f"/orders/{oid}", headers=auth, json={"status": "bogus"}).status_code == 422
    assert client.get("/orders/?status=bogus", headers=auth).status_code == 422
    assert client.patch(f"/orders/{oid}", headers=auth, json={"performer_id": 999}).status_code == 400
    assert client.post("/orders/", headers=auth, json={**ORDER, "performer_id": 999}).status_code == 400
    assert client.post("/orders/", headers=auth, json={**ORDER, "price": -1}).status_code == 422
    assert client.get("/orders/nope", headers=auth).status_code == 404
    assert client.patch("/orders/nope", headers=auth, json={"comment": "x"}).status_code == 404


def test_list_order_and_limit(client, auth):
    ids = [client.post("/orders/", headers=auth, json={**ORDER, "client_name": f"c{i}"}).json()["id"] for i in range(3)]
    lst = client.get("/orders/?limit=2", headers=auth).json()
    assert [o["id"] for o in lst] == ids[::-1][:2]


def test_persistence(client, auth, tmp_path):
    oid = client.post("/orders/", headers=auth, json=ORDER).json()["id"]
    conn = sqlite3.connect(tmp_path / "t.db")
    assert conn.execute("SELECT client_name FROM orders WHERE id=?", (oid,)).fetchone()[0] == "Иван"
    conn.close()


def test_audit(client, auth):
    login(client, password="bad")
    client.post("/users/", headers=auth, json={"username": "u2", "password": "secretpw123", "role": "dispatcher"})
    client.patch("/users/2", headers=auth, json={"password": "anotherpw123"})
    client.post("/performers/", headers=auth, json={"name": "P", "phone": "1"})
    oid = client.post("/orders/", headers=auth, json=ORDER).json()["id"]
    client.patch(f"/orders/{oid}", headers=auth, json={"status": "done"})
    client.post("/auth/password", headers=auth, json={"old_password": "adminpass123", "new_password": "newpass1234"})
    rows = client.get("/audit/", headers=auth).json()
    actions = {r["action"] for r in rows}
    assert {"login", "login_failed", "user_create", "user_update", "performer_create",
            "order_create", "order_update", "password_change"} <= actions
    assert rows[0]["id"] > rows[-1]["id"]
    blob = str(rows)
    for secret in ("secretpw123", "anotherpw123", "adminpass123", "newpass1234", auth["Authorization"][7:]):
        assert secret not in blob
    assert len(client.get("/audit/?limit=2", headers=auth).json()) == 2


def test_generated_admin_password(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setenv("DB_PATH", str(tmp_path / "g" / "g.db"))
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    with TestClient(app) as c:
        f = tmp_path / "g" / "admin_password.txt"
        assert f.exists() and oct(os.stat(f).st_mode & 0o777) == "0o600"
        pw = f.read_text().strip()
        assert len(pw) == 16
        tok = c.post("/auth/login", data={"username": "admin", "password": pw}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        c.post("/auth/password", headers=h, json={"old_password": pw, "new_password": "brandnew123"})
        assert not f.exists()


def test_concurrent_requests(client, auth):
    # Регрессия: соединение SQLite создаётся в одном потоке пула, а используется в другом.
    from concurrent.futures import ThreadPoolExecutor
    paths = ["/orders/", "/performers/", "/auth/me", "/users/"] * 10
    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(lambda p: client.get(p, headers=auth).status_code, paths))
    assert codes == [200] * len(paths)


def test_password_change_ends_other_sessions(client, auth):
    other = {"Authorization": "Bearer " + login(client).json()["access_token"]}
    assert client.get("/auth/me", headers=other).status_code == 200
    r = client.post("/auth/password", headers=auth,
                    json={"old_password": "adminpass123", "new_password": "brandnewpass1"})
    assert r.status_code == 200
    assert client.get("/auth/me", headers=auth).status_code == 200   # текущий вход остаётся
    assert client.get("/auth/me", headers=other).status_code == 401  # остальные завершены


def test_admin_password_reset_ends_user_sessions(client, auth):
    uid = client.post("/users/", headers=auth, json={
        "username": "olga", "password": "olgapass123", "role": "dispatcher"}).json()["id"]
    tok = {"Authorization": "Bearer " + login(client, "olga", "olgapass123").json()["access_token"]}
    assert client.patch(f"/users/{uid}", headers=auth, json={"password": "resetpass123"}).status_code == 200
    assert client.get("/auth/me", headers=tok).status_code == 401
    assert login(client, "olga", "resetpass123").status_code == 200


def test_limiter_does_not_grow_unbounded(client, monkeypatch):
    from app import security
    monkeypatch.setattr(security, "MAX_KEYS", 50)
    for i in range(120):
        security.register_fail((f"user{i}", "1.2.3.4"))
    assert len(security._fails) <= 50
    assert not security.is_locked(("nobody", "1.2.3.4"))
    assert ("nobody", "1.2.3.4") not in security._fails
