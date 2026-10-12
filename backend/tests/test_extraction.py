"""裁判理由提取规则测试（文书一/指导性案例/无关键词兜底）。"""
from app.services.extraction import extract_reasoning


def test_judgment_auto_extraction():
    """原始判决书：'本院认为'→'判决如下'。"""
    text = ("原告起诉。\n本院认为，原告的主张成立，被告应赔偿。\n"
            "综上所述，依照法律规定，判决如下：\n一、被告赔偿原告。")
    reasoning, start, end, method = extract_reasoning(text, "judgment")
    assert method == "auto"
    assert text[start:end].startswith("本院认为")
    assert "判决如下" not in reasoning  # 终点在"判决如下"之前


def test_judgment_last_benyuan_renwei():
    """当事人诉称中引用'本院认为'时取最后一次命中（真裁判理由）。"""
    text = ("原告诉称：'本院认为我应当胜诉'，故起诉。\n"
            "本院认为，原告的请求部分成立。判决如下：支持。")
    reasoning, start, end, method = extract_reasoning(text, "judgment")
    assert method == "auto"
    assert "原告的请求部分成立" in reasoning


def test_judgment_summary_fallback():
    """无'判决如下'时以'综上所述'兜底。"""
    text = "本院认为，原告主张成立。\n综上所述，被告应赔偿。"
    reasoning, start, end, method = extract_reasoning(text, "judgment")
    assert method == "auto"
    assert reasoning.rstrip().endswith("原告主张成立。")
    assert "被告应赔偿" not in reasoning


def test_judgment_manual_required():
    """无任何关键词 → manual_required。"""
    text = "这是一段没有任何关键词的文本。"
    reasoning, start, end, method = extract_reasoning(text, "judgment")
    assert method == "manual_required"


def test_case_heading_extraction():
    """指导性/参考案例：'裁判理由'标题段落到下一个标题。"""
    text = ("关键词 民事 合同\n基本案情\n某某案。\n裁判理由\n"
            "法院生效裁判认为：合同有效。\n裁判要旨\n合同应全面履行。\n关联索引\n民法典")
    reasoning, start, end, method = extract_reasoning(text, "ref_case")
    assert method == "auto"
    assert "法院生效裁判认为" in reasoning
    assert "合同应全面履行" not in reasoning


def test_case_manual_required():
    """指导性案例无'裁判理由'标题 → manual_required。"""
    text = "关键词 民事\n基本案情\n某某案。"
    _, _, _, method = extract_reasoning(text, "guiding_case")
    assert method == "manual_required"
