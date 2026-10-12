"""端到端流程测试：标注 → 提交 → 裁定 → 导出 → 锁定（需求四阶段）。"""
import json


def _put_props(client, headers, version_id, reasoning_text):
    """保存两个命题 + 一个支持关系。"""
    p1 = reasoning_text.index("依法成立")
    p2 = reasoning_text.index("当事人应当按照")
    e1 = reasoning_text.index("。", p1) + 1
    e2 = reasoning_text.index("。", p2) + 1
    payload = {
        "propositions": [
            {"char_start": p1, "char_end": e1, "text": reasoning_text[p1:e1],
             "type_code": "GM", "subtype_code": "GM-L"},
            {"char_start": p2, "char_end": e2, "text": reasoning_text[p2:e2],
             "type_code": "GM", "subtype_code": "GM-L"},
        ],
        "relations": [
            {"rel_type": "S", "args": [{"kind": "P", "id": 1}, {"kind": "P", "id": 2}]},
        ],
        "graph_layout": {"positions": {}},
    }
    return client.put(f"/api/versions/{version_id}/content", headers=headers, json=payload)


def test_full_four_stage_flow(client, users, demo_doc):
    doc, task = demo_doc
    th = users["teacher"]
    s1h = users["stu1"]

    # 阶段二：学生标注并提交
    mv = client.get(f"/api/documents/{doc['id']}/my-version", headers=s1h["headers"]).json()
    r = _put_props(client, s1h["headers"], mv["id"], doc["reasoning_text"])
    assert r.status_code == 200
    assert len(r.json()["propositions"]) == 2
    # 序号按原文顺序
    assert [p["seq"] for p in r.json()["propositions"]] == [1, 2]
    assert r.json()["relations"][0]["expr"] == "S(P1, P2)"
    # 文本不一致 → 409
    bad = r.json()
    bad["propositions"][0]["text"] = "篡改"
    r409 = client.put(f"/api/versions/{mv['id']}/content", headers=s1h["headers"], json=bad)
    assert r409.status_code == 409
    # 提交后只读
    assert client.post(f"/api/versions/{mv['id']}/submit", headers=s1h["headers"]).status_code == 200
    r403 = client.put(f"/api/versions/{mv['id']}/content", headers=s1h["headers"], json=r.json())
    assert r403.status_code == 403

    # 教师标准答案 + 阶段三：裁定
    mv2 = client.get(f"/api/documents/{doc['id']}/my-version", headers=th["headers"]).json()
    _put_props(client, th["headers"], mv2["id"], doc["reasoning_text"])
    cmp = client.get(f"/api/documents/{doc['id']}/compare", headers=th["headers"]).json()
    # 学生版与标准答案一致 → 无差异
    stu_group = next(g for g in cmp["groups"] if g["version_id"] == mv["id"])
    assert stu_group["granularity_rate"] == 0.0
    assert len([d for d in stu_group["prop_diffs"] if d["category"] != "identical"]) == 0
    assert len(stu_group["relation_diffs"]) == 0
    # 裁定
    adj = client.post(f"/api/documents/{doc['id']}/adjudicate", headers=th["headers"],
                      json={"base_version_id": mv2["id"], "note": "一致通过"})
    assert adj.status_code == 200
    assert adj.json()["kind"] == "final"
    fin = client.get(f"/api/documents/{doc['id']}/final", headers=th["headers"]).json()
    assert len(fin["propositions"]) == 2
    assert fin["relations"][0]["expr"] == "S(P1, P2)"

    # 阶段四：导出 + 锁定
    rj = client.post(f"/api/documents/{doc['id']}/export", headers=th["headers"],
                     params={"format": "json"})
    assert rj.status_code == 200
    data = json.loads(rj.content)
    assert data["guide_version"] == "v1.1"
    assert len(data["propositions"]) == 2
    assert data["relations"][0]["type"] == "S"
    re_ = client.post(f"/api/documents/{doc['id']}/export", headers=th["headers"],
                      params={"format": "excel"})
    assert re_.status_code == 200
    assert len(re_.content) > 1000  # xlsx 有实际内容
    # 锁定：编辑 403、裁定 403（payload 结构有效才能走到锁定守卫）
    valid_payload = {"propositions": [], "relations": [], "graph_layout": {}}
    assert client.put(f"/api/versions/{mv['id']}/content", headers=s1h["headers"],
                      json=valid_payload).status_code == 403
    assert client.post(f"/api/documents/{doc['id']}/adjudicate", headers=th["headers"],
                       json={"base_version_id": mv2["id"]}).status_code == 403
    # 导出记录
    recs = client.get(f"/api/documents/{doc['id']}/exports", headers=th["headers"]).json()
    formats = sorted(r["format"] for r in recs)
    assert formats == ["excel", "json"]
    assert all(r["guide_version"] == "v1.1" for r in recs)


def test_task_status_flow_irreversible(client, users, demo_doc):
    """任务阶段流转单向校验。"""
    _, task = demo_doc
    th = users["teacher"]["headers"]
    r = client.post(f"/api/tasks/{task['id']}/status", headers=th, json={"action": "start"})
    assert r.status_code == 200
    assert r.json()["status"] == "ANNOTATING"
    # 回退被拒
    r409 = client.post(f"/api/tasks/{task['id']}/status", headers=th, json={"action": "start"})
    assert r409.status_code == 409


def test_annotator_cannot_see_others_versions(client, users, demo_doc):
    """标注员只能看到自己的版本。"""
    doc, _ = demo_doc
    s1h = users["stu1"]
    s2h = users["stu2"]
    mv1 = client.get(f"/api/documents/{doc['id']}/my-version", headers=s1h["headers"]).json()
    mv2 = client.get(f"/api/documents/{doc['id']}/my-version", headers=s2h["headers"]).json()
    _put_props(client, s1h["headers"], mv1["id"], doc["reasoning_text"])
    _put_props(client, s2h["headers"], mv2["id"], doc["reasoning_text"])
    vlist = client.get(f"/api/documents/{doc['id']}/versions", headers=s1h["headers"]).json()
    ids = [v["id"] for v in vlist]
    assert mv1["id"] in ids
    assert mv2["id"] not in ids  # 看不到他人版本
