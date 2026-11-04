import { useEffect, useRef } from 'react'
import './TrashSheet.css'

export type TrashChoice = 'eaten' | 'discarded' | 'delete'

interface Props {
  open: boolean
  name: string // 맨 위에 보이는 식품 이름
  onChoose: (choice: TrashChoice) => void // 하나를 고르면 확인 창이 뜬다 (D-144)
  onCancel: () => void
}

// 휴지통 선택창: 아래에서 올라온다. 맨 위에 식품 이름, 아래에 다 먹음 · 버림 · 삭제 · 취소 (SCREEN-SPEC 4.8, D-143).
// 움직임은 0.3초 안팎이고, 기기에서 움직임 줄이기를 켜 두었으면 바로 나타난다 (0절).
export default function TrashSheet({ open, name, onChoose, onCancel }: Props) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      className="sheet"
      aria-label={`${name} 정리하기`}
      onCancel={(e) => {
        e.preventDefault() // Esc 로 닫을 때도 상태는 우리가 정한다
        onCancel()
      }}
      onClick={(e) => {
        if (e.target === ref.current) onCancel() // 창 밖(어두운 바탕)을 누르면 닫힌다
      }}
    >
      <p className="sheet__name">{name}</p>
      <div className="sheet__buttons">
        <button type="button" className="button button--wide" onClick={() => onChoose('eaten')}>
          다 먹음
        </button>
        <button type="button" className="button button--wide" onClick={() => onChoose('discarded')}>
          버림
        </button>
        <button type="button" className="button button--wide button--danger" onClick={() => onChoose('delete')}>
          삭제
        </button>
        <button type="button" className="button button--wide button--link" onClick={onCancel}>
          취소
        </button>
      </div>
    </dialog>
  )
}
