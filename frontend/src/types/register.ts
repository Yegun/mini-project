// [임시 계약] 식품 등록 요청·결과 모양 (A3, A4). 백엔드 담당과 합의 전 제안이다.
// 바뀌면 이 파일과 api/foods.ts, mocks/ 만 고친다.
import type { Storage } from './food'

// 규칙표에서 골라 등록 (A3). 기한은 API 가 계산한다.
export interface RuleRegisterInput {
  rule_id: string
  name: string
  storage: Storage
  quantity: number // 0보다 큰 숫자, 소수 둘째 자리까지 (D-027)
  unit: string
  purchase_date: string // YYYY-MM-DD
}

// 직접 등록 (A4). 기한은 날짜 또는 며칠 뒤 중 하나만 보낸다. "며칠 뒤"의 계산은 API 가 한다 (D-002, D-016).
export interface ManualRegisterInput {
  name: string
  storage: Storage
  quantity: number
  unit: string
  purchase_date: string
  expiry_date?: string // YYYY-MM-DD
  expiry_days?: number // 구매일 + N일
}

// 입력칸 이름. 입력 오류 응답이 "어느 칸 문제인지" 알려 줄 때 쓴다.
export type FieldName = 'name' | 'storage' | 'quantity' | 'unit' | 'purchase_date' | 'expiry'
export type FieldErrors = Partial<Record<FieldName, string>>

export type RegisterResult =
  | { status: 'ok' }
  | { status: 'invalid'; fieldErrors: FieldErrors } // API 가 입력 규칙 위반으로 거절 (칸 옆 안내)
  | { status: 'failed' } // 저장 실패 · API 에 닿지 못함 (화면 위 오류 알림)
