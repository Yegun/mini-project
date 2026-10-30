// 등록 화면의 미리 검사 (D-010). 알려 주는 용도이고 최종 판단은 API 가 한다.
// 날짜가 아닌 것만 본다. 기한이 과거인지, 구매일보다 앞인지는 API 가 막는다 (D-016).
// 안내 문구는 쉬운 말의 임시 문구다 (OQ-03).
import type { Storage } from '../types/food'
import type { FieldErrors } from '../types/register'

export type ExpiryMode = 'date' | 'days'

// 입력칸 값은 모두 글자로 들고 있다가, 검사를 통과하면 숫자로 바꿔 보낸다.
export interface FormValues {
  name: string
  quantity: string
  unit: string
  purchaseDate: string // YYYY-MM-DD
  storage: Storage | null
  expiryMode: ExpiryMode
  expiryDate: string // YYYY-MM-DD
  expiryDays: string
}

export function emptyValues(today: string): FormValues {
  return {
    name: '',
    quantity: '',
    unit: '',
    purchaseDate: today, // 기본은 오늘 (US-001). 오늘은 API 가 준 값 (D-021)
    storage: null,
    expiryMode: 'date',
    expiryDate: '',
    expiryDays: '',
  }
}

// 0보다 큰 숫자, 소수 둘째 자리까지 (V-02, D-027)
function checkQuantity(raw: string): string | undefined {
  const text = raw.trim()
  if (text === '') return '수량을 적어 주세요.'
  if (!/^\d+(\.\d+)?$/.test(text)) return '수량은 숫자로 적어 주세요.'
  if (Number(text) <= 0) return '수량은 0보다 커야 해요.'
  if (!/^\d+(\.\d{1,2})?$/.test(text)) return '수량은 소수 둘째 자리까지만 적을 수 있어요.'
  return undefined
}

function checkCommon(v: FormValues): FieldErrors {
  const errors: FieldErrors = {}
  const quantity = checkQuantity(v.quantity)
  if (quantity) errors.quantity = quantity
  if (v.unit.trim() === '') errors.unit = '단위를 적어 주세요.'
  if (v.purchaseDate === '') errors.purchase_date = '구매일을 골라 주세요.'
  if (v.storage === null) errors.storage = '보관 방법을 골라 주세요.'
  return errors
}

// 규칙표에서 골라 등록 (4.1)
export function checkRuleForm(v: FormValues): FieldErrors {
  return checkCommon(v)
}

// 직접 등록 (4.2)
export function checkManualForm(v: FormValues): FieldErrors {
  const errors = checkCommon(v)
  if (v.name.trim() === '') errors.name = '이름을 적어 주세요.'
  if (v.expiryMode === 'date') {
    if (v.expiryDate === '') errors.expiry = '기한을 골라 주세요.'
  } else if (v.expiryDays.trim() === '') {
    errors.expiry = '며칠 뒤인지 적어 주세요.'
  } else if (!/^\d+$/.test(v.expiryDays.trim())) {
    errors.expiry = '며칠 뒤는 0 이상의 정수로 적어 주세요.'
  }
  return errors
}
