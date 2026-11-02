import { useRef, useState } from 'react'
import { login, signup } from '../api/auth'
import ErrorNotice from '../components/ErrorNotice'
import FormField from '../components/FormField'
import { checkSignup, type AuthErrors } from '../lib/authForm'
import '../components/Register.css'

interface Props {
  onLoggedIn: () => void // 로그인 · 가입 성공 → 홈 (D-081)
}

type Mode = 'login' | 'signup'

// 사용자 확정 문구 (OQ-03)
const FAILED: Record<Mode, string> = {
  login: '로그인하지 못했어요. 잠시 뒤에 다시 시도해 주세요.',
  signup: '가입하지 못했어요. 잠시 뒤에 다시 시도해 주세요.',
}

// 로그인 화면 (US-012, SCREEN-SPEC 3절). '새 계정 만들기'를 누르면 가입 입력으로 바뀐다.
// 아래 탭이 없다 (D-080). 비밀번호 찾기 · 소셜 로그인 · 이메일 인증은 없다 (D-048 ~ D-051).
export default function LoginPage({ onLoggedIn }: Props) {
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<AuthErrors>({})
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const lock = useRef(false) // 연타해도 요청은 한 번 (D-100)

  function switchMode(next: Mode) {
    setMode(next)
    setErrors({})
    setNotice(null)
  }

  async function submit() {
    if (lock.current) return
    setNotice(null)
    // 가입만 미리 검사한다. 로그인은 어느 쪽이 틀렸는지 알리지 않으므로 API 에 맡긴다 (D-057)
    const found = mode === 'signup' ? checkSignup(email, password) : {}
    setErrors(found)
    if (Object.keys(found).length > 0) return

    lock.current = true
    setBusy(true)
    const res = mode === 'signup' ? await signup(email.trim(), password) : await login(email.trim(), password)
    lock.current = false
    if (res.status === 'ok') {
      onLoggedIn()
      return
    }
    setBusy(false) // 입력값은 그대로 둔다
    if (res.status === 'invalid') setErrors(res.fieldErrors)
    else setNotice(res.message ?? FAILED[mode])
  }

  const isSignup = mode === 'signup'

  return (
    <main className="register">
      <header className="register__header">
        <h1 className="register__title">{isSignup ? '새 계정 만들기' : '로그인'}</h1>
      </header>

      {notice && <ErrorNotice message={notice} />}

      <form
        className="register__form"
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          void submit()
        }}
      >
        <FormField label="이메일" id="email" error={errors.email}>
          <input
            id="email"
            className="input"
            type="email"
            inputMode="email"
            autoComplete="email"
            value={email}
            disabled={busy}
            aria-invalid={Boolean(errors.email)}
            aria-describedby={errors.email ? 'email-error' : undefined}
            onChange={(e) => {
              setEmail(e.target.value)
              setErrors((prev) => ({ ...prev, email: undefined }))
            }}
          />
        </FormField>

        <FormField label="비밀번호" id="password" error={errors.password}>
          <input
            id="password"
            className="input"
            type="password"
            autoComplete={isSignup ? 'new-password' : 'current-password'}
            value={password}
            disabled={busy}
            aria-invalid={Boolean(errors.password)}
            aria-describedby={errors.password ? 'password-error' : undefined}
            onChange={(e) => {
              setPassword(e.target.value)
              setErrors((prev) => ({ ...prev, password: undefined }))
            }}
          />
        </FormField>

        <button type="submit" className="button button--primary button--wide" disabled={busy}>
          {isSignup ? (busy ? '가입하는 중…' : '가입하기') : busy ? '로그인하는 중…' : '로그인'}
        </button>
      </form>

      <button
        type="button"
        className="button button--link"
        disabled={busy}
        onClick={() => switchMode(isSignup ? 'login' : 'signup')}
      >
        {isSignup ? '로그인으로 돌아가기' : '새 계정 만들기'}
      </button>
    </main>
  )
}
