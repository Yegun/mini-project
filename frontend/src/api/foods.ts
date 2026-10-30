// [임시 계약] 홈 목록을 가져오는 곳. 경로는 백엔드 담당 확인 전까지 임시다.
// 개발 중 가짜 데이터: frontend/.env.local (git 에 올리지 않는다)
//   VITE_USE_MOCK=1      식품 있음
//   VITE_USE_MOCK=empty  식품 없음
//   VITE_USE_MOCK=error  불러오기 실패
//   VITE_USE_MOCK=slow   2초 뒤 식품 있음 (불러오는 중 확인용)
import type { FoodListResponse } from '../types/food'
import foodsMock from '../mocks/foods.json'
import foodsEmptyMock from '../mocks/foods.empty.json'

const FOODS_PATH = '/api/foods'
const MOCK_MODE = import.meta.env.VITE_USE_MOCK

// 어떤 실패든 화면은 "불러오기 실패" 하나로 보여 준다 (API-SPEC 4절).
export class LoadFoodsError extends Error {}

async function getMockFoods(mode: string): Promise<FoodListResponse> {
  if (mode === 'error') throw new LoadFoodsError('mock error')
  if (mode === 'empty') return foodsEmptyMock as FoodListResponse
  if (mode === 'slow') await new Promise((resolve) => setTimeout(resolve, 2000))
  return foodsMock as FoodListResponse
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
