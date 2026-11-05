import { useRef, useState } from 'react'
import { login, signup } from '../api/auth'
import ErrorNotice from '../components/ErrorNotice'
import { AuthArt, EyeIcon, LockIcon, MailIcon } from '../components/AuthIcons'
import FormField from '../components/FormField'
import { checkSignup, signupRules, type AuthErrors } from '../lib/authForm'
import '../components/Register.css'
import '../components/Auth.css'

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
  const [showPassword, setShowPassword] = useState(false) // 비밀번호 보기 (눈 버튼)
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
    <main className="register auth">
      {/* 위쪽 띠: 앱 이름 · 소개 문장 · 냉장고 그림. 제목(h1)은 예전과 같은 "로그인" / "새 계정 만들기"다.
          로그인 화면에만 앱을 소개하는 아주 짧은 문장 한 줄이 있고, 가입 화면에는 더하지 않는다 (US-045, D-198) */}
      <header className="auth__hero">
        <div className="auth__hero-text">
          <p className="auth__brand">냉장고 관리</p>
          <h1 className="auth__title">{isSignup ? '새 계정 만들기' : '로그인'}</h1>
          <p className={isSignup ? 'auth__sub' : 'auth__sub auth__sub--tagline'}>{isSignup ? '계정을 만들고 시작해 보세요' : (
              <>
                <span className="auth__em auth__em--cool">냉장고</span> 앱과 함께{' '}
                <span className="auth__em auth__em--fresh">신선식품</span>을 관리해 보세요
              </>
            )}</p>
        </div>
        <AuthArt className="auth__art" />
      </header>

      {notice && <ErrorNotice message={notice} />}

      <form
        className="register__form auth__form"
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          void submit()
        }}
      >
        <FormField label="이메일" id="email" error={errors.email}>
          <span className="auth__input">
            <MailIcon className="auth__input-icon" />
            <input
              id="email"
              className="input"
              type="email"
              placeholder={isSignup ? 'abc@mail.com 처럼' : '이메일'}
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
          </span>
        </FormField>

        <FormField label="비밀번호" id="password" error={errors.password}>
          <span className="auth__input">
            <LockIcon className="auth__input-icon" />
            <input
              id="password"
              className="input auth__input-password"
              type={showPassword ? 'text' : 'password'}
              placeholder={isSignup ? '8자 이상, 영문 · 숫자 · 특수문자 모두 포함' : '비밀번호'}
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
            {/* 비밀번호 보기 · 숨기기: 입력값에는 영향이 없고 글자가 보이는지만 바뀐다 */}
            <button
              type="button"
              className="auth__eye"
              aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
              aria-pressed={showPassword}
              disabled={busy}
              onClick={() => setShowPassword((v) => !v)}
            >
              <EyeIcon className="auth__eye-icon" off={showPassword} />
            </button>
          </span>
        </FormField>

        {isSignup && (
          <ul className="rules" aria-label="가입 규칙">
            {signupRules(email, password).map((rule) => (
              <li key={rule.text} className={rule.ok ? 'rules__item rules__item--ok' : 'rules__item'}>
                <span aria-hidden="true">{rule.ok ? '✓' : '○'}</span> {rule.text}
                <span className="visually-hidden">{rule.ok ? ' (지켜짐)' : ' (아직)'}</span>
              </li>
            ))}
          </ul>
        )}

        <button type="submit" className="button button--primary button--wide auth__submit" disabled={busy}>
          {isSignup ? (busy ? '가입하는 중…' : '가입하기') : busy ? '로그인하는 중…' : '로그인'}
        </button>
      </form>

      <button
        type="button"
        className="button button--wide auth__switch"
        disabled={busy}
        onClick={() => switchMode(isSignup ? 'login' : 'signup')}
      >
        {isSignup ? '로그인으로 돌아가기' : '새 계정 만들기'}
      </button>
    </main>
  )
}
