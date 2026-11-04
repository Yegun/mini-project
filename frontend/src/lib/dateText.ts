// 표시용 날짜 글자: "26년 10월 30일(금)" (D-031). 날짜 비교·덧셈은 하지 않는다 (D-016).
import { getWeekday } from './week'

const WEEKDAY_NAMES = ['일', '월', '화', '수', '목', '금', '토']

// YYYY-MM-DD 가 아니면 빈 글자를 돌려준다.
export function formatKoreanDate(date: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return ''
  const yy = date.slice(2, 4)
  const month = Number(date.slice(5, 7))
  const day = Number(date.slice(8, 10))
  return `${yy}년 ${month}월 ${day}일(${WEEKDAY_NAMES[getWeekday(date)]})`
}

const WEEKDAY_FULL = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']

// 큰 날짜 표시용으로 나눈 조각: { year: '2026', month: 11, day: 5, weekday: '목요일' }.
// YYYY-MM-DD 가 아니면 null 이다. 나누기만 하고 날짜 비교·덧셈은 하지 않는다 (D-016).
export function formatDateParts(date: string): { year: string; month: number; day: number; weekday: string } | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null
  return {
    year: date.slice(0, 4),
    month: Number(date.slice(5, 7)),
    day: Number(date.slice(8, 10)),
    weekday: WEEKDAY_FULL[getWeekday(date)],
  }
}
