import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import DangerIcon from './DangerIcon'
import './DangerMark.css'

interface Props {
  note: string | null // 위험 이유 한 줄 (API 가 규칙표에서 읽어 붙여 준다)
}

// 말풍선과 화면 가장자리 · 눌린 버튼 사이의 간격(px)
const EDGE = 8
const GAP = 8

// 위험 식품 표시 "(!) 위험" (SCREEN-SPEC 16절). 색만으로 구분하지 않고 빨간 느낌표 모양과 "위험" 글자로 보인다. 색은 늘 빨강이다.
// 마우스를 올리면(휴대폰은 누르면) 이유가 말풍선으로 뜬다. 마우스를 치우면 닫히고,
// 휴대폰은 다시 누르거나 다른 곳을 누르면 닫힌다 (13.1 의 22번).
// 말풍선은 식품 줄 안이 아니라 화면 맨 위 층(document.body)에 따로 그린다. 줄 안에 두면 아래 줄이나 잘림 영역에 가려지기 때문이다.
// 위치는 눌린 버튼 아래(자리가 없으면 위)에 두고 화면 가장자리에서 잘리지 않게 좌우를 맞춘다.
export default function DangerMark({ note }: Props) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number; arrow: number; above: boolean } | null>(null)
  const root = useRef<HTMLSpanElement>(null)
  const mark = useRef<HTMLButtonElement>(null)
  const tip = useRef<HTMLSpanElement>(null)
  const tipId = useId()

  // 말풍선 위치 계산: 버튼 아래에 두고, 아래 자리가 모자라면 위로. 가로는 화면 안으로 밀어 넣고, 꼬리는 버튼 가운데를 가리킨다
  function place() {
    const button = mark.current
    const bubble = tip.current
    if (!button || !bubble) return
    const r = button.getBoundingClientRect()
    const w = bubble.offsetWidth
    const h = bubble.offsetHeight
    const vw = window.innerWidth
    const vh = window.innerHeight
    const left = Math.max(EDGE, Math.min(r.left, vw - w - EDGE))
    const below = r.bottom + GAP + h <= vh - EDGE
    const above = !below && r.top - GAP - h >= EDGE
    const top = above ? r.top - GAP - h : r.bottom + GAP
    const arrow = Math.max(14, Math.min(r.left + r.width / 2 - left, w - 14))
    setPos({ top, left, arrow, above })
  }

  // 열리면 그릴 위치를 계산한다(처음 그릴 때 크기를 재야 해서 그린 직후에 한 번 더 계산).
  useLayoutEffect(() => {
    if (open && note) place()
  }, [open, note])

  // 열려 있는 동안: 화면이 움직이거나 크기가 바뀌면 위치를 다시 잡고, 다른 곳을 누르거나 Esc 를 누르면 닫는다
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('scroll', place, true)
    window.addEventListener('resize', place)
    document.addEventListener('pointerdown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('scroll', place, true)
      window.removeEventListener('resize', place)
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
        ref={mark}
        type="button"
        className="danger__mark"
        aria-expanded={open}
        aria-describedby={open ? tipId : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        <DangerIcon className="danger__mark-icon" />
        위험
      </button>
      {open &&
        note &&
        createPortal(
          <span
            ref={tip}
            id={tipId}
            role="tooltip"
            className={pos?.above ? 'danger__tip danger__tip--above' : 'danger__tip'}
            // 위치를 계산하기 전(처음 한 번)에는 보이지 않게 그려서 크기만 잰다
            style={pos ? { top: pos.top, left: pos.left, ['--arrow' as string]: `${pos.arrow}px` } : { visibility: 'hidden' }}
          >
            <span className="danger__tip-head">
              <DangerIcon className="danger__tip-icon" />
              <strong>위험 식품</strong>
            </span>
            <span className="danger__tip-text">{note}</span>
          </span>,
          document.body,
        )}
    </span>
  )
}
