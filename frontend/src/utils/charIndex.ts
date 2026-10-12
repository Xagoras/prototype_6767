/**
 * 文本选区 → Unicode 码点偏移计算（需求 3.2：基于字符索引的定位）。
 *
 * 索引单位统一为 Unicode 码点：JS 用 Array.from 计数（规避 UTF-16 代理对），
 * Python str[start:end] 天然按码点切片，两侧一致。
 * 渲染约定：reasoning_text 按行渲染为 <span data-start=行起点码点>，
 * 选区端点所在文本节点即该 span 的 text node。
 */

/** 计算选区在全文中的 [start, end)（码点） */
export function selectionToRange(root: HTMLElement, textLength: number): { start: number; end: number } | null {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null
  const range = sel.getRangeAt(0)
  if (!root.contains(range.startContainer) || !root.contains(range.endContainer)) return null

  const start = nodeOffsetToGlobal(range.startContainer, range.startOffset)
  const end = nodeOffsetToGlobal(range.endContainer, range.endOffset)
  if (start === null || end === null) return null
  if (end <= start) return null
  return {
    start: Math.max(0, start),
    end: Math.min(textLength, end),
  }
}

/** 文本节点内偏移 → 全局码点偏移 */
function nodeOffsetToGlobal(node: Node, offset: number): number | null {
  // 向上找到 data-start 属性的行 span
  let el: HTMLElement | null = node.nodeType === Node.TEXT_NODE
    ? (node.parentElement as HTMLElement)
    : (node as HTMLElement)
  while (el && !el.hasAttribute('data-start')) el = el.parentElement
  if (!el) return null

  const lineStart = Number(el.getAttribute('data-start'))
  // 文本节点数据（选区端点必在行内文本节点中；嵌套 mark 时取父文本）
  const text = node.nodeType === Node.TEXT_NODE ? (node as Text).data : ''
  const offsetInNode = Math.min(offset, Array.from(text).length)
  return lineStart + offsetInNode
}

/** 字符串按码点切片的跨平台等价实现（JS 侧辅助） */
export function codePointSlice(text: string, start: number, end: number): string {
  return Array.from(text).slice(start, end).join('')
}

/** 计算字符串的码点长度 */
export function codePointLength(text: string): number {
  return Array.from(text).length
}

/** 行切分：返回每行的码点起点（渲染 data-start 用） */
export function lineStarts(text: string): { start: number; content: string }[] {
  const lines: { start: number; content: string }[] = []
  let pos = 0
  for (const line of text.split('\n')) {
    lines.push({ start: pos, content: line })
    pos += codePointLength(line) + 1
  }
  return lines
}
