/**
 * 论证图示区（右栏）：React Flow 渲染 + 子图页签 + 拖拽持久化 + 缩放导航。
 *
 * - 多独立论证结构按连通分量分页签展示（指南 3.6.1 多图支持）
 * - 节点拖拽结束 → graph_layout 回写（双向联动：图示调整 → 同步更新标注数据）
 * - 自动布局（dagre）与手动位置共存："重置布局"清空手动位置
 */
import { useCallback, useMemo, useRef, useState } from 'react'
import {
  Background, Controls, ReactFlow, applyEdgeChanges, applyNodeChanges,
  useEdgesState, useNodesState,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { toJpeg, toPng, toSvg } from 'html-to-image'
import type { Node, OnNodesChange } from '@xyflow/react'
import { api, errMsg } from '../../api/client'
import { useAnnotationStore } from '../../stores/annotationStore'
import { dagreLayout } from '../../utils/layout'
import { connectedComponents, treeToGraph } from './treeToGraph'
import IdentityNode from './nodes/IdentityNode'
import PropositionNode from './nodes/PropositionNode'
import RelationNode from './nodes/RelationNode'

const nodeTypes = {
  proposition: PropositionNode,
  relation: RelationNode,
  identity: IdentityNode,
}

interface Props {
  /** 子图渲染完成回调（M6 导出图片时用于 DOM 定位） */
  onGraphReady?: (container: HTMLDivElement | null) => void
}

export default function ArgumentGraph({ onGraphReady }: Props) {
  const store = useAnnotationStore()
  const [activeComponent, setActiveComponent] = useState(0)
  const canvasRef = useRef<HTMLDivElement>(null)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')

  // 关系树 → 节点/边
  const { allNodes, allEdges, components } = useMemo(() => {
    const seqs = store.propositions
      .filter((p) => p.seq != null)
      .map((p) => ({ seq: p.seq as number }))
    const { nodes, edges } = treeToGraph(seqs, store.relations)
    return {
      allNodes: nodes as Node[],
      allEdges: edges,
      components: connectedComponents(nodes, edges),
    }
  }, [store.propositions, store.relations])

  // 当前子图（默认含命题最多的）
  const currentIds = useMemo(() => {
    const idx = Math.min(activeComponent, Math.max(0, components.length - 1))
    return new Set(components[idx] ?? [])
  }, [components, activeComponent])

  const visibleNodes = useMemo(
    () => allNodes.filter((n) => currentIds.has(n.id)),
    [allNodes, currentIds],
  )
  const visibleEdges = useMemo(
    () => allEdges.filter((e) => currentIds.has(e.source) && currentIds.has(e.target)),
    [allEdges, currentIds],
  )

  // 布局：手动位置优先（graph_layout）
  const laidOut = useMemo(
    () => dagreLayout(visibleNodes, visibleEdges, store.graphLayout),
    [visibleNodes, visibleEdges, store.graphLayout],
  )

  const [nodes, setNodes] = useNodesState(laidOut)
  const [edges, setEdges] = useEdgesState(visibleEdges)

  // layout 变化时同步（节点 key 以 props 驱动的简单方案：直接整体替换）
  const key = useMemo(
    () => visibleNodes.map((n) => n.id).join('|') + '|' + visibleEdges.map((e) => e.id).join('|'),
    [visibleNodes, visibleEdges],
  )
  useMemo(() => {
    setNodes(dagreLayout(visibleNodes, visibleEdges, store.graphLayout))
    setEdges(visibleEdges)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [setNodes],
  )

  const onNodeDragStop = useCallback(
    (_event: unknown, _node: Node) => {
      // 拖拽结束 → 回写 layout（保存所有当前节点位置，保留其他子图位置）
      const positions: Record<string, { x: number; y: number }> = {}
      for (const n of nodes) {
        if (currentIds.has(n.id)) positions[n.id] = { x: n.position.x, y: n.position.y }
      }
      const merged = { ...store.graphLayout.positions, ...positions }
      store.updateGraphLayout({ positions: merged })
    },
    [nodes, currentIds, store],
  )

  const resetLayout = () => {
    const positions = { ...store.graphLayout.positions }
    for (const id of currentIds) delete positions[id]
    store.updateGraphLayout({ positions })
  }

  /** 导出当前子图为图片（需求 5.1.1：PNG/JPG/SVG），本地下载并登记导出记录 */
  const exportImage = async (format: 'png' | 'jpg' | 'svg') => {
    const el = canvasRef.current?.querySelector('.react-flow') as HTMLElement | null
    if (!el || !store.doc || store.kind !== 'final' || store.status !== 'submitted') return
    setExporting(true)
    setExportError('')
    try {
      const opts = {
        pixelRatio: 2,
        filter: (node: HTMLElement) => !node.classList?.contains('react-flow__controls'),
      }
      const dataUrl =
        format === 'png' ? await toPng(el, opts)
        : format === 'jpg' ? await toJpeg(el, opts)
        : await toSvg(el, opts)
      const a = document.createElement('a')
      a.href = dataUrl
      a.download = `${store.doc.name}_论证图.${format}`
      a.click()
      // 登记导出记录（同样触发文档锁定，需求 5.3）
      await api.post(`/documents/${store.doc.id}/exports/record`, {
        format, filename: a.download,
      }).catch(() => { /* 登记失败不阻断下载 */ })
    } catch (e) {
      setExportError(errMsg(e))
    } finally {
      setExporting(false)
    }
  }

  if (store.propositions.length === 0) {
    return (
      <div className="graph-empty">
        <div className="empty-hint">暂无命题。完成命题标注并建立关系后，论证图示将在此自动生成。</div>
      </div>
    )
  }

  return (
    <div className="argument-graph" ref={(el) => onGraphReady?.(el)}>
      <div className="graph-tabs">
        {components.map((ids, i) => {
          const propCount = ids.filter((x) => x.startsWith('p')).length
          return (
            <button
              key={i}
              className={`graph-tab${i === Math.min(activeComponent, components.length - 1) ? ' active' : ''}`}
              onClick={() => setActiveComponent(i)}
            >
              论证{i + 1} <em>({propCount} 命题)</em>
            </button>
          )
        })}
        <button className="graph-reset link-btn" onClick={resetLayout} title="清空手动位置重新自动布局">
          重置布局
        </button>
        {store.kind === 'final' && store.status === 'submitted' && (
          <span className="graph-export-group">
            <button className="graph-reset link-btn" disabled={exporting} onClick={() => exportImage('png')} title="导出当前子图为 PNG">
              {exporting ? '导出中…' : '导出 PNG'}
            </button>
            <button className="graph-reset link-btn" disabled={exporting} onClick={() => exportImage('svg')} title="导出当前子图为 SVG">
              SVG
            </button>
            <button className="graph-reset link-btn" disabled={exporting} onClick={() => exportImage('jpg')} title="导出当前子图为 JPG">
              JPG
            </button>
          </span>
        )}
      </div>
      {exportError && <div className="error" style={{ padding: '0 8px' }}>{exportError}</div>}
      <div className="graph-canvas" ref={canvasRef}>
        <ReactFlow
          key={key}
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={(changes) => setEdges((eds) => applyEdgeChanges(changes, eds))}
          onNodeDragStop={onNodeDragStop}
          fitView
          fitViewOptions={{ padding: 0.25, maxZoom: 1.4 }}
          nodesDraggable={store.editable}
          minZoom={0.2}
          maxZoom={2.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={24} color="#e8e5dc" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  )
}
