"""颗粒度自动切割（第二阶段需求 2.3 颗粒度）。

1. 引号保护：成对引号（“”「」‘’""）内的句读不参与切分（双引号内容为基本单位）
2. 第一次切割：按 。！？ 切句
3. 第二次考查：句内按 ，； 切子句候选（连续同性质子句是否合并由标注员决定，
   系统不替标注员做法律判断——UC-02 A3）
4. 过渡语词（"因此，""综上，"等）与其之后的第一个要素合并：过渡词并入后一候选
"""
import re

# 过渡语词（位于候选开头时并入后一候选块）
_TRANSITION_RE = re.compile(
    r"^(?:因此[，,]?|综上(?:所述|来看)?[，,]?|所以[，,]?|据此[，,]?|故[，,]?|"
    r"由此[，,]?|于是[，,]?|因而[，,]?|可见[，,]?|理由是[，,]|理由如下[：:])"
)

# 开引号 → 闭引号
_QUOTES = {'“': '”', '‘': '’', '「': '」', '"': '"', "'": "'"}
_CLOSING = set(_QUOTES.values())

# 句末与句内切分标点
_SENTENCE_ENDS = set("。！？")
_CLAUSE_SEPS = set("，；")


def _find_protected(text: str) -> list[tuple[int, int]]:
    """扫描成对引号，返回保护区间 [start, end)（闭引号不纳入切分点范围）。"""
    stack: list[tuple[str, int]] = []
    protected: list[tuple[int, int]] = []
    for i, ch in enumerate(text):
        if ch in _QUOTES:
            if stack and stack[-1][0] == ch:
                # 同一引号字符再次出现视为闭合（如英文双引号）
                _, start = stack.pop()
                protected.append((start, i + 1))
            else:
                stack.append((ch, i))
        elif ch in _CLOSING and stack and _QUOTES[stack[-1][0]] == ch:
            _, start = stack.pop()
            protected.append((start, i + 1))
    return protected


def _is_protected(pos: int, protected: list[tuple[int, int]]) -> bool:
    for s, e in protected:
        if s <= pos < e:
            return True
    return False


def segment_reasoning(text: str) -> list[dict]:
    """切割裁判理由文本，返回 [{start, end, text}]（Unicode 码点偏移）。

    start/end 相对传入文本；文本中保留标点（切分点标点留在前一块末尾）。
    """
    protected = _find_protected(text)
    n = len(text)
    # 切分点集合（句末与句内标点，保护区内跳过）
    cuts: list[int] = []
    for i, ch in enumerate(text):
        if ch in _SENTENCE_ENDS or ch in _CLAUSE_SEPS:
            if not _is_protected(i, protected):
                cuts.append(i)

    # 按切分点形成原子候选块（标点保留在块内；前导空白剥离，保证过渡词可匹配）
    blocks: list[dict] = []
    prev = 0
    for c in cuts:
        end = c + 1  # 含标点
        start = prev
        # 块内前导空白跳过（偏移指向第一个非空白字符）
        while start < end and text[start].isspace():
            start += 1
        if end > start:
            blocks.append({"start": start, "end": end, "text": text[start:end]})
        prev = end
    if prev < n:
        start = prev
        while start < n and text[start].isspace():
            start += 1
        if start < n:
            blocks.append({"start": start, "end": n, "text": text[start:n]})

    # 过渡语词归并：候选以过渡词开头 → 过渡词并入下一候选
    # 关键：并入时把下一块的 start 回退到过渡词起点，保证 text == reasoning_text[start:end]
    result: list[dict] = []
    pending_start: int | None = None  # 被剥离的纯过渡词块起点（待并入下一块）
    for b in blocks:
        t = b["text"]
        m = _TRANSITION_RE.match(t)
        if m and t[-1] not in _SENTENCE_ENDS:
            rest = t[m.end():]
            if rest.strip():
                # 块内：过渡词与其后内容同属一个要素，保持原样（偏移即原文）
                result.append({"start": b["start"], "end": b["end"], "text": text[b["start"]:b["end"]]})
                continue
            # 整块仅为过渡语词（如"因此，"）：并入下一要素
            if pending_start is None:
                pending_start = b["start"]
            continue
        if pending_start is not None:
            result.append({"start": pending_start, "end": b["end"],
                           "text": text[pending_start:b["end"]]})
            pending_start = None
        else:
            result.append({"start": b["start"], "end": b["end"], "text": text[b["start"]:b["end"]]})

    # 结尾遗留的 pending（如文末"因此"）独立成块
    if pending_start is not None:
        result.append({"start": pending_start, "end": n, "text": text[pending_start:n]})

    return result
