// 한꺼번에 등록(F2, POST /foods/bulk). 기준은 API-SPEC 2-5.
// 한 줄이라도 실패하면 전부 취소된다 (D-110). 줄 오류의 field 는 `items.N.칸이름` 이고 N 은 보낸 목록에서의 위치(0부터)다.
// 개발 중 가짜 응답: VITE_USE_MOCK 이 켜져 있으면 서버에 보내지 않는다. 성공하면 홈 mock 목록에 쌓는다.
//   (기본)                       전부 성공
//   VITE_USE_MOCK=save-error     저장 실패 (전부 취소)
//   VITE_USE_MOCK=save-invalid   첫 줄 수량 오류 (칸 옆 안내)
//   VITE_USE_MOCK=analysis-expired  읽기 결과가 30분 지남
//   VITE_USE_MOCK=slow           2초 걸림 (버튼 잠금 확인용)
import type { BulkInput, BulkResult } from '../types/bulk'
import type { FieldName } from '../types/register'
import { send } from './http'
import { foodsMock } from '../mocks/foodsMock'
import { addMockFood } from '../mocks/createdFoods'

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

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

interface ApiErrorBody {
  field?: string | null
  reason?: string
  message?: string
}

export async function registerBulk(input: BulkInput): Promise<BulkResult> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'slow') await wait(2000)
    if (MOCK_MODE === 'save-error') return { status: 'failed' }
    if (MOCK_MODE === 'analysis-expired') return { status: 'expired', message: '사진을 다시 올려 주세요.' }
    if (MOCK_MODE === 'save-invalid') {
      return { status: 'invalid', index: 0, field: 'quantity', message: '수량을 다시 확인해 주세요. (가짜 오류 응답)' }
    }
    for (const item of input.items) {
      addMockFood(
        {
          name: item.name,
          storage: item.storage,
          quantity: item.quantity,
          unit: item.unit,
          purchase_date: item.purchase_date,
          ...(item.expiry_date ? { expiry_date: item.expiry_date } : {}),
        },
        foodsMock.today,
      )
    }
    return { status: 'ok' }
  }

  const res = await send('/api/foods/bulk', 'POST', input)
  if (!res) return { status: 'failed' }
  if (res.ok) return { status: 'ok' }
  const body = (await res.json().catch(() => null)) as ApiErrorBody | null
  const message = body?.message || undefined
  if (body?.reason === 'analysis_expired') return { status: 'expired', message }
  const match = /^items\.(\d+)\.(\w+)$/.exec(body?.field ?? '')
  if (res.status === 422 && match) {
    return { status: 'invalid', index: Number(match[1]), field: FIELD_OF[match[2]] ?? null, message }
  }
  return { status: 'failed', message }
}
