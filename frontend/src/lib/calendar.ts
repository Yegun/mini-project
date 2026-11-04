// 전체 달력의 날짜 계산: 한 달을 7칸 × 몇 줄로 펼치고, 날짜 글자를 만든다.
// 화면이 하는 날짜 계산은 달력에 식품을 배치하는 것뿐이다. 상태 판정은 하지 않는다 (D-009, D-016).
import { addDays, getWeekday } from './week'

export interface MonthCell {
  date: string // YYYY-MM-DD
  day: number
  inMonth: boolean // 이 달에 속한 날짜인지 (앞뒤 빈 칸은 이전 · 다음 달 날짜)
}

const WEEKDAY_NAMES = ['일', '월', '화', '수', '목', '금', '토']

// 연 · 월에 n 달을 더한다 (n 은 음수도 된다). month 는 1~12.
export function addMonths(year: number, month: number, n: number): { year: number; month: number } {
  const total = year * 12 + (month - 1) + n
  return { year: Math.floor(total / 12), month: (((total % 12) + 12) % 12) + 1 }
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

// 그 달을 일요일 시작 7칸 × 필요한 줄로 펼친다 (앞뒤 빈 칸은 이전 · 다음 달 날짜)
export function monthGrid(year: number, month: number): MonthCell[] {
  const first = `${year}-${pad(month)}-01`
  const lead = getWeekday(first) // 첫날 앞의 빈 칸 수
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate()
  const weeks = Math.ceil((lead + daysInMonth) / 7)
  const start = addDays(first, -lead)
  const prefix = `${year}-${pad(month)}`
  return Array.from({ length: weeks * 7 }, (_, i) => {
    const date = addDays(start, i)
    return { date, day: Number(date.slice(8, 10)), inMonth: date.startsWith(prefix) }
  })
}

// "2026년 11월"
export function monthTitle(year: number, month: number): string {
  return `${year}년 ${month}월`
}

// "11월 6일 (금)" — 날짜 목록 창 맨 위에 보인다 (SCREEN-SPEC 14.3 의 2번)
export function formatMonthDay(date: string): string {
  return `${Number(date.slice(5, 7))}월 ${Number(date.slice(8, 10))}일 (${WEEKDAY_NAMES[getWeekday(date)]})`
}
