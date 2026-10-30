// [임시 계약] 규칙표 검색(A2) 응답 모양. 백엔드 담당과 합의 전 제안이다.
// 화면은 기한을 계산하지 않으므로 보관 기간(max_days)은 받지 않는다 (D-016).
import type { Storage } from './food'

export interface RuleStorageOption {
  storage: Storage
  allowed: boolean // false 면 "불가". 흐리게 보이고 고를 수 없다 (D-005)
}

export interface RuleCandidate {
  id: string
  name: string
  default_storage: Storage // 등록 화면에서 미리 선택되는 보관 방법
  storages: RuleStorageOption[]
}

export interface RuleSearchResponse {
  rules: RuleCandidate[] // 없으면 빈 목록 (성공)
}

// 등록 화면의 검색 진행 상태 (화면 안에서만 쓴다)
export type SearchState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'done'; q: string; rules: RuleCandidate[] }
