import './BottomTabs.css'

export type Tab = 'home' | 'records' | 'recommend' | 'settings'

interface Props {
  active: Tab | null // 지금 있는 탭. 식품 등록 · 상세 같은 하위 화면에서는 강조하지 않는다 (사용자 결정)
  disabled?: boolean // 다음 화면을 불러오는 동안
  onSelect: (tab: Tab) => void
}

const TABS: { tab: Tab; label: string }[] = [
  { tab: 'home', label: '홈' },
  { tab: 'records', label: '기록' },
  { tab: 'recommend', label: '음식추천' },
  { tab: 'settings', label: '설정' },
]

// 화면 맨 아래 탭 (US-016). 로그인 화면을 뺀 모든 화면에서 보인다 (D-080). 홈 · 기록 · 음식추천 · 설정 네 개 (D-124).
export default function BottomTabs({ active, disabled, onSelect }: Props) {
  return (
    <nav className="tabs" aria-label="화면 이동">
      {TABS.map(({ tab, label }) => (
        <button
          key={tab}
          type="button"
          className={active === tab ? 'tabs__item tabs__item--active' : 'tabs__item'}
          aria-current={active === tab ? 'page' : undefined}
          disabled={disabled}
          onClick={() => onSelect(tab)}
        >
          {label}
        </button>
      ))}
    </nav>
  )
}
