// 기록 조언(I1) — 기록 화면의 '조언 받기'. 기준은 API-SPEC 2-9, D-159 ~ D-163.
// 저장하지 않고, 버튼을 눌렀을 때만 부른다.
// 개발 중 가짜 응답: VITE_USE_MOCK 이 켜져 있으면 서버에 보내지 않는다.
//   (기본)                 조언 글 3개 (잠깐 기다린 뒤)
//   VITE_USE_MOCK=empty     식품도 기록도 없음 (조언할 내용 없음)
//   VITE_USE_MOCK=advice-error  AI 가 응답하지 못함
import { send } from './http'

export type AdviceResult =
  | { status: 'ok'; advice: string[] }
  | { status: 'no_data' } // 식품도 기록도 없음 (실패가 아니다)
  | { status: 'failed'; message?: string }

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

export const ADVICE_FAILED = 'AI 가 응답하지 못했어요. 다시 시도해 주세요.'

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function getAdvice(): Promise<AdviceResult> {
  if (MOCK_MODE) {
    await wait(1200)
    if (MOCK_MODE === 'advice-error') return { status: 'failed' }
    if (MOCK_MODE === 'empty') return { status: 'no_data' }
    return {
      status: 'ok',
      advice: [
        '고등어처럼 기한이 가까운 생선은 오늘 먼저 드시는 게 좋아요.',
        '최근에 버린 식품이 있어요. 한 번에 적게 사고, 먼저 산 식품을 앞쪽에 두어 보세요.',
        '냉장 식품이 많은 편이에요. 오래 두는 식품은 냉동으로 옮기면 더 오래 먹을 수 있어요.',
      ],
    }
  }
  const res = await send('/api/advice', 'POST')
  if (!res) return { status: 'failed' }
  if (!res.ok) {
    const data = (await res.json().catch(() => null)) as { message?: string } | null
    return { status: 'failed', message: data?.message }
  }
  try {
    const data = (await res.json()) as { advice?: unknown; reason?: string | null }
    const advice = Array.isArray(data.advice) ? data.advice.filter((t): t is string => typeof t === 'string') : []
    if (advice.length > 0) return { status: 'ok', advice }
    return data.reason === 'no_data' ? { status: 'no_data' } : { status: 'failed' }
  } catch {
    return { status: 'failed' }
  }
}
