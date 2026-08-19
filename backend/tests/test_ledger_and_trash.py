"""账本记录与回收站接口测试。"""


def _setup(client):
    svc = client.post("/api/services", json={"name": "面部清洁"}).json()
    cust = client.post("/api/customers", json={"display_name": "小红", "aliases": ["红姐"]}).json()
    return svc, cust


def test_one_time_service_does_not_change_package(client):
    svc, cust = _setup(client)
    pid = client.post(
        f"/api/customers/{cust['id']}/packages",
        json={"service_id": svc["id"], "total_count": 5},
    ).json()["id"]

    resp = client.post(
        f"/api/customers/{cust['id']}/ledger",
        json={"entry_type": "one_time_service", "service_id": svc["id"], "quantity": 1},
    )
    assert resp.status_code == 201
    assert resp.json()["service_name"] == "面部清洁"

    # 一次性服务不改变套餐余额
    detail = client.get(f"/api/customers/{cust['id']}").json()
    assert detail["packages"][0]["used_count"] == 0


def test_product_purchase(client):
    _, cust = _setup(client)
    resp = client.post(
        f"/api/customers/{cust['id']}/ledger",
        json={"entry_type": "product_purchase", "product_name": "面霜", "quantity": 2, "price_cents": 10000},
    )
    assert resp.status_code == 201
    assert resp.json()["product_name"] == "面霜"


def test_invalid_entry_type_rejected(client):
    _, cust = _setup(client)
    resp = client.post(
        f"/api/customers/{cust['id']}/ledger",
        json={"entry_type": "consume_service", "service_id": 1, "quantity": 1},
    )
    assert resp.status_code == 400


def test_trash_lists_deleted_items(client):
    svc, cust = _setup(client)
    sid = svc["id"]
    cid = cust["id"]
    client.delete(f"/api/services/{sid}")
    client.delete(f"/api/customers/{cid}")

    trash = client.get("/api/trash").json()
    types = {item["type"] for item in trash["items"]}
    assert "service" in types
    assert "customer" in types
