"""端到端演示流（README 演示流程的仓库内可复现版本）。

走完整四阶段：教师标准答案 → 双学生独立标注提交 → 文档 SUBMITTED →
学生提交后可比对（仅本人版本组，基准=标准答案）→ 裁定 → 定稿（草稿期导出被挡）
→ 导出锁定 → 各角色访问控制。
"""
import json

from app.services.taxonomy import default_taxonomy


def test_demo_flow_end_to_end(client, users):
    th = users["teacher"]["headers"]
    s1h = users["stu1"]["headers"]
    s2h = users["stu2"]["headers"]

    # ---------- 准备：指南 / 任务 / 文书 / 分配 ----------
    guides = client.get("/api/guides", headers=th).json()
    if guides:
        guide_id = guides[0]["id"]
    else:
        guide_id = client.post("/api/guides", headers=th, json={
            "version": "v1.1", "name": "测试指南",
            "content_text": "测试", "taxonomy": default_taxonomy(),
        }).json()["id"]
    task = client.post("/api/tasks", headers=th,
                       json={"name": "E2E 演示任务", "guide_id": guide_id}).json()
    text = ("本院认为，依法成立的合同，自成立时生效。当事人应当按照约定全面履行自己的义务。"
            "本案中，原告已依约提供劳务，被告应按照约定给付劳务报酬11000元。"
            "原告主张另有600元，但其证据不足，本院不予支持。判决如下：被告支付原告11000元。")
    doc = client.post(f"/api/tasks/{task['id']}/documents/text", headers=th,
                      json={"name": "E2E 文书", "text": text}).json()
    assert doc["extraction_method"] == "auto"                      # 裁判理由自动提取
    rt = doc["reasoning_text"]
    for uid, roles in ((users["stu1"]["id"], ["annotator"]),
                       (users["stu2"]["id"], ["annotator"]),
                       (users["teacher"]["id"], ["reference", "arbiter"])):
        r = client.post(f"/api/tasks/{task['id']}/assignments", headers=th,
                        json={"document_ids": [doc["id"]], "user_ids": [uid], "roles": roles})
        assert r.status_code == 200, r.text

    def my_version(headers):
        return client.get(f"/api/documents/{doc['id']}/my-version", headers=headers).json()

    def put_two_props(headers, vid=None, types=("GM", "GM")):
        a = rt.index("依法成立")
        ae = rt.index("。", a) + 1
        b = rt.index("当事人应当按照约定")
        be = rt.index("。", b) + 1
        payload = {
            "propositions": [
                {"char_start": a, "char_end": ae, "text": rt[a:ae], "type_code": types[0]},
                {"char_start": b, "char_end": be, "text": rt[b:be], "type_code": types[1]},
            ],
            "relations": [{"rel_type": "S",
                           "args": [{"kind": "P", "id": 1}, {"kind": "P", "id": 2}]}],
            "graph_layout": {"positions": {}},
        }
        target = vid if vid is not None else my_version(headers)["id"]
        return client.put(f"/api/versions/{target}/content", headers=headers, json=payload)

    # ---------- 阶段二：标注与提交 ----------
    ref_v = my_version(th)
    assert ref_v["kind"] == "reference"                            # 教师版本类型
    r = put_two_props(th)
    assert r.status_code == 200, r.text                            # 教师标准答案保存
    assert r.json()["relations"][0]["expr"] == "S(P1, P2)"
    assert client.post(f"/api/versions/{ref_v['id']}/submit", headers=th).status_code == 200

    v1 = my_version(s1h)
    assert put_two_props(s1h).status_code == 200                   # stu1 保存
    assert client.post(f"/api/versions/{v1['id']}/submit", headers=s1h).status_code == 200
    v2 = my_version(s2h)
    assert put_two_props(s2h, types=("SF", "SF")).status_code == 200  # stu2 保存
    assert client.post(f"/api/versions/{v2['id']}/submit", headers=s2h).status_code == 200
    assert my_version(s1h)["editable"] is False                    # 提交后只读

    status = client.get(f"/api/documents/{doc['id']}", headers=th).json()["status"]
    assert status == "SUBMITTED"                                   # 全部提交后等待裁定

    # ---------- 阶段三：比对与裁定 ----------
    cmp_t = client.get(f"/api/documents/{doc['id']}/compare", headers=th).json()
    ids = {g["version_id"] for g in cmp_t["groups"]}
    assert {v1["id"], v2["id"], ref_v["id"]} <= ids                # 裁定者见全部版本

    cmp1 = client.get(f"/api/documents/{doc['id']}/compare", headers=s1h)
    assert cmp1.status_code == 200                                 # 学生提交后可比对
    cmp1 = cmp1.json()
    assert [g["version_id"] for g in cmp1["groups"]] == [v1["id"]]  # 仅本人版本组
    base = next(v for v in client.get(f"/api/documents/{doc['id']}/versions",
                                      headers=th).json()
                if v["id"] == cmp1["base_version_id"])
    assert base["kind"] == "reference"                             # 基准=标准答案
    # 提交前学生比对被拒（不提前暴露标准答案）
    v2_draft = my_version(s2h)
    assert v2_draft["status"] == "submitted"

    adj = client.post(f"/api/documents/{doc['id']}/adjudicate", headers=th,
                      json={"base_version_id": ref_v["id"], "note": "E2E"})
    assert adj.status_code == 200 and adj.json()["kind"] == "final"
    final_id = adj.json()["id"]
    assert adj.json()["status"] == "draft"                         # 工作副本草稿期
    # 草稿期导出/登记被挡且不锁定（最终版未定稿）
    assert client.post(f"/api/documents/{doc['id']}/exports/record", headers=th,
                       json={"format": "png", "filename": "x.png"}).status_code == 409
    assert client.get(f"/api/documents/{doc['id']}", headers=th).json()["status"] != "OUTPUT"
    assert put_two_props(th, vid=final_id).status_code == 200      # 编辑期仍可保存
    assert client.post(f"/api/versions/{final_id}/submit", headers=th).status_code == 200
    status = client.get(f"/api/documents/{doc['id']}", headers=th).json()["status"]
    assert status == "ADJUDICATED"                                 # 提交定稿

    # ---------- 阶段四：导出与锁定 ----------
    rj = client.post(f"/api/documents/{doc['id']}/export", headers=th,
                     params={"format": "json"})
    assert rj.status_code == 200
    data = json.loads(rj.content)
    assert data["guide_version"] == "v1.1" and len(data["propositions"]) == 2
    assert client.get(f"/api/documents/{doc['id']}", headers=th).json()["status"] == "OUTPUT"
    assert client.put(f"/api/versions/{final_id}/content", headers=th,
                      json={"propositions": [], "relations": [],
                            "graph_layout": {}}).status_code == 403  # 锁定后编辑 403
    assert client.post(f"/api/documents/{doc['id']}/adjudicate", headers=th,
                       json={"base_version_id": ref_v["id"]}).status_code == 403

    # ---------- 各角色访问控制 ----------
    r = client.post("/api/auth/register", json={"username": "stranger_e2e",
                                                "password": "demo123",
                                                "display_name": "stranger"})
    stranger = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get(f"/api/versions/{v1['id']}", headers=stranger).status_code == 403
    assert client.get(f"/api/documents/{doc['id']}/compare", headers=stranger).status_code == 403
    assert client.post(f"/api/documents/{doc['id']}/exports/record", headers=stranger,
                       json={"format": "png", "filename": "x.png"}).status_code == 403
    assert client.post(f"/api/documents/{doc['id']}/exports/record", headers=th,
                       json={"format": "png", "filename": "x.png"}).status_code == 200
    recs = client.get(f"/api/documents/{doc['id']}/exports", headers=th).json()
    assert sorted(x["format"] for x in recs) == ["json", "png"]
