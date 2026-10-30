// [임시 계약] 식품 상세(A5), 수정(A6), 보관 방법 변경(A7), 처리(A8), 삭제(A9) 요청.
// 경로·본문·응답 모양은 백엔드 담당 확인 전까지 임시다. 모양은 types/foodDetail.ts 에 있다.
// 임시 약속: 성공은 2xx, 입력 규칙 위반은 422 + { errors: { 칸이름: 안내 } },
//   "기한을 다시 적어야 함"은 실패가 아니라 200 + { status: "need_expiry" }, 그 밖의 실패는 모두 "실패".
// 개발 중 가짜 데이터: VITE_USE_MOCK 이 켜져 있으면 mocks/ 를 쓴다 (홈, 등록과 같은 값).
//   VITE_USE_MOCK=detail-error  상세 불러오기 실패
//   VITE_USE_MOCK=save-error    수정 · 보관 방법 · 처리 · 삭제 실패
//   VITE_USE_MOCK=save-invalid  수정 · 보관 방법 입력 오류 응답 (칸 옆 안내)
//   VITE_USE_MOCK=slow          저장 · 처리 · 삭제가 2초 걸림 (요청 중 확인용)
import foodsMock from '../mocks/foods.json'
import {
  changeMockStorage,
  getMockFoodDetail,
  removeMockFood,
  updateMockFood,
} from '../mocks/createdFoods'
import type { FieldErrors } from '../types/register'
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

// 어떤 실패든 화면은 "불러오기 실패" 하나로 보여 준다 (D-008).
export class LoadFoodDetailError extends Error {}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function foodPath(id: string, tail = ''): string {
  return `${FOODS_PATH}/${encodeURIComponent(id)}${tail}`
}

export async function getFoodDetail(id: string): Promise<FoodDetail> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'detail-error') throw new LoadFoodDetailError('mock error')
    const found = getMockFoodDetail(id)
    if (!found) throw new LoadFoodDetailError('mock not found')
    return found
  }
  try {
    const res = await fetch(foodPath(id))
    if (!res.ok) throw new LoadFoodDetailError(`status ${res.status}`)
    return (await res.json()) as FoodDetail
  } catch (e) {
    throw e instanceof LoadFoodDetailError ? e : new LoadFoodDetailError('network')
  }
}

// 요청을 보내고 Response 를 돌려준다. API 에 닿지 못하면 null.
async function send(path: string, method: string, body?: object): Promise<Response | null> {
  try {
    return await fetch(path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    return null
  }
}

async function patchFood(path: string, body: object): Promise<SaveResult> {
  const res = await send(path, 'PATCH', body)
  if (!res) return { status: 'failed' } // API 에 닿지 못함도 같은 오류로 보인다
  if (res.ok) {
    const data = (await res.json().catch(() => null)) as { status?: string } | null
    return data?.status === 'need_expiry' ? { status: 'need_expiry' } : { status: 'ok' }
  }
  if (res.status === 422) {
    const data = (await res.json().catch(() => null)) as { errors?: FieldErrors } | null
    return { status: 'invalid', fieldErrors: data?.errors ?? {} }
  }
  return { status: 'failed' }
}

async function requestAction(path: string, method: string, body?: object): Promise<ActionResult> {
  const res = await send(path, method, body)
  return res?.ok ? { status: 'ok' } : { status: 'failed' }
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

// 가짜 처리 · 삭제 응답
async function mockRemove(mode: string, id: string): Promise<ActionResult> {
  if (mode === 'save-error') return { status: 'failed' }
  if (mode === 'slow') await wait(2000)
  return removeMockFood(id) ? { status: 'ok' } : { status: 'failed' }
}

export function updateFood(id: string, input: UpdateFoodInput): Promise<SaveResult> {
  if (MOCK_MODE) {
    return mockSave(MOCK_MODE, () => updateMockFood(id, input, MOCK_TODAY), {
      quantity: '수량을 다시 확인해 주세요. (가짜 오류 응답)',
    })
  }
  return patchFood(foodPath(id), input)
}

export function changeFoodStorage(id: string, input: ChangeStorageInput): Promise<SaveResult> {
  if (MOCK_MODE) {
    return mockSave(MOCK_MODE, () => changeMockStorage(id, input, MOCK_TODAY), {
      storage: '보관 방법을 다시 확인해 주세요. (가짜 오류 응답)',
    })
  }
  return patchFood(foodPath(id, '/storage'), input)
}

export function processFood(id: string, status: ProcessStatus): Promise<ActionResult> {
  if (MOCK_MODE) return mockRemove(MOCK_MODE, id)
  return requestAction(foodPath(id, '/process'), 'PATCH', { status })
}

export function deleteFood(id: string): Promise<ActionResult> {
  if (MOCK_MODE) return mockRemove(MOCK_MODE, id)
  return requestAction(foodPath(id), 'DELETE')
}
