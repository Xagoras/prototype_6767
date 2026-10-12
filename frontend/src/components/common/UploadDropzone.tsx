/**
 * 通用文件拖放/选择上传组件（支持多文件）。
 */
import { useRef, useState } from 'react'

interface Props {
  accept?: string
  multiple?: boolean
  onFiles: (files: File[]) => void
  hint?: string
}

export default function UploadDropzone({
  accept,
  multiple = false,
  onFiles,
  hint = '点击选择或拖拽文件到此处',
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handle = (list: FileList | null) => {
    if (!list || list.length === 0) return
    onFiles(Array.from(list))
  }

  return (
    <div
      className={`dropzone${dragging ? ' dragging' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files) }}
    >
      <div className="dropzone-icon">⇪</div>
      <div>{hint}</div>
      <div className="dropzone-sub">支持 PDF / Word / 纯文本</div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        style={{ display: 'none' }}
        onChange={(e) => { handle(e.target.files); e.target.value = '' }}
      />
    </div>
  )
}
