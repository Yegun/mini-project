import { useEffect, useRef } from 'react'
import type { Category } from '../types/food'
import CategoryIcon from './CategoryIcon'
import RecordIcon from './RecordIcon'
import { CuisineIcon } from './RecommendIcons'
import './FoodCapsules.css' // 식품 종류 색(cap--vegetable 등)
import './TrashSheet.css'

export type TrashChoice = 'eaten' | 'discarded' | 'delete'

interface Props {
  open: boolean
  name: string // 맨 위에 보이는 식품 이름
  category?: Category | null // 식품 종류. 알면 종류 그림, 모르면(서버가 아직 안 줌) 접시 그림
  onChoose: (choice: TrashChoice) => void // 하나를 고르면 확인 창이 뜬다 (D-144)
  onCancel: () => void
}

// 휴지통 선택창: 아래에서 올라온다. 맨 위에 식품 그림 · 이름, 가운데에 다 먹음 · 버림 · 삭제 행동 카드, 아래에 취소 (SCREEN-SPEC 4.8, D-143).
// 설명 글: 다 먹음 · 버림은 기록으로 남아 되돌릴 수 있고, 삭제는 되돌릴 수 없다 (D-144).
// 움직임은 0.3초 안팎이고, 기기에서 움직임 줄이기를 켜 두었으면 바로 나타난다 (0절).
export default function TrashSheet({ open, name, category = null, onChoose, onCancel }: Props) {
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
      className="sheet trash-sheet"
      aria-label={`${name} 정리하기`}
      onCancel={(e) => {
        e.preventDefault() // Esc 로 닫을 때도 상태는 우리가 정한다
        onCancel()
      }}
      onClick={(e) => {
        if (e.target === ref.current) onCancel() // 창 밖(어두운 바탕)을 누르면 닫힌다
      }}
    >
      <div className="trash-sheet__head">
        {category ? (
          <span className={`trash-sheet__art cap--${category}`} aria-hidden="true">
            <CategoryIcon category={category} className="trash-sheet__art-icon" />
          </span>
        ) : (
          <span className="trash-sheet__art trash-sheet__art--plain" aria-hidden="true">
            <CuisineIcon cuisine="western" className="trash-sheet__art-icon" />
          </span>
        )}
        <div className="trash-sheet__title">
          <p className="sheet__name">{name}</p>
          <p className="trash-sheet__ask">이 식품을 어떻게 할까요?</p>
        </div>
      </div>

      <div className="trash-sheet__actions">
        <button type="button" className="trash-action trash-action--eaten" onClick={() => onChoose('eaten')}>
          <span className="trash-action__art" aria-hidden="true">
            <RecordIcon kind="eaten" className="trash-action__icon" />
          </span>
          <span className="trash-action__text">
            <strong>다 먹었어요</strong>
            <small>먹은 것 기록에 남아요</small>
          </span>
          <span className="trash-action__chev" aria-hidden="true" />
        </button>
        <button type="button" className="trash-action trash-action--discarded" onClick={() => onChoose('discarded')}>
          <span className="trash-action__art" aria-hidden="true">
            <RecordIcon kind="discarded" className="trash-action__icon" />
          </span>
          <span className="trash-action__text">
            <strong>버렸어요</strong>
            <small>버린 것 기록에 남아요</small>
          </span>
          <span className="trash-action__chev" aria-hidden="true" />
        </button>
        <button type="button" className="trash-action trash-action--delete" onClick={() => onChoose('delete')}>
          <span className="trash-action__art" aria-hidden="true">
            {/* 삭제: 쓰레기통에 엑스 표시. 기록 없이 지운다 */}
            <svg className="trash-action__icon" viewBox="0 0 48 48" focusable="false">
              <circle cx="24" cy="24" r="22" fill="rgba(120, 120, 135, 0.14)" />
              <path d="M16 18l1.8 18a2.2 2.2 0 0 0 2.2 2h8a2.2 2.2 0 0 0 2.2-2L32 18z" fill="none" stroke="#8a8aa0" strokeWidth="2.2" strokeLinejoin="round" />
              <path d="M13.5 18h21M20 18v-3h8v3" fill="none" stroke="#8a8aa0" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M21 23.5l6 7M27 23.5l-6 7" stroke="#e0454a" strokeWidth="2.4" strokeLinecap="round" />
            </svg>
          </span>
          <span className="trash-action__text">
            <strong>지우기</strong>
            <small>되돌릴 수 없어요</small>
          </span>
          <span className="trash-action__chev" aria-hidden="true" />
        </button>
      </div>

      <button type="button" className="button button--wide button--link trash-sheet__cancel" onClick={onCancel}>
        취소
      </button>
    </dialog>
  )
}
