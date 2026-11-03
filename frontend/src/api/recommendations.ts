// 음식 추천(G1). 기준은 API-SPEC 2-6. 추천 결과는 저장하지 않는다 (D-122).
// 개발 중 가짜 응답: VITE_USE_MOCK 이 켜져 있으면 서버에 보내지 않는다.
//   (기본)             음식 3개. 재료 중 일부는 "없는 재료"
//   VITE_USE_MOCK=empty     가진 식품이 없음 (reason = no_foods)
//   VITE_USE_MOCK=no-match  맞는 음식이 없음 (reason = no_match)
//   VITE_USE_MOCK=ai-error  AI 가 응답하지 못함 (502)
//   VITE_USE_MOCK=slow      2초 걸림 (버튼 잠금 확인용)
import type { Dish, RecommendData, RecommendRequest, RecommendResult } from '../types/recommend'
import { CUISINE_LABEL, MEAL_LABEL } from '../types/recommend'
import { readMessage } from './errors'
import { send } from './http'

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// 가짜 음식: 고른 끼니 · 음식 종류가 이름에 들어가 다시 추천받았을 때 달라진 것을 알 수 있다
function mockDishes(req: RecommendRequest): Dish[] {
  const kind = req.cuisine === 'custom' ? (req.cuisineText ?? '').trim() : CUISINE_LABEL[req.cuisine]
  const meal = MEAL_LABEL[req.meal]
  return [
    {
      name: `${meal} ${kind} 달걀볶음밥`,
      ingredients: [
        { name: '달걀', have: true },
        { name: '대파', have: true },
        { name: '참기름', have: false },
      ],
    },
    {
      name: `${meal} ${kind} 두부조림`,
      ingredients: [
        { name: '두부', have: true },
        { name: '양파', have: true },
        { name: '간장', have: false },
        { name: '고춧가루', have: false },
      ],
    },
    {
      name: `${meal} ${kind} 감자채볶음`,
      ingredients: [
        { name: '감자', have: true },
        { name: '당근', have: true },
      ],
    },
  ]
}

export async function recommend(req: RecommendRequest): Promise<RecommendResult> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'slow') await wait(2000)
    if (MOCK_MODE === 'ai-error') return { status: 'failed', message: 'AI 가 응답하지 못했어요. 다시 시도해 주세요.' }
    if (MOCK_MODE === 'empty') return { status: 'ok', data: { dishes: [], reason: 'no_foods' } }
    if (MOCK_MODE === 'no-match') return { status: 'ok', data: { dishes: [], reason: 'no_match' } }
    return { status: 'ok', data: { dishes: mockDishes(req), reason: null } }
  }
  const res = await send('/api/recommendations', 'POST', {
    meal: req.meal,
    cuisine: req.cuisine,
    ...(req.cuisine === 'custom' ? { cuisine_text: req.cuisineText?.trim() } : {}),
  })
  if (!res) return { status: 'failed' }
  if (!res.ok) return { status: 'failed', message: await readMessage(res) }
  try {
    return { status: 'ok', data: (await res.json()) as RecommendData }
  } catch {
    return { status: 'failed' }
  }
}
