import { useEffect, useId, useRef, useState } from 'react'
import './DangerMark.css'

interface Props {
  note: string | null // 위험 이유 한 줄 (API 가 규칙표에서 읽어 붙여 준다)
}

// 위험 식품 표시 "⚠ 위험" (SCREEN-SPEC 16절). 색만으로 구분하지 않고 ⚠ 모양과 "위험" 글자로 보인다. 색은 늘 빨강이다.
// 마우스를 올리면(휴대폰은 누르면) 이유 한 줄이 말풍선으로 뜬다. 마우스를 치우면 닫히고,
// 휴대폰은 다시 누르거나 다른 곳을 누르면 닫힌다 (13.1 의 22번).
export default function DangerMark({ note }: Props) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLSpanElement>(null)
  const tipId = useId()

  // 열려 있는 동안 다른 곳을 누르거나 Esc 를 누르면 닫는다
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <span
      ref={root}
      className="danger"
      onPointerEnter={(e) => {
        if (e.pointerType === 'mouse') setOpen(true) // 마우스를 올리면 (휴대폰의 터치는 올리는 동작이 없다)
      }}
      onPointerLeave={(e) => {
        if (e.pointerType === 'mouse') setOpen(false)
      }}
    >
      <button
        type="button"
        className="danger__mark"
        aria-expanded={open}
        aria-describedby={open ? tipId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        <span aria-hidden="true">⚠</span> 위험
      </button>
      {open && note && (
        <span id={tipId} role="tooltip" className="danger__tip">
          {note}
        </span>
      )}
    </span>
  )
}
