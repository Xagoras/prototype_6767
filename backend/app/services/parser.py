"""文件解析与文本规范化。

- 支持 PDF（pypdf）、Word（python-docx）、纯文本（utf-8 优先、gbk 兜底）
- 规范化是字符偏移稳定的前提：服务器返回文本是唯一权威，前端不二次规范化
"""
import io
import re

from pypdf import PdfReader

# 中文之间的 PDF 干扰空格（pypdf 提取时常见）
_CJK_GAP = re.compile(r"(?<=[一-鿿])\s+(?=[一-鿿])")


def normalize_text(text: str) -> str:
    """统一换行、清除中文间干扰空格、压缩多余空行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CJK_GAP.sub("", text)
    # 压缩 3 个以上连续空行为 1 个
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return normalize_text("\n".join(pages))


def parse_docx(data: bytes) -> str:
    import docx

    doc = docx.Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs]
    # 表格内容也纳入（指南与文书常见）
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return normalize_text("\n".join(parts))


def parse_txt(data: bytes) -> str:
    for enc in ("utf-8", "gbk"):
        try:
            return normalize_text(data.decode(enc))
        except UnicodeDecodeError:
            continue
    # 都失败则忽略错误解码
    return normalize_text(data.decode("utf-8", errors="ignore"))


def parse_file(filename: str, data: bytes) -> str:
    """按扩展名分发解析。"""
    name = filename.lower()
    if name.endswith(".pdf"):
        return parse_pdf(data)
    if name.endswith(".docx"):
        return parse_docx(data)
    # txt / doc(旧格式按文本尝试) / 其他按文本
    return parse_txt(data)
