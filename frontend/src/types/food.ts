// 식품 한 건과 홈 목록(A1) 응답 모양. 기준은 API-SPEC 0-1, A1.
// 칸 이름·값이 바뀌면 이 파일(과 api/foods.ts, lib/statusColor.ts, mocks)만 고친다.

export type Storage = 'room' | 'fridge' | 'freezer' // D-032

// 화면에 보이는 보관 방법 이름 (D-032 값 ↔ 글자)
export const STORAGE_LABEL: Record<Storage, string> = {
  room: '상온',
  fridge: '냉장',
  freezer: '냉동',
}

// 상태 판정은 API 가 한다 (D-009).
export type ExpiryStatus = 'fresh' | 'warning' | 'soon' | 'expired' // 여유 · 주의 · 임박 · 지남

export type FoodSource = 'rule' | 'manual' // 규칙표 등록 / 직접 등록 (D-029)
export type FoodStatus = 'none' | 'eaten' | 'discarded' // 처리 상태 (D-032)

// 홈 목록(A1)과 상세(A4)는 처리 상태가 none 인 식품만 주므로 계산 칸 세 개는 늘 값이 있다.
// 처리된 식품은 계산 칸이 null 이고, 기록 화면에서만 다룬다 (API-SPEC 0-1).
export interface Food {
  id: string // UUID (D-033)
  name: string
  storage: Storage
  quantity: number
  unit: string
  purchase_date: string // YYYY-MM-DD (D-031)
  expiry_date: string // YYYY-MM-DD
  source: FoodSource
  status: FoodStatus
  processed_date: string | null // 처리하지 않았으면 null
  expiry_status: ExpiryStatus // 처리 상태 `status`(D-032)와 겹치지 않게 지은 이름
  days_left: number // 기한 − 오늘. 지났으면 음수 (−1 = 하루 지남)
  show_on_calendar: boolean // 지난 지 4일 이상이면 false (D-014). 목록에는 남는다
}

export interface FoodListResponse {
  today: string // YYYY-MM-DD. 오늘 세로선과 이번 주 기준 (D-021)
  items: Food[] // API 가 정렬해서 준다 (D-015). 화면은 순서를 바꾸지 않는다
}
