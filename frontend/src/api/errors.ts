// 백엔드 오류 응답을 화면이 쓰는 결과로 바꾼다.
// 백엔드 오류 모양: { field, reason, message } (API-SPEC 0-2). 입력 오류 422, 기한 다시 적기 409, 그 밖은 실패로 본다.
import type { SaveResult } from '../types/foodDetail'
import type { FieldErrors, FieldName } from '../types/register'

export type FailureResult = Exclude<SaveResult, { status: 'ok' }>

// 백엔드 칸 이름 -> 화면 입력칸 이름. 기한(날짜·며칠 뒤)은 한 칸에 안내한다.
const FIELD_OF: Record<string, FieldName | undefined> = {
  name: 'name',
  storage: 'storage',
  quantity: 'quantity',
  unit: 'unit',
  purchase_date: 'purchase_date',
  expiry_date: 'expiry',
  expiry_in_days: 'expiry',
}

const ALL_FIELDS: readonly FieldName[] = ['name', 'storage', 'quantity', 'unit', 'purchase_date', 'expiry']

interface ApiErrorBody {
  field?: string | null
  reason?: string
  message?: string
}

async function readBody(res: Response): Promise<ApiErrorBody | null> {
  return (await res.json().catch(() => null)) as ApiErrorBody | null
}

// 실패한 응답의 쉬운 문구. 없으면 undefined (화면이 기본 문구를 쓴다).
export async function readMessage(res: Response | null): Promise<string | undefined> {
  if (!res) return undefined
  return (await readBody(res))?.message || undefined
}

// 실패한 응답(또는 API 에 닿지 못해 null)을 읽는다.
// fields: 지금 화면에 안내를 붙일 수 있는 칸. 그 밖의 칸 오류는 화면 위 오류 알림으로 보인다.
export async function readFailure(
  res: Response | null,
  fields: readonly FieldName[] = ALL_FIELDS,
): Promise<FailureResult> {
  if (!res) return { status: 'failed' }
  const body = await readBody(res)
  if (res.status === 409 && body?.reason === 'expiry_required') return { status: 'need_expiry' }
  const message = body?.message || undefined
  if (res.status === 422) {
    const field = body?.field ? FIELD_OF[body.field] : undefined
    if (field && fields.includes(field) && message) {
      const fieldErrors: FieldErrors = { [field]: message }
      return { status: 'invalid', fieldErrors }
    }
  }
  return { status: 'failed', message } // 칸에 붙일 수 없는 오류 · 없는 식품 · 서버 오류
}
