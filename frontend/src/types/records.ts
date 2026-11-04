// 기록 화면의 응답 모양: 기록 숫자(D1) · 처리한 식품 목록(D2). 기준은 API-SPEC 2-4.
// 숫자는 API 가 세어 주고 화면은 보여 주기만 한다 (D-009).
import type { Category, ExpiryStatus, Storage } from './food'

export interface RecordSummary {
  eaten: { year: number; month: number } // 처리한 날짜가 올해 / 이번 달인 다 먹음 수
  discarded: { year: number; month: number } // 같은 기준의 버림 수
  food_kinds: number // 지금 있는 식품의 이름 종류 수 (같은 이름은 한 종류)
  by_storage: Record<Storage, number>
  // 식품 종류별 수. 서버(API-SPEC D1)에 아직 없는 칸이라 없을 수 있다. 있으면 기록 화면에 "식품 종류별" 줄이 보이고, 없으면 줄이 보이지 않는다.
  by_category?: Record<Category, number>
  by_status: Record<ExpiryStatus, number> // 달력에 안 보이는 지난 지 4일 이상도 expired 에 센다
}

// 처리한 식품 한 줄 (D2)
export interface ProcessedFood {
  id: string
  name: string
  quantity: number
  unit: string
  processed_date: string // YYYY-MM-DD
  // 식품 종류. 서버(API-SPEC D2)에 아직 없는 칸이라 없을 수 있다. 있으면 처리한 식품 카드에 종류 그림이 보이고, 없으면 먹은 식품 · 버린 식품 기본 그림이 보인다.
  category?: Category | null
}

export interface ProcessedFoods {
  eaten: ProcessedFood[] // 최근 처리한 순 → 이름순 (API 가 정렬해서 준다)
  discarded: ProcessedFood[]
}

// 기록 화면은 D1 과 D2 를 함께 불러 한 번에 보여 준다
export interface RecordsData {
  summary: RecordSummary
  foods: ProcessedFoods
}
