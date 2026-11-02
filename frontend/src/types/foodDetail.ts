// 식품 상세(A4), 정보 수정(A5), 보관 방법 변경(A6), 처리(A7), 삭제(A8) 요청·결과 모양. 기준은 API-SPEC 2-3.
// 칸 이름·값이 바뀌면 이 파일과 api/foodDetail.ts, mocks/ 만 고친다.
import type { Food, Storage } from './food'
import type { FieldErrors } from './register'
import type { RuleStorageOption } from './rule'

export type { FoodSource } from './food'

// A4 응답(식품 한 건) + 화면이 채우는 보관 방법별 가능 여부.
// 상태(expiry_status)는 API 가 판정한 값이고 화면은 색만 입힌다 (D-009).
export interface FoodDetail extends Food {
  storages: RuleStorageOption[] // 방법별 가능 여부. 직접 등록은 모두 true (D-005)
}

// A5 요청: 바뀐 칸만 보낸다. expiry_date 는 "기한 다시 적기"로 적었을 때만 (D-023, ARCH 3절)
export interface UpdateFoodInput {
  name?: string
  quantity?: number
  unit?: string
  purchase_date?: string
  expiry_date?: string
}

// A6 요청. expiry_date 는 직접 등록 식품이 "기한 다시 적기"로 적었을 때만 (D-023)
export interface ChangeStorageInput {
  storage: Storage
  expiry_date?: string
}

// A7 요청 (D-013)
export type ProcessStatus = 'eaten' | 'discarded'

// 수정·보관 방법 변경 결과
export type SaveResult =
  | { status: 'ok' }
  | { status: 'need_expiry' } // 실패가 아닌 정해진 응답: 기한을 다시 적어야 함 (ARCH 3절)
  | { status: 'invalid'; fieldErrors: FieldErrors } // 입력 규칙 위반 (칸 옆 안내)
  | { status: 'failed'; message?: string } // 화면 위 오류 알림. message 는 API 문구, 없으면 화면 기본 문구

// 처리·삭제 결과
export type ActionResult = { status: 'ok' } | { status: 'failed'; message?: string }
