// 가입 화면의 미리 검사. 최종 판단은 API 가 한다 (D-010).
// 로그인에서는 검사하지 않는다. 맞지 않으면 API 가 login_failed 로 돌려준다 (API-SPEC B2, D-057).

export type AuthField = 'email' | 'password'
export type AuthErrors = Partial<Record<AuthField, string>>

// API-SPEC 3절의 정해진 문구
export const WEAK_PASSWORD = '비밀번호는 8자 이상이고 영문·숫자·특수문자를 모두 넣어 주세요.'
// invalid_email 문구는 "구현 단계에서 정함" (API-SPEC 3절). 사용자 확정 문구
export const INVALID_EMAIL = '이메일을 example@mail.com 처럼 적어 주세요.'

// @ 와 점이 있는 모양까지만 본다 (D-096)
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// 8자 이상, 영문·숫자·특수문자를 모두 포함 (D-047)
export function isStrongPassword(password: string): boolean {
  return (
    password.length >= 8 &&
    /[A-Za-z]/.test(password) &&
    /[0-9]/.test(password) &&
    /[^A-Za-z0-9]/.test(password)
  )
}

// 가입 입력 중 규칙마다 지켜졌는지 보여 주기 위한 목록 (D-184). 보여 주기만 하고 최종 판단은 API 가 한다
export function signupRules(email: string, password: string): { text: string; ok: boolean }[] {
  return [
    { text: '이메일은 @ 와 점이 있는 주소', ok: EMAIL_SHAPE.test(email.trim()) },
    { text: '비밀번호 8자 이상', ok: password.length >= 8 },
    { text: '영문 포함', ok: /[A-Za-z]/.test(password) },
    { text: '숫자 포함', ok: /[0-9]/.test(password) },
    { text: '특수문자 포함', ok: /[^A-Za-z0-9]/.test(password) },
  ]
}

export function checkSignup(email: string, password: string): AuthErrors {
  const errors: AuthErrors = {}
  if (!EMAIL_SHAPE.test(email.trim())) errors.email = INVALID_EMAIL
  if (!isStrongPassword(password)) errors.password = WEAK_PASSWORD
  return errors
}
