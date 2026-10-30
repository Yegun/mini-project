// [임시 계약] 식품 상세(A5), 정보 수정(A6), 보관 방법 변경(A7), 처리(A8), 삭제(A9) 요청·응답 모양.
// 백엔드 담당과 합의 전 제안이다. 칸 이름·값이 바뀌면 이 파일과 api/foodDetail.ts, mocks/ 만 고친다.
import type { ExpiryLevel, Storage } from './food'
import type { FieldErrors } from './register'
import type { RuleStorageOption } from './rule'

export type FoodSource = 'rule' | 'manual' // 규칙표 등록 / 직접 등록 (D-029)

// A5 응답. 상태(expiry_level)는 API 가 판정한 값이고 화면은 색만 입힌다 (D-009).
export interface FoodDetail {
  id: string
  name: string
  storage: Storage
  quantity: number
  unit: string
  purchase_date: string // YYYY-MM-DD
  expiry_date: string // YYYY-MM-DD
  expiry_level: ExpiryLevel
  source: FoodSource
  storages: RuleStorageOption[] // 방법별 가능 여부. 직접 등록은 모두 true (D-005)
}

// A6 요청: 바뀐 칸만 보낸다. expiry_date 는 "기한 다시 적기"로 적었을 때만 (D-023, ARCH 3절)
export interface UpdateFoodInput {
  name?: string
  quantity?: number
  unit?: string
  purchase_date?: string
  expiry_date?: string
}

// A7 요청. expiry_date 는 직접 등록 식품이 "기한 다시 적기"로 적었을 때만 (D-023)
export interface ChangeStorageInput {
  storage: Storage
  expiry_date?: string
}

// A8 요청 (D-013)
export type ProcessStatus = 'eaten' | 'discarded'

// 수정·보관 방법 변경 결과
export type SaveResult =
  | { status: 'ok' }
  | { status: 'need_expiry' } // 실패가 아닌 정해진 응답: 기한을 다시 적어야 함 (ARCH 3절)
  | { status: 'invalid'; fieldErrors: FieldErrors } // 입력 규칙 위반 (칸 옆 안내)
  | { status: 'failed' } // 저장 실패 · API 에 닿지 못함 (화면 위 오류 알림)

// 처리·삭제 결과
export type ActionResult = { status: 'ok' } | { status: 'failed' }
