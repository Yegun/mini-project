import { useState, type CSSProperties } from 'react'
import { addDays, clipBar, getWeekDays, getWeekday, weekMonthLabel } from '../lib/week'
import type { Food } from '../types/food'
import FoodBarRow from './FoodBarRow'
import './WeekCalendar.css'

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

interface Props {
  today: string // API 가 준 오늘 날짜 (D-021). 화면 시계는 쓰지 않는다
  foods: Food[] // 거르기를 거친 식품. 이번 주에 걸친 것만 막대로 그린다
  onSelectFood?: (id: string) => void // 막대의 식품을 누르면 상세 화면으로
  onOpenFull?: () => void // 연 · 월 옆 동그란 `>` : 전체 달력 열기 (이슈 5에서 연결한다)
}

type Direction = 'next' | 'prev' | null

// 막대 달력 카드 (SCREEN-SPEC 4.7, D-145, D-192).
// 위쪽: 가운데에 연 · 월 + 동그란 `>`(전체 달력) + '오늘', 양쪽 끝에 이전 주 `<` · 다음 주 `>`.
// 7일(일~토) 단위로 넘기고 API 를 다시 부르지 않는다. 같은 목록으로 그 주의 막대를 다시 자른다.
// 연 · 월 글자나 '오늘'을 누르면 오늘이 있는 주로 돌아온다. 넘기는 범위에 제한은 없다 (13.2 의 5번).
export default function WeekCalendar({ today, foods, onSelectFood, onOpenFull }: Props) {
  const [offset, setOffset] = useState(0) // 오늘이 있는 주에서 몇 주 떨어졌는지 (0 = 이번 주)
  const [direction, setDirection] = useState<Direction>(null) // 넘긴 방향. 달력이 그쪽에서 스르륵 들어온다

  const weekDate = addDays(today, offset * 7) // 보이는 주에 들어 있는 날짜
  const days = getWeekDays(weekDate)
  const todayCol = getWeekday(today)
  const rows = foods.filter((f) => f.show_on_calendar && clipBar(weekDate, f.purchase_date, f.expiry_date))

  function move(delta: number) {
    setDirection(delta > 0 ? 'next' : 'prev')
    setOffset((n) => n + delta)
  }

  function goToday() {
    if (offset === 0) return
    setDirection(offset > 0 ? 'prev' : 'next')
    setOffset(0)
  }

  return (
    <section className="week-calendar" aria-label="막대 달력">
      <div className="week-calendar__nav">
        <button type="button" className="week-calendar__arrow" aria-label="이전 주" onClick={() => move(-1)}>
          ‹
        </button>
        <div className="week-calendar__title">
          <button type="button" className="week-calendar__month" onClick={goToday}>
            {weekMonthLabel(days)}
          </button>
          {onOpenFull && (
            <button type="button" className="week-calendar__full" aria-label="전체 달력 열기" onClick={onOpenFull}>
              ›
            </button>
          )}
          <button
            type="button"
            className={offset === 0 ? 'week-calendar__today week-calendar__today--here' : 'week-calendar__today'}
            onClick={goToday}
          >
            오늘
          </button>
        </div>
        <button type="button" className="week-calendar__arrow" aria-label="다음 주" onClick={() => move(1)}>
          ›
        </button>
      </div>

      <div className="week-calendar__viewport">
        {/* 주가 바뀔 때마다 새로 그려 옆에서 들어오는 움직임이 다시 시작된다 */}
        <div
          key={offset}
          className={direction ? `week-calendar__slide week-calendar__slide--${direction}` : 'week-calendar__slide'}
        >
          <div className="week-grid week-calendar__head">
            <span />
            {days.map((d) => (
              <div
                key={d.date}
                className={
                  d.weekday === 0
                    ? 'week-calendar__day week-calendar__day--sun' // 일요일은 빨간 글자
                    : d.weekday === 6
                      ? 'week-calendar__day week-calendar__day--sat' // 토요일은 파란 글자
                      : 'week-calendar__day'
                }
              >
                <span className="week-calendar__weekday">{WEEKDAY_LABELS[d.weekday]}</span>
                <span
                  className={
                    d.date === today
                      ? 'week-calendar__date week-calendar__date--today'
                      : 'week-calendar__date'
                  }
                >
                  {d.day}
                </span>
              </div>
            ))}
            <span />
            <span />
          </div>
          <div className="week-calendar__body">
            {offset === 0 && (
              <div
                className="week-calendar__today-line"
                style={{ '--today-col': todayCol } as CSSProperties}
                aria-hidden="true"
              />
            )}
            {rows.map((food, i) => (
              <FoodBarRow key={food.id} food={food} weekDate={weekDate} onSelect={onSelectFood} index={i} />
            ))}
            {rows.length === 0 && <p className="week-calendar__empty">이 주에는 막대로 보이는 식품이 없어요.</p>}
          </div>
        </div>
      </div>
    </section>
  )
}
