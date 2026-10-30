// 가짜 API 흉내. 개발 중(VITE_USE_MOCK)에만 쓴다. 실제 화면 코드가 아니다.
// 진짜 API 가 하는 일(기한 계산, 상태 판정, 정렬)을 여기서만 대신한다.
// 화면(pages · components)에는 이런 계산을 넣지 않는다 (D-009, D-016).
// 새로고침하면 등록·수정·처리·삭제한 내용은 모두 처음으로 돌아간다.
// 가짜 계산은 실제 규칙(D-006 계산식, D-024 등)을 재현하지 않는다. 화면 확인용 흉내일 뿐이다.
import type { ExpiryLevel, Food, FoodListResponse, Storage } from '../types/food'
import type {
  ChangeStorageInput,
  FoodDetail,
  FoodSource,
  SaveResult,
  UpdateFoodInput,
} from '../types/foodDetail'
import type { ManualRegisterInput, RuleRegisterInput } from '../types/register'
import type { RuleStorageOption } from '../types/rule'
import foodDetailsMock from './foodDetails.json'
import foodsMock from './foods.json'
import rulesMock from './rules.json'

interface MockRule {
  id: string
  name: string
  storages: { storage: string; allowed: boolean; max_days?: number }[]
}

interface MockExtra {
  quantity: number
  unit: string
  source: FoodSource
}
type MockRecord = Food & MockExtra

const DAY_MS = 24 * 60 * 60 * 1000
const FALLBACK_DAYS = 7 // 규칙표 값을 못 찾을 때
const ALL_STORAGES: Storage[] = ['room', 'fridge', 'freezer']

const created: MockRecord[] = []
const patches = new Map<string, Partial<MockRecord>>() // 수정한 내용 (처음 mock 식품과 등록한 식품 모두)
const gone = new Set<string>() // 처리했거나 삭제한 식품

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

function ruleByName(name: string): MockRule | undefined {
  return (rulesMock.rules as MockRule[]).find((r) => r.name === name)
}

function maxDays(rule: MockRule | undefined, storage: Storage): number {
  return rule?.storages.find((s) => s.storage === storage)?.max_days ?? FALLBACK_DAYS
}

function expiryOf(input: RuleRegisterInput | ManualRegisterInput): string {
  if ('rule_id' in input) {
    const rule = (rulesMock.rules as MockRule[]).find((r) => r.id === input.rule_id)
    return addDays(input.purchase_date, maxDays(rule, input.storage))
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
    quantity: input.quantity,
    unit: input.unit,
    source: 'rule_id' in input ? 'rule' : 'manual',
  })
}

// 기존 mock 목록에 등록한 식품을 합치고, 수정·처리·삭제를 반영해 API 처럼 기한 → 구매일 → 이름 순으로 정렬한다 (D-015)
export function withCreatedFoods(res: FoodListResponse): FoodListResponse {
  const foods = [...res.foods, ...created]
    .filter((f) => !gone.has(f.id))
    .map((f): Food => ({ ...f, ...patches.get(f.id) }))
    .sort(
      (a, b) =>
        a.expiry_date.localeCompare(b.expiry_date) ||
        a.purchase_date.localeCompare(b.purchase_date) ||
        a.name.localeCompare(b.name),
    )
  return { ...res, foods }
}

// ---- 식품 상세 (A5 ~ A9) 가짜 처리 ----

function recordOf(id: string): MockRecord | null {
  if (gone.has(id)) return null
  const base = (foodsMock.foods as Food[]).find((f) => f.id === id)
  const extra = (foodDetailsMock as unknown as Record<string, MockExtra | undefined>)[id]
  const found: MockRecord | undefined = base && extra ? { ...base, ...extra } : created.find((f) => f.id === id)
  return found ? { ...found, ...patches.get(id) } : null
}

function storagesOf(rec: MockRecord): RuleStorageOption[] {
  const rule = rec.source === 'rule' ? ruleByName(rec.name) : undefined
  return ALL_STORAGES.map((storage) => ({
    storage,
    allowed: rule ? (rule.storages.find((s) => s.storage === storage)?.allowed ?? false) : true,
  }))
}

export function getMockFoodDetail(id: string): FoodDetail | null {
  const rec = recordOf(id)
  if (!rec) return null
  return {
    id: rec.id,
    name: rec.name,
    storage: rec.storage,
    quantity: rec.quantity,
    unit: rec.unit,
    purchase_date: rec.purchase_date,
    expiry_date: rec.expiry_date,
    expiry_level: rec.expiry_level,
    source: rec.source,
    storages: storagesOf(rec),
  }
}

function applyPatch(id: string, patch: Partial<MockRecord>, today: string): void {
  const next = { ...patches.get(id), ...patch }
  if (patch.expiry_date) {
    next.expiry_level = mockLevel(today, patch.expiry_date)
    next.show_on_calendar = dayNumber(patch.expiry_date) - dayNumber(today) >= -3
  }
  patches.set(id, next)
}

const PAST_EXPIRY = { expiry: '기한은 오늘보다 이전 날짜로 적을 수 없어요. (가짜 응답)' }

export function updateMockFood(id: string, input: UpdateFoodInput, today: string): SaveResult {
  const rec = recordOf(id)
  if (!rec) return { status: 'failed' }
  if (input.expiry_date && dayNumber(input.expiry_date) < dayNumber(today)) {
    return { status: 'invalid', fieldErrors: PAST_EXPIRY }
  }

  const purchase = input.purchase_date ?? rec.purchase_date
  let expiry = rec.expiry_date
  let source = rec.source
  let recalculated = false

  if (input.name !== undefined && input.name !== rec.name) {
    const rule = ruleByName(input.name)
    if (rule) {
      source = 'rule'
      expiry = addDays(purchase, maxDays(rule, rec.storage))
      recalculated = true
    } else {
      if (rec.expiry_level === 'expired') {
        return {
          status: 'invalid',
          fieldErrors: { name: '기한이 지난 식품은 목록에 없는 이름으로 바꿀 수 없어요. (가짜 응답)' },
        }
      }
      if (!input.expiry_date) return { status: 'need_expiry' }
      source = 'manual'
      expiry = input.expiry_date
      recalculated = true
    }
  }

  if (input.purchase_date !== undefined && input.purchase_date !== rec.purchase_date) {
    if (source === 'manual') {
      if (dayNumber(purchase) > dayNumber(expiry)) {
        return {
          status: 'invalid',
          fieldErrors: { purchase_date: '구매일이 기한보다 늦어요. (가짜 응답)' },
        }
      }
    } else if (!recalculated) {
      expiry = addDays(expiry, dayNumber(purchase) - dayNumber(rec.purchase_date)) // 구매일 이동만큼 기한 이동 (D-024)
    }
  }

  const patch: Partial<MockRecord> = { source, purchase_date: purchase }
  if (input.name !== undefined) patch.name = input.name
  if (input.quantity !== undefined) patch.quantity = input.quantity
  if (input.unit !== undefined) patch.unit = input.unit
  if (expiry !== rec.expiry_date) patch.expiry_date = expiry
  applyPatch(id, patch, today)
  return { status: 'ok' }
}

export function changeMockStorage(id: string, input: ChangeStorageInput, today: string): SaveResult {
  const rec = recordOf(id)
  if (!rec) return { status: 'failed' }
  let expiry: string

  if (rec.source === 'manual') {
    if (!input.expiry_date) return { status: 'need_expiry' }
    if (dayNumber(input.expiry_date) < dayNumber(today)) {
      return { status: 'invalid', fieldErrors: PAST_EXPIRY }
    }
    expiry = input.expiry_date
  } else {
    const allowed = storagesOf(rec).find((s) => s.storage === input.storage)?.allowed
    if (!allowed) {
      return { status: 'invalid', fieldErrors: { storage: '이 보관 방법은 고를 수 없어요. (가짜 응답)' } }
    }
    expiry = addDays(rec.purchase_date, maxDays(ruleByName(rec.name), input.storage)) // 가짜 계산: D-006 식이 아님
    if (rec.expiry_level === 'expired' && dayNumber(expiry) <= dayNumber(today)) {
      return {
        status: 'invalid',
        fieldErrors: { storage: '이미 기한이 지나서 이 보관 방법으로 바꿀 수 없어요. (가짜 응답)' },
      }
    }
  }
  applyPatch(id, { storage: input.storage, expiry_date: expiry }, today)
  return { status: 'ok' }
}

// 다 먹음 · 버림 · 삭제는 모두 목록에서 빠진다. 없는 식품이면 false (D-008)
export function removeMockFood(id: string): boolean {
  if (!recordOf(id)) return false
  gone.add(id)
  return true
}
