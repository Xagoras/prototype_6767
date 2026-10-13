"""版本读取与多版本比对的访问控制回归测试（修复 2 / B1）。

覆盖：
- 无关用户不能按 id 读取他人标注版本
- 被分配的标注员"提交前"不可比对（不提前暴露标准答案），"提交后"可比对
- 标注员比对只返回"本人版本"一组，看不到其他标注员版本
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


def _make_task_doc(client, users, name):
    th = users["teacher"]["headers"]
    task = client.post("/api/tasks", headers=th,
                       json={"name": name, "guide_id": _ensure_guide(client, th)}).json()
    text = ("本院认为，依法成立的合同，自成立时生效。当事人应当按照约定全面履行义务。"
            "本案中，原告已依约提供劳务，被告应给付报酬。判决如下：支持原告。")
    doc = client.post(f"/api/tasks/{task['id']}/documents/text", headers=th,
                      json={"name": name, "text": text}).json()
    return doc, task


def _assign(client, users, task, doc, user_key, roles):
    r = client.post(f"/api/tasks/{task['id']}/assignments",
                    headers=users["teacher"]["headers"],
                    json={"document_ids": [doc["id"]],
                          "user_ids": [users[user_key]["id"]], "roles": roles})
    assert r.status_code == 200, r.text


def _put_prop(client, headers, version_id, reasoning_text):
    p1 = reasoning_text.index("依法成立")
    e1 = reasoning_text.index("。", p1) + 1
    payload = {
        "propositions": [{"char_start": p1, "char_end": e1,
                          "text": reasoning_text[p1:e1], "type_code": "GM"}],
        "relations": [], "graph_layout": {"positions": {}},
    }
    r = client.put(f"/api/versions/{version_id}/content", headers=headers, json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _stranger(client, username):
    r = client.post("/api/auth/register", json={
        "username": username, "password": "demo123", "display_name": username})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_stranger_cannot_read_version_by_id(client, users):
    doc, task = _make_task_doc(client, users, "ACL-读版本")
    th = users["teacher"]["headers"]
    mv = client.get(f"/api/documents/{doc['id']}/my-version", headers=th).json()
    stranger = _stranger(client, "stranger_read")
    assert client.get(f"/api/versions/{mv['id']}", headers=stranger).status_code == 403
    # 本人可读
    assert client.get(f"/api/versions/{mv['id']}", headers=th).status_code == 200


def test_annotator_compare_gated_by_submit_and_scoped_to_self(client, users):
    doc, task = _make_task_doc(client, users, "ACL-比对")
    _assign(client, users, task, doc, "stu1", ["annotator"])
    _assign(client, users, task, doc, "stu2", ["annotator"])
    _assign(client, users, task, doc, "teacher", ["reference", "arbiter"])
    s1, s2 = users["stu1"]["headers"], users["stu2"]["headers"]

    mv1 = client.get(f"/api/documents/{doc['id']}/my-version", headers=s1).json()
    mv2 = client.get(f"/api/documents/{doc['id']}/my-version", headers=s2).json()
    _put_prop(client, s1, mv1["id"], doc["reasoning_text"])
    _put_prop(client, s2, mv2["id"], doc["reasoning_text"])

    # 提交前：比对被拒（不提前暴露标准答案）
    assert client.get(f"/api/documents/{doc['id']}/compare", headers=s1).status_code == 403

    # 提交后：可比对，且只看到自己的版本组
    assert client.post(f"/api/versions/{mv1['id']}/submit", headers=s1).status_code == 200
    cmp = client.get(f"/api/documents/{doc['id']}/compare", headers=s1).json()
    ids = [g["version_id"] for g in cmp["groups"]]
    assert mv1["id"] in ids
    assert mv2["id"] not in ids

    # 非参与者比对被拒
    stranger = _stranger(client, "stranger_compare")
    assert client.get(f"/api/documents/{doc['id']}/compare", headers=stranger).status_code == 403


def test_manager_compare_sees_all(client, users):
    doc, task = _make_task_doc(client, users, "ACL-裁定者全量")
    _assign(client, users, task, doc, "stu1", ["annotator"])
    _assign(client, users, task, doc, "stu2", ["annotator"])
    _assign(client, users, task, doc, "teacher", ["reference", "arbiter"])
    s1, s2 = users["stu1"]["headers"], users["stu2"]["headers"]
    mv1 = client.get(f"/api/documents/{doc['id']}/my-version", headers=s1).json()
    mv2 = client.get(f"/api/documents/{doc['id']}/my-version", headers=s2).json()
    _put_prop(client, s1, mv1["id"], doc["reasoning_text"])
    _put_prop(client, s2, mv2["id"], doc["reasoning_text"])
    cmp = client.get(f"/api/documents/{doc['id']}/compare",
                     headers=users["teacher"]["headers"]).json()
    ids = {g["version_id"] for g in cmp["groups"]}
    assert {mv1["id"], mv2["id"]} <= ids


def test_final_gated_until_own_submit(client, users):
    """未提交学生不能读 /final（即使最终版工作副本已存在）；提交后可读。

    与 compare 的"须已提交"门槛对齐（原型 2.1：提交前不得暴露标准答案内容）。
    """
    doc, task = _make_task_doc(client, users, "ACL-final门槛")
    _assign(client, users, task, doc, "stu1", ["annotator"])
    _assign(client, users, task, doc, "teacher", ["reference", "arbiter"])
    th = users["teacher"]["headers"]
    s1 = users["stu1"]["headers"]
    # teacher 标准答案并提交，裁定生成最终版工作副本（stu1 从未提交）
    mv_t = client.get(f"/api/documents/{doc['id']}/my-version", headers=th).json()
    _put_prop(client, th, mv_t["id"], doc["reasoning_text"])
    client.post(f"/api/versions/{mv_t['id']}/submit", headers=th)
    adj = client.post(f"/api/documents/{doc['id']}/adjudicate", headers=th,
                      json={"base_version_id": mv_t["id"], "note": ""})
    assert adj.status_code == 200, adj.text
    # 未提交 → 403；裁定者本人 → 200
    assert client.get(f"/api/documents/{doc['id']}/final", headers=s1).status_code == 403
    assert client.get(f"/api/documents/{doc['id']}/final", headers=th).status_code == 200
    # stu1 提交自己的标注 → 可读最终版
    mv1 = client.get(f"/api/documents/{doc['id']}/my-version", headers=s1).json()
    _put_prop(client, s1, mv1["id"], doc["reasoning_text"])
    assert client.post(f"/api/versions/{mv1['id']}/submit", headers=s1).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}/final", headers=s1).status_code == 200


def test_reference_author_gates_align_with_compare(client, users):
    """仅 reference 角色（非创建者/裁定者）：/final 与 compare 门禁一致。

    标准答案作者提交自己的 reference 版本后，两项门禁同放行；
    未提交时两项门禁同拒绝（回归：/final 曾额外过滤 kind=normal 导致不对称）。
    """
    doc, task = _make_task_doc(client, users, "ACL-refonly")
    th = users["teacher"]["headers"]
    # 注册仅 reference 角色的用户（无 annotator，非创建者/裁定者）
    r = client.post("/api/auth/register", json={
        "username": "refonly_gate", "password": "demo123", "display_name": "refonly"})
    assert r.status_code == 200, r.text
    ref = {"Authorization": f"Bearer {r.json()['token']}"}
    ref_id = client.get("/api/auth/me", headers=ref).json()["id"]
    _assign_ref = client.post(f"/api/tasks/{task['id']}/assignments", headers=th,
                              json={"document_ids": [doc["id"]],
                                    "user_ids": [ref_id], "roles": ["reference"]})
    assert _assign_ref.status_code == 200, _assign_ref.text

    mv = client.get(f"/api/documents/{doc['id']}/my-version", headers=ref).json()
    assert mv["kind"] == "reference"
    _put_prop(client, ref, mv["id"], doc["reasoning_text"])
    # 未提交：compare 与 /final 同拒
    assert client.get(f"/api/documents/{doc['id']}/compare", headers=ref).status_code == 403
    assert client.get(f"/api/documents/{doc['id']}/final", headers=ref).status_code == 403
    # 提交自己的 reference 版本；裁定者以其为基准生成最终版工作副本
    assert client.post(f"/api/versions/{mv['id']}/submit", headers=ref).status_code == 200
    adj = client.post(f"/api/documents/{doc['id']}/adjudicate", headers=th,
                      json={"base_version_id": mv["id"], "note": ""})
    assert adj.status_code == 200, adj.text
    # 提交后：compare 与 /final 同放行
    assert client.get(f"/api/documents/{doc['id']}/compare", headers=ref).status_code == 200
    assert client.get(f"/api/documents/{doc['id']}/final", headers=ref).status_code == 200


def test_document_read_gated_to_participants(client, users):
    """文书详情（含全文）仅参与者/创建者/管理员可读（回归：此前登录即可读任意文书）。"""
    doc, task = _make_task_doc(client, users, "ACL-读文档")
    th = users["teacher"]["headers"]
    stranger = _stranger(client, "stranger_docread")
    # 无关用户 → 403
    assert client.get(f"/api/documents/{doc['id']}", headers=stranger).status_code == 403
    # 创建者 → 200；被分配的标注员 → 200
    assert client.get(f"/api/documents/{doc['id']}", headers=th).status_code == 200
    _assign(client, users, task, doc, "stu1", ["annotator"])
    assert client.get(f"/api/documents/{doc['id']}",
                      headers=users["stu1"]["headers"]).status_code == 200
