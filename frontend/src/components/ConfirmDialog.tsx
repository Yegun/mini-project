import { useEffect, useRef } from 'react'

interface Props {
  open: boolean
  message: string
  confirmLabel: string
  busy?: boolean // 요청 중에는 버튼을 잠근다
  onConfirm: () => void
  onCancel: () => void
}

// 확인 창 (OQ-06). 다 먹음 · 버림 · 삭제는 여기서 확인해야 요청을 보낸다.
export default function ConfirmDialog({ open, message, confirmLabel, busy, onConfirm, onCancel }: Props) {
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
      className="confirm"
      aria-label="확인"
      onCancel={(e) => {
        e.preventDefault() // Esc 로 닫을 때도 상태는 우리가 정한다
        if (!busy) onCancel()
      }}
    >
      <p className="confirm__message">{message}</p>
      <div className="confirm__buttons">
        <button type="button" className="button" disabled={busy} onClick={onCancel}>
          취소
        </button>
        <button type="button" className="button button--primary" disabled={busy} onClick={onConfirm}>
          {busy ? '처리하는 중…' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
