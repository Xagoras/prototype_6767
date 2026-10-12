"""标签体系：默认 taxonomy 模板（指南 v1.1）与从指南文本提取版本号。

导入指南时以该模板为起点供用户校对——标签体系不硬编码在界面，
而是来自指南记录（见 models/guide.py），保证"旧版本指南导入后界面自然不同"。
"""
import re

VERSION_RE = re.compile(r"[vV](\d+(?:\.\d+)+)")


def extract_version(text: str, filename: str = "") -> str:
    """从指南文本/文件名提取版本号，失败返回空串（由用户手工填写）。"""
    m = VERSION_RE.search(filename)
    if m:
        return f"v{m.group(1)}"
    m = VERSION_RE.search(text[:2000])
    if m:
        return f"v{m.group(1)}"
    return ""


def default_taxonomy() -> dict:
    """指南 v1.1 的标签体系：四类命题 + 两类非命题 + GM/SM 子类型 + 五种关系。"""
    return {
        "elements": [
            {
                "code": "IS",
                "name": "争议焦点",
                "kind": "non_prop",
                "description": "小标题以及法院对案件争议的概括语言",
            },
            {
                "code": "Non",
                "name": "非论证成分",
                "kind": "non_prop",
                "description": "与论证无关的信息",
            },
            {
                "code": "SF",
                "name": "个别事实判断",
                "kind": "prop",
                "description": "关于案件中个别对象的事实判断，是规范适用的前提条件",
                "cues": ["原告已依约提供劳务", "被告尚欠原告劳务报酬11000元"],
            },
            {
                "code": "GF",
                "name": "一般事实判断",
                "kind": "prop",
                "description": "为规范适用提供经验或背景支撑的判断（社会常识、经验法则、行业知识、科学规律等）",
            },
            {
                "code": "SM",
                "name": "个别规范判断",
                "kind": "prop",
                "description": "具体相关主体做出的具有法律意义的评价判断，通常作为结论出现",
                "cues": ["被告应向原告支付该11000元", "对其主张本院不予支持"],
                "subtypes": [
                    {
                        "code": "SM",
                        "name": "普通个别规范判断",
                        "kind": "prop",
                        "description": "具体相关主体做出的具有法律意义的评价判断",
                        "cues": ["原告请求支付违约金", "一审法院认定", "缺乏事实与法律依据"],
                    },
                    {
                        "code": "SM-C",
                        "name": "合同及合同解释",
                        "kind": "prop",
                        "description": "来源于合同条款或对合同条款的规范性解释",
                        "cues": ["双方在合同中约定", "根据合同约定", "该条款应理解为"],
                    },
                ],
            },
            {
                "code": "GM",
                "name": "一般规范判断",
                "kind": "prop",
                "description": "构成法律论证的规范基础，连接个案事实与裁判结论的核心要素",
                "subtypes": [
                    {
                        "code": "GM-L",
                        "name": "法律条文",
                        "kind": "prop",
                        "description": "属于法源的权威性规范性文件，包括直接引用或转述",
                        "cues": ["依照《××法》第×条规定", "根据法律规定"],
                    },
                    {
                        "code": "GM-I",
                        "name": "法律解释",
                        "kind": "prop",
                        "description": "对法律条文含义、适用范围或适用条件所作的解释性判断",
                        "cues": ["应当理解为", "可以解释为", "该条规定的本意在于"],
                    },
                    {
                        "code": "GM-U",
                        "name": "习惯与行业惯例",
                        "kind": "prop",
                        "description": "来源于社会习惯、交易习惯或行业通行规则的规范性判断",
                        "cues": ["按照交易习惯", "行业通常做法是", "依照行业惯例"],
                    },
                    {
                        "code": "GM-M",
                        "name": "道德与价值观念",
                        "kind": "prop",
                        "description": "基于价值判断、公序良俗或基本原则作出的规范性判断",
                        "cues": ["违反公序良俗", "有悖公平原则", "违背诚实信用原则"],
                    },
                    {
                        "code": "GM-O",
                        "name": "其他规范判断",
                        "kind": "prop",
                        "description": "无法稳定归入上述类型的一般规范判断",
                        "cues": ["根据相关政策精神", "依照xxx的管理规定"],
                    },
                ],
            },
        ],
        "relations": [
            {
                "code": "S",
                "name": "支持关系",
                "arity": 2,
                "ordered": True,
                "formal": "S(pi, pj)",
                "description": "命题 pi 为命题 pj 的成立提供理由（实心圆●有向边）",
            },
            {
                "code": "A",
                "name": "反对关系",
                "arity": 2,
                "ordered": True,
                "formal": "A(po, pc)",
                "description": "命题 po 为命题 pc 的不成立提供理由（空心圆○有向边）",
            },
            {
                "code": "J",
                "name": "组合关系",
                "arity": 2,
                "ordered": False,
                "formal": "J(p1, p2, ..., pn)",
                "description": "多个命题“缺一不可”的合取结构（带+圆节点⊕无向连线）",
            },
            {
                "code": "M",
                "name": "匹配关系",
                "arity": 2,
                "ordered": True,
                "formal": "M(ps, pg)",
                "description": "个别判断与一般判断之间的对应（要件-事实匹配，⊕有向边）",
            },
            {
                "code": "I",
                "name": "同一关系",
                "arity": 2,
                "ordered": False,
                "formal": "I(p1, p2, ..., pn)",
                "description": "多个命题语义上表达同一判断内容（矩形框内“/”分隔）",
            },
        ],
    }
