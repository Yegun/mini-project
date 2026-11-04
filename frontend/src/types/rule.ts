// 규칙표 검색(C1) 응답 모양. 백엔드 응답은 ApiRule, 화면이 쓰는 모양은 RuleCandidate 이고 api/rules.ts 가 바꿔 준다.
// 화면은 기한을 계산하지 않으므로 보관 기간(max_days)은 받지 않는다 (D-016).
import type { Category, Storage } from './food'

export interface RuleStorageOption {
  storage: Storage
  allowed: boolean // false 면 "불가". 흐리게 보이고 고를 수 없다 (D-005)
}

// 백엔드가 주는 규칙표 후보 한 건. "불가"인 보관 방법만 알려 준다 (API-SPEC C1).
export interface ApiRule {
  name: string
  default_storage: Storage
  disallowed_storages: Storage[]
  category: Category
}

export interface RuleCandidate {
  name: string // 규칙표 이름은 겹치지 않아 목록의 key 로도 쓴다 (D-035)
  default_storage: Storage // 등록 화면에서 미리 선택되는 보관 방법
  category?: Category // 식품 종류. 가짜 데이터에는 없다
  storages: RuleStorageOption[]
}

// 화면이 쓰는 검색 결과 (api/rules.ts 가 백엔드의 items 를 바꿔 담는다)
export interface RuleSearchResponse {
  rules: RuleCandidate[] // 없으면 빈 목록 (성공)
}

// 등록 화면의 검색 진행 상태 (화면 안에서만 쓴다)
export type SearchState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'done'; q: string; rules: RuleCandidate[] }
