import { useRef, useState } from 'react'
import { logout } from '../api/auth'
import { AppIcon } from './AuthIcons'
import ErrorNotice from './ErrorNotice'
import './LogoutBar.css'

interface Props {
  onLoggedOut: () => void // 로그아웃 → 로그인 화면 (D-060)
  onLogoClick?: () => void // 아이콘과 "냉장고앱"을 눌렀을 때 (홈으로 가기)
  showLogo?: boolean // 참이면 맨 위 왼쪽에 앱 아이콘과 "냉장고앱"을 보인다 (홈 · 기록 · 뭐 먹지? · 설정 탭 화면)
}

// 사용자 확정 문구 (OQ-03)
const LOGOUT_FAILED = '로그아웃하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'

// 로그아웃 버튼: 로그인 화면을 뺀 모든 화면의 맨 위 오른쪽 (D-130, SCREEN-SPEC 13.1 의 13번)
export default function LogoutBar({ onLoggedOut, showLogo = false, onLogoClick }: Props) {
  const [loggingOut, setLoggingOut] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const lock = useRef(false) // 연타해도 요청은 한 번

  async function run() {
    if (lock.current) return
    lock.current = true
    setLoggingOut(true)
    setError(null)
    const res = await logout()
    lock.current = false
    if (res.status === 'ok') {
      onLoggedOut() // 이 기기만 로그아웃된다. 다른 기기는 그대로 (D-054)
      return
    }
    setLoggingOut(false)
    setError((res.status === 'failed' && res.message) || LOGOUT_FAILED)
  }

  return (
    <>
      <div className={showLogo ? 'logout-bar logout-bar--logo' : 'logout-bar'}>
        {showLogo && (
          <button type="button" className="logout-bar__logo" aria-label="냉장고앱 홈으로" onClick={onLogoClick}>
            <AppIcon className="logout-bar__logo-icon" />
            냉장고앱
          </button>
        )}
        <button type="button" className="logout-bar__button" disabled={loggingOut} onClick={() => void run()}>
          <svg className="logout-bar__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
            <path d="M9 4H6.5A1.5 1.5 0 0 0 5 5.5v13A1.5 1.5 0 0 0 6.5 20H9" />
            <path d="M14 8l4 4-4 4M18 12H9.5" />
          </svg>
          {loggingOut ? '로그아웃 중…' : '로그아웃'}
        </button>
      </div>
      {error && (
        <div className="logout-bar__notice">
          <ErrorNotice message={error} />
        </div>
      )}
    </>
  )
}
