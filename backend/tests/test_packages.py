"""套餐卡接口测试。"""


def _setup(client):
    svc = client.post("/api/services", json={"name": "面部清洁"}).json()
    cust = client.post("/api/customers", json={"display_name": "小红", "aliases": ["红姐"]}).json()
    return svc, cust


def test_create_package_and_balance(client):
    svc, cust = _setup(client)
    resp = client.post(
        f"/api/customers/{cust['id']}/packages",
        json={"service_id": svc["id"], "total_count": 10, "price_cents": 66600},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_count"] == 10
    assert body["used_count"] == 0
    assert body["remaining_count"] == 10


def test_used_cannot_exceed_total_on_update(client):
    svc, cust = _setup(client)
    pid = client.post(
        f"/api/customers/{cust['id']}/packages",
        json={"service_id": svc["id"], "total_count": 5},
    ).json()["id"]
    resp = client.patch(f"/api/packages/{pid}", json={"opening_used_count": 6})
    assert resp.status_code == 400


def test_inactive_service_cannot_create_package(client):
    svc, cust = _setup(client)
    client.patch(f"/api/services/{svc['id']}", json={"status": "inactive"})
    resp = client.post(
        f"/api/customers/{cust['id']}/packages",
        json={"service_id": svc["id"], "total_count": 5},
    )
    assert resp.status_code == 400


def test_total_must_be_positive(client):
    svc, cust = _setup(client)
    resp = client.post(
        f"/api/customers/{cust['id']}/packages",
        json={"service_id": svc["id"], "total_count": 0},
    )
    assert resp.status_code == 400


def test_delete_and_restore_package(client):
    svc, cust = _setup(client)
    pid = client.post(
        f"/api/customers/{cust['id']}/packages",
        json={"service_id": svc["id"], "total_count": 5},
    ).json()["id"]
    assert client.delete(f"/api/packages/{pid}").status_code == 200
    detail = client.get(f"/api/customers/{cust['id']}").json()
    assert detail["packages"] == []
    assert client.post(f"/api/packages/{pid}/restore").status_code == 200
    detail = client.get(f"/api/customers/{cust['id']}").json()
    assert len(detail["packages"]) == 1
