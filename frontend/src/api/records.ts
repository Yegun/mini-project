// 기록 숫자(D1) · 처리한 식품 목록(D2) · 홈으로 되돌리기(D3). 기준은 API-SPEC 2-4.
// 개발 중 가짜 데이터: VITE_USE_MOCK 이 켜져 있으면 mocks/createdFoods.ts 의 지금 상태로 센다.
//   상세에서 다 먹음 · 버림을 하면 기록에 쌓이고, 되돌리면 홈에 다시 나온다 (새로고침하면 처음으로).
//   VITE_USE_MOCK=empty          식품 없음 → 기록이 모두 0
//   VITE_USE_MOCK=records-error  기록 불러오기 실패
//   VITE_USE_MOCK=save-error     되돌리기 실패
//   VITE_USE_MOCK=slow           2초 걸림
import type { FoodListResponse } from '../types/food'
import type { ActionResult } from '../types/foodDetail'
import type { ProcessedFoods, RecordsData, RecordSummary } from '../types/records'
import { readMessage } from './errors'
import { send } from './http'
import { foodsEmptyMock, foodsMock } from '../mocks/foodsMock'
import { getMockRecords, restoreMockFood } from '../mocks/createdFoods'

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// 어떤 실패든 화면은 "불러오기 실패" 하나로 보여 준다. apiMessage 는 API 문구 (없으면 화면 기본 문구).
export class LoadRecordsError extends Error {
  readonly apiMessage?: string
  constructor(reason: string, apiMessage?: string) {
    super(reason)
    this.apiMessage = apiMessage
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await send(path)
  if (!res) throw new LoadRecordsError('network')
  if (!res.ok) throw new LoadRecordsError(`status ${res.status}`, await readMessage(res))
  try {
    return (await res.json()) as T
  } catch {
    throw new LoadRecordsError('bad response')
  }
}

// D1 과 D2 를 함께 부른다. 하나라도 실패하면 기록 화면 전체가 "불러오지 못함"이다 (API-SPEC 1절)
export async function getRecords(): Promise<RecordsData> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'records-error') throw new LoadRecordsError('mock error')
    if (MOCK_MODE === 'slow') await wait(2000)
    const base = (MOCK_MODE === 'empty' ? foodsEmptyMock : foodsMock) as FoodListResponse
    return getMockRecords(base)
  }
  const [summary, foods] = await Promise.all([
    getJson<RecordSummary>('/api/records/summary'),
    getJson<ProcessedFoods>('/api/records/foods'),
  ])
  return { summary, foods }
}

// 홈으로 되돌리기. 이름 · 수량 · 단위 · 구매일 · 보관 방법 · 기한은 처리하기 전 그대로다 (D-076)
export async function restoreFood(id: string): Promise<ActionResult> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'save-error') return { status: 'failed' }
    if (MOCK_MODE === 'slow') await wait(2000)
    return restoreMockFood(id) ? { status: 'ok' } : { status: 'failed', message: '찾을 수 없는 식품이에요.' }
  }
  const res = await send(`/api/foods/${encodeURIComponent(id)}/restore`, 'PATCH')
  if (res?.ok) return { status: 'ok' }
  return { status: 'failed', message: await readMessage(res) }
}
