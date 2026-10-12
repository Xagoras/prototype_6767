/**
 * 标签选择面板（中栏上）：按钮组由指南 taxonomy 动态生成。
 * 交互：先在原文划选（浮动工具条创建）或选中命题后点击标签赋值。
 * 本面板维护"当前选中命题"，点击标签即应用。
 */
import { useAnnotationStore } from '../../stores/annotationStore'

const TYPE_COLORS: Record<string, string> = {
  SF: 'var(--sf)', GF: 'var(--gf)', SM: 'var(--sm)', GM: 'var(--gm)',
  IS: 'var(--is)', Non: 'var(--non)',
}

export default function LabelPicker() {
  const store = useAnnotationStore()
  const activeSeq = store.selectedPropSeq

  const guide = store.guide
  if (!guide) return <div className="empty-hint">未找到任务指南</div>

  const elements = guide.taxonomy.elements
  const active = store.propositions.find((p) => p.seq === activeSeq)

  const apply = (code: string, sub?: string) => {
    if (activeSeq == null) return
    store.updateProp(activeSeq, { type_code: code, subtype_code: sub ?? null })
  }

  return (
    <div className="label-picker">
      <div className="picker-head">
        命题类型
        {active && (
          <span className="picker-active">当前：P{active.seq}</span>
        )}
        {!active && <span className="picker-hint">点击命题列表中的命题后选标签</span>}
      </div>
      {elements.map((e) => (
        <div key={e.code} className="label-group">
          <button
            className={`label-btn${active?.type_code === e.code ? ' active' : ''}`}
            style={{ background: TYPE_COLORS[e.code] ?? '#f0f0f0' }}
            title={e.description}
            onClick={() => apply(e.code)}
          >
            <b>{e.code}</b> {e.name}
          </button>
          {e.subtypes && e.subtypes.length > 0 && (
            <div className="subtype-row">
              {e.subtypes.map((s) => (
                <button
                  key={s.code}
                  className={`sub-btn${active?.type_code === e.code && active?.subtype_code === s.code ? ' active' : ''}`}
                  title={s.description}
                  onClick={() => apply(e.code, s.code)}
                >
                  {s.code} {s.name}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
