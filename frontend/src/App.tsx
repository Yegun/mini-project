import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import { getFoods, LoadFoodsError } from './api/foods'
import { getRecords, LoadRecordsError } from './api/records'
import { setLoginRequiredListener } from './api/session'
import BottomTabs, { type Tab } from './components/BottomTabs'
import ConfirmDialog from './components/ConfirmDialog'
import ErrorNotice from './components/ErrorNotice'
import FullCalendar from './components/FullCalendar'
import Guide from './components/Guide'
import LogoutBar from './components/LogoutBar'
import { finishGuide, forgetAccount, markLoggedIn, markLoggedOut, markSignedUp, shouldShowGuide } from './lib/guide'
import FoodDetailPage from './pages/FoodDetailPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RecommendPage from './pages/RecommendPage'
import RecordsPage from './pages/RecordsPage'
import RegisterPage from './pages/RegisterPage'
import SettingsPage from './pages/SettingsPage'
import type { CalendarView } from './types/calendar'
import { INITIAL_CALENDAR_VIEW } from './types/calendar'
import type { FoodListResponse } from './types/food'
import type { RecordsData } from './types/records'

// 화면 전환은 상태값으로 한다. 상세에서 새로고침하면 홈으로 돌아온다.
// 등록 · 상세는 하위 화면이라 어느 탭에서 왔는지(from)를 기억해 뒤로 가면 그 화면으로 간다 (D-085).
type Screen =
  | { name: 'login' }
  | { name: 'guide'; again: boolean } // 사용 설명서. 아래 탭과 로그아웃 버튼이 없는 전체 화면. again: 설정에서 다시 보는 중 (D-199)
  | { name: 'home'; initial?: FoodListResponse }
  | { name: 'records'; initial?: RecordsData }
  | { name: 'recommend' }
  | { name: 'settings' }
  | { name: 'calendar'; initial: FoodListResponse; view: CalendarView } // 전체 달력 (홈의 연 · 월 옆 >)
  | { name: 'register'; today: string; from: Tab }
  | { name: 'detail'; id: string; from: Tab; back?: Screen } // back: 뒤로 가면 돌아갈 화면(전체 달력은 보던 모습 그대로, D-150)

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
  // 가입한 뒤 설명서를 닫지 않고 나갔다 돌아온 기기에서는, 로그인이 살아 있는지 확인될 때까지 화면을 비워 두었다가 설명서를 보인다 (D-206).
  // 로그인이 끝났으면(401) 아래 로그인 필요 처리가 로그인 화면으로 보낸다
  const [checkingGuide, setCheckingGuide] = useState(() => shouldShowGuide())
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

  // 앱을 켰을 때 이 기기에 설명서를 보여 줄 차례가 남아 있으면, 홈 목록을 한 번 불러 로그인이 살아 있는지 보고 설명서를 연다 (D-206)
  useEffect(() => {
    if (!checkingGuide) return
    let alive = true
    getFoods()
      .then(() => {
        if (alive) setScreen({ name: 'guide', again: false })
      })
      .catch(() => {
        // 로그인이 끝났으면 위 리스너가 로그인 화면으로 보내고, 그 밖의 실패는 홈이 보인다
      })
      .finally(() => {
        if (alive) setCheckingGuide(false)
      })
    return () => {
      alive = false
    }
  }, [checkingGuide])

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

  // 기록이 모두 비었을 때(D-071)와 추천할 식품이 없을 때(OQ-05)의 식품 등록 버튼.
  // 구매일 기본값(오늘)은 홈 목록이 주는 today 를 쓰므로 먼저 불러온다
  function addFoodFrom(from: Tab) {
    void loadThenGo(async () => ({ name: 'register', today: (await getFoods()).today, from }))
  }

  // 설명서를 볼 차례인지 확인하는 동안(로그인이 살아 있는지 보는 짧은 순간)은 홈이 깜빡이지 않게 비워 둔다
  if (checkingGuide) return null

  if (screen.name === 'login') {
    return (
      <LoginPage
        onLoggedIn={({ email, signup }) => {
          if (signup) {
            // 새 계정을 만든 직후: 설명서를 보여 줄 차례를 이 기기에 남기고 설명서를 먼저 보인다 (D-199, D-206)
            markSignedUp(email)
            go({ name: 'guide', again: false })
            return
          }
          // 이미 있는 계정: 설명서 없이 홈으로. 단 이 기기에 이 계정의 '차례'가 남아 있으면(가입 직후 설명서를 닫지 않고 나간 경우) 설명서가 먼저다
          markLoggedIn(email)
          go(shouldShowGuide() ? { name: 'guide', again: false } : { name: 'home' })
        }}
      />
    )
  }

  // 사용 설명서: 아래 탭 · 로그아웃 버튼이 없는 전체 화면 (SCREEN-SPEC 17.2).
  // 가입 직후에는 닫으면(끝까지 봄 · 건너뜀) 차례를 지우고 홈으로, 설정에서 다시 볼 때는 차례를 건드리지 않고 설정으로 돌아간다 (D-206)
  if (screen.name === 'guide') {
    const again = screen.again
    return (
      <Guide
        again={again}
        onClose={() => {
          if (!again) finishGuide()
          go(again ? { name: 'settings' } : { name: 'home' })
        }}
      />
    )
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
        onBack={() => go(screen.back ?? screenOf(screen.from))}
        onDone={() => go({ name: 'home' })} // 저장 · 처리 · 삭제 성공 → 홈 (D-020). 홈이 목록을 새로 불러온다
        onDirtyChange={setDirty}
      />
    )
  } else if (screen.name === 'calendar') {
    page = (
      <FullCalendar
        today={screen.initial.today}
        foods={screen.initial.items}
        view={screen.view}
        onClose={() => go({ name: 'home' })} // 닫기(X) → 홈 (13.2 의 2번)
        onSelectFood={(id, view) =>
          go({ name: 'detail', id, from: 'home', back: { name: 'calendar', initial: screen.initial, view } })
        }
      />
    )
  } else if (screen.name === 'records') {
    page = <RecordsPage initial={screen.initial} onAddFood={() => addFoodFrom('records')} />
  } else if (screen.name === 'recommend') {
    page = <RecommendPage onAddFood={() => addFoodFrom('recommend')} onDirtyChange={setDirty} />
  } else if (screen.name === 'settings') {
    page = (
      <SettingsPage
        onWithdrawn={() => {
          forgetAccount() // 탈퇴하면 이 기기에 남은 계정 흔적(설명서 차례 포함)도 지운다
          go({ name: 'login' })
        }}
        onOpenGuide={() => go({ name: 'guide', again: true })}
      />
    )
  } else {
    page = (
      <HomePage
        initial={screen.initial}
        onAddFood={(today) => go({ name: 'register', today, from: 'home' })}
        onSelectFood={(id) => go({ name: 'detail', id, from: 'home' })}
        onOpenCalendar={(data) => go({ name: 'calendar', initial: data, view: INITIAL_CALENDAR_VIEW })}
      />
    )
  }

  return (
    <div className="app--tabs">
      {/* 전체 달력은 홈에서 여는 달력이라 로그아웃 버튼을 따로 두지 않는다 (13.2 의 2번) */}
      {screen.name !== 'calendar' && (
        <LogoutBar
          showLogo={activeTab !== null} // 앱 아이콘과 이름은 네 탭 화면(홈 · 기록 · 뭐 먹지? · 설정)에서만 보인다
          onLogoClick={() => pressTab('home')} // 누르면 홈으로 (홈에서는 아무 일도 없다)
          onLoggedOut={() => {
            markLoggedOut() // 이 기기에 지금 로그인한 계정이 없다
            go({ name: 'login' })
          }}
        />
      )}
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
