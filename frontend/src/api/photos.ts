// 사진 읽기(F1). 기준은 API-SPEC 2-5. 사진은 저장하지 않고 읽는 동안만 쓴다 (D-102).
// 개발 중 가짜 응답: VITE_USE_MOCK 이 켜져 있으면 서버에 보내지 않는다.
//   (기본)                  식품 3개 (규칙표에 있는 것 1개, AI 가 알려 준 것 2개)
//   VITE_USE_MOCK=empty     식품을 하나도 못 읽음 (items 가 비고 analysis_id 가 null)
//   VITE_USE_MOCK=ai-error  AI 가 응답하지 못함 (502)
//   VITE_USE_MOCK=slow      2초 걸림 (버튼 잠금 확인용)
import type { AnalyzeData, AnalyzeResult } from '../types/photo'
import { send } from './http'

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

interface ApiErrorBody {
  reason?: string
  message?: string
}

function mockData(): AnalyzeData {
  const today = new Date().toISOString().slice(0, 10) // 가짜 응답이라 화면 시계를 쓴다. 실제로는 API 가 정한다
  return {
    analysis_id: 'mock-analysis',
    items: [
      {
        item_no: 0,
        name: '우유',
        recommended_storage: 'fridge',
        storages: [
          { storage: 'room', allowed: false, max_days: null },
          { storage: 'fridge', allowed: true, max_days: 7 },
          { storage: 'freezer', allowed: true, max_days: 30 },
        ],
        purchase_date: today,
        from_rule: true,
      },
      {
        item_no: 1,
        name: '닭가슴살',
        recommended_storage: 'fridge',
        storages: [
          { storage: 'room', allowed: false, max_days: null },
          { storage: 'fridge', allowed: true, max_days: 3 },
          { storage: 'freezer', allowed: true, max_days: 90 },
        ],
        purchase_date: today,
        from_rule: false,
      },
      {
        item_no: 2,
        name: '김치',
        recommended_storage: 'fridge',
        storages: [
          { storage: 'room', allowed: true, max_days: 2 },
          { storage: 'fridge', allowed: true, max_days: 60 },
          { storage: 'freezer', allowed: false, max_days: null },
        ],
        purchase_date: today,
        from_rule: false,
      },
    ],
  }
}

export async function analyzePhoto(file: File): Promise<AnalyzeResult> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'slow') await wait(2000)
    if (MOCK_MODE === 'ai-error') return { status: 'failed', message: 'AI 가 응답하지 못했어요. 다시 시도해 주세요.' }
    if (MOCK_MODE === 'empty') return { status: 'ok', data: { analysis_id: null, items: [] } }
    return { status: 'ok', data: mockData() }
  }
  const form = new FormData()
  form.append('image', file) // 사진은 image 칸에 파일로 보낸다 (API-SPEC 5절 23번)
  const res = await send('/api/photos/analyze', 'POST', form)
  if (!res) return { status: 'failed' }
  if (res.ok) {
    try {
      return { status: 'ok', data: (await res.json()) as AnalyzeData }
    } catch {
      return { status: 'failed' }
    }
  }
  const body = (await res.json().catch(() => null)) as ApiErrorBody | null
  const message = body?.message || undefined
  if (res.status === 422 && body?.reason === 'photo_invalid') return { status: 'invalid', message }
  return { status: 'failed', message }
}
