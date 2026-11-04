// 식품 등록 요청·결과 모양 (A2 규칙표, A3 직접). 기준은 API-SPEC 2-3.
// 바뀌면 이 파일과 api/foods.ts, mocks/ 만 고친다.
import type { Category, Storage } from './food'

// 규칙표에서 골라 등록 (A2). 기한은 API 가 계산한다.
export interface RuleRegisterInput {
  name: string
  storage: Storage
  quantity: number // 0보다 큰 숫자, 소수 둘째 자리까지 (D-027)
  unit: string
  purchase_date: string // YYYY-MM-DD
}

// 직접 등록 (A3). 기한은 날짜 또는 며칠 뒤 중 하나만 보낸다. "며칠 뒤"의 계산은 API 가 한다 (D-002, D-016).
export interface ManualRegisterInput {
  name: string
  storage: Storage
  quantity: number
  unit: string
  purchase_date: string
  expiry_date?: string // YYYY-MM-DD
  expiry_in_days?: number // 구매일 + N일
  category?: Category // 식품 종류. API-SPEC 에서는 필수이고, 등록 화면에 종류 고르기를 넣을 때(이슈 6) 필수로 바꾼다
}

// 입력칸 이름. 입력 오류 응답이 "어느 칸 문제인지" 알려 줄 때 쓴다.
export type FieldName = 'name' | 'storage' | 'quantity' | 'unit' | 'purchase_date' | 'expiry'
export type FieldErrors = Partial<Record<FieldName, string>>

export type RegisterResult =
  | { status: 'ok' }
  | { status: 'invalid'; fieldErrors: FieldErrors } // API 가 입력 규칙 위반으로 거절 (칸 옆 안내)
  | { status: 'failed'; message?: string } // 화면 위 오류 알림. message 는 API 문구, 없으면 화면 기본 문구
