/**
 * 标注工作台状态：版本内容、撤销/重做快照栈、防抖保存、双向联动枢纽。
 *
 * 本地模型约定（与后端 payload 一致）：
 * - propositions：数组，序号 seq 按 char_start 排序实时计算
 * - relations：数组，args 中 P 引用 seq、R 引用数组下标
 * 保存为全量 PUT；响应后应用服务器返回内容（id 重新对齐）。
 */
import { create } from 'zustand'
import { api, errMsg } from '../api/client'
import type {
  AnnotationVersion, Document, GraphLayout, Guide, Proposition,
  RelationNode, RelType, VersionKind,
} from '../types'

/** 可撤销快照 */
interface Snapshot {
  propositions: Proposition[]
  relations: RelationNode[]
  graphLayout: GraphLayout
}

const MAX_UNDO = 50
const SAVE_DEBOUNCE_MS = 1200

interface AnnotationState {
  doc: Document | null
  guide: Guide | null
  versionId: number | null
  kind: VersionKind | null
  status: string
  editable: boolean
  propositions: Proposition[]
  relations: RelationNode[]
  graphLayout: GraphLayout
  loading: boolean
  saving: boolean
  lastError: string
  selection: { start: number; end: number; text: string } | null
  selectedPropSeq: number | null
  undoStack: Snapshot[]
  redoStack: Snapshot[]
  canUndo: boolean
  canRedo: boolean

  load: (docId: number, versionId?: number) => Promise<void>
  setSelection: (sel: { start: number; end: number; text: string } | null) => void
  setSelectedPropSeq: (seq: number | null) => void
  createProp: (start: number, end: number, text: string, typeCode?: string, subtypeCode?: string) => void
  updateProp: (seq: number, patch: Partial<Proposition>) => void
  deleteProp: (seq: number) => void
  mergeProps: (seqA: number, seqB: number) => void
  editPropText: (seq: number, text: string) => void
  addRelation: (type: RelType, args: { kind: 'P' | 'R'; id: number }[]) => void
  updateRelation: (index: number, patch: Partial<RelationNode>) => void
  deleteRelation: (index: number) => void
  updateGraphLayout: (layout: GraphLayout) => void
  undo: () => void
  redo: () => void
  saveNow: () => Promise<void>
  submit: () => Promise<void>
}

function snapshotOf(s: Pick<AnnotationState, 'propositions' | 'relations' | 'graphLayout'>): Snapshot {
  return JSON.parse(JSON.stringify({
    propositions: s.propositions, relations: s.relations, graphLayout: s.graphLayout,
  }))
}

let saveTimer: ReturnType<typeof setTimeout> | null = null

/**
 * 服务器关系 → 本地形式转换：
 * 服务器 args 的 id 是数据库主键（P=命题 dbId、R=关系 dbId），
 * 本地约定 args 的 id 是命题 seq / 关系数组下标（与保存 payload 一致）。
 */
function relationsFromServer(relations: RelationNode[], props: Proposition[]): RelationNode[] {
  const idToIdx = new Map(relations.map((r, i) => [r.id, i]))
  const propIdToSeq = new Map(props.map((p) => [p.id, p.seq as number]))
  return relations.map((r) => ({
    ...r,
    args: r.args.map((a) =>
      a.kind === 'P'
        ? { ...a, id: propIdToSeq.get(a.id) ?? a.id }
        : { ...a, id: idToIdx.get(a.id) ?? a.id },
    ),
  }))
}

/** 为 propositions 实时重排 seq（按 char_start） */
function renumber(props: Proposition[]): Proposition[] {
  return [...props].sort((a, b) => a.char_start - b.char_start)
    .map((p, i) => ({ ...p, seq: i + 1 }))
}

export const useAnnotationStore = create<AnnotationState>((set, get) => {
  /** 压入撤销栈并调度防抖保存 */
  const pushSnapshotAndSave = (newState: Partial<AnnotationState>) => {
    const s = get()
    const undoStack = [...s.undoStack, snapshotOf(s)].slice(-MAX_UNDO)
    set({ ...newState, undoStack, redoStack: [], canUndo: true, canRedo: false })
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => { void get().saveNow() }, SAVE_DEBOUNCE_MS)
  }

  return {
    doc: null,
    guide: null,
    versionId: null,
    kind: null,
    status: 'draft',
    editable: false,
    propositions: [],
    relations: [],
    graphLayout: { positions: {} },
    loading: false,
    saving: false,
    lastError: '',
    selection: null,
    selectedPropSeq: null,
    undoStack: [],
    redoStack: [],
    canUndo: false,
    canRedo: false,

    load: async (docId, versionId) => {
      set({ loading: true, lastError: '' })
      try {
        const verUrl = versionId
          ? `/versions/${versionId}` // 裁定工作副本 / 教学比对：加载指定版本
          : `/documents/${docId}/my-version`
        const [ver, doc, guides] = await Promise.all([
          api.get<AnnotationVersion>(verUrl),
          api.get<Document>(`/documents/${docId}`),
          api.get<Guide[]>('/guides'),
        ])
        const docData = doc.data
        const guide = guides.data.find((g) => g.version === docData.guide_version_snapshot)
        const props = renumber(ver.data.propositions ?? [])
        set({
          doc: docData,
          guide: guide ?? null,
          versionId: ver.data.id,
          kind: ver.data.kind,
          status: ver.data.status,
          editable: ver.data.editable,
          propositions: props,
          relations: relationsFromServer(ver.data.relations ?? [], props),
          graphLayout: ver.data.graph_layout,
          undoStack: [], redoStack: [], canUndo: false, canRedo: false,
        })
      } catch (e) {
        set({ lastError: errMsg(e) })
      } finally {
        set({ loading: false })
      }
    },

    setSelection: (sel) => set({ selection: sel }),

    setSelectedPropSeq: (seq) => set({ selectedPropSeq: seq }),

    createProp: (start, end, text, typeCode, subtypeCode) => {
      const prop: Proposition = {
        id: -Date.now(), version_id: 0, char_start: start, char_end: end,
        text, edited_text: null, type_code: typeCode ?? null,
        subtype_code: subtypeCode ?? null, flagged: false, flag_note: '',
        segment_id: null,
      }
      pushSnapshotAndSave({ propositions: renumber([...get().propositions, prop]) })
    },

    updateProp: (seq, patch) => {
      const props = get().propositions.map((p) =>
        p.seq === seq ? { ...p, ...patch } : p)
      pushSnapshotAndSave({ propositions: renumber(props) })
    },

    deleteProp: (seq) => {
      const props = get().propositions.filter((p) => p.seq !== seq)
      const renumbered = renumber(props)
      // 旧 seq → 新 seq 映射，用于关系引用重定向
      const seqMap = new Map<number, number>()
      get().propositions.forEach((p) => {
        const target = renumbered.find((q) =>
          q.char_start === p.char_start && q.char_end === p.char_end)
        if (target && p.seq) seqMap.set(p.seq, target.seq ?? p.seq)
      })
      const relations = get().relations
        .filter((r) => !r.args.some((a) => a.kind === 'P' && a.id === seq))
        .map((r) => ({
          ...r,
          args: r.args.map((a) =>
            a.kind === 'P' ? { ...a, id: seqMap.get(a.id) ?? a.id } : a),
        }))
      pushSnapshotAndSave({ propositions: renumbered, relations })
    },

    mergeProps: (seqA, seqB) => {
      const s = get()
      const a = s.propositions.find((p) => p.seq === seqA)
      const b = s.propositions.find((p) => p.seq === seqB)
      if (!a || !b || !s.doc) return
      const start = Math.min(a.char_start, b.char_start)
      const end = Math.max(a.char_end, b.char_end)
      const merged: Proposition = {
        ...a, id: -Date.now(), char_start: start, char_end: end,
        text: s.doc.reasoning_text.slice(start, end),
        type_code: a.type_code ?? b.type_code,
        subtype_code: a.subtype_code ?? b.subtype_code,
      }
      const rest = s.propositions.filter((p) => p !== a && p !== b)
      const renumbered = renumber([...rest, merged])
      // 旧 seq → 新 seq（按区间内容匹配）
      const seqMap = new Map<number, number>()
      for (const old of [...renumber([...rest, merged]), a, b]) {
        const target = renumbered.find((q) =>
          q.char_start === old.char_start && q.char_end === old.char_end)
        if (target && old.seq) seqMap.set(old.seq, target.seq ?? old.seq)
      }
      const relations = s.relations.map((r) => ({
        ...r,
        args: r.args.map((x) =>
          x.kind === 'P' ? { ...x, id: seqMap.get(x.id) ?? x.id } : x),
      }))
      pushSnapshotAndSave({ propositions: renumbered, relations })
    },

    editPropText: (seq, text) => {
      get().updateProp(seq, { edited_text: text })
    },

    addRelation: (type, args) => {
      const rel: RelationNode = {
        id: -Date.now(), version_id: 0, rel_type: type, args,
        note: '', flagged: false, flag_note: '',
      }
      pushSnapshotAndSave({ relations: [...get().relations, rel] })
    },

    updateRelation: (index, patch) => {
      const relations = get().relations.map((r, i) =>
        i === index ? { ...r, ...patch } : r)
      pushSnapshotAndSave({ relations })
    },

    deleteRelation: (index) => {
      const all = get().relations
      // 沿引用链迭代收集全部待删节点：直接引用被删节点者、以及引用了这些节点者
      // （多层嵌套，如 A(p3, S(J(p1,p2),p3)) 删内层 J 时 M/S 链需一并删除），
      // 否则会残留悬空 R 引用 → 关系表达式递归越界崩溃
      const toRemove = new Set<number>([index])
      let changed = true
      while (changed) {
        changed = false
        all.forEach((r, i) => {
          if (toRemove.has(i)) return
          if (r.args.some((a) => a.kind === 'R' && toRemove.has(a.id))) {
            toRemove.add(i)
            changed = true
          }
        })
      }
      const kept = all.filter((_, i) => !toRemove.has(i))
      // 旧下标 → 新下标（保留节点间的引用全部落在保留集合内，映射必存在）
      const remap = new Map<number, number>()
      let next = 0
      all.forEach((_, i) => {
        if (!toRemove.has(i)) remap.set(i, next++)
      })
      const cleaned = kept.map((r) => ({
        ...r,
        args: r.args.map((a) =>
          a.kind === 'R' ? { ...a, id: remap.get(a.id) ?? a.id } : a),
      }))
      pushSnapshotAndSave({ relations: cleaned })
    },

    updateGraphLayout: (layout) => {
      pushSnapshotAndSave({ graphLayout: layout })
    },

    undo: () => {
      const s = get()
      if (s.undoStack.length === 0) return
      const prev = s.undoStack[s.undoStack.length - 1]
      set({
        propositions: prev.propositions, relations: prev.relations,
        graphLayout: prev.graphLayout,
        undoStack: s.undoStack.slice(0, -1),
        redoStack: [...s.redoStack, snapshotOf(s)],
        canUndo: s.undoStack.length > 1,
        canRedo: true,
      })
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(() => { void get().saveNow() }, SAVE_DEBOUNCE_MS)
    },

    redo: () => {
      const s = get()
      if (s.redoStack.length === 0) return
      const next = s.redoStack[s.redoStack.length - 1]
      set({
        propositions: next.propositions, relations: next.relations,
        graphLayout: next.graphLayout,
        redoStack: s.redoStack.slice(0, -1),
        undoStack: [...s.undoStack, snapshotOf(s)],
        canRedo: s.redoStack.length > 1,
        canUndo: true,
      })
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(() => { void get().saveNow() }, SAVE_DEBOUNCE_MS)
    },

    saveNow: async () => {
      const s = get()
      if (saveTimer) { clearTimeout(saveTimer); saveTimer = null }
      if (!s.versionId || !s.editable) return
      set({ saving: true })
      try {
        const props = renumber(s.propositions)
        const payload = {
          propositions: props.map((p) => ({
            char_start: p.char_start, char_end: p.char_end, text: p.text,
            edited_text: p.edited_text, type_code: p.type_code,
            subtype_code: p.subtype_code, flagged: p.flagged, flag_note: p.flag_note,
          })),
          relations: s.relations.map((r) => ({
            rel_type: r.rel_type, args: r.args, note: r.note,
            flagged: r.flagged, flag_note: r.flag_note,
          })),
          graph_layout: s.graphLayout,
        }
        const res = await api.put<AnnotationVersion>(`/versions/${s.versionId}/content`, payload)
        const savedProps = renumber(res.data.propositions ?? [])
        set({
          propositions: savedProps,
          relations: relationsFromServer(res.data.relations ?? [], savedProps),
          graphLayout: res.data.graph_layout,
          status: res.data.status,
          lastError: '',
        })
      } catch (e) {
        set({ lastError: errMsg(e) })
      } finally {
        set({ saving: false })
      }
    },

    submit: async () => {
      const s = get()
      if (!s.versionId) return
      await get().saveNow()
      try {
        await api.post(`/versions/${s.versionId}/submit`)
        set({ status: 'submitted', editable: false })
      } catch (e) {
        set({ lastError: errMsg(e) })
      }
    },
  }
})
