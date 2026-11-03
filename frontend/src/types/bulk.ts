// 한꺼번에 등록(F2)의 요청 · 결과. 기준은 API-SPEC 2-5.
import type { Storage } from './food'
import type { FieldName } from './register'

// 확인 화면에서 남긴 줄 하나. 이름을 고쳐 규칙표에 없게 된 줄만 expiry_date 를 함께 보낸다 (ARCH 9절 25번)
export interface BulkItemInput {
  item_no: number
  name: string
  quantity: number
  unit: string
  purchase_date: string // YYYY-MM-DD
  storage: Storage
  expiry_date?: string // YYYY-MM-DD
}

export interface BulkInput {
  analysis_id: string
  items: BulkItemInput[]
}

export type BulkResult =
  | { status: 'ok' } // 201. 전부 등록됨
  | { status: 'expired'; message?: string } // analysis_expired. 사진을 다시 올려야 한다
  | { status: 'invalid'; index: number; field: FieldName | null; message?: string } // 보낸 줄 목록에서 index 번째 줄의 입력 오류 (첫 오류 하나만)
  | { status: 'failed'; message?: string } // 전부 취소됨. 확인하던 목록은 그대로 남아 다시 시도할 수 있다 (D-110)
