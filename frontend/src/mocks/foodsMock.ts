// 가짜 홈 목록 (개발 중 VITE_USE_MOCK 에서만 쓴다). foods.json 의 날짜는 2026-10-30 을 "오늘"로 적어 둔 값이라,
// 그대로 쓰면 실제 날짜와 어긋나 달력의 주가 틀리게 보인다. 그래서 불러올 때 "오늘"을 이 기기의 오늘 날짜로 맞추고
// 모든 식품 날짜를 같은 일수만큼 옮긴다. 남은 날 · 상태는 오늘 기준이라 옮겨도 그대로 맞는다.
import type { Food, FoodListResponse } from '../types/food'
import emptyRaw from './foods.empty.json'
import raw from './foods.json'

const DAY_MS = 24 * 60 * 60 * 1000

function dayNumber(date: string): number {
  const [y, m, d] = date.split('-').map(Number)
  return Date.UTC(y, m - 1, d) / DAY_MS
}

// 이 기기의 오늘 날짜 (YYYY-MM-DD)
function deviceToday(): string {
  const now = new Date()
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${mm}-${dd}`
}

const TODAY = deviceToday()
const SHIFT_DAYS = dayNumber(TODAY) - dayNumber(raw.today)

function shift(date: string): string {
  return new Date((dayNumber(date) + SHIFT_DAYS) * DAY_MS).toISOString().slice(0, 10)
}

export const foodsMock: FoodListResponse = {
  today: TODAY,
  items: (raw.items as unknown as Food[]).map((f) => ({
    ...f,
    purchase_date: shift(f.purchase_date),
    expiry_date: shift(f.expiry_date),
  })),
}

export const foodsEmptyMock: FoodListResponse = { today: TODAY, items: emptyRaw.items as unknown as Food[] }
