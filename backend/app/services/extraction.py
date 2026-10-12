"""裁判理由自动提取（第二阶段需求 2.2.1：标注范围）。

原始判决书：起点为最后一次命中的"本院认为/本院经审理认为/本院再审认为"，
终点为"判决如下/裁定如下"（其次"综上所述"）。
指导性/参考案例：定位独立段落的"裁判理由"标题，向后收集至下一个标题。
未命中任何规则 → manual_required，由用户在界面上人工校正。
"""
import re

# 原始判决书起点（取最后一次命中，规避诉称中引用）
_START_RE = re.compile(r"本院(?:经审理)?(?:再审)?认为[，,：:]?")

# 终点：优先"判决如下/裁定如下"，其次"综上所述/综上"
_VERDICT_RE = re.compile(r"(?:判决|裁定)如下[：:]?")
_SUMMARY_RE = re.compile(r"综上(?:所述|来看)?[，,：:]?")

# 指导性/参考案例：独立成段的"裁判理由"标题
_HEADING_RE = re.compile(r"^\s*裁判理由\s*$")

# "裁判理由"之后的下一标题（收集至此为止）
_NEXT_HEADING_RE = re.compile(
    r"^\s*(裁判要旨|裁判结果|关联索引|生效裁判|典型意义|相关法条|基本案情|"
    r"裁判要点|关键词|入库编号|审理法院|案件概述|法理提示|注解)\s*$"
)


def extract_judgment(text: str) -> tuple[int | None, int | None, str]:
    """原始判决书：返回 (start, end, method)。offset 为 Unicode 码点。"""
    start = None
    for m in _START_RE.finditer(text):
        start = m.start()
    if start is None:
        return None, None, "manual_required"

    # 起点之后的第一个"判决如下/裁定如下"；没有则以"综上"兜底
    end = None
    m = _VERDICT_RE.search(text, start)
    if m:
        end = m.start()
    else:
        m = _SUMMARY_RE.search(text, start)
        if m:
            end = m.start()
    if end is None:
        return start, None, "manual_required"
    return start, end, "auto"


def _iter_heading_lines(text: str):
    """按行迭代，返回 (line_start, line_text)。"""
    pos = 0
    for line in text.split("\n"):
        yield pos, line
        pos += len(line) + 1


def extract_case(text: str) -> tuple[int | None, int | None, str]:
    """指导性/参考案例：返回 (start, end, method)。"""
    lines = list(_iter_heading_lines(text))
    start = None
    for i, (pos, line) in enumerate(lines):
        if _HEADING_RE.match(line):
            start = pos + len(line) + 1  # 标题行之后
            end = None
            # 向后找下一个标题
            for pos2, line2 in lines[i + 1:]:
                if _NEXT_HEADING_RE.match(line2):
                    end = pos2
                    break
            return start, end, "auto"
    return None, None, "manual_required"


def extract_reasoning(text: str, doc_type: str) -> tuple[str, int, int, str]:
    """统一入口：返回 (reasoning_text, start, end, method)。

    doc_type：judgment / guiding_case / ref_case。
    未命中或只有一半边界时 method=manual_required，界面强制人工校正。
    """
    if doc_type == "judgment":
        start, end, method = extract_judgment(text)
    else:
        start, end, method = extract_case(text)

    if start is None or end is None or end <= start:
        # 仅有一半边界或完全未命中：给默认值（全文或后半段），但标记需人工校正
        if start is None:
            start = 0
        if end is None or end <= start:
            end = len(text)
        return text[start:end], start, end, "manual_required"

    # 保留"本院认为，"导语（标注时可不选或标 Non）
    return text[start:end], start, end, method
