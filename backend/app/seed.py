"""演示数据种子脚本。

用法：
    python -m app.seed            # 重置数据库并导入演示数据
    python -m app.seed --keep     # 已存在数据时跳过（幂等）

演示账号（密码统一 demo123）：admin / teacher / stu1 / stu2 / arbiter
"""
import argparse
import json
import re
import sys
from pathlib import Path

from .auth import hash_password
from .config import SEED_DIR
from .database import Base, SessionLocal, engine
from .models import (
    AnnotationVersion, Assignment, Document, Guide, Proposition, RelationNode,
    Task, User,
)
from .services.extraction import extract_reasoning
from .services.segmentation import segment_reasoning
from .services.taxonomy import default_taxonomy

DEMO_USERS = [
    ("admin", "管理员", True),
    ("teacher", "王老师", False),
    ("stu1", "学生甲", False),
    ("stu2", "学生乙", False),
    ("arbiter", "裁定员", False),
]
DEMO_PASSWORD = "demo123"


def seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for username, display_name, is_admin in DEMO_USERS:
        u = User(
            username=username,
            password_hash=hash_password(DEMO_PASSWORD),
            display_name=display_name,
            is_admin=is_admin,
        )
        db.add(u)
        users[username] = u
    db.flush()  # 获得 id
    return users


def seed_guide(db, user: User) -> Guide:
    """导入预置指南 v1.1（正文 + taxonomy）。"""
    path = SEED_DIR / "guide_v1_1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    g = Guide(
        version=data["version"],
        name=data["name"],
        source_filename="guide_v1_1.json（内置）",
        content_text=data["content_text"],
        taxonomy=default_taxonomy(),
        imported_by=user.id,
        is_active=True,
    )
    db.add(g)
    db.flush()
    return g


def _locate(text: str, target: str) -> tuple[int, int] | None:
    """忽略空白定位目标文本（PDF 提取文本常含换行断裂）。"""
    pat = r"\s*".join(re.escape(ch) for ch in target)
    m = re.search(pat, text)
    if m is None:
        return None
    return m.start(), m.end()


def seed_demo(db, users: dict[str, User], guide: Guide) -> None:
    """完整演示：任务 + 文书一 + 分配 + 标准答案 + 学生差异版/一致版 + 裁定。"""
    # 文书一（余某徐某劳务合同纠纷，指南 7 节示例）
    wenshu_text = (SEED_DIR / "wenshu_1.txt").read_text(encoding="utf-8")
    reasoning_text, rs, re_end, method = extract_reasoning(wenshu_text, "judgment")

    task = Task(name="演示任务：劳务合同纠纷标注（文书一）", guide_id=guide.id,
                created_by=users["teacher"].id, annotators_per_doc=2,
                status="ADJUDICATING")
    db.add(task)
    db.flush()

    doc = Document(
        task_id=task.id, name="文书一：余某、徐某劳务合同纠纷",
        doc_type="judgment", source_filename="wenshu_1.txt（内置）",
        original_text=wenshu_text, reasoning_text=reasoning_text,
        reasoning_start=rs, reasoning_end=re_end, extraction_method=method,
        case_info={
            "案号": "(2023)苏0106民初18909号", "裁判法院": "江苏省南京市鼓楼区人民法院",
            "法院层级": "基层法院", "审级": "一审", "裁判日期": "2023年12月28日",
            "案件性质": "民事", "案由": "劳务合同纠纷", "裁判结果类型": "部分支持",
        },
        base_segments=segment_reasoning(reasoning_text),
        guide_version_snapshot=guide.version,
        status="ADJUDICATED",
    )
    db.add(doc)
    db.flush()

    # 分配：stu1/stu2 标注员；teacher 标准答案 + 裁定者
    for uname, role in [("stu1", "annotator"), ("stu2", "annotator"),
                        ("teacher", "reference"), ("teacher", "arbiter")]:
        db.add(Assignment(task_id=task.id, document_id=doc.id,
                          user_id=users[uname].id, role=role,
                          assigned_by=users["admin"].id))

    # 标准答案 P1-P13（指南表 9）
    P_TEXTS = [
        "依法成立的合同，自成立时生效。",
        "当事人应当按照约定全面履行自己的义务。",
        "当事人一方未支付价款、报酬、租金、利息，或者不履行其他金钱债务的，对方可以请求其支付。",
        "本案中，原、被告之间系劳务合同关系，",
        "原告已依约提供劳务，",
        "被告应按照原、被告之间的约定给付劳务报酬。",
        "根据原告提交的欠条、微信转账记录可以认定，",
        "被告尚欠原告劳务报酬 11000 元，",
        "被告应向原告支付该 11000 元。",
        "原告主张另有劳务报酬 600 元，",
        "但其提供的证据不足以证明其主张，",
        "对其主张被告支付该 600 元劳务报酬的请求，",
        "本院不予支持。",
    ]
    P_TYPES = [("GM", "GM-L")] * 3 + [("SM", None), ("SF", None), ("SM", None),
                                       ("SF", None), ("SF", None), ("SM", None),
                                       ("SF", None), ("SF", None), ("SM", None),
                                       ("SM", None)]
    # 关系 R1-R10（指南表 10）：args 用 (kind, seq/下标)
    R_DEFS = [
        ("J", [("P", 4), ("P", 5)]),
        ("M", [("R", 0), ("P", 2)]),
        ("S", [("R", 1), ("P", 6)]),
        ("S", [("P", 7), ("P", 8)]),
        ("J", [("P", 8), ("P", 6)]),
        ("M", [("R", 4), ("P", 3)]),
        ("S", [("R", 5), ("P", 9)]),
        ("S", [("P", 10), ("P", 12)]),
        ("A", [("P", 11), ("P", 10)]),
        ("S", [("P", 11), ("P", 13)]),
    ]

    def fill_version(version: AnnotationVersion, p_types, r_defs) -> None:
        """按 P_TEXTS 定位偏移并写入命题/关系（P 引用 seq、R 引用下标）。"""
        prop_ids: dict[int, int] = {}
        for seq, (ptext, (tc, sc)) in enumerate(zip(P_TEXTS, p_types), start=1):
            loc = _locate(reasoning_text, ptext)
            if loc is None:
                print(f"  警告：未定位到 P{seq}（{ptext[:16]}…），跳过")
                continue
            p = Proposition(version_id=version.id, char_start=loc[0],
                            char_end=loc[1], text=reasoning_text[loc[0]:loc[1]],
                            type_code=tc, subtype_code=sc)
            db.add(p)
            db.flush()
            prop_ids[seq] = p.id
        rel_ids: dict[int, int] = {}
        for i, (rt, args) in enumerate(r_defs):
            r = RelationNode(version_id=version.id, rel_type=rt, args=[])
            db.add(r)
            db.flush()
            rel_ids[i] = r.id
        for i, (rt, args) in enumerate(r_defs):
            mapped = []
            for kind, ref in args:
                if kind == "P":
                    mapped.append({"kind": "P", "id": prop_ids[ref]})
                else:
                    mapped.append({"kind": "R", "id": rel_ids[ref]})
            rel = db.get(RelationNode, rel_ids[i])
            rel.args = mapped

    def make_version(annotator: User, kind: str, status: str) -> AnnotationVersion:
        v = AnnotationVersion(document_id=doc.id, annotator_id=annotator.id,
                              kind=kind, status=status)
        db.add(v)
        db.flush()
        return v

    # teacher 标准答案
    ref_v = make_version(users["teacher"], "reference", "submitted")
    fill_version(ref_v, P_TYPES, R_DEFS)

    # stu1 差异版：P4 误标 SF、缺 R5（J(P8,P6) 及其上层）、R9 方向反
    p_types_1 = list(P_TYPES)
    p_types_1[3] = ("SF", None)
    r_defs_1 = (
        [("J", [("P", 4), ("P", 5)]),
         ("M", [("R", 0), ("P", 2)]),
         ("S", [("R", 1), ("P", 6)]),
         ("S", [("P", 7), ("P", 8)]),
         ("M", [("R", 3), ("P", 3)]),
         ("S", [("R", 4), ("P", 9)]),
         ("S", [("P", 10), ("P", 12)]),
         ("A", [("P", 10), ("P", 11)]),
         ("S", [("P", 11), ("P", 13)])]
    )
    stu1_v = make_version(users["stu1"], "normal", "submitted")
    fill_version(stu1_v, p_types_1, r_defs_1)

    # stu2 一致版（与标准答案完全相同）
    stu2_v = make_version(users["stu2"], "normal", "submitted")
    fill_version(stu2_v, P_TYPES, R_DEFS)

    # 裁定：以标准答案为基础生成最终版
    final_v = AnnotationVersion(document_id=doc.id, annotator_id=users["teacher"].id,
                                kind="final", status="submitted")
    db.add(final_v)
    db.flush()
    # 复制标准答案
    prop_map: dict[int, int] = {}
    for p in db.query(Proposition).filter(Proposition.version_id == ref_v.id).all():
        np = Proposition(version_id=final_v.id, char_start=p.char_start,
                         char_end=p.char_end, text=p.text, edited_text=p.edited_text,
                         type_code=p.type_code, subtype_code=p.subtype_code,
                         flagged=p.flagged, flag_note=p.flag_note)
        db.add(np)
        db.flush()
        prop_map[p.id] = np.id
    rel_map: dict[int, int] = {}
    for r in db.query(RelationNode).filter(RelationNode.version_id == ref_v.id).all():
        nr = RelationNode(version_id=final_v.id, rel_type=r.rel_type, args=[])
        db.add(nr)
        db.flush()
        rel_map[r.id] = nr.id
    for r in db.query(RelationNode).filter(RelationNode.version_id == ref_v.id).all():
        remapped = []
        for a in r.args:
            if a["kind"] == "P":
                remapped.append({"kind": "P", "id": prop_map[a["id"]]})
            else:
                remapped.append({"kind": "R", "id": rel_map[a["id"]]})
        db.get(RelationNode, rel_map[r.id]).args = remapped

    print(f"  演示任务「{task.name}」：文档「{doc.name}」")
    print(f"  标准答案 P{len(P_TEXTS)} / R{len(R_DEFS)}；stu1 差异版（P4 类型、缺 R5、R9 方向反）；stu2 一致版；最终版已裁定")


def run(reset: bool) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0 and not reset:
            print("数据库已有数据，跳过导入（使用 --reset 可重建）")
            return
        users = seed_users(db)
        guide = seed_guide(db, users["admin"])
        seed_demo(db, users, guide)
        db.commit()
        print(f"种子完成：用户 {len(users)} 个；指南 {guide.version}（id={guide.id}）；演示任务 1 个")
        print("演示账号（密码均为 demo123）：admin / teacher / stu1 / stu2 / arbiter")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="演示数据种子")
    parser.add_argument("--reset", action="store_true", help="重建数据库（默认）")
    parser.add_argument("--keep", action="store_true", help="幂等模式：已有数据则跳过")
    args = parser.parse_args()
    run(reset=not args.keep)
    sys.exit(0)
