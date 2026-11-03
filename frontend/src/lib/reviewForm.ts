// 확인 화면(사진으로 읽은 식품)의 줄 상태와 미리 검사 (D-010, D-108). 알려 주는 용도이고 최종 판단은 API 가 한다.
import type { FormValues } from './registerForm'
import { checkQuantity } from './registerForm'
import type { Storage } from '../types/food'
import type { AnalyzeData, AnalyzedItem } from '../types/photo'
import type { FieldErrors } from '../types/register'
import type { RuleStorageOption } from '../types/rule'

// 이름을 고친 줄이 규칙표에 있는 이름인지 알아내는 단계 (C1 검색)
//  original: AI 가 읽은 이름 그대로 (읽은 보관 정보를 쓴다)
//  checking: 규칙표에서 찾는 중
//  rule:     고친 이름이 규칙표에 있음 (규칙표 값으로 API 가 계산)
//  manual:   고친 이름이 규칙표에 없음 → 기한 입력칸이 열린다 (SCREEN-SPEC 5.4)
//  error:    규칙표를 확인하지 못함
export type NameCheck = 'original' | 'checking' | 'rule' | 'manual' | 'error'

export interface ReviewLine {
  item: AnalyzedItem // AI 가 읽은 줄 (바뀌지 않는다)
  name: string
  quantity: string
  unit: string
  purchaseDate: string
  storage: Storage | null
  expiryDate: string // 이름을 고쳐 규칙표에 없게 된 줄에서만 쓴다
  included: boolean // 처음에는 모두 선택돼 있다 (D-109)
  nameCheck: NameCheck
  ruleOptions?: RuleStorageOption[] // 고친 이름이 규칙표에 있을 때 그 식품의 보관 방법 가능 여부
  errors: FieldErrors
}

// 수량 · 단위는 영수증에서 읽지 못할 수 있어 비어 있고, 사용자가 적어야 한다 (US-019)
export function linesFromAnalysis(data: AnalyzeData): ReviewLine[] {
  return data.items.map((item) => ({
    item,
    name: item.name,
    quantity: '',
    unit: '',
    purchaseDate: item.purchase_date,
    storage: item.recommended_storage, // 권장 보관 방법이 미리 선택된다
    expiryDate: '',
    included: true,
    nameCheck: 'original',
    errors: {},
  }))
}

// 줄의 입력칸 값을 등록 화면 입력 조각(QuantityUnitDateFields)이 쓰는 모양으로
export function valuesOf(line: ReviewLine): FormValues {
  return {
    name: line.name,
    quantity: line.quantity,
    unit: line.unit,
    purchaseDate: line.purchaseDate,
    storage: line.storage,
    expiryMode: 'date',
    expiryDate: line.expiryDate,
    expiryDays: '',
  }
}

// 사용자가 처음과 다르게 고치거나 뺀 것이 있는지 (탭 이동 확인 창 기준, D-083, D-084)
export function isEdited(line: ReviewLine): boolean {
  const fresh = linesFromAnalysis({ analysis_id: null, items: [line.item] })[0]
  return (
    !line.included ||
    line.name !== fresh.name ||
    line.quantity !== '' ||
    line.unit !== '' ||
    line.purchaseDate !== fresh.purchaseDate ||
    line.storage !== fresh.storage ||
    line.expiryDate !== ''
  )
}

// 남긴 줄의 입력 검사 (이름 · 수량 · 단위 필수, 수량은 0보다 큰 숫자). 직접 등록과 같은 규칙이다 (D-108)
export function checkLine(line: ReviewLine): FieldErrors {
  const errors: FieldErrors = {}
  if (line.name.trim() === '') errors.name = '이름을 적어 주세요.'
  const quantity = checkQuantity(line.quantity)
  if (quantity) errors.quantity = quantity
  if (line.unit.trim() === '') errors.unit = '단위를 적어 주세요.'
  if (line.purchaseDate === '') errors.purchase_date = '구매일을 골라 주세요.'
  if (line.storage === null) errors.storage = '보관 방법을 골라 주세요.'
  if (line.nameCheck === 'manual' && line.expiryDate === '') errors.expiry = '기한을 골라 주세요.'
  return errors
}
