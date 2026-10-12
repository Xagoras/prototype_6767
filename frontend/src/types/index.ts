/**
 * 全局类型定义（与后端 schemas/models 对应）
 */

// ---------- 用户与认证 ----------
export interface User {
  id: number
  username: string
  display_name: string
  is_admin: boolean
  created_at: string
}

export interface TokenResponse {
  token: string
  token_type: string
}

// ---------- 指南与标签体系 ----------
/** 要素类型定义（由指南 taxonomy 决定，不硬编码） */
export interface ElementDef {
  code: string // 如 "GM"、"IS"
  name: string
  kind: 'prop' | 'non_prop' // 命题要素 / 非命题要素
  description?: string
  cues?: string[] // 标志性表述
  subtypes?: ElementDef[] // GM/SM 的子类型
}

export interface RelationDef {
  code: string // S/A/J/M/I
  name: string
  arity: number // S/A/M=2，J/I>=2
  ordered: boolean // 参数顺序是否有语义（方向）
  formal?: string // 形式化表达示例
  description?: string
}

export interface Taxonomy {
  elements: ElementDef[]
  relations: RelationDef[]
}

export interface Guide {
  id: number
  version: string
  name: string
  source_filename: string
  content_text: string
  taxonomy: Taxonomy
  is_active: boolean
  created_at: string
}

export interface GuidePreview {
  version: string
  name: string
  source_filename: string
  text_preview: string
  content_text: string
  taxonomy: Taxonomy
  duplicate_warning: string | null
}

// ---------- 任务与文档 ----------
export type TaskStatus = 'CREATED' | 'ANNOTATING' | 'ADJUDICATING' | 'OUTPUT'
export type DocStatus =
  | 'CREATED'
  | 'ASSIGNED'
  | 'ANNOTATING'
  | 'SUBMITTED'
  | 'ADJUDICATED'
  | 'OUTPUT'
export type DocType = 'judgment' | 'guiding_case' | 'ref_case'

export interface Task {
  id: number
  name: string
  guide_id: number
  created_by: number
  status: TaskStatus
  annotators_per_doc: number
  settings: Record<string, unknown>
  created_at: string
  // 展示冗余字段
  guide_version?: string
  document_count?: number
}

/** 案例信息：按 doc_type 三套字段 */
export interface JudgmentCaseInfo {
  案号: string
  裁判法院: string
  法院层级: string
  审级: string
  裁判日期: string
  案件性质: string
  案由: string
  裁判结果类型: string
}

export interface CaseCaseInfo {
  案例类型: '指导性案例' | '参考案例'
  案件名称: string
  发布时间?: string
  入库编号?: string
  案件类型: string
  相关法条: string
  裁判要点?: string
  裁判要旨?: string
}

export type CaseInfo = JudgmentCaseInfo | CaseCaseInfo | Record<string, string>

/** 颗粒度切割片段（要素区） */
export interface Segment {
  start: number // 相对 reasoning_text 的码点偏移
  end: number
  text: string
}

export interface Document {
  id: number
  task_id: number
  name: string
  doc_type: DocType
  source_filename: string
  original_text: string
  reasoning_text: string
  reasoning_start: number | null
  reasoning_end: number | null
  extraction_method: 'auto' | 'manual_corrected' | 'manual' | 'manual_required'
  case_info: CaseInfo
  base_segments: Segment[]
  guide_version_snapshot: string
  status: DocStatus
  created_at: string
}

// ---------- 分配 ----------
export type AssignmentRole = 'annotator' | 'reference' | 'arbiter'

export interface Assignment {
  id: number
  task_id: number
  document_id: number
  user_id: number
  role: AssignmentRole
  assigned_by: number | null
  assigned_at: string
  // 冗余展示字段
  username?: string
  display_name?: string
  document_name?: string
}

/** 上传处理结果（单文件） */
export interface UploadResult {
  filename: string
  ok: boolean
  error: string | null
  document_id: number | null
  extraction_method: string | null
}

// ---------- 标注版本 ----------
export type VersionKind = 'normal' | 'reference' | 'final'
export type VersionStatus = 'draft' | 'submitted'

export interface AnnotationVersion {
  id: number
  document_id: number
  annotator_id: number
  kind: VersionKind
  status: VersionStatus
  graph_layout: GraphLayout
  note: string
  created_at: string
  updated_at: string
  submitted_at: string | null
  // 展示冗余字段
  annotator_name?: string
  document_name?: string
  // my-version / PUT content 返回的完整内容
  propositions?: Proposition[]
  relations?: RelationNode[]
  editable?: boolean
}

/** 图示拖拽结果：visualId（命题 id 或关系 id）→ 坐标 */
export interface GraphLayout {
  positions: Record<string, { x: number; y: number }>
}

export interface Proposition {
  id: number
  version_id: number
  segment_id: number | null
  char_start: number
  char_end: number
  text: string
  edited_text: string | null
  type_code: string | null
  subtype_code: string | null
  flagged: boolean
  flag_note: string
  /** 序号：按 char_start 排序实时计算（后端返回，不落库） */
  seq?: number
}

/** 关系参数：命题或嵌套关系节点 */
export interface RelationArg {
  kind: 'P' | 'R'
  id: number
}

export type RelType = 'S' | 'A' | 'J' | 'M' | 'I'

export interface RelationNode {
  id: number
  version_id: number
  rel_type: RelType
  args: RelationArg[]
  note: string
  flagged: boolean
  flag_note: string
  /** 形式化表达式（后端计算，如 "S(M(J(P1,P2,P3),P4),P5)"） */
  expr?: string
}

export interface VersionContent {
  propositions: Proposition[]
  relations: RelationNode[]
  graph_layout: GraphLayout
}

// ---------- 差异比对 ----------
export type DiffCategory =
  | 'identical' // 完全一致
  | 'boundary' // 边界差异
  | 'type' // 类型差异
  | 'subtype' // 子类型差异
  | 'edited_text' // 文字已编辑
  | 'only_a' // 仅 A 版有
  | 'only_b' // 仅 B 版有

export interface PropositionDiff {
  category: DiffCategory
  a: Proposition | null
  b: Proposition | null
  a_seq: number | null
  b_seq: number | null
}

export interface RelationDiff {
  category: DiffCategory | 'direction' | 'nested' | 'missing' | 'extra'
  a: RelationNode | null
  b: RelationNode | null
  a_expr: string | null
  b_expr: string | null
}

export interface ComparePayload {
  versions: AnnotationVersion[]
  proposition_diffs: PropositionDiff[]
  relation_diffs: RelationDiff[]
  granularity_rate: number | null // 颗粒度差异率（0~1）
  warn_threshold_exceeded: boolean
}

// ---------- 导出 ----------
export interface ExportRecord {
  id: number
  document_id: number
  task_id: number
  user_id: number
  format: string
  filename: string
  guide_version: string
  created_at: string
  username?: string
}
