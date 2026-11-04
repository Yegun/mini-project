import { useEffect, useRef } from 'react'
import type { FoodDetail, SaveResult, UpdateFoodInput } from '../types/foodDetail'
import InfoEditForm from './InfoEditForm'
import './TrashSheet.css'
import './InfoEditSheet.css'

interface Props {
  open: boolean
  food: FoodDetail
  busy: boolean
  error: string | null
  onSave: (patch: UpdateFoodInput) => Promise<SaveResult>
  onCancel: () => void // 취소 버튼: 고치던 값을 버리고 닫는다 (SCREEN-SPEC 6.2)
  onRequestClose: () => void // 창 밖(어두운 바탕) · Esc: 고친 값이 있으면 확인 창을 먼저 띄운다 (D-175). 판단은 부르는 쪽이 한다
  onDirtyChange?: (dirty: boolean) => void
}

// 정보 고치기 창 (SCREEN-SPEC 6.2, 13.2 의 3번): 아래에서 올라오는 창. 뒤에 상세 화면이 그대로 보인다.
// 창 안에 입력칸과 저장 · 취소 버튼이 있다. 열 때마다 처음 값으로 새로 시작한다.
export default function InfoEditSheet({ open, food, busy, error, onSave, onCancel, onRequestClose, onDirtyChange }: Props) {
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
      className="sheet sheet--edit"
      aria-label="정보 고치기"
      onCancel={(e) => {
        e.preventDefault() // Esc 로 닫을 때도 상태는 우리가 정한다
        if (!busy) onRequestClose()
      }}
      onClick={(e) => {
        if (e.target === ref.current && !busy) onRequestClose() // 창 밖(어두운 바탕)을 누르면
      }}
    >
      <div className="sheet__inner">
        {open && (
          <InfoEditForm
            food={food}
            busy={busy}
            error={error}
            onSave={onSave}
            onCancel={onCancel}
            onDirtyChange={onDirtyChange}
          />
        )}
      </div>
    </dialog>
  )
}
