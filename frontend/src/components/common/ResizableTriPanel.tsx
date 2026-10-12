/**
 * 三栏可调布局（需求：界面各区域比例可调节）。
 * 基于 react-resizable-panels v4（Group/Separator/Panel），
 * 默认比例左 30% | 中 25% | 右 45%。
 */
import { Group, Panel, Separator } from 'react-resizable-panels'
import type { ReactNode } from 'react'

interface Props {
  left: ReactNode
  middle: ReactNode
  right: ReactNode
  /** 默认比例（百分比数字），如 30 表示 30% */
  defaultLeft?: number
  defaultMiddle?: number
}

export default function ResizableTriPanel({
  left,
  middle,
  right,
  defaultLeft = 30,
  defaultMiddle = 25,
}: Props) {
  return (
    <Group orientation="horizontal" className="tri-panel">
      <Panel defaultSize={`${defaultLeft}`} minSize="15" className="tri-pane">
        {left}
      </Panel>
      <Separator className="resize-handle" />
      <Panel defaultSize={`${defaultMiddle}`} minSize="15" className="tri-pane">
        {middle}
      </Panel>
      <Separator className="resize-handle" />
      <Panel minSize="20" className="tri-pane">
        {right}
      </Panel>
    </Group>
  )
}
