import type { CSSProperties, ReactNode } from 'react'
import { getWeekDays, getWeekday } from '../lib/week'
import './WeekCalendar.css'

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

interface Props {
  today: string // API 가 준 오늘 날짜 (D-021). 화면 시계는 쓰지 않는다
  children?: ReactNode // 식품 막대 줄들. 줄은 .week-grid 를 써서 7칸 열을 맞춘다
}

// 이번 주 7일(일요일 시작) 틀과 오늘 세로선. 막대 줄은 children 으로 받는다.
export default function WeekCalendar({ today, children }: Props) {
  const days = getWeekDays(today)
  const todayCol = getWeekday(today)

  return (
    <section className="week-calendar" aria-label="이번 주 달력">
      <div className="week-grid week-calendar__head">
        <span />
        {days.map((d) => (
          <div key={d.date} className="week-calendar__day">
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
      </div>
      <div className="week-calendar__body">
        <div
          className="week-calendar__today-line"
          style={{ '--today-col': todayCol } as CSSProperties}
          aria-hidden="true"
        />
        {children}
      </div>
    </section>
  )
}
