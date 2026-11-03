// 음식 추천(G1)의 요청 · 응답. 기준은 API-SPEC 2-6.
export type Meal = 'breakfast' | 'lunch' | 'dinner'
export type Cuisine = 'western' | 'korean' | 'japanese' | 'chinese' | 'simple' | 'custom'

export const MEALS: Meal[] = ['breakfast', 'lunch', 'dinner']
export const MEAL_LABEL: Record<Meal, string> = { breakfast: '아침', lunch: '점심', dinner: '저녁' }

export const CUISINES: Cuisine[] = ['western', 'korean', 'japanese', 'chinese', 'simple', 'custom']
export const CUISINE_LABEL: Record<Cuisine, string> = {
  western: '양식',
  korean: '한식',
  japanese: '일식',
  chinese: '중식',
  simple: '간단히',
  custom: '직접 입력',
}

// '직접 입력'으로 적는 글은 30자까지 (API-SPEC 5절 22번)
export const CUSTOM_CUISINE_MAX = 30

export interface Ingredient {
  name: string
  have: boolean // 내 식품이면 true, 지금 없는 재료면 false (D-115)
}

export interface Dish {
  name: string
  ingredients: Ingredient[] // 이름과 재료만 있고 만드는 법은 없다 (D-121)
}

export interface RecommendData {
  dishes: Dish[] // 최대 3개 (D-113)
  reason: 'no_foods' | 'no_match' | null // dishes 가 비었을 때만. 가진 식품이 없음 / 맞는 음식이 없음
}

export interface RecommendRequest {
  meal: Meal
  cuisine: Cuisine
  cuisineText?: string // cuisine 이 custom 일 때만
}

export type RecommendResult =
  | { status: 'ok'; data: RecommendData }
  | { status: 'failed'; message?: string } // AI 가 응답하지 못함 · 서버 오류. 고른 것은 그대로 남아 다시 시도한다
