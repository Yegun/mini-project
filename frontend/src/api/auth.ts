// 가입(B1), 로그인(B2), 로그아웃(B3). 기준은 API-SPEC 2-1.
// 성공하면 서버가 로그인 쿠키(session)를 심는다. 화면은 쿠키를 읽거나 만들지 않는다.
// 개발 중 가짜 응답: VITE_USE_MOCK 이 켜져 있으면 서버에 보내지 않는다.
//   가입: 이메일이 taken@example.com 이면 "이미 가입된 이메일", 그 밖은 성공
//   로그인: 비밀번호가 wrong 으로 시작하면 "이메일 또는 비밀번호가 맞지 않아요", 그 밖은 성공
//   로그아웃: 늘 성공
//   VITE_USE_MOCK=save-error  가입 · 로그인 · 로그아웃 모두 서버 오류
//   VITE_USE_MOCK=slow        2초 걸림 (버튼 잠금 확인용)
import type { AuthErrors, AuthField } from '../lib/authForm'
import { send } from './http'

const MOCK_MODE = import.meta.env.VITE_USE_MOCK

export type AuthResult =
  | { status: 'ok' }
  | { status: 'invalid'; fieldErrors: AuthErrors } // 칸 옆 안내 (이메일 모양 · 비밀번호 규칙 · 이미 가입된 이메일)
  | { status: 'failed'; message?: string } // 화면 위 오류 알림 (로그인 실패 · 서버 오류). message 는 API 문구

interface ApiErrorBody {
  field?: string | null
  message?: string
}

const AUTH_FIELDS: readonly AuthField[] = ['email', 'password']

async function readAuthFailure(res: Response | null): Promise<AuthResult> {
  if (!res) return { status: 'failed' }
  const body = (await res.json().catch(() => null)) as ApiErrorBody | null
  const message = body?.message || undefined
  const field = AUTH_FIELDS.find((f) => f === body?.field)
  // invalid_email · weak_password(422), email_taken(409) 은 칸 옆에. login_failed(401) 는 칸을 가리지 않는다 (D-057)
  if (field && message && (res.status === 422 || res.status === 409)) {
    return { status: 'invalid', fieldErrors: { [field]: message } }
  }
  return { status: 'failed', message }
}

async function postAuth(path: string, body?: object): Promise<AuthResult> {
  const res = await send(path, 'POST', body)
  if (res?.ok) return { status: 'ok' }
  return readAuthFailure(res)
}

async function mockAuth(result: AuthResult): Promise<AuthResult> {
  if (MOCK_MODE === 'save-error') return { status: 'failed' }
  if (MOCK_MODE === 'slow') await new Promise((resolve) => setTimeout(resolve, 2000))
  return result
}

export function signup(email: string, password: string): Promise<AuthResult> {
  if (MOCK_MODE) {
    return mockAuth(
      email.trim().toLowerCase() === 'taken@example.com'
        ? { status: 'invalid', fieldErrors: { email: '이미 가입된 이메일이에요.' } }
        : { status: 'ok' },
    )
  }
  return postAuth('/api/auth/signup', { email, password })
}

export function login(email: string, password: string): Promise<AuthResult> {
  if (MOCK_MODE) {
    return mockAuth(
      password.startsWith('wrong')
        ? { status: 'failed', message: '이메일 또는 비밀번호가 맞지 않아요.' }
        : { status: 'ok' },
    )
  }
  return postAuth('/api/auth/login', { email, password })
}

// 이미 로그인이 끝난 상태(401 login_required)여도 화면은 어차피 로그인 화면으로 가므로 성공으로 본다 (API-SPEC B3)
export async function logout(): Promise<AuthResult> {
  if (MOCK_MODE) return mockAuth({ status: 'ok' })
  const res = await send('/api/auth/logout', 'POST')
  if (res?.ok || res?.status === 401) return { status: 'ok' }
  return readAuthFailure(res)
}
