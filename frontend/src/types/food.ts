// [임시 계약] 홈 목록 응답 모양. 백엔드 담당과 합의 전 제안이다.
// 칸 이름·값이 바뀌면 이 파일(과 api/foods.ts, lib/statusColor.ts, mocks)만 고친다.

export type Storage = 'room' | 'fridge' | 'freezer' // D-032

// 상태 판정은 API 가 한다 (D-009). 값 이름은 제안.
export type ExpiryLevel = 'relaxed' | 'caution' | 'urgent' | 'expired' // 여유 · 주의 · 임박 · 지남

export interface Food {
  id: string // UUID (D-033)
  name: string
  storage: Storage
  purchase_date: string // YYYY-MM-DD (D-031)
  expiry_date: string // YYYY-MM-DD
  expiry_level: ExpiryLevel // 처리 상태 `status`(D-032)와 겹치지 않게 지은 이름
  show_on_calendar: boolean // 지난 지 4일 이상이면 false (D-014). 목록에는 남는다
}

export interface FoodListResponse {
  today: string // YYYY-MM-DD. 오늘 세로선과 이번 주 기준 (D-021)
  foods: Food[] // API 가 정렬해서 준다 (D-015). 화면은 순서를 바꾸지 않는다
}
