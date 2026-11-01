// 백엔드 오류 응답을 화면이 쓰는 결과로 바꾼다.
// 백엔드 오류 모양: { field, reason, message }. 입력 오류 422, 기한 다시 적기 409, 그 밖은 실패로 본다.
import type { SaveResult } from '../types/foodDetail'
import type { FieldErrors, FieldName } from '../types/register'

export type FailureResult = Exclude<SaveResult, { status: 'ok' }>

// 백엔드 칸 이름 -> 화면 입력칸 이름. 기한만 이름이 다르다.
const FIELD_OF: Record<string, FieldName | undefined> = {
  name: 'name',
  storage: 'storage',
  quantity: 'quantity',
  unit: 'unit',
  purchase_date: 'purchase_date',
  expiry_date: 'expiry',
}

interface ApiErrorBody {
  field?: string | null
  reason?: string
  message?: string
}

// 실패한 응답(또는 API 에 닿지 못해 null)을 읽는다.
export async function readFailure(res: Response | null): Promise<FailureResult> {
  if (!res) return { status: 'failed' }
  const body = (await res.json().catch(() => null)) as ApiErrorBody | null
  if (res.status === 409 && body?.reason === 'expiry_required') return { status: 'need_expiry' }
  if (res.status === 422) {
    const field = body?.field ? FIELD_OF[body.field] : undefined
    if (field && body?.message) {
      const fieldErrors: FieldErrors = { [field]: body.message }
      return { status: 'invalid', fieldErrors }
    }
  }
  return { status: 'failed' } // 칸을 알 수 없는 오류 · 없는 식품 · 서버 오류
}
