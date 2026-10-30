// 가짜 API 흉내. 개발 중(VITE_USE_MOCK)에만 쓴다. 실제 화면 코드가 아니다.
// 진짜 API 가 하는 일(기한 계산, 상태 판정, 정렬)을 여기서만 대신한다.
// 화면(pages · components)에는 이런 계산을 넣지 않는다 (D-009, D-016).
// 새로고침하면 등록한 식품은 사라진다.
import type { ExpiryLevel, Food, FoodListResponse } from '../types/food'
import type { ManualRegisterInput, RuleRegisterInput } from '../types/register'
import rulesMock from './rules.json'

interface MockRule {
  id: string
  storages: { storage: string; allowed: boolean; max_days?: number }[]
}

const DAY_MS = 24 * 60 * 60 * 1000
const FALLBACK_DAYS = 7 // 규칙표 값을 못 찾을 때

const created: Food[] = []

function dayNumber(date: string): number {
  const [y, m, d] = date.split('-').map(Number)
  return Date.UTC(y, m - 1, d) / DAY_MS
}

function addDays(date: string, days: number): string {
  return new Date((dayNumber(date) + days) * DAY_MS).toISOString().slice(0, 10)
}

// 가짜 상태 판정 (D-014 기준을 흉내만 낸다)
function mockLevel(today: string, expiry: string): ExpiryLevel {
  const left = dayNumber(expiry) - dayNumber(today)
  if (left < 0) return 'expired'
  if (left <= 2) return 'urgent'
  if (left <= 5) return 'caution'
  return 'relaxed'
}

function expiryOf(input: RuleRegisterInput | ManualRegisterInput): string {
  if ('rule_id' in input) {
    const rule = (rulesMock.rules as MockRule[]).find((r) => r.id === input.rule_id)
    const days = rule?.storages.find((s) => s.storage === input.storage)?.max_days
    return addDays(input.purchase_date, days ?? FALLBACK_DAYS)
  }
  if (input.expiry_date) return input.expiry_date
  return addDays(input.purchase_date, input.expiry_days ?? FALLBACK_DAYS)
}

export function addMockFood(input: RuleRegisterInput | ManualRegisterInput, today: string): void {
  const expiry = expiryOf(input)
  created.push({
    id: crypto.randomUUID(),
    name: input.name,
    storage: input.storage,
    purchase_date: input.purchase_date,
    expiry_date: expiry,
    expiry_level: mockLevel(today, expiry),
    show_on_calendar: true,
  })
}

// 기존 mock 목록에 등록한 식품을 합쳐, API 처럼 기한 → 구매일 → 이름 순으로 정렬한다 (D-015)
export function withCreatedFoods(res: FoodListResponse): FoodListResponse {
  if (created.length === 0) return res
  const foods = [...res.foods, ...created].sort(
    (a, b) =>
      a.expiry_date.localeCompare(b.expiry_date) ||
      a.purchase_date.localeCompare(b.purchase_date) ||
      a.name.localeCompare(b.name),
  )
  return { ...res, foods }
}
