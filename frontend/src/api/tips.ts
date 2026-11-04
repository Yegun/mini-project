// 오늘의 일반 조언(J1) — 확인 중 화면에 곁들이는 조언. 기준은 API-SPEC 2-10, D-156 ~ D-158.
// 이 요청이 실패해도 사용자에게 오류를 보이지 않는다. 조언 칸만 비고 사진 읽기 · 음식 추천은 계속된다 (API-SPEC 5절 53번).
// 개발 중 가짜 응답: VITE_USE_MOCK 이 켜져 있으면 서버에 보내지 않는다.
//   (기본)                  AI 가 만든 조언과 미리 써 둔 조언이 섞여 있음
//   VITE_USE_MOCK=tips-error  조언을 읽지 못함 (조언 칸이 빈다)
import type { TipsData } from '../types/tips'
import { send } from './http'

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

function mockTips(): TipsData {
  return {
    tip_date: new Date().toISOString().slice(0, 10), // 가짜 응답이라 화면 시계를 쓴다. 실제로는 API 가 정한다
    tips: [
      { text: '냉장고 문 쪽은 온도가 자주 변해요. 우유와 달걀은 안쪽 선반에 두세요.', from_ai: true },
      { text: '냉장고는 70% 정도만 채우면 찬 공기가 잘 돌아요.', from_ai: true },
      { text: '남은 음식은 식힌 뒤 작은 통에 나눠 담으면 더 오래 신선해요.', from_ai: true },
      { text: '생고기와 생선은 아래 칸에 두면 다른 식품에 국물이 떨어지지 않아요.', from_ai: false },
      { text: '장을 보고 오면 먼저 먹을 식품을 앞쪽으로 옮겨 두세요.', from_ai: false },
    ],
  }
}

// 읽지 못하면 null. 호출하는 쪽은 조언 칸을 비운다.
export async function getTips(): Promise<TipsData | null> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'tips-error') return null
    return mockTips()
  }
  const res = await send('/api/tips')
  if (!res || !res.ok) return null
  try {
    const data = (await res.json()) as TipsData
    return Array.isArray(data.tips) ? data : null
  } catch {
    return null
  }
}
