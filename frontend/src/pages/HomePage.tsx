import { useRef, useState } from 'react'
import { logout } from '../api/auth'
import ErrorNotice from '../components/ErrorNotice'
import { useFoods } from '../hooks/useFoods'
import type { FoodListResponse } from '../types/food'
import Home from './Home'

interface Props {
  initial?: FoodListResponse // 탭을 눌러 올 때 이미 불러온 목록 (D-086)
  onSelectFood: (id: string) => void // 달력 막대나 목록의 식품을 누르면 상세 화면으로
  onAddFood: (today: string) => void // 등록 화면으로. 구매일 기본값용으로 API 가 준 오늘 날짜를 함께 넘긴다
  onLoggedOut: () => void // 로그아웃 → 로그인 화면 (D-060)
}

// 사용자 확정 문구 (OQ-03)
const LOGOUT_FAILED = '로그아웃하지 못했어요. 잠시 뒤에 다시 시도해 주세요.'

// 홈 화면: 목록을 불러와 Home 에 넘긴다. 오른쪽 위에 로그아웃 버튼 (사용자 결정).
export default function HomePage({ initial, onAddFood, onSelectFood, onLoggedOut }: Props) {
  const { result, reload } = useFoods(initial)
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<string | null>(null)
  const lock = useRef(false) // 연타해도 요청은 한 번

  async function runLogout() {
    if (lock.current) return
    lock.current = true
    setLoggingOut(true)
    setLogoutError(null)
    const res = await logout()
    lock.current = false
    if (res.status === 'ok') {
      onLoggedOut() // 이 기기만 로그아웃된다. 다른 기기는 그대로 (D-054)
      return
    }
    setLoggingOut(false)
    setLogoutError((res.status === 'failed' && res.message) || LOGOUT_FAILED)
  }

  return (
    <>
      <div className="home__top">
        <button type="button" className="home__logout" disabled={loggingOut} onClick={() => void runLogout()}>
          {loggingOut ? '로그아웃하는 중…' : '로그아웃'}
        </button>
      </div>
      {logoutError && (
        <div className="home__top-notice">
          <ErrorNotice message={logoutError} />
        </div>
      )}
      <Home
        result={result}
        onRetry={reload}
        onSelectFood={onSelectFood}
        onAddFood={() => {
          if (result.status === 'ready') onAddFood(result.data.today) // 등록 버튼은 목록을 불러온 뒤에만 보인다
        }}
      />
    </>
  )
}
