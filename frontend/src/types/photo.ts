// 사진 읽기(F1)의 응답. 기준은 API-SPEC 2-5.
import type { Storage } from './food'

export interface StorageInfo {
  storage: Storage
  allowed: boolean // false 면 "불가". 흐리게 보이고 고를 수 없다 (D-005)
  max_days: number | null // 이 방법으로 보관할 수 있는 최대 일수. 불가이면 null
}

export interface AnalyzedItem {
  item_no: number // 이 결과 안에서 줄을 구분하는 번호 (0부터)
  name: string
  recommended_storage: Storage // 확인 화면이 미리 선택해 둔다
  storages: StorageInfo[]
  purchase_date: string // 영수증에서 읽은 날짜, 못 읽으면 오늘 (D-106, D-107)
  from_rule: boolean // 규칙표 값이면 true, AI 가 알려 준 값이면 false
}

export interface AnalyzeData {
  analysis_id: string | null // 식품이 하나도 없으면 null (실패가 아니다)
  items: AnalyzedItem[] // 냉장 · 냉동 보관이 필요한 식품만 (D-103)
}

export type AnalyzeResult =
  | { status: 'ok'; data: AnalyzeData }
  | { status: 'invalid'; message?: string } // 사진 규칙 위반 (photo_invalid). 올라가지 않는다
  | { status: 'failed'; message?: string } // AI 가 응답하지 못함 · 서버 오류. 올린 사진은 그대로 남아 다시 시도한다
