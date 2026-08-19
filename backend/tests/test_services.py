"""服务项目接口测试。"""


def _create_service(client, name):
    return client.post("/api/services", json={"name": name})


def test_create_service(client):
    resp = _create_service(client, "面部清洁")
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"


def test_duplicate_name_rejected(client):
    _create_service(client, "面部清洁")
    resp = _create_service(client, "面部清洁")
    assert resp.status_code == 400


def test_update_status(client):
    sid = _create_service(client, "面部清洁").json()["id"]
    resp = client.patch(f"/api/services/{sid}", json={"status": "inactive"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"


def test_invalid_status_rejected(client):
    sid = _create_service(client, "面部清洁").json()["id"]
    resp = client.patch(f"/api/services/{sid}", json={"status": "bogus"})
    assert resp.status_code == 400


def test_delete_and_restore(client):
    sid = _create_service(client, "面部清洁").json()["id"]
    assert client.delete(f"/api/services/{sid}").status_code == 200
    assert client.get("/api/services").json() == []
    assert client.post(f"/api/services/{sid}/restore").status_code == 200
    assert len(client.get("/api/services").json()) == 1
