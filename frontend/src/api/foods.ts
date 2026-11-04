// 홈 목록(A1)과 식품 등록(A2 규칙표, A3 직접). 기준은 API-SPEC 2-3.
// 개발 중 가짜 데이터: frontend/.env.local (git 에 올리지 않는다)
//   VITE_USE_MOCK=1      식품 있음
//   VITE_USE_MOCK=empty  식품 없음
//   VITE_USE_MOCK=error  불러오기 실패
//   VITE_USE_MOCK=slow   2초 뒤 식품 있음 (불러오는 중 · 등록 중 확인용)
//   VITE_USE_MOCK=expired  로그인이 끝남(30분 만료) → 로그인 화면으로 (로그인하면 식품 있음)
// 식품 등록도 같은 값으로 가짜 응답을 쓴다. 등록한 식품은 홈 목록 mock 에 합쳐진다.
//   VITE_USE_MOCK=save-error    등록 저장 실패
//   VITE_USE_MOCK=save-invalid  등록 입력 오류 응답 (칸 옆 안내)
import type { FoodListResponse } from '../types/food'
import type {
  FieldErrors,
  FieldName,
  ManualRegisterInput,
  RegisterResult,
  RuleRegisterInput,
} from '../types/register'
import { readFailure, readMessage } from './errors'
import { send } from './http'
import { notifyLoginRequired } from './session'
import { foodsEmptyMock, foodsMock } from '../mocks/foodsMock'
import { addMockFood, withCreatedFoods } from '../mocks/createdFoods'

const FOODS_PATH = '/api/foods'
const MANUAL_PATH = '/api/foods/manual'
const MOCK_MODE = import.meta.env.VITE_USE_MOCK

// 등록 화면마다 안내를 붙일 수 있는 칸. 규칙표 등록은 이름을 검색 결과에서 고르므로 이름 칸이 없다.
const RULE_FORM_FIELDS: readonly FieldName[] = ['storage', 'quantity', 'unit', 'purchase_date']
const MANUAL_FORM_FIELDS: readonly FieldName[] = ['name', 'category', 'storage', 'quantity', 'unit', 'purchase_date', 'expiry']

// 어떤 실패든 화면은 "불러오기 실패" 하나로 보여 준다. message 는 API 문구 (없으면 화면 기본 문구).
export class LoadFoodsError extends Error {
  readonly apiMessage?: string
  constructor(reason: string, apiMessage?: string) {
    super(reason)
    this.apiMessage = apiMessage
  }
}

let mockExpiredShown = false // expired 는 처음 한 번만. 다시 로그인하면 목록이 보인다

async function getMockFoods(mode: string): Promise<FoodListResponse> {
  if (mode === 'error') throw new LoadFoodsError('mock error')
  if (mode === 'expired' && !mockExpiredShown) {
    mockExpiredShown = true
    notifyLoginRequired()
    throw new LoadFoodsError('mock login required', '다시 로그인해 주세요.')
  }
  if (mode === 'empty') return withCreatedFoods(foodsEmptyMock as FoodListResponse)
  if (mode === 'slow') await new Promise((resolve) => setTimeout(resolve, 2000))
  return withCreatedFoods(foodsMock as FoodListResponse)
}

export async function getFoods(): Promise<FoodListResponse> {
  if (MOCK_MODE) return getMockFoods(MOCK_MODE)
  const res = await send(FOODS_PATH)
  if (!res) throw new LoadFoodsError('network')
  if (!res.ok) throw new LoadFoodsError(`status ${res.status}`, await readMessage(res))
  try {
    return (await res.json()) as FoodListResponse
  } catch {
    throw new LoadFoodsError('bad response')
  }
}

// 성공은 201, 입력 규칙 위반은 422 + { field, reason, message }, 그 밖의 실패는 모두 "저장 실패" (api/errors.ts).
async function postFood(path: string, body: object, fields: readonly FieldName[]): Promise<RegisterResult> {
  const res = await send(path, 'POST', body)
  if (res?.ok) return { status: 'ok' }
  const failure = await readFailure(res, fields) // API 에 닿지 못함(null)도 같은 오류로 보인다
  return failure.status === 'need_expiry' ? { status: 'failed' } : failure // 등록에는 "기한 다시 적기"가 없다
}

// 가짜 등록 응답. 성공하면 mock 목록에 식품을 쌓는다.
async function mockRegister(
  mode: string,
  save: () => void,
  invalidFields: FieldErrors,
): Promise<RegisterResult> {
  if (mode === 'save-error') return { status: 'failed' }
  if (mode === 'save-invalid') return { status: 'invalid', fieldErrors: invalidFields }
  if (mode === 'slow') await new Promise((resolve) => setTimeout(resolve, 2000))
  save()
  return { status: 'ok' }
}

// 오늘 날짜는 mock 목록이 쓰는 값과 같게 맞춘다.
const MOCK_TODAY = foodsMock.today

export function createRuleFood(input: RuleRegisterInput): Promise<RegisterResult> {
  if (MOCK_MODE) {
    return mockRegister(
      MOCK_MODE,
      () => addMockFood(input, MOCK_TODAY),
      { quantity: '수량을 다시 확인해 주세요. (가짜 오류 응답)' },
    )
  }
  return postFood(FOODS_PATH, input, RULE_FORM_FIELDS)
}

export function createManualFood(input: ManualRegisterInput): Promise<RegisterResult> {
  if (MOCK_MODE) {
    return mockRegister(
      MOCK_MODE,
      () => addMockFood(input, MOCK_TODAY),
      { expiry: '기한을 다시 확인해 주세요. (가짜 오류 응답)' },
    )
  }
  return postFood(MANUAL_PATH, input, MANUAL_FORM_FIELDS)
}
