"""导出/登记接口的访问控制回归测试（修复 1）。

覆盖：
- 与该文档无关的用户不能导出/登记，更不能据此把文档锁成 OUTPUT
- 未生成最终版时，即便有权限也不能登记图片导出（不锁定）
"""
from app.services.taxonomy import default_taxonomy


def _ensure_guide(client, headers) -> int:
    guides = client.get("/api/guides", headers=headers).json()
    if guides:
        return guides[0]["id"]
    r = client.post("/api/guides", headers=headers, json={
        "version": "v1.1", "name": "测试指南",
        "content_text": "测试", "taxonomy": default_taxonomy(),
    })
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _make_doc(client, users, name):
    th = users["teacher"]["headers"]
    task = client.post("/api/tasks", headers=th,
                       json={"name": name, "guide_id": _ensure_guide(client, th)}).json()
    text = ("本院认为，依法成立的合同，自成立时生效。当事人应当按照约定全面履行义务。"
            "本案中，原告已依约提供劳务，被告应给付报酬。判决如下：支持原告。")
    doc = client.post(f"/api/tasks/{task['id']}/documents/text", headers=th,
                      json={"name": name, "text": text}).json()
    return doc, task


def _stranger(client, username):
    r = client.post("/api/auth/register", json={
        "username": username, "password": "demo123", "display_name": username})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_unrelated_user_cannot_lock_document(client, users):
    doc, _ = _make_doc(client, users, "ACL-导出")
    stranger = _stranger(client, "stranger_export")
    r = client.post(f"/api/documents/{doc['id']}/exports/record", headers=stranger,
                    json={"format": "png", "filename": "x.png"})
    assert r.status_code == 403
    # 文档状态未被改成 OUTPUT
    status = client.get(f"/api/documents/{doc['id']}",
                        headers=users["teacher"]["headers"]).json()["status"]
    assert status != "OUTPUT"


def test_image_export_requires_final_version(client, users):
    doc, _ = _make_doc(client, users, "ACL-需最终版")
    th = users["teacher"]["headers"]
    # 创建者有权，但尚未生成最终版 → 409，且不锁定
    r = client.post(f"/api/documents/{doc['id']}/exports/record", headers=th,
                    json={"format": "png", "filename": "x.png"})
    assert r.status_code == 409
    assert client.get(f"/api/documents/{doc['id']}", headers=th).json()["status"] != "OUTPUT"


def test_export_blocked_until_final_submitted(client, users):
    """裁定工作副本（kind=final, status=draft）不算定稿：

    编辑期导出/登记 → 409 且不锁定（否则锁死后定稿流程无法继续）；
    提交定稿后 → 可登记并锁定。
    """
    doc, _ = _make_doc(client, users, "ACL-定稿门")
    th = users["teacher"]["headers"]
    # teacher 标准答案（reference 版本）并提交
    mv = client.get(f"/api/documents/{doc['id']}/my-version", headers=th).json()
    rt = doc["reasoning_text"]
    a = rt.index("依法成立")
    ae = rt.index("。", a) + 1
    payload = {"propositions": [{"char_start": a, "char_end": ae,
                                 "text": rt[a:ae], "type_code": "GM"}],
               "relations": [], "graph_layout": {"positions": {}}}
    assert client.put(f"/api/versions/{mv['id']}/content", headers=th, json=payload).status_code == 200
    client.post(f"/api/versions/{mv['id']}/submit", headers=th)
    # 生成最终版工作副本（draft）
    adj = client.post(f"/api/documents/{doc['id']}/adjudicate", headers=th,
                      json={"base_version_id": mv["id"], "note": ""})
    assert adj.status_code == 200, adj.text
    assert adj.json()["kind"] == "final" and adj.json()["status"] == "draft"
    final_id = adj.json()["id"]
    # 编辑期：导出与登记均 409，文档不锁定
    assert client.post(f"/api/documents/{doc['id']}/exports/record", headers=th,
                       json={"format": "png", "filename": "x.png"}).status_code == 409
    assert client.post(f"/api/documents/{doc['id']}/export", headers=th,
                       params={"format": "json"}).status_code == 409
    assert client.get(f"/api/documents/{doc['id']}", headers=th).json()["status"] != "OUTPUT"
    # 提交定稿 → 可登记并锁定
    assert client.post(f"/api/versions/{final_id}/submit", headers=th).status_code == 200
    assert client.post(f"/api/documents/{doc['id']}/exports/record", headers=th,
                       json={"format": "png", "filename": "x.png"}).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}", headers=th).json()["status"] == "OUTPUT"
