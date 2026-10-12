// @vitest-environment jsdom
/**
 * 选区码点偏移回归测试（修复 3）。
 *
 * 关键点：命题序号角标通过 CSS `content` 渲染（不是 DOM 文本节点），
 * 因此 Range 测量只统计原文文本；同行存在多个文本节点（高亮 <mark>）时
 * 偏移仍与 reasoning_text 的码点下标一致。
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { selectionToRange } from './charIndex'

/** 用给定 range 替换 window.getSelection 的返回值 */
function mockSelection(startNode: Node, startOffset: number, endNode: Node, endOffset: number) {
  const range = document.createRange()
  range.setStart(startNode, startOffset)
  range.setEnd(endNode, endOffset)
  vi.spyOn(window, 'getSelection').mockReturnValue({
    rangeCount: 1,
    isCollapsed: false,
    getRangeAt: () => range,
  } as unknown as Selection)
}

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('selectionToRange 码点偏移', () => {
  it('无高亮行：单个文本节点', () => {
    document.body.innerHTML =
      '<div id="root"><div class="text-line" data-start="0">甲说。乙说。</div></div>'
    const root = document.getElementById('root') as HTMLElement
    const line = document.querySelector('.text-line') as HTMLElement
    const text = line.firstChild as Text
    mockSelection(text, 3, text, 5) // 选中"乙说"
    expect(selectionToRange(root, 9)).toEqual({ start: 3, end: 5 })
  })

  it('高亮行内：序号角标不参与偏移（修复 3 回归）', () => {
    // 行 DOM 文本总量 == 原文"甲说。乙说，丙说。"（9 码点）；序号由 CSS content 渲染
    document.body.innerHTML =
      '<div id="root"><div class="text-line" data-start="0">甲说。' +
      '<mark class="prop-mark" data-seq="1">乙说，</mark>丙说。</div></div>'
    const root = document.getElementById('root') as HTMLElement
    const line = document.querySelector('.text-line') as HTMLElement
    const after = line.lastChild as Text // "丙说。"
    mockSelection(after, 0, after, 2) // 选中"丙说"
    // 若序号"1"被计入会得到 7..9；正确应为 6..8
    expect(selectionToRange(root, 9)).toEqual({ start: 6, end: 8 })
  })

  it('跨文本节点：起点在高亮内、终点在其后', () => {
    document.body.innerHTML =
      '<div id="root"><div class="text-line" data-start="0">甲说。' +
      '<mark class="prop-mark" data-seq="1">乙说，</mark>丙说。</div></div>'
    const root = document.getElementById('root') as HTMLElement
    const line = document.querySelector('.text-line') as HTMLElement
    const markText = line.querySelector('.prop-mark')!.firstChild as Text // "乙说，"
    const after = line.lastChild as Text // "丙说。"
    mockSelection(markText, 1, after, 2) // 从"乙说"的"说"选到"丙说"末尾
    expect(selectionToRange(root, 9)).toEqual({ start: 4, end: 8 })
  })
})
