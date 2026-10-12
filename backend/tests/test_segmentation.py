"""颗粒度切割规则测试（指南 2.3）。"""
from app.services.segmentation import segment_reasoning


def test_sentence_split():
    """按句号切句，标点保留在块内。"""
    segs = segment_reasoning("第一句话。第二句话。")
    assert [s["text"] for s in segs] == ["第一句话。", "第二句话。"]


def test_clause_split():
    """句内按逗号切子句候选。"""
    segs = segment_reasoning("本院认为，依法成立的合同，自成立时生效。")
    texts = [s["text"] for s in segs]
    assert "本院认为，" in texts
    assert "依法成立的合同，" in texts
    assert "自成立时生效。" in texts


def test_quote_protection():
    """双引号内的句读不参与切分（引号内容为基本单位）。"""
    segs = segment_reasoning("原告称：“2023 年 1 月。双方结算。”此后起诉。")
    texts = [s["text"] for s in segs]
    # 引号内句号不应切开
    assert any("2023 年 1 月。双方结算。" in t for t in texts)


def test_transition_merge():
    """过渡语词'因此，'并入后一要素。"""
    segs = segment_reasoning("被告未付款。因此，被告构成违约。")
    texts = [s["text"] for s in segs]
    assert "因此，被告构成违约。" in texts


def test_offsets_are_codepoints():
    """偏移与文本一致（码点切片验证）。"""
    text = "甲说。乙说，丙说。"
    for s in segment_reasoning(text):
        assert text[s["start"]:s["end"]] == s["text"]


def test_transition_merge_offsets_consistent():
    """过渡词块并入后一要素时，text 仍与码点切片一致（回归 bug）。"""
    text = "被告未付款，因此，被告构成违约。"
    segs = segment_reasoning(text)
    assert "因此，被告构成违约。" in [s["text"] for s in segs]
    for s in segs:
        assert text[s["start"]:s["end"]] == s["text"]

