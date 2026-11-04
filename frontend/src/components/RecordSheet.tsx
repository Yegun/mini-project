import { useEffect, useRef } from 'react'
import { formatKoreanDate } from '../lib/dateText'
import { CATEGORY_LABEL } from '../types/food'
import type { ProcessedFood } from '../types/records'
import CategoryIcon from './CategoryIcon'
import ErrorNotice from './ErrorNotice'
import RecordIcon from './RecordIcon'
import './FoodCapsules.css' // 식품 종류 색(cap--vegetable 등)
import './RecordSheet.css'

export type RecordKind = 'eaten' | 'discarded'

const TITLE: Record<RecordKind, string> = { eaten: '먹은 것', discarded: '버린 것' }
const VERB: Record<RecordKind, string> = { eaten: '먹었어요', discarded: '버렸어요' }
const NOTHING_TO_RESTORE = '되돌릴 식품이 없어요.' // 사용자 확정 문구 (OQ-03)

interface Props {
  kind: RecordKind | null // 열린 종류. null 이면 닫혀 있다
  foods: ProcessedFood[] // 그 종류의 처리한 식품. API 가 준 순서(최근 처리한 순 → 이름순)를 그대로 쓴다 (D-073, D-074)
  restoringId: string | null
  error: string | null // 되돌리기 실패 안내. 팝업이 화면을 덮으므로 팝업 안에도 보인다
  onRestore: (id: string) => void
  onClose: () => void
}

// 처리한 날짜가 같은 식품끼리 묶는다. 순서는 API 가 준 그대로라 날짜는 최근 것부터 나온다.
function groupByDate(foods: ProcessedFood[]): { date: string; items: ProcessedFood[] }[] {
  const groups: { date: string; items: ProcessedFood[] }[] = []
  for (const food of foods) {
    const last = groups[groups.length - 1]
    if (last && last.date === food.processed_date) last.items.push(food)
    else groups.push({ date: food.processed_date, items: [food] })
  }
  return groups
}

// 기록 화면의 먹은 식품 · 버린 식품 팝업: 화면 맨 아래에서 올라오는 창 (TrashSheet 와 같은 방식의 dialog).
// 위에 제목 · 개수 · 닫기, 아래에 처리한 날짜별로 묶은 식품 카드(식품 종류 그림 · 이름 · 종류와 수량 · 홈으로 되돌리기).
// 목록이 길면 팝업 안에서 스크롤된다. 어두운 바탕을 누르거나 Esc 를 눌러도 닫힌다. 움직임 줄이기를 켜 두었으면 바로 나타난다 (0절).
export default function RecordSheet({ kind, foods, restoringId, error, onRestore, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const open = kind !== null
  const shown: RecordKind = kind ?? 'eaten'

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      className="record-sheet"
      data-kind={shown}
      aria-labelledby="record-sheet-title"
      onCancel={(e) => {
        e.preventDefault() // Esc 로 닫을 때도 상태는 우리가 정한다
        onClose()
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose() // 창 밖(어두운 바탕)을 누르면 닫힌다
      }}
    >
      <div className="record-sheet__head">
        <div className="record-sheet__heading">
          <h2 className="record-sheet__title" id="record-sheet-title">
            {TITLE[shown]}
          </h2>
          {foods.length > 0 && <span className="record-sheet__count">{foods.length}개</span>}
        </div>
        <button type="button" className="record-sheet__close" aria-label="닫기" onClick={onClose}>
          <span aria-hidden="true">✕</span>
        </button>
      </div>
      <div className="record-sheet__body">
        {error && <ErrorNotice message={error} />}
        {foods.length === 0 ? (
          <div className="rs-empty">
            <RecordIcon kind={shown} className="rs-empty__icon" />
            <p>{NOTHING_TO_RESTORE}</p>
          </div>
        ) : (
          groupByDate(foods).map((group) => (
            <section key={group.date} className="rs-group">
              <h3 className="rs-group__date">
                {formatKoreanDate(group.date)} · {VERB[shown]}
              </h3>
              <ul className="rs-list">
                {group.items.map((food) => (
                  <li key={food.id} className="rs-item">
                    {/* 식품 종류 그림. 종류를 모르면(서버가 아직 안 줌) 먹은 식품 · 버린 식품 기본 그림 */}
                    {food.category ? (
                      <span className={`rs-item__art cap--${food.category}`} aria-hidden="true">
                        <CategoryIcon category={food.category} className="rs-item__art-icon" />
                      </span>
                    ) : (
                      <span className="rs-item__art rs-item__art--kind" aria-hidden="true">
                        <RecordIcon kind={shown} className="rs-item__art-icon" />
                      </span>
                    )}
                    <div className="rs-item__text">
                      <span className="rs-item__name">{food.name}</span>
                      <span className="rs-item__chips">
                        {food.category && <span className={`rs-item__cat cap--${food.category}`}>{CATEGORY_LABEL[food.category]}</span>}
                        <span className="rs-item__qty">
                          {food.quantity}
                          {food.unit}
                        </span>
                      </span>
                    </div>
                    <button
                      type="button"
                      className="rs-item__restore"
                      disabled={restoringId !== null}
                      onClick={() => onRestore(food.id)}
                    >
                      <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false">
                        <path
                          d="M9 6.5H4.5V11M4.8 11a8 8 0 1 1 2.2 6"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.4"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      {restoringId === food.id ? '되돌리는 중…' : '다시 냉장고로'}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ))
        )}
      </div>
    </dialog>
  )
}
