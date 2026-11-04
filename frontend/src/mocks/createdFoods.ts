// 가짜 API 흉내. 개발 중(VITE_USE_MOCK)에만 쓴다. 실제 화면 코드가 아니다.
// 진짜 API 가 하는 일(기한 계산, 상태 판정, 정렬)을 여기서만 대신한다.
// 화면(pages · components)에는 이런 계산을 넣지 않는다 (D-009, D-016).
// 새로고침하면 등록·수정·처리·삭제한 내용은 모두 처음으로 돌아간다.
// 가짜 계산은 실제 규칙(D-006 계산식, D-024 등)을 재현하지 않는다. 화면 확인용 흉내일 뿐이다.
import type { ExpiryStatus, Food, FoodListResponse, Storage } from '../types/food'
import type {
  ChangeStorageInput,
  FoodDetail,
  ProcessStatus,
  SaveResult,
  UpdateFoodInput,
} from '../types/foodDetail'
import type { ProcessedFood, RecordsData } from '../types/records'
import type { ManualRegisterInput, RuleRegisterInput } from '../types/register'
import type { RuleStorageOption } from '../types/rule'
import foodsMock from './foods.json'
import rulesMock from './rules.json'
import { ruleFields } from './ruleInfo'

interface MockRule {
  id: string
  name: string
  storages: { storage: string; allowed: boolean; max_days?: number }[]
}

type MockRecord = Food

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
function mockLevel(today: string, expiry: string): ExpiryStatus {
  const left = dayNumber(expiry) - dayNumber(today)
  if (left < 0) return 'expired'
  if (left <= 2) return 'soon'
  if (left <= 5) return 'warning'
  return 'fresh'
}

function ruleByName(name: string): MockRule | undefined {
  return (rulesMock.rules as MockRule[]).find((r) => r.name === name)
}

function maxDays(rule: MockRule | undefined, storage: Storage): number {
  return rule?.storages.find((s) => s.storage === storage)?.max_days ?? FALLBACK_DAYS
}

// 직접 등록은 기한(expiry_date 또는 expiry_in_days)을 보내고, 규칙표 등록은 보내지 않는다.
function isManual(input: RuleRegisterInput | ManualRegisterInput): input is ManualRegisterInput {
  return 'expiry_date' in input || 'expiry_in_days' in input
}

function expiryOf(input: RuleRegisterInput | ManualRegisterInput): string {
  if (!isManual(input)) {
    const rule = ruleByName(input.name)
    return addDays(input.purchase_date, maxDays(rule, input.storage))
  }
  if (input.expiry_date) return input.expiry_date
  return addDays(input.purchase_date, input.expiry_in_days ?? FALLBACK_DAYS)
}

export function addMockFood(input: RuleRegisterInput | ManualRegisterInput, today: string): void {
  const expiry = expiryOf(input)
  created.push({
    id: crypto.randomUUID(),
    name: input.name,
    storage: input.storage,
    quantity: input.quantity,
    unit: input.unit,
    purchase_date: input.purchase_date,
    expiry_date: expiry,
    source: isManual(input) ? 'manual' : 'rule',
    status: 'none',
    processed_date: null,
    expiry_status: mockLevel(today, expiry),
    days_left: dayNumber(expiry) - dayNumber(today),
    show_on_calendar: true,
    // 직접 등록 식품은 위험 표시가 없고 종류는 등록할 때 고른 값, 규칙표 식품은 규칙표 값 (D-166, API-SPEC 0-1)
    ...(isManual(input)
      ? { is_danger: false, danger_note: null, category: input.category ?? 'other' }
      : ruleFields(input.name)),
  })
}

// 기존 mock 목록에 등록한 식품을 합치고, 수정·처리·삭제를 반영해 API 처럼 기한 → 구매일 → 이름 순으로 정렬한다 (D-015)
export function withCreatedFoods(res: FoodListResponse): FoodListResponse {
  const items = [...res.items, ...created]
    .filter((f) => !gone.has(f.id))
    .map((f): Food => ({ ...f, ...patches.get(f.id) }))
    .sort(
      (a, b) =>
        a.expiry_date.localeCompare(b.expiry_date) ||
        a.purchase_date.localeCompare(b.purchase_date) ||
        a.name.localeCompare(b.name),
    )
  return { ...res, items }
}

// ---- 식품 상세 (A4 ~ A8) 가짜 처리 ----

function recordOf(id: string): MockRecord | null {
  if (gone.has(id)) return null
  const found = (foodsMock.items as Food[]).find((f) => f.id === id) ?? created.find((f) => f.id === id)
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
  return { ...rec, storages: storagesOf(rec) }
}

function applyPatch(id: string, patch: Partial<MockRecord>, today: string): void {
  const next = { ...patches.get(id), ...patch }
  if (patch.expiry_date) {
    next.expiry_status = mockLevel(today, patch.expiry_date)
    next.days_left = dayNumber(patch.expiry_date) - dayNumber(today)
    next.show_on_calendar = next.days_left >= -3
  }
  patches.set(id, next)
}

const PAST_EXPIRY = { expiry: '기한은 오늘보다 이전 날짜로 적을 수 없어요. (가짜 응답)' }
const NOT_FOUND = '찾을 수 없는 식품이에요.' // API-SPEC 3절의 not_found 문구

export function updateMockFood(id: string, input: UpdateFoodInput, today: string): SaveResult {
  const rec = recordOf(id)
  if (!rec) return { status: 'failed', message: NOT_FOUND }
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
      if (rec.expiry_status === 'expired') {
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
  // 이름 · 등록 방식이 바뀌면 위험 · 종류 칸도 바뀐다 (API-SPEC A5, DATA-MODEL Q-34)
  if (source === 'rule' && (rec.source !== 'rule' || (input.name !== undefined && input.name !== rec.name))) {
    Object.assign(patch, ruleFields(input.name ?? rec.name)) // 규칙표 값을 읽어 붙인다
  } else if (source === 'manual' && rec.source === 'rule') {
    Object.assign(patch, { is_danger: false, danger_note: null, category: rec.category ?? 'other' }) // 바뀌기 전 규칙표의 종류를 저장
  }
  if (source === 'manual' && input.category !== undefined) patch.category = input.category // 직접 등록 식품만 종류를 고친다
  if (input.quantity !== undefined) patch.quantity = input.quantity
  if (input.unit !== undefined) patch.unit = input.unit
  if (expiry !== rec.expiry_date) patch.expiry_date = expiry
  applyPatch(id, patch, today)
  return { status: 'ok' }
}

export function changeMockStorage(id: string, input: ChangeStorageInput, today: string): SaveResult {
  const rec = recordOf(id)
  if (!rec) return { status: 'failed', message: NOT_FOUND }
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
    if (rec.expiry_status === 'expired' && dayNumber(expiry) <= dayNumber(today)) {
      return {
        status: 'invalid',
        fieldErrors: { storage: '이미 기한이 지나서 이 보관 방법으로 바꿀 수 없어요. (가짜 응답)' },
      }
    }
  }
  applyPatch(id, { storage: input.storage, expiry_date: expiry }, today)
  return { status: 'ok' }
}

// 삭제: 목록에서 빠지고 기록에도 남지 않는다. 없는 식품이면 false (D-008, D-013)
export function removeMockFood(id: string): boolean {
  if (!recordOf(id)) return false
  gone.add(id)
  return true
}

// ---- 기록 (D1 ~ D3) 가짜 처리 ----

interface MockProcessed {
  status: ProcessStatus
  processed_date: string
}
const processed = new Map<string, MockProcessed>() // 다 먹음 · 버림한 식품. 홈에서는 빠지고 기록에 남는다

// 다 먹음 · 버림: 홈에서 빠지고 처리한 날짜(오늘)와 함께 기록에 남는다 (D-064)
export function processMockFood(id: string, status: ProcessStatus, today: string): boolean {
  if (!recordOf(id)) return false
  gone.add(id)
  processed.set(id, { status, processed_date: today })
  return true
}

// 홈으로 되돌리기: 처리 상태와 처리한 날짜만 지우고 나머지는 그대로 (D-075, D-076)
export function restoreMockFood(id: string): boolean {
  if (!processed.has(id)) return false // 없는 · 처리되지 않은 식품
  processed.delete(id)
  gone.delete(id)
  return true
}

function processedList(status: ProcessStatus): ProcessedFood[] {
  const list: ProcessedFood[] = []
  for (const [id, p] of processed) {
    if (p.status !== status) continue
    const rec = recordOfAny(id)
    if (!rec) continue
    list.push({ id, name: rec.name, quantity: rec.quantity, unit: rec.unit, processed_date: p.processed_date })
  }
  // 최근 처리한 순 → 이름순 (API-SPEC D2)
  return list.sort((a, b) => b.processed_date.localeCompare(a.processed_date) || a.name.localeCompare(b.name))
}

// 처리해서 gone 에 들어간 식품도 찾는다 (기록용)
function recordOfAny(id: string): MockRecord | null {
  const found = (foodsMock.items as Food[]).find((f) => f.id === id) ?? created.find((f) => f.id === id)
  return found ? { ...found, ...patches.get(id) } : null
}

// 가짜 기록: 지금 mock 상태로 숫자를 센다. base 는 홈 목록 mock (식품 있음 / 없음)
export function getMockRecords(base: FoodListResponse): RecordsData {
  const current = withCreatedFoods(base).items
  const eaten = processedList('eaten')
  const discarded = processedList('discarded')
  const year = base.today.slice(0, 4)
  const month = base.today.slice(0, 7)
  const count = (list: ProcessedFood[], prefix: string) =>
    list.filter((f) => f.processed_date.startsWith(prefix)).length
  const byStorage = { room: 0, fridge: 0, freezer: 0 }
  const byStatus = { fresh: 0, warning: 0, soon: 0, expired: 0 }
  for (const f of current) {
    byStorage[f.storage] += 1
    byStatus[f.expiry_status] += 1
  }
  return {
    summary: {
      eaten: { year: count(eaten, year), month: count(eaten, month) },
      discarded: { year: count(discarded, year), month: count(discarded, month) },
      food_kinds: new Set(current.map((f) => f.name)).size,
      by_storage: byStorage,
      by_status: byStatus,
    },
    foods: { eaten, discarded },
  }
}
