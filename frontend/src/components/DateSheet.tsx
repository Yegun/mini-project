import { useRef, type PointerEvent } from 'react'
import { categoryTintClass } from '../lib/categoryTint'
import { formatMonthDay } from '../lib/calendar'
import type { Food } from '../types/food'
import type { CalendarBasis } from '../types/calendar'
import DaysLeftBubble from './DaysLeftBubble'
import { StorageCapsule } from './FoodCapsules'
import './DateSheet.css'

interface Props {
  date: string // 누른 날짜 (YYYY-MM-DD)
  basis: CalendarBasis
  onDay: Food[] // 이날 끝나는(시작하는) 식품. 기한이 임박한 순 (API 가 준 순서 그대로)
  staying: Food[] // 이날 남아 있는 식품 (그날 냉장고에 있었고 위 목록에 없는 식품)
  expanded: boolean // 끌어올렸는지
  onExpandedChange: (expanded: boolean) => void
  onClose: () => void
  onSelectFood: (id: string) => void // 식품 상세로 (모달 없이 화면 이동)
}

const DRAG_PX = 28 // 이만큼 이상 끌면 끌어올림 · 내림으로 본다

// 날짜 목록 창 (SCREEN-SPEC 14.3 의 2 · 3번): 아래에서 올라오는 창.
// 맨 위에 "11월 6일 (금)", 그 아래 '이날 끝나는 식품'(시작하는 날 기준이면 '이날 시작한 식품'). 손잡이를 위로 끌어올리면
// '이날 남아 있는 식품'도 보인다. 손잡이를 누르거나 아래로 끌어도 접힌다. 식품을 누르면 식품 상세로 간다.
export default function DateSheet({ date, basis, onDay, staying, expanded, onExpandedChange, onClose, onSelectFood }: Props) {
  const startY = useRef<number | null>(null)

  function down(e: PointerEvent<HTMLButtonElement>) {
    startY.current = e.clientY
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  function up(e: PointerEvent<HTMLButtonElement>) {
    if (startY.current === null) return
    const dy = e.clientY - startY.current
    startY.current = null
    if (dy <= -DRAG_PX) onExpandedChange(true) // 위로 끌어올림
    else if (dy >= DRAG_PX) onExpandedChange(false) // 아래로 내림
    else onExpandedChange(!expanded) // 가볍게 누르면 접고 펼침
  }

  const onDayTitle = basis === 'end' ? '이날 끝나는 식품' : '이날 시작한 식품'

  return (
    <section className={expanded ? 'ds ds--expanded' : 'ds'} aria-label="날짜 목록">
      <button
        type="button"
        className="ds__handle"
        aria-label={expanded ? '목록 접기' : '목록 끌어올리기'}
        aria-expanded={expanded}
        onPointerDown={down}
        onPointerUp={up}
        onPointerCancel={() => (startY.current = null)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onExpandedChange(!expanded)
          }
        }}
      >
        <span className="ds__grip" aria-hidden="true" />
      </button>

      <header className="ds__head">
        <h2 className="ds__date">{formatMonthDay(date)}</h2>
        <button type="button" className="ds__close" aria-label="날짜 목록 닫기" onClick={onClose}>
          ✕
        </button>
      </header>

      <div className="ds__body">
        <h3 className="ds__title">{onDayTitle}</h3>
        <List foods={onDay} emptyText={`${onDayTitle}이 없어요.`} onSelectFood={onSelectFood} />

        {expanded ? (
          <>
            <h3 className="ds__title">이날 남아 있는 식품</h3>
            <List foods={staying} emptyText="이날 남아 있는 식품이 없어요." onSelectFood={onSelectFood} />
          </>
        ) : (
          <p className="ds__hint">위로 끌어올리면 이날 남아 있는 식품도 볼 수 있어요.</p>
        )}
      </div>
    </section>
  )
}

function List({ foods, emptyText, onSelectFood }: { foods: Food[]; emptyText: string; onSelectFood: (id: string) => void }) {
  if (foods.length === 0) return <p className="ds__empty">{emptyText}</p>
  return (
    <ul className="ds__list">
      {foods.map((food) => (
        <li key={food.id}>
          <button
            type="button"
            className={['ds__row', categoryTintClass(food.category)].filter(Boolean).join(' ')}
            onClick={() => onSelectFood(food.id)}
          >
            <span className="ds__name">
              {food.name}
              {food.is_danger && <span className="ds__danger"> ⚠ 위험</span>}
            </span>
            <StorageCapsule storage={food.storage} />
            <DaysLeftBubble status={food.expiry_status} daysLeft={food.days_left} />
          </button>
        </li>
      ))}
    </ul>
  )
}
