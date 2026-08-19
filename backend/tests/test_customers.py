"""客户接口测试。"""


def _create_customer(client, name="小红", aliases=("红姐",)):
    return client.post("/api/customers", json={"display_name": name, "aliases": list(aliases)})


def test_create_and_list_customer(client):
    resp = _create_customer(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["display_name"] == "小红"
    assert {"id": body["aliases"][0]["id"], "alias": "红姐"} == body["aliases"][0]

    listing = client.get("/api/customers").json()
    assert len(listing) == 1


def test_search_by_alias_and_name(client):
    _create_customer(client, "小红", ["红姐"])
    assert len(client.get("/api/customers", params={"q": "红姐"}).json()) == 1
    assert len(client.get("/api/customers", params={"q": "小红"}).json()) == 1
    assert len(client.get("/api/customers", params={"q": "不存在"}).json()) == 0


def test_delete_then_not_in_list_then_restore(client):
    body = _create_customer(client).json()
    cid = body["id"]

    assert client.delete(f"/api/customers/{cid}").status_code == 200
    assert client.get("/api/customers").json() == []

    assert client.post(f"/api/customers/{cid}/restore").status_code == 200
    assert len(client.get("/api/customers").json()) == 1


def test_display_name_required(client):
    resp = client.post("/api/customers", json={"display_name": "", "aliases": []})
    assert resp.status_code == 400
