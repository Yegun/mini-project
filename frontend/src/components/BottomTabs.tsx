import type { ReactNode } from 'react'
import './BottomTabs.css'

export type Tab = 'home' | 'records' | 'recommend' | 'settings'

interface Props {
  active: Tab | null // 지금 있는 탭. 식품 등록 · 상세 같은 하위 화면에서는 강조하지 않는다 (사용자 결정)
  disabled?: boolean // 다음 화면을 불러오는 동안
  onSelect: (tab: Tab) => void
}

// 탭 그림: 가는 선으로 그린 작은 그림. 색은 글자 색(currentColor)을 따라가서 밝은색 · 어두운색 · 포인트 색에 맞게 바뀐다.
const ICONS: Record<Tab, ReactNode> = {
  home: (
    <>
      <rect x="5.5" y="2.8" width="13" height="18.4" rx="2.4" />
      <path d="M5.5 9.5h13" />
      <path d="M9 5.8v1.4M9 12.2v2.8" />
    </>
  ), // 냉장고 (위 냉동칸 · 아래 냉장칸, 손잡이 둘)
  records: (
    <>
      <path d="M4 12a8 8 0 1 0 2.4-5.7" />
      <path d="M4 4.5v3.8h3.8" />
      <path d="M12 8v4.2l2.8 1.8" />
    </>
  ), // 되감기 시계
  recommend: (
    <>
      <path d="M7 3v7a2 2 0 0 0 2 2v9" />
      <path d="M4.5 3v6.2A2.5 2.5 0 0 0 7 11.7M9.5 3v6.2A2.5 2.5 0 0 1 7 11.7" />
      <path d="M17 21V3c-2.2 1.2-3.5 3.8-3.5 7 0 1.6.9 2.5 2 2.8H17" />
    </>
  ), // 포크와 나이프
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7" />
      <circle cx="12" cy="12" r="6.2" />
    </>
  ), // 톱니바퀴
}

const TABS: { tab: Tab; label: string }[] = [
  { tab: 'home', label: '내 냉장고' },
  { tab: 'records', label: '기록' },
  { tab: 'recommend', label: '뭐 먹지?' },
  { tab: 'settings', label: '설정' },
]

// 화면 맨 아래 탭 (US-016). 로그인 화면을 뺀 모든 화면에서 보인다 (D-080). 홈 · 기록 · 음식추천 · 설정 네 개 (D-124).
// 탭마다 아이콘과 글자가 함께 보인다 (SCREEN-SPEC 10.1).
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
          <svg
            className="tabs__icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {ICONS[tab]}
          </svg>
          <span className="tabs__label">{label}</span>
        </button>
      ))}
    </nav>
  )
}
