import { useMemo, useState } from 'react'
import { addMonths, monthGrid, monthTitle } from '../lib/calendar'
import { statusColor } from '../lib/statusColor'
import type { CalendarBasis, CalendarView } from '../types/calendar'
import type { Food } from '../types/food'
import DateSheet from './DateSheet'
import './FullCalendar.css'

interface Props {
  today: string // API 가 준 오늘 날짜 (D-021). 화면 시계는 쓰지 않는다
  foods: Food[] // 홈에서 불러온 목록 그대로. 알약 · 드롭다운으로 거르지 않고 모든 식품(4일 이상 지난 식품 포함)을 쓴다 (D-146, 13.2 의 4번)
  view: CalendarView // 처음 보여 줄 모습 (식품 상세에서 뒤로 왔을 때 보던 그대로)
  onClose: () => void // 닫기(X): 홈으로 (13.2 의 2번)
  onSelectFood: (id: string, view: CalendarView) => void // 식품 상세로. 뒤로 오면 view 그대로 다시 열린다 (D-085, D-150)
}

type Direction = 'next' | 'prev' | null

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']
const MAX_CHIPS = 2 // 날짜 칸에 이름을 보이는 최대 개수. 넘으면 '+N' (D-148)

// 전체 달력 (SCREEN-SPEC 14절, D-145 ~ D-150): 한 달 달력. 맨 위 '끝나는 날 / 시작하는 날' 기준을 고르면 날짜 칸에
// 그 기준에 맞는 식품 이름이 상태 색 점과 함께 보인다. 날짜를 누르면 아래에서 날짜 목록 창이 올라온다.
// 달 이동 · 날짜별 묶기는 홈의 식품 목록 하나를 화면이 날짜별로 묶어서 한다. 상태는 API 가 준 값을 그대로 쓴다 (ARCH 9절 31번).
export default function FullCalendar({ today, foods, view, onClose, onSelectFood }: Props) {
  const [offset, setOffset] = useState(view.monthOffset)
  const [basis, setBasis] = useState<CalendarBasis>(view.basis)
  const [selected, setSelected] = useState<string | null>(view.selectedDate)
  const [expanded, setExpanded] = useState(view.expanded)
  const [direction, setDirection] = useState<Direction>(null) // 달을 넘긴 방향. 달력이 그쪽에서 스르륵 들어온다

  const todayYear = Number(today.slice(0, 4))
  const todayMonth = Number(today.slice(5, 7))
  const { year, month } = addMonths(todayYear, todayMonth, offset)
  const cells = useMemo(() => monthGrid(year, month), [year, month])

  // 기준에 맞는 날짜 → 식품들 (끝나는 날은 기한, 시작하는 날은 구매일). 식품 순서는 API 가 준 순서 그대로
  const byDate = useMemo(() => {
    const map = new Map<string, Food[]>()
    for (const f of foods) {
      const key = basis === 'end' ? f.expiry_date : f.purchase_date
      const list = map.get(key)
      if (list) list.push(f)
      else map.set(key, [f])
    }
    return map
  }, [foods, basis])

  function currentView(): CalendarView {
    return { monthOffset: offset, basis, selectedDate: selected, expanded }
  }

  function moveMonth(delta: number) {
    setDirection(delta > 0 ? 'next' : 'prev')
    setOffset((n) => n + delta)
  }

  function goToday() {
    if (offset === 0) return
    setDirection(offset > 0 ? 'prev' : 'next')
    setOffset(0)
  }

  function pickDate(date: string) {
    setSelected(date)
    setExpanded(false)
  }

  // 날짜 목록 창의 두 목록: 이날 끝나는(시작하는) 식품 / 이날 남아 있는 식품(그날 냉장고에 있었고 위 목록에 없는 식품, ARCH 6절 V-33)
  const onDay = selected ? (byDate.get(selected) ?? []) : []
  const staying = selected
    ? foods.filter(
        (f) => f.purchase_date <= selected && selected <= f.expiry_date && !onDay.includes(f),
      )
    : []

  return (
    <main className="fc">
      <header className="fc__top">
        <h1 className="fc__title">전체 달력</h1>
        <button type="button" className="fc__close" aria-label="전체 달력 닫기" onClick={onClose}>
          ✕
        </button>
      </header>

      <div className="fc__basis" role="group" aria-label="달력 기준">
        <button
          type="button"
          className={basis === 'end' ? 'fc__basis-btn fc__basis-btn--on' : 'fc__basis-btn'}
          aria-pressed={basis === 'end'}
          onClick={() => setBasis('end')}
        >
          끝나는 날
        </button>
        <button
          type="button"
          className={basis === 'start' ? 'fc__basis-btn fc__basis-btn--on' : 'fc__basis-btn'}
          aria-pressed={basis === 'start'}
          onClick={() => setBasis('start')}
        >
          시작하는 날
        </button>
      </div>

      <div className="fc__nav">
        <button type="button" className="fc__arrow" aria-label="이전 달" onClick={() => moveMonth(-1)}>
          ‹
        </button>
        <div className="fc__month-group">
          <span className="fc__month">{monthTitle(year, month)}</span>
          <button
            type="button"
            className={offset === 0 ? 'fc__today fc__today--here' : 'fc__today'}
            onClick={goToday}
          >
            오늘
          </button>
        </div>
        <button type="button" className="fc__arrow" aria-label="다음 달" onClick={() => moveMonth(1)}>
          ›
        </button>
      </div>

      <div className="fc__weekdays" aria-hidden="true">
        {WEEKDAYS.map((w, i) => (
          <span key={w} className={i === 0 ? 'fc__weekday fc__weekday--sun' : i === 6 ? 'fc__weekday fc__weekday--sat' : 'fc__weekday'}>
            {w}
          </span>
        ))}
      </div>

      <div className="fc__viewport">
        {/* 달이 바뀔 때마다 새로 그려 옆에서 들어오는 움직임이 다시 시작된다 */}
        <div key={offset} className={direction ? `fc__grid fc__grid--${direction}` : 'fc__grid'}>
          {cells.map((c, i) => {
            const items = byDate.get(c.date) ?? []
            const isToday = c.date === today
            // 한 줄이 일요일부터 시작하므로 7로 나눈 나머지가 0 이면 일요일, 6 이면 토요일
            const dayClass = ['fc__day', isToday && 'fc__day--today', i % 7 === 0 && 'fc__day--sun', i % 7 === 6 && 'fc__day--sat']
              .filter(Boolean)
              .join(' ')
            const cls = [
              'fc__cell',
              !c.inMonth && 'fc__cell--out',
              c.date === selected && 'fc__cell--selected',
            ]
              .filter(Boolean)
              .join(' ')
            return (
              <button
                key={c.date}
                type="button"
                className={cls}
                aria-label={`${c.date.slice(5, 7)}월 ${c.day}일${items.length ? `, 식품 ${items.length}개` : ''}`}
                aria-pressed={c.date === selected}
                onClick={() => pickDate(c.date)}
              >
                <span className={dayClass}>{c.day}</span>
                {items.slice(0, MAX_CHIPS).map((f) => (
                  <span key={f.id} className="fc__chip">
                    <span
                      className="fc__dot"
                      data-status={f.expiry_status}
                      style={{ background: statusColor(f.expiry_status) }}
                      aria-hidden="true"
                    />
                    <span className="fc__chip-name">{f.name}</span>
                  </span>
                ))}
                {items.length > MAX_CHIPS && <span className="fc__more">+{items.length - MAX_CHIPS}</span>}
              </button>
            )
          })}
        </div>
      </div>

      {foods.length === 0 && <p className="fc__empty">표시할 식품이 없어요.</p>}

      {selected && (
        <DateSheet
          date={selected}
          basis={basis}
          onDay={onDay}
          staying={staying}
          expanded={expanded}
          onExpandedChange={setExpanded}
          onClose={() => setSelected(null)}
          onSelectFood={(id) => onSelectFood(id, currentView())}
        />
      )}
    </main>
  )
}
