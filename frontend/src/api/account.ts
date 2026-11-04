// 계정 탈퇴(H1). 기준은 API-SPEC 2-7.
// 성공하면 204 이고, 계정 · 식품 · 모든 기기의 로그인이 한 묶음으로 지워진다. 화면은 로그인 화면으로 간다 (D-129).
// 개발 중 가짜 응답: VITE_USE_MOCK 이 켜져 있으면 서버에 보내지 않는다.
//   비밀번호가 wrong 으로 시작하면 "비밀번호가 맞지 않음", 그 밖은 성공
//   VITE_USE_MOCK=save-error  삭제 실패 (아무것도 지워지지 않음)
//   VITE_USE_MOCK=slow        2초 걸림 (버튼 잠금 확인용)
import { send } from './http'

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

export type WithdrawResult =
  | { status: 'ok' }
  | { status: 'wrong_password'; message?: string } // 비밀번호가 틀리거나 비었음. 탈퇴되지 않고 확인 창에 안내 (D-128)
  | { status: 'failed'; message?: string } // 삭제 실패 · 서버에 닿지 못함. 아무것도 지워지지 않았다

interface ApiErrorBody {
  reason?: string
  message?: string
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export async function withdraw(password: string): Promise<WithdrawResult> {
  if (MOCK_MODE) {
    if (MOCK_MODE === 'slow') await wait(2000)
    if (MOCK_MODE === 'save-error') return { status: 'failed' }
    return password.startsWith('wrong') ? { status: 'wrong_password' } : { status: 'ok' }
  }
  const res = await send('/api/account/withdraw', 'POST', { password })
  if (res?.ok) return { status: 'ok' }
  if (!res) return { status: 'failed' }
  const body = (await res.json().catch(() => null)) as ApiErrorBody | null
  const message = body?.message || undefined
  if (res.status === 422 && body?.reason === 'password_mismatch') return { status: 'wrong_password', message }
  return { status: 'failed', message }
}
