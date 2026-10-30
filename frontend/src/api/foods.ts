// [임시 계약] 홈 목록을 가져오는 곳. 경로는 백엔드 담당 확인 전까지 임시다.
// 개발 중 가짜 데이터: frontend/.env.local 에 VITE_USE_MOCK=1 (git 에 올리지 않는다)
import type { FoodListResponse } from '../types/food'
import foodsMock from '../mocks/foods.json'

const FOODS_PATH = '/api/foods'
const USE_MOCK = import.meta.env.VITE_USE_MOCK === '1'

// 어떤 실패든 화면은 "불러오기 실패" 하나로 보여 준다 (API-SPEC 4절).
export class LoadFoodsError extends Error {}

export async function getFoods(): Promise<FoodListResponse> {
  if (USE_MOCK) {
    return foodsMock as FoodListResponse
  }
  try {
    const res = await fetch(FOODS_PATH)
    if (!res.ok) throw new LoadFoodsError(`status ${res.status}`)
    return (await res.json()) as FoodListResponse
  } catch (e) {
    throw e instanceof LoadFoodsError ? e : new LoadFoodsError('network')
  }
}
