import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { getFoods, LoadFoodsError } from './api/foods'
import { getRecords, LoadRecordsError } from './api/records'
import { setLoginRequiredListener } from './api/session'
import BottomTabs, { type Tab } from './components/BottomTabs'
import ConfirmDialog from './components/ConfirmDialog'
import ErrorNotice from './components/ErrorNotice'
import LogoutBar from './components/LogoutBar'
import FoodDetailPage from './pages/FoodDetailPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RecommendPage from './pages/RecommendPage'
import RecordsPage from './pages/RecordsPage'
import RegisterPage from './pages/RegisterPage'
import SettingsPage from './pages/SettingsPage'
import type { FoodListResponse } from './types/food'
import type { RecordsData } from './types/records'

// 화면 전환은 상태값으로 한다. 상세에서 새로고침하면 홈으로 돌아온다.
// 등록 · 상세는 하위 화면이라 어느 탭에서 왔는지(from)를 기억해 뒤로 가면 그 화면으로 간다 (D-085).
type Screen =
  | { name: 'login' }
  | { name: 'home'; initial?: FoodListResponse }
  | { name: 'records'; initial?: RecordsData }
  | { name: 'recommend' }
  | { name: 'settings' }
  | { name: 'register'; today: string; from: Tab }
  | { name: 'detail'; id: string; from: Tab }

function screenOf(tab: Tab): Screen {
  if (tab === 'records') return { name: 'records' }
  if (tab === 'recommend') return { name: 'recommend' }
  if (tab === 'settings') return { name: 'settings' }
  return { name: 'home' }
}

// 사용자 확정 문구 (OQ-03)
const LEAVE_MESSAGE = '입력한 내용이 사라져요. 이동할까요?'
const RECORDS_LOAD_FAILED = '기록을 불러오지 못했어요. 잠시 뒤에 다시 시도해 주세요.'

// 불러오기 실패의 API 문구 (없으면 undefined → 화면 기본 문구)
function apiMessageOf(e: unknown): string | undefined {
  return e instanceof LoadFoodsError || e instanceof LoadRecordsError ? e.apiMessage : undefined
}

function App() {
  // 앱을 켜면 홈 목록을 불러 보고, 로그인이 필요하면(401 login_required) 로그인 화면으로 간다 (API-SPEC 2-1)
  const [screen, setScreen] = useState<Screen>({ name: 'home' })
  const [tabError, setTabError] = useState<{ message?: string } | null>(null)
  const [tabBusy, setTabBusy] = useState(false)
  const [leavingTo, setLeavingTo] = useState<Tab | null>(null) // 입력 중 이동 확인 창이 열려 있으면 갈 탭
  const tabLock = useRef(false)
  const dirty = useRef(false) // 지금 화면(식품 등록 · 상세)에 입력한 것이 있는지 (D-083)
  const setDirty = useCallback((d: boolean) => {
    dirty.current = d
  }, [])

  function go(next: Screen) {
    setTabError(null)
    dirty.current = false
    setScreen(next)
  }

  // 어느 화면이든 로그인이 끝났으면(30분 만료 등) 로그인 화면으로. 입력 중이던 내용은 사라진다 (D-055)
  useEffect(() => {
    setLoginRequiredListener(() => {
      setTabError(null)
      setLeavingTo(null)
      dirty.current = false
      setScreen({ name: 'login' })
    })
    return () => setLoginRequiredListener(null)
  }, [])

  // 탭 화면(홈 · 기록 · 음식추천 · 설정)에서만 그 탭을 강조한다. 등록 · 상세에서는 강조하지 않는다 (사용자 결정)
  const activeTab: Tab | null =
    screen.name === 'home' || screen.name === 'records' || screen.name === 'recommend' || screen.name === 'settings'
      ? screen.name
      : null

  // 탭을 눌렀을 때. 식품 등록 · 수정 화면에 입력한 것이 있으면 먼저 확인 창을 띄운다.
  // 확인하면 이동하고 입력은 사라지며, 취소하면 그 화면에 남는다. 입력한 것이 없으면 바로 이동한다 (D-083, D-084)
  function pressTab(tab: Tab) {
    if (tab === activeTab) return // 지금 있는 탭을 다시 누르면 아무 일도 없다 (D-082)
    if (dirty.current) {
      setLeavingTo(tab)
      return
    }
    void selectTab(tab)
  }

  function confirmLeave() {
    const tab = leavingTo
    setLeavingTo(null)
    if (tab) void selectTab(tab)
  }

  // 다음 화면의 데이터를 먼저 불러온다. 실패하면 지금 화면에 그대로 남고 오류만 보인다.
  // 같은 탭을 다시 눌러 다시 시도할 수 있다 (D-086)
  async function loadThenGo(load: () => Promise<Screen>, failMessage?: string) {
    if (tabLock.current) return
    tabLock.current = true
    setTabBusy(true)
    try {
      go(await load())
    } catch (e) {
      setTabError({ message: apiMessageOf(e) ?? failMessage })
    } finally {
      tabLock.current = false
      setTabBusy(false)
    }
  }

  function selectTab(tab: Tab) {
    // 음식추천 · 설정은 처음 열 때 서버에 요청하지 않는다 (USER-WORKFLOW 7-9)
    if (tab === 'recommend' || tab === 'settings') {
      go(screenOf(tab))
      return Promise.resolve()
    }
    if (tab === 'records') {
      return loadThenGo(async () => ({ name: 'records', initial: await getRecords() }), RECORDS_LOAD_FAILED)
    }
    return loadThenGo(async () => ({ name: 'home', initial: await getFoods() }))
  }

  // 기록이 모두 비었을 때의 식품 등록 버튼 (D-071). 구매일 기본값(오늘)은 홈 목록이 주는 today 를 쓰므로 먼저 불러온다
  function addFoodFromRecords() {
    void loadThenGo(async () => ({ name: 'register', today: (await getFoods()).today, from: 'records' }))
  }

  if (screen.name === 'login') {
    return <LoginPage onLoggedIn={() => go({ name: 'home' })} />
  }

  let page
  if (screen.name === 'register') {
    page = (
      <RegisterPage
        today={screen.today}
        onBack={() => go(screenOf(screen.from))}
        onDone={() => go({ name: 'home' })} // 등록 성공 → 홈. 홈이 목록을 새로 불러온다
        onDirtyChange={setDirty}
      />
    )
  } else if (screen.name === 'detail') {
    page = (
      <FoodDetailPage
        id={screen.id}
        onBack={() => go(screenOf(screen.from))}
        onDone={() => go({ name: 'home' })} // 저장 · 처리 · 삭제 성공 → 홈 (D-020). 홈이 목록을 새로 불러온다
        onDirtyChange={setDirty}
      />
    )
  } else if (screen.name === 'records') {
    page = <RecordsPage initial={screen.initial} onAddFood={addFoodFromRecords} />
  } else if (screen.name === 'recommend') {
    page = <RecommendPage />
  } else if (screen.name === 'settings') {
    page = <SettingsPage />
  } else {
    page = (
      <HomePage
        initial={screen.initial}
        onAddFood={(today) => go({ name: 'register', today, from: 'home' })}
        onSelectFood={(id) => go({ name: 'detail', id, from: 'home' })}
      />
    )
  }

  return (
    <div className="app--tabs">
      <LogoutBar onLoggedOut={() => go({ name: 'login' })} />
      {tabError && (
        <div className="app__notice">
          <ErrorNotice message={tabError.message} />
        </div>
      )}
      {page}
      <BottomTabs active={activeTab} disabled={tabBusy} onSelect={pressTab} />
      <ConfirmDialog
        open={leavingTo !== null}
        message={LEAVE_MESSAGE}
        confirmLabel="이동"
        onConfirm={confirmLeave}
        onCancel={() => setLeavingTo(null)}
      />
    </div>
  )
}

export default App
