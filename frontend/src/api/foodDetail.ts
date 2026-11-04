// 식품 상세(A4), 정보 수정(A5), 보관 방법 변경(A6), 처리(A7), 삭제(A8) 요청. 기준은 API-SPEC 2-3.
// 모양은 types/foodDetail.ts 에 있다.
// 약속: 성공은 2xx, 입력 규칙 위반은 422 + { field, reason, message },
//   "기한을 다시 적어야 함"은 실패가 아니라 409 + reason "expiry_required", 그 밖의 실패는 모두 "실패". (api/errors.ts)
// 개발 중 가짜 데이터: VITE_USE_MOCK 이 켜져 있으면 mocks/ 를 쓴다 (홈, 등록과 같은 값).
//   VITE_USE_MOCK=detail-error  상세 불러오기 실패
//   VITE_USE_MOCK=save-error    수정 · 보관 방법 · 처리 · 삭제 실패
//   VITE_USE_MOCK=save-invalid  수정 · 보관 방법 입력 오류 응답 (칸 옆 안내)
//   VITE_USE_MOCK=slow          저장 · 처리 · 삭제가 2초 걸림 (요청 중 확인용)
import { readFailure, readMessage } from './errors'
import { send } from './http'
import { foodsMock } from '../mocks/foodsMock'
import {
  changeMockStorage,
  getMockFoodDetail,
  processMockFood,
  removeMockFood,
  updateMockFood,
} from '../mocks/createdFoods'
import { searchRules, storagesFromDisallowed } from './rules'
import type { Food } from '../types/food'
import type { FieldErrors, FieldName } from '../types/register'
import type { RuleStorageOption } from '../types/rule'
import type {
  ActionResult,
  ChangeStorageInput,
  FoodDetail,
  ProcessStatus,
  SaveResult,
  UpdateFoodInput,
} from '../types/foodDetail'

const FOODS_PATH = '/api/foods'
const MOCK_MODE = import.meta.env.VITE_USE_MOCK
const MOCK_TODAY = foodsMock.today // mock 목록이 쓰는 오늘과 같게 맞춘다

// 화면마다 안내를 붙일 수 있는 칸. 정보 고치기에는 보관 방법 칸이 없어서,
// 이름을 바꿔 보관 방법이 "불가"가 된 경우(storage_not_allowed)는 화면 위 오류 알림으로 보인다.
const INFO_FORM_FIELDS: readonly FieldName[] = ['name', 'quantity', 'unit', 'purchase_date', 'expiry']
const STORAGE_FORM_FIELDS: readonly FieldName[] = ['storage', 'expiry']

// 어떤 실패든 화면은 "불러오기 실패" 하나로 보여 준다 (D-008). apiMessage 는 API 문구 (없으면 화면 기본 문구).
export class LoadFoodDetailError extends Error {
  readonly apiMessage?: string
  constructor(reason: string, apiMessage?: string) {
    super(reason)
    this.apiMessage = apiMessage
  }
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function foodPath(id: string, tail = ''): string {
  return `${FOODS_PATH}/${encodeURIComponent(id)}${tail}`
}

export async function getFoodDetail(id: string): Promise<FoodDetail> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'detail-error') throw new LoadFoodDetailError('mock error')
    const found = getMockFoodDetail(id)
    if (!found) throw new LoadFoodDetailError('mock not found', '찾을 수 없는 식품이에요.')
    return found
  }
  const res = await send(foodPath(id))
  if (!res) throw new LoadFoodDetailError('network')
  if (!res.ok) throw new LoadFoodDetailError(`status ${res.status}`, await readMessage(res))
  let food: Food
  try {
    food = (await res.json()) as Food
  } catch {
    throw new LoadFoodDetailError('bad response')
  }
  return { ...food, storages: await storagesFor(food) }
}

// 백엔드의 식품 상세 응답에는 보관 방법별 가능 여부가 없다. 그래서 여기서 채운다 (D-005).
// - 직접 등록 식품: 규칙표가 없으니 세 방법 모두 가능
// - 규칙표 식품: 규칙표 검색(C1)에서 이름이 정확히 같은 항목의 "불가" 목록을 쓴다.
//   못 찾거나 검색이 실패하면, 가능 여부를 모른 채 모두 고르게 둘 수 없어서 불러오기 실패로 본다.
async function storagesFor(food: Food): Promise<RuleStorageOption[]> {
  if (food.source === 'manual') return storagesFromDisallowed([])
  let found
  try {
    found = (await searchRules(food.name)).rules.find((rule) => rule.name === food.name)
  } catch {
    throw new LoadFoodDetailError('rule search failed')
  }
  if (!found) throw new LoadFoodDetailError('rule not found')
  return found.storages
}

async function patchFood(path: string, body: object, fields: readonly FieldName[]): Promise<SaveResult> {
  const res = await send(path, 'PATCH', body)
  if (res?.ok) return { status: 'ok' }
  return readFailure(res, fields) // API 에 닿지 못함(null)도 같은 오류로 보인다
}

async function requestAction(path: string, method: string, body?: object): Promise<ActionResult> {
  const res = await send(path, method, body)
  if (res?.ok) return { status: 'ok' }
  return { status: 'failed', message: await readMessage(res) }
}

// 가짜 저장 응답
async function mockSave(
  mode: string,
  run: () => SaveResult,
  invalidFields: FieldErrors,
): Promise<SaveResult> {
  if (mode === 'save-error') return { status: 'failed' }
  if (mode === 'save-invalid') return { status: 'invalid', fieldErrors: invalidFields }
  if (mode === 'slow') await wait(2000)
  return run()
}

// 가짜 처리 · 삭제 응답. 처리한 식품은 기록에 남고, 삭제한 식품은 남지 않는다 (D-013)
async function mockAction(mode: string, run: () => boolean): Promise<ActionResult> {
  if (mode === 'save-error') return { status: 'failed' }
  if (mode === 'slow') await wait(2000)
  return run() ? { status: 'ok' } : { status: 'failed', message: '찾을 수 없는 식품이에요.' }
}

export function updateFood(id: string, input: UpdateFoodInput): Promise<SaveResult> {
  if (MOCK_MODE) {
    return mockSave(MOCK_MODE, () => updateMockFood(id, input, MOCK_TODAY), {
      quantity: '수량을 다시 확인해 주세요. (가짜 오류 응답)',
    })
  }
  return patchFood(foodPath(id), input, INFO_FORM_FIELDS)
}

export function changeFoodStorage(id: string, input: ChangeStorageInput): Promise<SaveResult> {
  if (MOCK_MODE) {
    return mockSave(MOCK_MODE, () => changeMockStorage(id, input, MOCK_TODAY), {
      storage: '보관 방법을 다시 확인해 주세요. (가짜 오류 응답)',
    })
  }
  return patchFood(foodPath(id, '/storage'), input, STORAGE_FORM_FIELDS)
}

export function processFood(id: string, status: ProcessStatus): Promise<ActionResult> {
  if (MOCK_MODE) return mockAction(MOCK_MODE, () => processMockFood(id, status, MOCK_TODAY))
  return requestAction(foodPath(id, '/process'), 'PATCH', { status })
}

export function deleteFood(id: string): Promise<ActionResult> {
  if (MOCK_MODE) return mockAction(MOCK_MODE, () => removeMockFood(id))
  return requestAction(foodPath(id), 'DELETE')
}
