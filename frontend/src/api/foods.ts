// [임시 계약] 홈 목록을 가져오는 곳. 경로는 백엔드 담당 확인 전까지 임시다.
// 개발 중 가짜 데이터: frontend/.env.local (git 에 올리지 않는다)
//   VITE_USE_MOCK=1      식품 있음
//   VITE_USE_MOCK=empty  식품 없음
//   VITE_USE_MOCK=error  불러오기 실패
//   VITE_USE_MOCK=slow   2초 뒤 식품 있음 (불러오는 중 · 등록 중 확인용)
// 식품 등록(A3, A4)도 같은 값으로 가짜 응답을 쓴다. 등록한 식품은 홈 목록 mock 에 합쳐진다.
//   VITE_USE_MOCK=save-error    등록 저장 실패
//   VITE_USE_MOCK=save-invalid  등록 입력 오류 응답 (칸 옆 안내)
import type { FoodListResponse } from '../types/food'
import type {
  FieldErrors,
  ManualRegisterInput,
  RegisterResult,
  RuleRegisterInput,
} from '../types/register'
import foodsMock from '../mocks/foods.json'
import foodsEmptyMock from '../mocks/foods.empty.json'
import { addMockFood, withCreatedFoods } from '../mocks/createdFoods'

const FOODS_PATH = '/api/foods'
const MANUAL_PATH = '/api/foods/manual'
const MOCK_MODE = import.meta.env.VITE_USE_MOCK

// 어떤 실패든 화면은 "불러오기 실패" 하나로 보여 준다 (API-SPEC 4절).
export class LoadFoodsError extends Error {}

async function getMockFoods(mode: string): Promise<FoodListResponse> {
  if (mode === 'error') throw new LoadFoodsError('mock error')
  if (mode === 'empty') return withCreatedFoods(foodsEmptyMock as FoodListResponse)
  if (mode === 'slow') await new Promise((resolve) => setTimeout(resolve, 2000))
  return withCreatedFoods(foodsMock as FoodListResponse)
}

export async function getFoods(): Promise<FoodListResponse> {
  if (MOCK_MODE) return getMockFoods(MOCK_MODE)
  try {
    const res = await fetch(FOODS_PATH)
    if (!res.ok) throw new LoadFoodsError(`status ${res.status}`)
    return (await res.json()) as FoodListResponse
  } catch (e) {
    throw e instanceof LoadFoodsError ? e : new LoadFoodsError('network')
  }
}

// [임시 계약] 식품 등록 요청. 경로·본문·오류 응답 모양은 백엔드 담당 확인 전까지 임시다.
// 임시 약속: 성공은 2xx, 입력 규칙 위반은 422 + { errors: { 칸이름: 안내 } }, 그 밖의 실패는 모두 "저장 실패".
async function postFood(path: string, body: object): Promise<RegisterResult> {
  try {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (res.ok) return { status: 'ok' }
    if (res.status === 422) {
      const data = (await res.json().catch(() => null)) as { errors?: FieldErrors } | null
      return { status: 'invalid', fieldErrors: data?.errors ?? {} }
    }
    return { status: 'failed' }
  } catch {
    return { status: 'failed' } // API 에 닿지 못함도 같은 오류로 보인다
  }
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
  return postFood(FOODS_PATH, input)
}

export function createManualFood(input: ManualRegisterInput): Promise<RegisterResult> {
  if (MOCK_MODE) {
    return mockRegister(
      MOCK_MODE,
      () => addMockFood(input, MOCK_TODAY),
      { expiry: '기한을 다시 확인해 주세요. (가짜 오류 응답)' },
    )
  }
  return postFood(MANUAL_PATH, input)
}
