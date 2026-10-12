"""pytest 共享 fixture：独立测试数据库 + 登录用户。"""
import os
import tempfile

# 必须在导入 app 之前设置测试数据库地址
_TEST_DB = os.path.join(tempfile.gettempdir(), "test_annotation_db.sqlite")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)
os.environ["DB_URL"] = f"sqlite:///{_TEST_DB}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def users(client):
    """创建演示用户并返回 {name: {headers, id}}。"""
    out = {}
    for name in ("teacher", "stu1", "stu2", "arbiter"):
        r = client.post("/api/auth/register",
                        json={"username": name, "password": "demo123",
                              "display_name": name})
        assert r.status_code == 200, r.text
        headers = {"Authorization": f"Bearer {r.json()['token']}"}
        me = client.get("/api/auth/me", headers=headers).json()
        out[name] = {"headers": headers, "id": me["id"]}
    return out


@pytest.fixture(scope="session")
def demo_doc(client, users):
    """创建演示任务 + 文档 + 分配，返回 (doc, task)。"""
    th = users["teacher"]["headers"]
    r = client.get("/api/guides", headers=th)
    guide_id = r.json()[0]["id"] if r.json() else None
    if guide_id is None:
        # 测试库没有种子指南：创建一份
        from app.services.taxonomy import default_taxonomy
        r = client.post("/api/guides", headers=th, json={
            "version": "v1.1", "name": "测试指南",
            "content_text": "测试", "taxonomy": default_taxonomy(),
        })
        guide_id = r.json()["id"]
    t = client.post("/api/tasks", headers=th,
                    json={"name": "测试任务", "guide_id": guide_id}).json()
    text = ("本院认为，依法成立的合同，自成立时生效。当事人应当按照约定全面履行自己的义务。"
            "本案中，原告已依约提供劳务，被告应按照约定给付劳务报酬。判决如下：支持原告。")
    d = client.post(f"/api/tasks/{t['id']}/documents/text", headers=th,
                    json={"name": "测试文书", "text": text}).json()
    # 分配：stu1/stu2 标注员；teacher 标准答案 + 裁定者
    client.post(f"/api/tasks/{t['id']}/assignments", headers=th,
                json={"document_ids": [d["id"]],
                      "user_ids": [users["stu1"]["id"], users["stu2"]["id"]],
                      "roles": ["annotator"]})
    client.post(f"/api/tasks/{t['id']}/assignments", headers=th,
                json={"document_ids": [d["id"]],
                      "user_ids": [users["teacher"]["id"]],
                      "roles": ["reference", "arbiter"]})
    return d, t
